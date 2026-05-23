from datetime import datetime, time, timedelta
import logging
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from django.db import IntegrityError
from django.utils import timezone

from auth_user.models import ScheduledPost, UserProfile
from nano_banana.models import NanoBananaImage

from .gemini_image import build_image_prompt, business_name_from_profile, enhance_image_prompt, generate_image, normalize_reference_list
from .planner import generate_blog_email_content, generate_blog_email_plan, generate_campaign_batch, generate_weekly_topics, normalize_blog_email_plan, normalize_campaign_item_plan, platform_caption, schedule_dates
from ..models import BlogEmailPlan, BrandSetting, BusinessProfile, CampaignWeek, GeneratedPost, GenerationJob, MediaAsset, Topic

logger = logging.getLogger(__name__)

PLATFORM_ALIASES = {
    'x': 'twitter',
}


def scheduling_preferences(plan):
    default = {
        'timezone': 'Asia/Dhaka',
        'default_schedule_time': '09:00',
        'smart_captions': {'enabled': True},
    }
    profile = UserProfile.objects.filter(user=plan.user, workspace=plan.workspace).first() if plan else None
    brand_voice = profile.brand_voice if profile and isinstance(profile.brand_voice, dict) else {}
    preferences = brand_voice.get('content_preferences') if isinstance(brand_voice.get('content_preferences'), dict) else {}
    smart_captions = preferences.get('smart_captions') if isinstance(preferences.get('smart_captions'), dict) else {}
    return {
        'timezone': preferences.get('timezone') or default['timezone'],
        'default_schedule_time': preferences.get('default_schedule_time') or default['default_schedule_time'],
        'smart_captions': {'enabled': bool(smart_captions.get('enabled', True))},
    }


def generated_post_approval_status(user, workspace):
    profile = UserProfile.objects.filter(user=user, workspace=workspace).first()
    if profile is None or profile.approval_toggle:
        return 'not_approved'
    return 'approved'


def default_schedule_time(plan):
    raw = scheduling_preferences(plan).get('default_schedule_time') or '09:00'
    try:
        hour, minute = [int(part) for part in str(raw).split(':', 1)]
    except (TypeError, ValueError):
        hour, minute = 9, 0
    return max(0, min(23, hour)), max(0, min(59, minute))


def calendar_datetime(day, plan=None):
    prefs = scheduling_preferences(plan)
    hour, minute = default_schedule_time(plan)
    value = datetime.combine(day, time(hour=hour, minute=minute))
    try:
        tz = ZoneInfo(prefs.get('timezone') or 'Asia/Dhaka')
    except Exception:
        tz = ZoneInfo('Asia/Dhaka')
    if timezone.is_naive(value):
        value = timezone.make_aware(value, tz)
    if value <= timezone.now():
        return timezone.now() + timedelta(minutes=5)
    return value


def smart_captions_enabled(plan):
    return bool(scheduling_preferences(plan).get('smart_captions', {}).get('enabled', True))


def make_meta(content_type, title, extra=None):
    data = {
        'content_type': content_type,
        'title': title,
        'approved_platforms': [],
    }
    if isinstance(extra, dict):
        data.update(extra)
    return data


def caption_payload(base_captions, meta):
    payload = dict(base_captions or {})
    payload['__meta'] = meta
    return payload


def generation_task_prefix(plan, week_number):
    return f'content_engine:{plan.id}:{week_number}:'


def cleanup_generated_week(plan, week_number):
    scheduled = ScheduledPost.objects.filter(task_id__startswith=generation_task_prefix(plan, week_number))
    nano_ids = list(scheduled.values_list('nano_banana_id', flat=True))
    scheduled.delete()
    if nano_ids:
        NanoBananaImage.objects.filter(id__in=nano_ids).delete()


def content_engine_task_id(plan, week_number, content_type, nano_id):
    return f'{generation_task_prefix(plan, week_number)}{content_type}:{nano_id}'


def limited_week_topics(plan, kind, week_number, limit):
    try:
        limit = max(0, int(limit or 0))
    except (TypeError, ValueError):
        limit = 0
    topics = list(plan.topics.filter(kind=kind, week_number=week_number).order_by('position', 'created_at'))
    if limit <= 0:
        return []
    return topics[:limit]


def persisted_topic_for_generation(plan, topic, content_type, title='', metadata=None):
    """Return a DB-backed Topic for GeneratedPost FK writes.

    Campaign prompt rows can be edited/regenerated independently from Topic rows.
    If a stale prompt/topic object leaks into generation, never let that FK block
    calendar item creation.
    """
    if topic and getattr(topic, 'pk', None):
        existing = Topic.objects.filter(pk=topic.pk, content_plan=plan).first()
        if existing:
            return existing
    if topic and isinstance(getattr(topic, 'metadata', None), dict):
        metadata = {**topic.metadata, **(metadata or {})}
    kind = 'blog' if content_type == 'blog' else 'social'
    title = title or getattr(topic, 'title', '') or 'Generated content'
    try:
        week_number = int(getattr(topic, 'week_number', None) or 1)
    except (TypeError, ValueError):
        week_number = 1
    try:
        position = int(getattr(topic, 'position', None) or 1)
    except (TypeError, ValueError):
        position = 1
    return Topic.objects.create(
        content_plan=plan,
        week_number=week_number,
        position=position,
        kind=kind,
        title=title,
        metadata=metadata or {'source': 'generation_repair'},
    )


def create_generated_post_safely(**kwargs):
    try:
        return GeneratedPost.objects.create(**kwargs)
    except IntegrityError as exc:
        if kwargs.get('topic') is None:
            raise
        logger.warning("GeneratedPost topic FK failed; saving without topic: %s", exc)
        kwargs['topic'] = None
        return GeneratedPost.objects.create(**kwargs)


def create_topics_from_campaign_week(plan, campaign_week, profile, brand):
    if not campaign_week:
        return []
    item_plan = normalize_campaign_item_plan(
        {'theme': campaign_week.theme, 'funnel_goal': campaign_week.funnel_goal, 'item_plan': campaign_week.item_plan},
        profile,
        brand,
        plan,
        max(0, int(campaign_week.week_number or 1) - 1),
    )
    prompts = item_plan.get('post_prompts') if isinstance(item_plan.get('post_prompts'), list) else []
    positions = {'social': 0, 'blog': 0}
    created = []
    for prompt in prompts:
        if not isinstance(prompt, dict):
            continue
        kind = str(prompt.get('type') or 'social').strip().lower()
        if kind == 'email':
            continue
        if kind != 'blog':
            kind = 'social'
        positions[kind] += 1
        reference_media = []
        if isinstance(prompt.get('reference_images'), list):
            reference_media.extend(prompt.get('reference_images'))
        if isinstance(prompt.get('reference_media'), list):
            reference_media.extend(prompt.get('reference_media'))
        if prompt.get('reference_image'):
            reference_media.insert(0, prompt.get('reference_image'))
        reference_media = normalize_reference_list(reference_media)
        created.append(Topic.objects.create(
            content_plan=plan,
            week_number=campaign_week.week_number,
            position=positions[kind],
            kind=kind,
            title=prompt.get('topic') or prompt.get('title') or item_plan.get('title') or campaign_week.theme,
            metadata={
                'source': 'campaign_planner',
                'campaign_week_id': str(campaign_week.id),
                'campaign_title': item_plan.get('title') or campaign_week.theme,
                'campaign_type': item_plan.get('campaign_type', ''),
                'prompt': prompt,
                'reference_media': reference_media,
                'primary_reference_url': reference_media[0] if reference_media else '',
                'reference_images': reference_media,
                'reference_lock': bool(reference_media),
                'source_prompt_id': str(prompt.get('id') or ''),
                'content_plan_id': str(plan.id),
                'theme': item_plan.get('theme', ''),
                'call_to_action': item_plan.get('call_to_action', ''),
                'audience': item_plan.get('audience', ''),
            },
        ))
    return created


def resolve_plan_context(plan):
    profile = plan.business_profile
    brand = plan.brand_setting
    updates = []
    if plan.workspace_id and (not profile or profile.workspace_id != plan.workspace_id):
        profile = BusinessProfile.objects.filter(user=plan.user, workspace=plan.workspace).first()
        if profile and plan.business_profile_id != profile.id:
            plan.business_profile = profile
            updates.append('business_profile')
    if plan.workspace_id and (not brand or brand.workspace_id != plan.workspace_id):
        brand = BrandSetting.objects.filter(user=plan.user, workspace=plan.workspace).first()
        if brand and plan.brand_setting_id != brand.id:
            plan.brand_setting = brand
            updates.append('brand_setting')
    if profile and brand and not brand.business_profile_id:
        brand.business_profile = profile
        brand.save(update_fields=['business_profile', 'updated_at'])
    if updates:
        plan.save(update_fields=[*updates, 'updated_at'])
    return profile, brand


def _validate_image_url(url, timeout=5):
    """Quick HEAD/GET check that an image URL is reachable. Returns True/False."""
    import requests as _requests
    try:
        resp = _requests.head(str(url), timeout=timeout, allow_redirects=True)
        if resp.status_code < 400:
            return True
        resp = _requests.get(str(url), timeout=timeout, stream=True)
        resp.raise_for_status()
        return True
    except Exception:
        return False


def inspiration_images_for_brand(user, workspace, brand, extra_references=None):
    try:
        from .intelligence import image_fingerprint
    except Exception:
        image_fingerprint = lambda value: normalize_image_url(value)
    prompt_refs = normalize_reference_list(extra_references or [])
    logo_refs = []
    if brand and isinstance(brand.logos, list):
        raw_logos = normalize_reference_list(brand.logos)
        # Validate logo URLs so broken/invalid logos are silently skipped
        for logo_url in raw_logos[:3]:
            if logo_url and _validate_image_url(logo_url):
                logo_refs.append(logo_url)
            else:
                logger.info("Skipping invalid/unreachable logo URL: %s", str(logo_url)[:200])

    images = []
    # Product/reference images always come FIRST — they are the hero subject
    images.extend(prompt_refs)
    # Logo comes after the first reference so Gemini sees product first
    for logo in logo_refs:
        if logo not in images:
            insert_at = 1 if prompt_refs else 0
            images.insert(insert_at, logo)
    uploaded_assets = MediaAsset.objects.filter(user=user, workspace=workspace, asset_type='image').exclude(source__in=['generated', 'gemini', 'local-placeholder']).order_by('-created_at')[:10]
    images.extend([asset.url for asset in uploaded_assets if asset.url])
    seen = set()
    unique = []
    for image in images:
        key = image_fingerprint(image)
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(image)
    return unique[:10]


def create_calendar_item(job, plan, topic, content_type, title, body, image_prompt, scheduled_day, hour=None, platform_outputs=None, meta_extra=None, extra_image_prompts=None, week_number=1):
    profile, brand = resolve_plan_context(plan)
    prompt_topic = topic or SimpleNamespace(title=title)
    safe_topic = persisted_topic_for_generation(plan, topic, content_type, title, metadata=meta_extra)
    base_prompt = build_image_prompt(profile, brand, prompt_topic, platform=(plan.platforms or ['instagram'])[0])
    if image_prompt and str(image_prompt).strip().startswith('Create one premium'):
        prompt = image_prompt
    elif image_prompt:
        prompt = f"{base_prompt}\n\nApproved content-specific visual direction:\n{image_prompt}"
    else:
        prompt = base_prompt
    prompt = enhance_image_prompt(prompt)
    topic_meta = topic.metadata if topic and isinstance(topic.metadata, dict) else {}
    prompt_data = topic_meta.get('prompt') if isinstance(topic_meta.get('prompt'), dict) else {}
    reference_images = []
    if prompt_data.get('reference_image'):
        reference_images.append(prompt_data.get('reference_image'))
    if isinstance(prompt_data.get('reference_images'), list):
        reference_images.extend(prompt_data.get('reference_images'))
    if isinstance(prompt_data.get('reference_media'), list):
        reference_images.extend(prompt_data.get('reference_media'))
    if topic_meta.get('primary_reference_url'):
        reference_images.insert(0, topic_meta.get('primary_reference_url'))
    if isinstance(topic_meta.get('reference_images'), list):
        reference_images.extend(topic_meta.get('reference_images'))
    if isinstance(topic_meta.get('reference_media'), list):
        reference_images.extend(topic_meta.get('reference_media'))
    reference_images = normalize_reference_list(reference_images)
    inspiration_images = inspiration_images_for_brand(job.user, job.workspace, brand, reference_images)
    reference_mode = 'required' if reference_images else 'optional'
    # Determine if logo is available and valid
    has_valid_logo = bool(brand and isinstance(brand.logos, list) and any(
        _validate_image_url(url) for url in normalize_reference_list(brand.logos)[:2]
    )) if brand else False
    if inspiration_images:
        # Build a product-specific anchoring block when reference images exist
        product_anchor = ''
        if reference_images:
            product_anchor = (
                '\n\nCRITICAL PRODUCT REFERENCE ANCHORING:\n'
                '- The FIRST supplied image is the PRIMARY PRODUCT REFERENCE. This is the exact product the post is about.\n'
                '- You MUST reproduce this exact product in the generated image: same product type, same shape/silhouette, same colors, same material/texture, same style.\n'
                '- Do NOT substitute with a different product, different clothing style, different color, or generic alternative.\n'
                '- The generated image must clearly feature THIS specific product as the main subject.\n'
                '- If the reference shows a dress, generate that exact dress. If it shows a suit, generate that exact suit. If it shows shoes, generate those exact shoes.\n'
                '- Match the product\'s color palette, design details, fabric texture, and overall aesthetic precisely.\n'
            )
        logo_rules = ''
        if has_valid_logo:
            logo_rules = (
                '\n- The brand logo image IS supplied. You MUST include it in the final image.\n'
                '- Preserve the supplied brand logo exactly: same shape, letters, proportions, and colors. Do not redraw or reinterpret the logo.\n'
                '- The logo must be visible as a clean corner lockup, product mark, packaging mark, signage, or natural UI element.\n'
                '- Do not invent, redraw, stylize, translate, recolor, crop, warp, or replace the logo.\n'
            )
        else:
            logo_rules = (
                '\n- No valid brand logo is available. Do NOT invent, create, or add any fake logo text or logo mark.\n'
                '- Only include the brand name as clean text overlay if the prompt requests text.\n'
            )
        prompt = (
            f"{prompt}{product_anchor}"
            f"\n\nReference image rules:\n"
            "- This is a text-plus-images Gemini image request: use the text prompt and every supplied image part together.\n"
            "- Gemini will receive selected source images with this request. Use them as concrete visual references, not loose inspiration.\n"
            f"{logo_rules}"
            "- If founder, team, workspace, or hero images are supplied, base the subject, styling, props, and scene on those images.\n"
            "- Multiple references may be supplied. Combine them intentionally: product as the main subject, logo as brand mark, and other brand media as environment/style context.\n"
            "- Include the requested short overlay text in the brand typography direction; do not leave the social image text-free unless the prompt explicitly forbids text.\n"
            "- Do not replace brand-specific references with generic stock-looking alternatives."
        )
    brand_name = business_name_from_profile(profile)
    image_url, model = generate_image(
        prompt,
        inspiration_images=inspiration_images,
        brand_name=brand_name,
        reference_mode=reference_mode,
    )
    if not image_url:
        raise RuntimeError('Gemini image generation returned no image URL.')
    image_assets = [{'slot': 'primary', 'url': image_url, 'model': model, 'prompt': prompt}]
    asset = MediaAsset.objects.create(
        user=job.user,
        workspace=job.workspace,
        url=image_url,
        source='gemini',
        metadata={'model': model, 'prompt': prompt, 'content_type': content_type},
    )
    for extra in extra_image_prompts or []:
        slot = extra.get('slot', 'inline') if isinstance(extra, dict) else 'inline'
        extra_prompt = extra.get('prompt') if isinstance(extra, dict) else str(extra)
        if not extra_prompt:
            continue
        extra_base = build_image_prompt(profile, brand, prompt_topic, platform=(plan.platforms or ['instagram'])[0], aspect_ratio=extra.get('aspect_ratio', '4:3') if isinstance(extra, dict) else '4:3')
        extra_final_prompt = enhance_image_prompt(
            f"{extra_base}\n\nApproved content-specific visual direction:\n{extra_prompt}\n\n"
            "Include the brand logo and a short readable overlay text where appropriate for this blog image."
        )
        extra_url, extra_model = generate_image(
            extra_final_prompt,
            inspiration_images=inspiration_images,
            brand_name=brand_name,
            reference_mode=reference_mode,
        )
        if not extra_url:
            raise RuntimeError(f'Gemini image generation returned no URL for {slot}.')
        MediaAsset.objects.create(
            user=job.user,
            workspace=job.workspace,
            url=extra_url,
            source='gemini',
            metadata={'model': extra_model, 'prompt': extra_final_prompt, 'content_type': content_type, 'slot': slot},
        )
        image_assets.append({'slot': slot, 'url': extra_url, 'model': extra_model, 'prompt': extra_final_prompt})
    create_generated_post_safely(
        user=job.user,
        workspace=job.workspace,
        content_plan=plan,
        topic=safe_topic,
        job=job,
        image=asset,
        platform_outputs=platform_outputs or {},
        image_prompt=prompt,
        status='need_review',
        scheduled_for=scheduled_day,
    )
    flat_captions = {
        PLATFORM_ALIASES.get(platform, platform): output.get('caption', '')
        for platform, output in (platform_outputs or {}).items()
        if isinstance(output, dict)
    }
    body_text = body or title
    display_caption = f'{title}\n\n{body_text}' if title and body_text and not body_text.startswith(title) else body_text
    merged_meta = dict(meta_extra or {})
    if reference_images:
        merged_meta['primary_reference_url'] = reference_images[0]
        merged_meta['reference_images'] = reference_images
        merged_meta['reference_lock'] = True
    merged_meta['image_assets'] = image_assets
    merged_meta['content_plan_id'] = str(plan.id)
    merged_meta['campaign_week_id'] = str(job.campaign_week_id) if job.campaign_week_id else None
    merged_meta['week_number'] = week_number
    merged_meta['generation_source'] = 'content_engine'
    meta = make_meta(content_type, title, merged_meta)
    nano_post = NanoBananaImage.objects.create(
        user=job.user,
        workspace=job.workspace,
        picture_url=image_url,
        caption=display_caption,
        platform_captions=caption_payload(flat_captions, meta),
    )
    ScheduledPost.objects.create(
        user=job.user,
        workspace=job.workspace,
        nano_banana=nano_post,
        task_id=content_engine_task_id(plan, week_number, content_type, nano_post.id),
        scheduled_at=calendar_datetime(scheduled_day, plan=plan),
        approval=generated_post_approval_status(job.user, job.workspace),
    )
    return nano_post


def create_text_calendar_item(job, plan, topic, content_type, title, body, scheduled_day, hour=None, platform_outputs=None, meta_extra=None, week_number=1):
    safe_topic = persisted_topic_for_generation(plan, topic, content_type, title, metadata=meta_extra)
    create_generated_post_safely(
        user=job.user,
        workspace=job.workspace,
        content_plan=plan,
        topic=safe_topic,
        job=job,
        image=None,
        platform_outputs=platform_outputs or {},
        image_prompt='',
        status='need_review',
        scheduled_for=scheduled_day,
    )
    flat_captions = {
        PLATFORM_ALIASES.get(platform, platform): output.get('caption', '')
        for platform, output in (platform_outputs or {}).items()
        if isinstance(output, dict)
    }
    merged_meta = dict(meta_extra or {})
    merged_meta.update({
        'content_plan_id': str(plan.id),
        'campaign_week_id': str(job.campaign_week_id) if job.campaign_week_id else None,
        'week_number': week_number,
        'generation_source': 'content_engine',
        'image_assets': [],
    })
    meta = make_meta(content_type, title, merged_meta)
    body_text = body or title
    display_caption = f'{title}\n\n{body_text}' if title and body_text and not body_text.startswith(title) else body_text
    nano_post = NanoBananaImage.objects.create(
        user=job.user,
        workspace=job.workspace,
        picture_url='',
        caption=display_caption,
        platform_captions=caption_payload(flat_captions, meta),
    )
    ScheduledPost.objects.create(
        user=job.user,
        workspace=job.workspace,
        nano_banana=nano_post,
        task_id=content_engine_task_id(plan, week_number, content_type, nano_post.id),
        scheduled_at=calendar_datetime(scheduled_day, plan=plan),
        approval=generated_post_approval_status(job.user, job.workspace),
    )
    return nano_post


def create_next_campaign_batch_if_needed(plan):
    existing = list(plan.campaign_weeks.order_by('week_number')) if plan else []
    if len(existing) < 4:
        logger.info('Next campaign batch skipped because fewer than 4 weeks exist plan=%s count=%s', getattr(plan, 'id', None), len(existing))
        return
    latest_four = existing[-4:]
    if not all(week.status == 'generated' for week in latest_four):
        logger.info('Next campaign batch skipped because latest four weeks are not all generated plan=%s weeks=%s', getattr(plan, 'id', None), [week.week_number for week in latest_four])
        return
    start_number = latest_four[-1].week_number + 1
    if plan.campaign_weeks.filter(week_number__gte=start_number).exists():
        logger.info('Next campaign batch skipped because next batch already exists plan=%s start_number=%s', plan.id, start_number)
        return
    logger.info('Creating next campaign batch plan=%s start_number=%s', plan.id, start_number)
    for item in generate_campaign_batch(plan.business_profile, plan.brand_setting, plan, start_number=start_number, count=4):
        CampaignWeek.objects.create(
            content_plan=plan,
            week_number=item['week_number'],
            theme=item['item_plan'].get('title') or item.get('theme', ''),
            funnel_goal=item.get('funnel_goal', ''),
            item_plan=item['item_plan'],
            status='draft',
        )
    logger.info('Next campaign batch created plan=%s start_number=%s count=%s', plan.id, start_number, 4)


def queue_next_campaign_week_if_needed(plan, completed_week):
    """
    DISALED: Automatic sequential queuing is disabled.
    Weeks 2-4 and rolling batches now require manual approval via CampaignWeekApproveView.
    """
    if not plan or not completed_week:
        return None
    
    logger.info(
        'Automatic next-week queue is disabled. Manual approval required for plan=%s week=%s',
        plan.id,
        completed_week.week_number
    )
    
    # Check if we should trigger rolling batch creation for the NEXT 4 weeks
    try:
        current_week_num = int(completed_week.week_number or 0)
        if current_week_num > 0 and current_week_num % 4 == 0:
            logger.info('End of 4-week cycle reached for plan=%s week=%s. Triggering rolling batch creation.', plan.id, current_week_num)
            create_next_campaign_batch_if_needed(plan)
    except Exception as exc:
        logger.error('Failed to trigger rolling batch creation for plan=%s: %s', plan.id, exc)

    return None



def generate_first_week(job):
    job.status = 'running'
    job.attempts += 1
    job.save(update_fields=['status', 'attempts', 'updated_at'])
    plan = job.content_plan
    profile, brand = resolve_plan_context(plan)
    campaign_week = job.campaign_week
    week_number = campaign_week.week_number if campaign_week else 1
    cleanup_generated_week(plan, week_number)
    social_limit = max(1, int(plan.posts_per_week or 1))
    blog_limit = max(0, int(plan.blog_posts_per_week or 0))
    # If blog_limit is 0 but campaign week has blog-type prompts, count them
    if blog_limit == 0 and campaign_week and isinstance(campaign_week.item_plan, dict):
        campaign_prompts = campaign_week.item_plan.get('post_prompts') or []
        campaign_blog_count = sum(1 for p in campaign_prompts if isinstance(p, dict) and str(p.get('type', '')).lower() == 'blog')
        if campaign_blog_count > 0:
            blog_limit = campaign_blog_count
            logger.info("Blog limit overridden from campaign week prompts: %d blog topics found", campaign_blog_count)
    email_limit = 0
    social_topics = limited_week_topics(plan, 'social', week_number, social_limit)
    if not social_topics and campaign_week:
        generated_topics = []
        try:
            created_from_campaign = create_topics_from_campaign_week(plan, campaign_week, profile, brand)
        except Exception as exc:
            logger.exception("Campaign prompt topic creation failed; falling back: %s", exc)
            created_from_campaign = []
        if not created_from_campaign:
            try:
                generated_topics = generate_weekly_topics(profile, brand, plan)
            except Exception as exc:
                logger.exception("Weekly topic generation failed: %s", exc)
                raise
        theme = campaign_week.theme or ''
        for item in generated_topics:
            item['week_number'] = week_number
            if theme and item.get('kind') == 'social':
                item['title'] = f"{theme}: {item.get('title', '')}"
            Topic.objects.create(
                content_plan=plan,
                week_number=week_number,
                position=item.get('position', 1),
                kind=item.get('kind', 'social'),
                title=item.get('title') or '',
                metadata=item.get('metadata', {}),
            )
        social_topics = limited_week_topics(plan, 'social', week_number, social_limit)
    dates = [day + timedelta(days=(week_number - 1) * 7) for day in schedule_dates(max(len(social_topics), 3))]
    item_errors = []
    created_count = 0
    for index, topic in enumerate(social_topics):
        try:
            if smart_captions_enabled(plan):
                platform_outputs = {
                    platform: {
                        'caption': platform_caption(topic, platform, profile, brand),
                        'tone_rule': platform,
                    }
                    for platform in plan.platforms
                }
            else:
                shared_caption = platform_caption(topic, 'facebook', profile, brand)
                platform_outputs = {
                    platform: {
                        'caption': shared_caption,
                        'tone_rule': 'shared',
                    }
                    for platform in plan.platforms
                }
            scheduled_day = dates[index] if index < len(dates) else dates[-1]
            fallback_caption = next(iter(platform_outputs.values()), {}).get('caption', topic.title)
            image_brief = build_image_prompt(profile, brand, topic, platform=(plan.platforms or ['instagram'])[0])
            create_calendar_item(
                job=job,
                plan=plan,
                topic=topic,
                content_type='social',
                title=topic.title,
                body=fallback_caption,
                image_prompt=image_brief,
                scheduled_day=scheduled_day,
                hour=9 + (index % 5),
                platform_outputs=platform_outputs,
                meta_extra={'topic_id': str(topic.id), 'source': 'first_week_social'},
                week_number=week_number,
            )
            created_count += 1
        except Exception as exc:
            logger.exception("Social item generation failed for topic %s: %s", getattr(topic, 'id', None), exc)
            item_errors.append(str(exc))

    blog_email = None
    blogs = []
    if blog_limit:
        try:
            blog_email = getattr(plan, 'blog_email_plan', None)
            if blog_email is None:
                plan_payload = generate_blog_email_plan(profile, brand, plan)
                blog_email = BlogEmailPlan.objects.create(
                    content_plan=plan,
                    blog_plan=plan_payload.get('blog_plan', {}),
                    email_plan={},
                )
            else:
                normalized_payload = normalize_blog_email_plan(
                    {'blog_plan': blog_email.blog_plan, 'email_plan': {}},
                    profile,
                    plan,
                )
                if normalized_payload.get('blog_plan') != blog_email.blog_plan or blog_email.email_plan:
                    blog_email.blog_plan = normalized_payload.get('blog_plan', {})
                    blog_email.email_plan = {}
                    blog_email.save(update_fields=['blog_plan', 'email_plan', 'updated_at'])
            full_content = generate_blog_email_content(profile, brand, plan, blog_email)
            blogs = (full_content.get('blogs') or [])[:blog_limit]
        except Exception as exc:
            logger.exception("Blog plan/content generation failed: %s", exc)
            item_errors.append(str(exc))

    all_dates = [day + timedelta(days=(week_number - 1) * 7) for day in schedule_dates(max(len(social_topics) + len(blogs), 3))]
    blog_plan_items = (blog_email.blog_plan or {}).get('items') if blog_email and isinstance((blog_email.blog_plan or {}).get('items'), list) else []
    existing_blog_topics = limited_week_topics(plan, 'blog', week_number, blog_limit)
    for index, blog in enumerate(blogs):
        try:
            scheduled_day = all_dates[min(len(social_topics) + index, len(all_dates) - 1)]
            blog_plan_item = blog_plan_items[index] if index < len(blog_plan_items) else {}
            blog_title = blog.get('title') or blog_plan_item.get('title') or 'Brand blog post'
            blog_body = blog.get('body') or blog.get('excerpt') or blog_title
            blog_topic = existing_blog_topics[index] if index < len(existing_blog_topics) else Topic.objects.create(
                content_plan=plan,
                week_number=week_number,
                position=index + 1,
                kind='blog',
                title=blog_title,
                metadata={'source': 'gemini', 'plan': blog_plan_item},
            )
            create_calendar_item(
                job=job,
                plan=plan,
                topic=blog_topic,
                content_type='blog',
                title=blog_title,
                body=blog_body,
                image_prompt=blog.get('cover_image_prompt') or f'Brand-aligned 16:9 cover image for {blog_title}',
                scheduled_day=scheduled_day,
                hour=14,
                platform_outputs={'blog': {'caption': blog_body, 'tone_rule': 'long-form'}},
                meta_extra={'excerpt': blog.get('excerpt', ''), 'blog_plan': blog_plan_item},
                extra_image_prompts=[{'slot': 'inline', 'prompt': blog.get('inline_image_prompt') or f'Brand-aligned 4:3 inline image for {blog_title}', 'aspect_ratio': '4:3'}],
                week_number=week_number,
            )
            created_count += 1
        except Exception as exc:
            logger.exception("Blog item generation failed: %s", exc)
            item_errors.append(str(exc))

    if campaign_week and not item_errors and created_count:
        campaign_week.status = 'generated'
        campaign_week.generated_at = timezone.now()
        campaign_week.save(update_fields=['status', 'generated_at', 'updated_at'])
        queue_next_campaign_week_if_needed(plan, campaign_week)
    job.status = 'failed' if item_errors or not created_count else 'completed'
    job.error = '; '.join(item_errors[:5])
    if not created_count and not job.error:
        job.error = 'No content was generated.'
    job.save(update_fields=['status', 'error', 'updated_at'])
    if job.status == 'failed':
        raise RuntimeError(job.error)
