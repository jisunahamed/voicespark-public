from datetime import date, datetime, time, timedelta
import json
import re
import os
from .generation_orchestrator import orchestrate_generation


PLATFORM_RULES = {
    'facebook': 'casual, engaging, conversational',
    'instagram': 'visual storytelling, emotional',
    'linkedin': 'professional, research-based, authority tone',
    'x': 'short, punchy, high engagement',
}


def brand_context(profile, brand, plan=None):
    preferences = get_content_preferences(profile)
    profile_data = profile.profile if profile and isinstance(profile.profile, dict) else {}
    if profile and not profile_data.get('name'):
        profile_data = {**profile_data, 'name': business_name(profile)}
    intelligence = {}
    try:
        from auth_user.models import ImageUrl
        from content_engine.models import AudienceProfile, BrandManualData, ChannelVoiceConfig, CompetitorAnalysis, MediaAsset
        if profile and profile.workspace:
            media_assets = MediaAsset.objects.filter(user=profile.user, workspace=profile.workspace, asset_type='image').order_by('-created_at')[:20]
            media_asset_urls = {asset.url for asset in media_assets}
            intelligence = {
                'channel_voice': [
                    {
                        'platform': item.platform,
                        'tone': item.tone,
                        'emotion': item.emotion,
                        'character': item.character,
                        'syntax': item.syntax,
                        'language': item.language,
                    }
                    for item in ChannelVoiceConfig.objects.filter(user=profile.user, workspace=profile.workspace)
                ],
                'audience_profiles': [
                    {
                        'name': item.name,
                        'age_range': item.age_range,
                        'location': item.location,
                        'occupation': item.occupation,
                        'pain_points': item.pain_points,
                        'frustrations': item.frustrations,
                        'goals': item.goals,
                        'behaviors': item.behaviors,
                        'buying_patterns': item.buying_patterns,
                        'awareness_level': item.awareness_level,
                    }
                    for item in AudienceProfile.objects.filter(user=profile.user, workspace=profile.workspace)[:8]
                ],
                'manual_business_data': (
                    {
                        'processes': manual.processes,
                        'methodology': manual.methodology,
                        'deliverables': manual.deliverables,
                        'pricing': manual.pricing,
                        'onboarding': manual.onboarding,
                    }
                    if (manual := BrandManualData.objects.filter(user=profile.user, workspace=profile.workspace).first())
                    else {}
                ),
                'competitors': [
                    {
                        'name': item.name,
                        'website_url': item.website_url,
                        'pricing_model': item.pricing_model,
                        'key_features': item.key_features,
                        'differentiators': item.differentiators,
                    }
                    for item in CompetitorAnalysis.objects.filter(user=profile.user, workspace=profile.workspace)[:8]
                ],
                'media_library': [
                    {
                        'url': asset.url,
                        'source': asset.source,
                        'metadata': asset.metadata,
                    }
                    for asset in media_assets
                ] + [
                    {'url': item.image_url, 'source': 'media_library', 'metadata': {}}
                    for item in ImageUrl.objects.filter(user=profile.user, workspace=profile.workspace).exclude(image_url__in=media_asset_urls).order_by('-created_at')[:12]
                ],
            }
    except Exception:
        intelligence = {}
    return {
        'profile': profile_data,
        'business_profile_markdown': (profile.editable_markdown or '')[:5000] if profile else '',
        'website_url': profile.website_url if profile else '',
        'tone': (brand.tone if brand else '') or (profile.tone if profile else ''),
        'visual_style': brand.visual_style if brand else '',
        'recommended_visual_style': brand.recommended_visual_style if brand else {},
        'font': brand.font if brand else {},
        'brand_colors': brand.colors if brand else [],
        'brand_logos': brand.logos if brand else [],
        'brand_image_style': brand.image_style if brand else '',
        'brand_context': brand.brand_context if brand else {},
        'platforms': plan.platforms if plan else [],
        'posts_per_week': plan.posts_per_week if plan else 5,
        'blog_posts_per_week': getattr(plan, 'blog_posts_per_week', 0) if plan else 0,
        'emails_per_week': 0,
        'content_preferences': preferences,
        'output_language': preferences.get('language', {}),
        'content_style': preferences.get('content_style', {}),
        'brand_intelligence': intelligence,
    }


def business_name(profile):
    if not profile:
        return 'the brand'
    profile_data = profile.profile if isinstance(profile.profile, dict) else {}
    for key in ('name', 'business_name', 'brand_name', 'title'):
        value = str(profile_data.get(key) or '').strip()
        if value:
            return value
    markdown = profile.editable_markdown or ''
    for pattern in (
        r"^#\s+(.+?)(?:'s Business Profile| Business Profile)?\s*$",
        r"^(.+?)(?:'s Business Profile| Business Profile)\s*$",
    ):
        match = re.search(pattern, markdown, flags=re.MULTILINE)
        if match:
            value = match.group(1).strip()
            if value:
                return value
    if profile.website_url:
        host = re.sub(r'^https?://', '', profile.website_url).split('/')[0]
        return host.replace('www.', '').split('.')[0].replace('-', ' ').title()
    return 'the brand'


def nonnegative_int(value, default=0):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(0, parsed)


def compact_json(value):
    try:
        return json.dumps(value or {}, ensure_ascii=False)
    except TypeError:
        return "{}"


def get_content_preferences(profile):
    default = {
        'language': {'code': 'en', 'label': 'English'},
        'content_style': {
            'id': 'ultra_realistic',
            'name': 'Ultra Realistic',
            'label': 'Ultra Realistic',
            'prompt': 'ultra-realistic commercial photography with real humans or real places, natural lighting, no cartoon or illustration',
        },
        'timezone': 'Asia/Dhaka',
        'default_schedule_time': '09:00',
        'smart_captions': {'enabled': True},
    }
    if not profile:
        return default
    try:
        from auth_user.models import UserProfile
        user_profile = UserProfile.objects.filter(user=profile.user, workspace=profile.workspace).first()
        brand_voice = user_profile.brand_voice if user_profile and isinstance(user_profile.brand_voice, dict) else {}
        preferences = brand_voice.get('content_preferences') if isinstance(brand_voice.get('content_preferences'), dict) else {}
        language = preferences.get('language') if isinstance(preferences.get('language'), dict) else {}
        content_style = preferences.get('content_style') if isinstance(preferences.get('content_style'), dict) else {}
        smart_captions = preferences.get('smart_captions') if isinstance(preferences.get('smart_captions'), dict) else {}
        return {
            'language': {
                **default['language'],
                **language,
            },
            'content_style': {
                **default['content_style'],
                **content_style,
            },
            'timezone': preferences.get('timezone') or default['timezone'],
            'default_schedule_time': preferences.get('default_schedule_time') or default['default_schedule_time'],
            'smart_captions': {
                **default['smart_captions'],
                **smart_captions,
            },
        }
    except Exception:
        return default


def language_label_from_context(info):
    language = info.get('output_language') or {}
    return language.get('label') or language.get('name') or 'English'


def parse_ai_json(text):
    if not text:
        return None
    cleaned = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", cleaned, re.DOTALL | re.IGNORECASE)
    if fenced:
        cleaned = fenced.group(1).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        cleaned = cleaned[start:end + 1]
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None


def generate_with_gpt(prompt):
    from utils.chatbot import gemini_json
    return gemini_json(
        prompt,
        system_prompt=(
            "You are a senior content strategist for a brand-specific AI marketing platform. "
            "Generate specific, non-generic strategy outputs from the real business context. "
            "Return valid JSON only. No markdown, no explanation."
        ),
        fallback=None,
    )


CAMPAIGN_IMAGE_FALLBACKS = [
    'https://images.unsplash.com/photo-1517245386807-bb43f82c33c4?w=600&q=85',
    'https://images.unsplash.com/photo-1556761175-b413da4baf72?w=600&q=85',
    'https://images.unsplash.com/photo-1551836022-d5d88e9218df?w=600&q=85',
    'https://images.unsplash.com/photo-1556761175-5973dc0f32e7?w=600&q=85',
]


def campaign_week_dates(index):
    start = date.today() + timedelta(days=index * 7)
    end = start + timedelta(days=6)
    return start, end


def format_campaign_date(value):
    return value.strftime('%a, %b ') + str(value.day)


def date_for_week_number(week_number):
    return date.today() + timedelta(days=(max(1, int(week_number or 1)) - 1) * 7)


def datetime_local_for_day(day, hour=9, minute=0):
    if isinstance(day, datetime):
        return day.replace(second=0, microsecond=0).strftime('%Y-%m-%dT%H:%M')
    return datetime.combine(day, time(hour=hour, minute=minute)).strftime('%Y-%m-%dT%H:%M')


def normalize_schedule_value(value, fallback_day, hour=9):
    raw = str(value or '').strip()
    if raw:
        if 'T' in raw:
            return raw[:16]
        if re.match(r'^\d{4}-\d{2}-\d{2}$', raw):
            return f'{raw}T{hour:02d}:00'
    return datetime_local_for_day(fallback_day, hour=hour)


def apply_campaign_timing(item_plan, week_number):
    item_plan = item_plan if isinstance(item_plan, dict) else {}
    start = date_for_week_number(week_number)
    end = start + timedelta(days=6)
    timing = item_plan.get('timing') if isinstance(item_plan.get('timing'), dict) else {}
    item_plan['timing'] = {
        **timing,
        'start_date': start.isoformat(),
        'end_date': end.isoformat(),
        'range_label': f'{format_campaign_date(start)} - {format_campaign_date(end)}',
        'duration': timing.get('duration') or '1 week',
    }
    item_plan['generate_on'] = (start - timedelta(days=2)).isoformat()
    if week_number == 1:
        item_plan['status_label'] = 'Posting'
    else:
        item_plan['status_label'] = f'Generating on {format_campaign_date(start - timedelta(days=2)).replace(", ", " ")}'
    prompts = item_plan.get('post_prompts') if isinstance(item_plan.get('post_prompts'), list) else []
    for index, prompt in enumerate(prompts):
        if isinstance(prompt, dict):
            prompt['scheduled_at'] = normalize_schedule_value(
                prompt.get('scheduled_at'),
                start + timedelta(days=index),
                hour=9 + min(index, 8),
            )
    item_plan['post_prompts'] = prompts
    return item_plan


def campaign_thumbnail(brand, index=0):
    if brand and isinstance(brand.logos, list):
        for item in brand.logos:
            if isinstance(item, dict):
                url = item.get('url') or item.get('image') or item.get('src')
            else:
                url = str(item or '')
            if url:
                return url
    return CAMPAIGN_IMAGE_FALLBACKS[index % len(CAMPAIGN_IMAGE_FALLBACKS)]


def brand_logo_references(brand, limit=3):
    if not brand or not isinstance(brand.logos, list):
        return []
    return dedupe_urls(brand.logos, limit=limit)


def include_logo_references(reference_images, brand, limit=7):
    """Keep the selected product/reference image first, then force exact logo refs in."""
    refs = dedupe_urls(reference_images, limit=limit)
    logos = brand_logo_references(brand, limit=3)
    if not logos:
        return refs
    for logo in logos:
        if logo and logo not in refs:
            refs.append(logo)
    return dedupe_urls(refs, limit=limit)


def dedupe_urls(values, limit=8):
    result = []
    seen = set()
    for item in values or []:
        if isinstance(item, dict):
            url = item.get('url') or item.get('src') or item.get('image')
        else:
            url = item
        url = str(url or '').strip()
        if not url or url in seen:
            continue
        seen.add(url)
        result.append(url)
        if len(result) >= limit:
            break
    return result


def query_terms(value):
    stop = {
        'this', 'that', 'with', 'from', 'into', 'about', 'post', 'topic', 'brand',
        'social', 'blog', 'image', 'content', 'campaign', 'week', 'practical',
        'insight', 'through', 'for', 'and', 'the', 'your', 'our',
    }
    return [
        term for term in re.findall(r'[a-zA-Z][a-zA-Z0-9-]{2,}', str(value or '').lower())
        if term not in stop
    ][:16]


def media_reference_text(url, metadata):
    metadata = metadata if isinstance(metadata, dict) else {}
    values = [url]
    for key in ('label', 'alt', 'description', 'source_page', 'source', 'title', 'name'):
        values.append(str(metadata.get(key) or ''))
    return ' '.join(values).lower()


def media_references(profile, labels=None, limit=8, query=''):
    if not profile or not profile.workspace_id:
        return []
    labels = set(labels or [])
    try:
        from auth_user.models import ImageUrl
        from content_engine.models import MediaAsset
        assets = list(MediaAsset.objects.filter(user=profile.user, workspace=profile.workspace, asset_type='image').order_by('-created_at')[:80])
        image_rows = list(ImageUrl.objects.filter(user=profile.user, workspace=profile.workspace).order_by('-created_at')[:80])
    except Exception:
        return []
    scored = []
    seen = set()
    terms = query_terms(query)
    for asset in assets:
        if not asset.url or asset.url in seen:
            continue
        seen.add(asset.url)
        metadata = asset.metadata if isinstance(asset.metadata, dict) else {}
        label = str(metadata.get('label') or '').lower()
        score = 5 if label in labels else 2
        if label == 'logo':
            score += 1 if 'logo' in labels else -2
        searchable = media_reference_text(asset.url, metadata)
        score += sum(4 for term in terms if term in searchable)
        if label == 'product' and any(term in searchable for term in ('shirt', 't-shirt', 'polo', 'pant', 'dress', 'collection', 'fashion', 'wear')):
            score += 3
        scored.append((score, asset.url, metadata))
    for row in image_rows:
        if not row.image_url or row.image_url in seen:
            continue
        seen.add(row.image_url)
        score = 1 + sum(3 for term in terms if term in row.image_url.lower())
        scored.append((score, row.image_url, {}))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [{'url': url, 'metadata': metadata} for _, url, metadata in scored[:limit]]


def campaign_thumbnail_for(profile, brand, index=0):
    refs = media_references(profile, labels={'product', 'hero', 'team', 'workspace', 'testimonial'}, limit=12)
    non_logo = [item['url'] for item in refs if (item.get('metadata') or {}).get('label') != 'logo']
    if non_logo:
        return non_logo[index % len(non_logo)]
    return campaign_thumbnail(brand, index)


def prompt_references_for(profile, prompt_type, topic, limit=3, offset=0, brand=None):
    text = f'{prompt_type} {topic}'.lower()
    preferences = get_content_preferences(profile)
    content_style = preferences.get('content_style') if isinstance(preferences.get('content_style'), dict) else {}
    style_text = f"{content_style.get('id', '')} {content_style.get('name', '')} {content_style.get('label', '')}".lower()
    if ('product-studio' in style_text or 'product_studio' in style_text or any(term in text for term in ('product', 'offer', 'pricing', 'buy', 'shop', 'feature', 'demo', 'arrival', 'collection'))):
        labels = {'product', 'hero'}
    elif any(term in text for term in ('brand', 'trust', 'awareness', 'logo')):
        labels = {'hero', 'team', 'workspace', 'product', 'logo'}
    elif any(term in text for term in ('story', 'team', 'founder', 'customer', 'testimonial')):
        labels = {'team', 'testimonial', 'hero', 'workspace'}
    else:
        labels = {'product', 'hero', 'team', 'workspace', 'section'}
    refs = media_references(profile, labels=labels, limit=max(16, limit + 8), query=text)
    non_logo = [item['url'] for item in refs if (item.get('metadata') or {}).get('label') != 'logo']
    fallback = [item['url'] for item in refs if item['url'] not in non_logo]
    ordered = non_logo or fallback
    if ordered:
        offset = int(offset or 0) % len(ordered)
        ordered = [*ordered[offset:], *ordered[:offset]]
    selected = dedupe_urls(ordered, limit=limit)
    return include_logo_references(selected, brand, limit=limit + 3)


def prompt_reference_for(profile, prompt_type, topic):
    refs = prompt_references_for(profile, prompt_type, topic, limit=1)
    return refs[0] if refs else ''


IMAGE_PROMPT_MARKERS = (
    'shot of',
    'photo of',
    'image of',
    'generate an image',
    'visual prompt',
    'caption should',
    'lighting',
    'composition',
    'camera',
    'ultra-realistic',
    'ultra_realistic',
    'minimalist lifestyle',
)


def topic_looks_like_image_prompt(value):
    text = str(value or '').lower()
    return any(marker in text for marker in IMAGE_PROMPT_MARKERS)


GENERIC_TOPIC_RE = re.compile(
    r'\b(?:campaign\s+week\s+\d+|week\s+\d+|practical\s+post\s+\d+|social\s+post\s+idea\s+\d+|blog\s+idea\s+\d+|caption\s*(?:number)?\s*\d+|prompt\s+\d+)\b',
    re.I,
)


def clean_campaign_label(value, business=''):
    text = re.sub(r'\s+', ' ', str(value or '').strip())
    text = GENERIC_TOPIC_RE.sub('', text).strip(' :-')
    if not text:
        text = str(business or 'Brand growth plan').strip()
    return text


def fallback_topic_from_context(title, prompt_index, content_type, business=''):
    base = clean_campaign_label(title, business)
    social_angles = [
        'show the customer problem and why it matters now',
        'explain one product benefit through a specific use case',
        'build trust with proof, quality, or behind-the-scenes detail',
        'answer a common buying objection with a practical example',
        'invite action with one clear next step',
    ]
    blog_angles = [
        'write a practical guide around the customer problem',
        'compare common options and explain the branded approach',
        'turn proof points into a useful long-form article',
    ]
    angles = blog_angles if content_type == 'blog' else social_angles
    angle = angles[prompt_index % len(angles)]
    return f'{base}: {angle}'


def default_post_prompts(plan, campaign_title, business, week_number):
    prompts = []
    platforms = plan.platforms if plan else ['facebook', 'instagram', 'linkedin', 'x']
    social_count = max(1, int(getattr(plan, 'posts_per_week', 5) or 1))
    blog_count = nonnegative_int(getattr(plan, 'blog_posts_per_week', 0), 0)
    start, _ = campaign_week_dates(week_number - 1)
    position = 1
    clean_title = clean_campaign_label(campaign_title, business)
    for index in range(social_count):
        topic = fallback_topic_from_context(clean_title, index, 'social', business)
        reference_images = prompt_references_for(plan.business_profile if plan else None, 'social', topic, limit=3, offset=index, brand=plan.brand_setting if plan else None)
        prompts.append({
            'id': f'w{week_number}-social-{index + 1}',
            'type': 'social',
            'topic': topic,
            'platforms': platforms,
            'accounts': len(platforms),
            'scheduled_at': datetime_local_for_day(start + timedelta(days=index), hour=9 + min(index, 8)),
            'reference_image': reference_images[0] if reference_images else '',
            'reference_images': reference_images,
            'status': 'draft',
            'position': position,
        })
        position += 1
    for index in range(blog_count):
        topic = fallback_topic_from_context(clean_title, index, 'blog', business)
        reference_images = prompt_references_for(plan.business_profile if plan else None, 'blog', topic, limit=3, offset=social_count + index, brand=plan.brand_setting if plan else None)
        prompts.append({
            'id': f'w{week_number}-blog-{index + 1}',
            'type': 'blog',
            'topic': topic,
            'platforms': [],
            'accounts': 0,
            'scheduled_at': datetime_local_for_day(start + timedelta(days=social_count + index), hour=9 + min(social_count + index, 8)),
            'reference_image': reference_images[0] if reference_images else '',
            'reference_images': reference_images,
            'status': 'draft',
            'position': position,
        })
        position += 1
    return prompts


def normalize_campaign_item_plan(item, profile, brand, plan, index):
    business = business_name(profile) if profile else 'Your brand'
    week_number = index + 1
    start, end = campaign_week_dates(index)
    item = item if isinstance(item, dict) else {}
    raw_plan = item.get('item_plan') if isinstance(item.get('item_plan'), dict) else item
    default_titles = [
        f'{business}: Awareness and demand campaign',
        f'{business}: Education and engagement campaign',
        f'{business}: Proof and conversion campaign',
        f'{business}: Trust and retention campaign',
    ]
    title = str(raw_plan.get('title') or item.get('title') or item.get('theme') or default_titles[index % len(default_titles)]).strip()
    title = clean_campaign_label(title, business)
    campaign_type = str(raw_plan.get('campaign_type') or item.get('campaign_type') or 'Thought Leadership').strip()
    theme = str(raw_plan.get('theme') or raw_plan.get('summary') or item.get('theme') or '').strip()
    if not theme:
        theme = f'Build a focused {campaign_type.lower()} campaign around {title}, using the brand position and weekly content mix.'
    call_to_action = str(raw_plan.get('call_to_action') or raw_plan.get('cta') or f'Take the next step with {business}').strip()
    audience = str(raw_plan.get('audience') or 'Current and potential customers who match the saved business profile.').strip()
    timing = raw_plan.get('timing') if isinstance(raw_plan.get('timing'), dict) else {}
    prompts = raw_plan.get('post_prompts') if isinstance(raw_plan.get('post_prompts'), list) else []
    if not prompts:
        prompts = default_post_prompts(plan, title, business, week_number)
    normalized_prompts = []
    used_primary_references = set()
    for prompt_index, prompt in enumerate(prompts):
        if not isinstance(prompt, dict):
            prompt = {'topic': str(prompt)}
        content_type = str(prompt.get('type') or prompt.get('kind') or 'social').strip().lower()
        if content_type in ('post', 'still image', 'feed post'):
            content_type = 'social'
        if content_type == 'email':
            continue
        topic_text = str(prompt.get('topic') or prompt.get('title') or f'{title}: prompt {prompt_index + 1}').strip()
        if topic_looks_like_image_prompt(topic_text):
            topic_text = fallback_topic_from_context(title, prompt_index, content_type, business)
        reference_images = []
        if isinstance(prompt.get('reference_images'), list):
            reference_images.extend(prompt.get('reference_images'))
        if isinstance(prompt.get('reference_media'), list):
            reference_images.extend(prompt.get('reference_media'))
        if prompt.get('reference_image'):
            reference_images.insert(0, prompt.get('reference_image'))
        reference_images = dedupe_urls(reference_images, limit=4)
        auto_references = prompt_references_for(profile, content_type, topic_text, limit=3, offset=prompt_index, brand=brand)
        if not reference_images:
            reference_images = auto_references
        primary_candidates = dedupe_urls([*auto_references, *reference_images], limit=8)
        reference_image = reference_images[0] if reference_images else ''
        if reference_image in used_primary_references:
            reference_image = next((url for url in primary_candidates if url not in used_primary_references), reference_image)
        elif not reference_image and primary_candidates:
            reference_image = primary_candidates[0]
        used_primary_references.add(reference_image)
        reference_images = include_logo_references([reference_image, *reference_images, *auto_references], brand, limit=7)
        normalized_prompts.append({
            'id': str(prompt.get('id') or f'w{week_number}-prompt-{prompt_index + 1}'),
            'type': content_type,
            'topic': topic_text,
            'platforms': prompt.get('platforms') if isinstance(prompt.get('platforms'), list) else (plan.platforms if content_type == 'social' and plan else []),
            'accounts': int(prompt.get('accounts') or (len(plan.platforms) if content_type == 'social' and plan else 0)),
            'connected_accounts': int(prompt.get('connected_accounts') or 0),
            'connected_platforms': prompt.get('connected_platforms') if isinstance(prompt.get('connected_platforms'), list) else [],
            'scheduled_at': normalize_schedule_value(
                prompt.get('scheduled_at'),
                start + timedelta(days=prompt_index),
                hour=9 + min(prompt_index, 8),
            ),
            'reference_image': reference_image,
            'reference_images': reference_images,
            'reference_media': reference_images,
            'status': str(prompt.get('status') or 'draft'),
            'position': int(prompt.get('position') or prompt_index + 1),
        })
    return {
        'title': title,
        'campaign_type': campaign_type,
        'theme': theme,
        'call_to_action': call_to_action,
        'audience': audience,
        'timing': {
            'start_date': timing.get('start_date') or start.isoformat(),
            'end_date': timing.get('end_date') or end.isoformat(),
            'range_label': timing.get('range_label') or f'{format_campaign_date(start)} - {format_campaign_date(end)}',
            'duration': timing.get('duration') or '1 week',
        },
        'status_label': raw_plan.get('status_label') or ('Posting' if week_number == 1 else f'Generating on {format_campaign_date(start - timedelta(days=2)).replace(", ", " ")}'),
        'generate_on': raw_plan.get('generate_on') or (start - timedelta(days=2)).isoformat(),
        'thumbnail_url': raw_plan.get('thumbnail_url') or campaign_thumbnail_for(profile, brand, index),
        'reference_media': dedupe_urls(raw_plan.get('reference_media'), limit=8) if isinstance(raw_plan.get('reference_media'), list) else [item['url'] for item in media_references(profile, labels={'product', 'hero', 'team', 'workspace'}, limit=6, query=title)],
        'source_materials': raw_plan.get('source_materials') if isinstance(raw_plan.get('source_materials'), list) else [],
        'post_prompts': normalized_prompts,
        'summary': theme,
    }


def generate_campaign_batch(profile, brand, plan, start_number=1, count=4):
    generated = generate_campaign_weeks(profile, brand, plan)
    result = []
    for offset in range(count):
        source = generated[offset % len(generated)] if generated else {}
        number = start_number + offset
        item = {
            **(source if isinstance(source, dict) else {}),
            'week_number': number,
        }
        normalized = normalize_campaign_item_plan(item, profile, brand, plan, number - 1)
        normalized = apply_campaign_timing(normalized, number)
        result.append({
            'week_number': number,
            'theme': normalized.get('title') or item.get('theme', ''),
            'funnel_goal': item.get('funnel_goal') or normalized.get('funnel_goal') or ['awareness', 'engagement', 'conversion', 'retention'][(number - 1) % 4],
            'item_plan': normalized,
        })
    return result


def regenerate_campaign_plan(profile, brand, plan, current_item_plan, instruction):
    """Instruction-based regeneration of a single campaign item plan."""
    if os.getenv('ADVANCED_PIPELINE_ENABLED', 'false').lower() == 'true':
        try:
            result = orchestrate_generation(
                flow='campaign_regen',
                user=profile.user,
                workspace=profile.workspace,
                payload={'item_plan': current_item_plan},
                user_instruction=instruction,
                campaign_context={'plan_id': str(plan.id) if plan else None}
            )
            if result.get('status') == 'completed' and result.get('item_plan'):
                # Normalize via existing helper to ensure consistency
                return normalize_campaign_item_plan(
                    {'item_plan': result['item_plan']},
                    profile, brand, plan,
                    current_item_plan.get('week_number', 1) - 1
                )
        except Exception as e:
            from .context_builder import structured_log
            import logging
            structured_log(logging.getLogger(__name__), 'campaign_regen_advanced_failed', error=str(e))

    # Legacy fallback
    info = brand_context(profile, brand, plan)
    current_item_plan = current_item_plan if isinstance(current_item_plan, dict) else {}
    preserve_images = {
        'thumbnail_url': current_item_plan.get('thumbnail_url', ''),
        'reference_media': current_item_plan.get('reference_media', []),
        'prompt_images': {
            str(prompt.get('id')): prompt.get('reference_image', '')
            for prompt in current_item_plan.get('post_prompts', [])
            if isinstance(prompt, dict) and prompt.get('reference_image')
        },
    }
    prompt = f"""
Regenerate this campaign plan using the user's instruction.

Business and brand context:
{compact_json(info)}

Current campaign item_plan:
{compact_json(current_item_plan)}

User instruction:
{instruction}

Rules:
- Return only an updated item_plan JSON object.
- Improve title, campaign_type, theme, call_to_action, audience, funnel strategy, and post_prompts when relevant.
- Preserve existing thumbnail_url and post_prompts[].reference_image unless the user explicitly asks to replace images.
- Keep post prompt count close to the existing plan unless the instruction asks otherwise.
- post_prompts[].topic must be a content topic or posting idea only. Do not write image-generation prompts, caption copy, camera direction, lighting, or visual composition in topic.
- Keep all visible copy in this language: {language_label_from_context(info)}.

Return JSON only with the item_plan fields.
""".strip()
    try:
        generated = generate_with_gpt(prompt)
    except Exception:
        generated = {}
    if not isinstance(generated, dict):
        return current_item_plan
    if not generated.get('thumbnail_url') and preserve_images.get('thumbnail_url'):
        generated['thumbnail_url'] = preserve_images['thumbnail_url']
    if not isinstance(generated.get('reference_media'), list):
        generated['reference_media'] = preserve_images.get('reference_media', [])
    prompts = generated.get('post_prompts') if isinstance(generated.get('post_prompts'), list) else current_item_plan.get('post_prompts', [])
    for prompt_item in prompts:
        if not isinstance(prompt_item, dict):
            continue
        prompt_id = str(prompt_item.get('id') or '')
        if not prompt_item.get('reference_image') and preserve_images['prompt_images'].get(prompt_id):
            prompt_item['reference_image'] = preserve_images['prompt_images'][prompt_id]
    generated['post_prompts'] = prompts
    return generated


def regenerate_campaign_prompt(profile, brand, plan, campaign_item_plan, prompt_item, instruction):
    info = brand_context(profile, brand, plan)
    prompt = f"""
Regenerate one campaign post prompt.

Business and brand context:
{compact_json(info)}

Campaign item_plan:
{compact_json(campaign_item_plan)}

Current prompt:
{compact_json(prompt_item)}

User instruction:
{instruction}

Rules:
- Return one JSON object for the updated post prompt.
- Keep id, type, platforms, accounts, scheduled_at, status, position, and reference_image unless the instruction clearly asks to change them.
- Make the topic specific, useful, and campaign-aligned.
- The topic must stay a content topic or posting idea only. Do not write image-generation prompts, camera direction, lighting, composition, or caption copy in topic.
- Keep visible text in this language: {language_label_from_context(info)}.

Return JSON only.
""".strip()
    generated = generate_with_gpt(prompt)
    if not isinstance(generated, dict):
        return prompt_item
    preserved = prompt_item if isinstance(prompt_item, dict) else {}
    for key in ['id', 'type', 'platforms', 'accounts', 'scheduled_at', 'status', 'position', 'reference_image']:
        if preserved.get(key) and not generated.get(key):
            generated[key] = preserved[key]
    return generated


def generate_style_previews(profile, visual_style):
    return [
        {
            'id': 'ultra_realistic',
            'name': 'Ultra Realistic',
            'preview_image': 'https://images.unsplash.com/photo-1556761175-b413da4baf72?w=900&q=85',
            'description': 'Real humans, real places, natural light, premium commercial photography.',
            'prompt': 'ultra-realistic commercial photography with real humans or real places, natural skin texture, authentic environments, premium lighting, no cartoon or illustration',
        },
        {
            'id': 'infographic',
            'name': 'Infographic',
            'preview_image': 'https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=900&q=85',
            'description': 'Clean data-led layouts, diagrams, icons, comparison blocks, readable structure.',
            'prompt': 'modern branded infographic style with clean layout, data visualization, icons, diagrams, structured composition, minimal text only when necessary',
        },
        {
            'id': 'cartoon_animated',
            'name': 'Cartoon / Animated',
            'preview_image': 'https://images.unsplash.com/photo-1633356122544-f134324a6cee?w=900&q=85',
            'description': 'Friendly illustrated characters, animated brand scenes, playful visual storytelling.',
            'prompt': 'polished cartoon animation style with expressive illustrated characters, playful shapes, clean brand colors, social-media-ready composition',
        },
        {
            'id': 'product_studio',
            'name': 'Product Studio',
            'preview_image': 'https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=900&q=85',
            'description': 'Sharp product or service visuals, studio lighting, clean premium backgrounds.',
            'prompt': 'premium product studio photography, sharp focus, clean background, controlled lighting, polished product or service hero composition',
        },
        {
            'id': 'editorial_lifestyle',
            'name': 'Editorial Lifestyle',
            'preview_image': 'https://images.unsplash.com/photo-1497366754035-f200968a6e72?w=900&q=85',
            'description': 'Human lifestyle moments with brand context, workplace scenes, editorial mood.',
            'prompt': 'editorial lifestyle photography with real people, workplace or customer context, cinematic but natural lighting, brand-specific story moment',
        },
    ]


def normalize_topic_items(items, kind, count, business, fallback_seed):
    cleaned = []
    if isinstance(items, list):
        for index, item in enumerate(items[:count]):
            title = item.get('title') if isinstance(item, dict) else str(item)
            title = str(title or '').strip()
            if title:
                cleaned.append({
                    'week_number': 1,
                    'position': index + 1,
                    'kind': kind,
                    'title': title,
                    'metadata': {
                        'source': 'gemini',
                        'angle': item.get('angle', '') if isinstance(item, dict) else '',
                    },
                })
    if len(cleaned) < count:
        raise RuntimeError(f'Gemini returned {len(cleaned)} {kind} topics; expected {count}.')
    return cleaned


def generate_weekly_topics(profile, brand, plan):
    social_count = max(1, int(plan.posts_per_week or 5))
    blog_count = nonnegative_int(getattr(plan, 'blog_posts_per_week', 0), 0)

    if os.getenv('ADVANCED_PIPELINE_ENABLED', 'false').lower() == 'true':
        try:
            result = orchestrate_generation(
                flow='topic_generation',
                user=profile.user,
                workspace=profile.workspace,
                payload={'social_count': social_count, 'blog_count': blog_count},
                campaign_context={'plan_id': str(plan.id) if plan else None}
            )
            if result.get('status') == 'completed' and result.get('topics'):
                social = result['topics'].get('social_topics')
                blog = result['topics'].get('blog_topics')
                business = business_name(profile)
                return (
                    normalize_topic_items(social, 'social', social_count, business, 'social content idea')
                    + normalize_topic_items(blog, 'blog', blog_count, business, 'blog article idea')
                )
        except Exception as e:
            from .context_builder import structured_log
            import logging
            structured_log(logging.getLogger(__name__), 'topic_generation_advanced_failed', error=str(e))

    # Legacy fallback
    info = brand_context(profile, brand, plan)
    business = info['profile'].get('name') or business_name(profile)
    social_count = max(1, int(plan.posts_per_week or 5))
    blog_count = nonnegative_int(getattr(plan, 'blog_posts_per_week', 0), 0)
    email_count = 0
    prompt = f"""
Create a first-week content topic plan for this exact business.

Business and brand context:
{compact_json(info)}

Rules:
- Generate exactly {social_count} social media post topics.
- Generate exactly {blog_count} blog topics.
- Topics must be based on the business profile, services, audience, positioning, keywords, selected platforms, visual style, and brand tone.
- Follow the selected content language for all visible topic text: {language_label_from_context(info)}.
- Reflect the selected content style in topic angles where useful: {compact_json(info.get('content_style'))}.
- Do not use generic software/web-development preset topics unless the business actually sells that.
- Each topic should feel specific enough that the business owner can recognize it as their brand.
- Cover different angles: pain point, proof/benefit, education, objection handling, brand story, offer/use case, trust.
- Keep titles concise but concrete, suitable for content planning.
- Do not write captions; only topic titles.
- Blog topics should be long-form article ideas.

Return JSON only in this shape:
{{
  "social_topics": [
    {{"title": "topic title", "angle": "pain_point|education|proof|story|offer|objection|trust"}}
  ],
  "blog_topics": [
    {{"title": "blog topic title", "angle": "education|proof|guide|comparison"}}
  ],
  "email_topics": []
}}
""".strip()
    generated = generate_with_gpt(prompt)
    if not isinstance(generated, dict):
        raise RuntimeError('Gemini did not return a topic JSON object.')
    social = generated.get('social_topics') or generated.get('topics')
    blog = generated.get('blog_topics')
    return (
        normalize_topic_items(social, 'social', social_count, business, 'social content idea')
        + normalize_topic_items(blog, 'blog', blog_count, business, 'blog article idea')
    )


def topic_titles(plan, kind):
    return [topic.title for topic in plan.topics.filter(kind=kind).order_by('position', 'created_at')]


def generate_blog_email_plan(profile, brand, plan):
    info = brand_context(profile, brand, plan)
    blog_count = nonnegative_int(getattr(plan, 'blog_posts_per_week', 0), 0)
    email_count = 0
    if blog_count == 0:
        return {'blog_plan': {'items': []}, 'email_plan': {'items': []}}
    blog_topics = topic_titles(plan, 'blog')
    prompt = f"""
Create a brand-specific blog plan for the same first-week campaign.

Business and brand context:
{compact_json(info)}

Approved blog topics:
{compact_json(blog_topics)}

Rules:
- Must be specific to this business, audience, services, brand tone, platforms, and selected visual style.
- Write all visible titles, outlines, and section headings in this language: {language_label_from_context(info)}.
- Generate exactly {blog_count} blog plan items.
- Each blog plan needs a concrete title, outline, sections, and exactly two image placements: cover and inline.
- Do not use generic React/Python/custom-development topics unless this business actually sells those.

Return JSON only in this shape:
{{
  "blog_plan": {{
    "items": [
      {{
        "title": "specific blog title",
        "outline": ["point 1", "point 2", "point 3"],
        "sections": [
          {{"heading": "section heading", "goal": "section goal"}}
        ],
        "image_placements": [
          {{"slot": "cover", "prompt_role": "cover image direction", "aspect_ratio": "16:9"}},
          {{"slot": "inline", "prompt_role": "inline image direction", "aspect_ratio": "4:3"}}
        ]
      }}
    ]
  }},
  "email_plan": {{"items": []}}
}}
""".strip()
    generated = generate_with_gpt(prompt)
    if isinstance(generated, dict) and isinstance(generated.get('blog_plan'), dict) and isinstance(generated.get('email_plan'), dict):
        return normalize_blog_email_plan(generated, profile, plan)
    raise RuntimeError('Gemini did not return a valid blog plan JSON object.')


def normalize_blog_email_plan(payload, profile=None, plan=None):
    business = business_name(profile) if profile else 'Your brand'
    blog_count = nonnegative_int(getattr(plan, 'blog_posts_per_week', 0), 0)
    email_count = 0
    blog_plan = payload.get('blog_plan') if isinstance(payload, dict) else {}
    raw_blogs = blog_plan.get('items') if isinstance(blog_plan.get('items'), list) else [blog_plan]
    blog_items = []
    for index, item in enumerate(raw_blogs[:blog_count]):
        if not isinstance(item, dict):
            item = {'title': str(item)}
        title = clean_campaign_label(item.get('title'), business) if item.get('title') else f'{business}: Practical customer guide'
        placements = item.get('image_placements')
        if not isinstance(placements, list) or len(placements) < 2:
            placements = [
                {'slot': 'cover', 'prompt_role': 'brand-aligned blog cover image', 'aspect_ratio': '16:9'},
                {'slot': 'inline', 'prompt_role': 'supporting image for the article body', 'aspect_ratio': '4:3'},
            ]
        blog_items.append({**item, 'title': title, 'image_placements': placements[:2]})
    while len(blog_items) < blog_count:
        blog_items.append({
            'title': fallback_topic_from_context(f'{business}: Practical customer guide', len(blog_items), 'blog', business),
            'outline': ['Customer problem', 'Brand-specific approach', 'Next step'],
            'sections': [{'heading': 'The practical path', 'goal': 'Explain the idea clearly.'}],
            'image_placements': [
                {'slot': 'cover', 'prompt_role': 'brand-aligned blog cover image', 'aspect_ratio': '16:9'},
                {'slot': 'inline', 'prompt_role': 'supporting image for the article body', 'aspect_ratio': '4:3'},
            ],
        })
    return {'blog_plan': {'items': blog_items}, 'email_plan': {'items': []}}


def validate_campaign_week_payload(item, index, plan):
    if not isinstance(item, dict):
        raise RuntimeError(f'Campaign week {index + 1} is not a JSON object.')
    raw_plan = item.get('item_plan') if isinstance(item.get('item_plan'), dict) else {}
    required = ('title', 'theme', 'call_to_action', 'audience')
    missing = [field for field in required if not str(raw_plan.get(field) or item.get(field) or '').strip()]
    if missing:
        raise RuntimeError(f'Campaign week {index + 1} is missing fields: {", ".join(missing)}.')
    prompts = raw_plan.get('post_prompts')
    if not isinstance(prompts, list):
        raise RuntimeError(f'Campaign week {index + 1} is missing post_prompts.')
    social_count = max(1, int(plan.posts_per_week or 1)) if plan else 5
    blog_count = nonnegative_int(getattr(plan, 'blog_posts_per_week', 0), 0) if plan else 0
    expected = social_count + blog_count
    usable = [
        prompt for prompt in prompts
        if isinstance(prompt, dict)
        and str(prompt.get('type') or 'social').strip().lower() != 'email'
        and str(prompt.get('topic') or prompt.get('title') or '').strip()
    ]
    if len(usable) < expected:
        raise RuntimeError(f'Campaign week {index + 1} returned {len(usable)} usable prompts; expected {expected}.')


def generate_campaign_weeks(profile, brand, plan, allow_fallback=False):
    if os.getenv('ADVANCED_PIPELINE_ENABLED', 'false').lower() == 'true':
        try:
            result = orchestrate_generation(
                flow='campaign_generation',
                user=profile.user,
                workspace=profile.workspace,
                payload={'plan': plan},
                campaign_context={'plan_id': str(plan.id) if plan else None}
            )
            if result.get('status') == 'completed' and result.get('campaign_plan'):
                weeks = result['campaign_plan'].get('weeks')
                if isinstance(weeks, list) and len(weeks) >= 4:
                    cleaned = []
                    for index, item in enumerate(weeks[:4]):
                        validate_campaign_week_payload(item, index, plan)
                        cleaned.append({
                            'week_number': index + 1,
                            'theme': str(item.get('theme') or item.get('item_plan', {}).get('title') or '').strip(),
                            'funnel_goal': str(item.get('funnel_goal') or '').strip() or ['awareness', 'engagement', 'conversion', 'retention'][index],
                            'item_plan': normalize_campaign_item_plan(item, profile, brand, plan, index),
                        })
                    return cleaned
        except Exception as e:
            from .context_builder import structured_log
            import logging
            structured_log(logging.getLogger(__name__), 'campaign_generation_advanced_failed', error=str(e))

    # Legacy fallback
    info = brand_context(profile, brand, plan)
    prompt = f"""
Create a 4-week executive-grade marketing campaign plan for this exact business.

Business and brand context:
{compact_json(info)}

Rules:
- Generate exactly 4 weeks.
- Week 1 should feed immediate first-week content.
- Weeks should follow a sensible marketing arc: awareness, engagement, conversion, retention or advocacy.
- Make each campaign feel like a real marketing team could brief creative, copy, and media from it.
- Make every title, theme, CTA, audience, and post prompt specific to the business, services, audience, positioning, brand voice, visual style, content style, and platform mix.
- Each week needs exactly {max(1, int(plan.posts_per_week or 1)) if plan else 5} social prompts and {nonnegative_int(getattr(plan, 'blog_posts_per_week', 0), 0) if plan else 0} blog prompts. Do not create email prompts.
- Write visible text in this language: {language_label_from_context(info)}.
- post_prompts[].topic must be a content topic or posting idea only. It must never be an image-generation prompt, caption draft, camera direction, lighting direction, visual composition, or instruction like "a shot of...".
- Image-generation prompts will be created later by the backend from the topic plus brand kit, logo, product references, and content style.

Return JSON only:
{{
  "weeks": [
    {{
      "week_number": 1,
      "theme": "short campaign title",
      "funnel_goal": "awareness|engagement|conversion|retention",
      "item_plan": {{
        "title": "campaign list title",
        "campaign_type": "Thought Leadership",
        "theme": "detailed campaign strategy paragraph",
        "call_to_action": "specific CTA",
        "audience": "specific audience",
        "post_prompts": [
          {{"type": "social", "topic": "specific content topic", "platforms": ["facebook", "instagram"], "status": "draft"}}
        ]
      }}
    }}
  ]
}}
""".strip()
    generated = generate_with_gpt(prompt)
    if not isinstance(generated, dict) and not allow_fallback:
        raise RuntimeError('Gemini did not return a campaign plan JSON object.')
    weeks = generated.get('weeks') if isinstance(generated, dict) else None
    if not isinstance(weeks, list) or len(weeks) < 4:
        raise RuntimeError('Gemini campaign planner returned fewer than 4 weeks.')
    cleaned = []
    if isinstance(weeks, list):
        for index, item in enumerate(weeks[:4]):
            if not isinstance(item, dict):
                continue
            validate_campaign_week_payload(item, index, plan)
            cleaned.append({
                'week_number': int(item.get('week_number') or index + 1),
                'theme': str(item.get('theme') or item.get('item_plan', {}).get('title') or '').strip(),
                'funnel_goal': str(item.get('funnel_goal') or '').strip() or ['awareness', 'engagement', 'conversion', 'retention'][index],
                'item_plan': normalize_campaign_item_plan(item, profile, brand, plan, index),
            })
    if not cleaned and not allow_fallback:
        raise RuntimeError('Gemini returned no campaign weeks.')
    if len(cleaned) < 4 and not allow_fallback:
        raise RuntimeError(f'Gemini returned {len(cleaned)} campaign weeks; expected 4.')
    for index, item in enumerate(cleaned[:4]):
        item['week_number'] = index + 1
        item['item_plan'] = normalize_campaign_item_plan(item, profile, brand, plan, index)
        item['theme'] = item['item_plan'].get('title') or item['theme']
    return cleaned[:4]


def platform_caption(topic, platform, profile, brand):
    business = business_name(profile) if profile else 'Our team'
    rule = PLATFORM_RULES.get(platform, 'clear and useful')
    title = topic.title if hasattr(topic, 'title') else str(topic)
    info = brand_context(profile, brand)
    prompt = f"""
Write a finished social caption for one specific platform.

Business and brand context:
{compact_json(info)}

Topic:
{title}

Platform:
{platform}

Platform tone rule:
{rule}

Rules:
- Write in this language: {language_label_from_context(info)}.
- Make it specific to the business, services, audience, offer, and brand positioning.
- Match the selected content style, but do not describe the style directly.
- Facebook: casual, engaging, conversational.
- Instagram: visual storytelling, emotional.
- LinkedIn: professional, research-based, authority tone.
- X/Twitter: short, punchy, high engagement, max 280 characters.
- No markdown. No bullet list. No generic filler.

Return JSON only:
{{"caption": "finished caption"}}
""".strip()
    generated = generate_with_gpt(prompt)
    if isinstance(generated, dict) and str(generated.get('caption') or '').strip():
        caption = str(generated['caption']).strip()
        if platform in ('x', 'twitter') and len(caption) > 280:
            caption = caption[:277].rstrip() + '...'
        return caption
    raise RuntimeError(f'Gemini did not return a valid {platform} caption.')


def generate_blog_email_content(profile, brand, plan, blog_email_plan):
    """Generate blog content using advanced pipeline if enabled."""
    is_advanced = os.getenv('ADVANCED_PIPELINE_ENABLED', 'false').lower() == 'true'
    info = brand_context(profile, brand, plan)
    blog_plan = getattr(blog_email_plan, 'blog_plan', {}) or {}
    items = blog_plan.get('blog_prompts', []) or []

    if is_advanced:
        try:
            from content_engine.services.generation_orchestrator import orchestrate_generation
            blogs = []
            for item in items:
                result = orchestrate_generation(
                    user=profile.user if profile else None,
                    workspace=profile.workspace if profile else None,
                    flow='create_blog',
                    payload={'blog_plan_item': item},
                    correlation_id=f"blog_{getattr(blog_email_plan, 'id', 'new')}_{items.index(item)}"
                )
                if result.get('status') == 'completed' and 'blog_content' in result:
                    blogs.append(_map_advanced_blog_to_legacy(result['blog_content']))

            if blogs:
                return {'blogs': blogs, 'emails': []}

        except Exception as e:
            logger.error(f"Advanced blog generation failed: {str(e)}", exc_info=True)
            # Fallback to legacy

    # Legacy Pipeline
    prompt = f"""
Generate full first-week blog content from the approved plan.

Business and brand context:
{compact_json(info)}

Approved blog plan:
{compact_json(blog_plan)}

Rules:
- Write every visible word in this language: {language_label_from_context(info)}.
- Generate one complete publishable article for every blog plan item, not only outlines.
- Use the business profile, services, audience, tone, brand colors, font, platforms, and content style.
- Keep the content specific enough that it clearly belongs to this business.
- Include image prompts for every blog cover image and every blog inline image.
- Avoid generic software examples unless the business actually sells software.

Return JSON only:
{{
  "blogs": [
    {{
      "title": "publishable blog title",
      "excerpt": "short summary",
      "body": "complete blog article with clean section headings and paragraphs",
      "cover_image_prompt": "image prompt",
      "inline_image_prompt": "image prompt"
    }}
  ]
}}
""".strip()
    generated = generate_with_gpt(prompt)
    if isinstance(generated, dict):
        if isinstance(generated.get('blogs'), list) or isinstance(generated.get('emails'), list):
            return {
                'blogs': [item for item in generated.get('blogs', []) if isinstance(item, dict)],
                'emails': [],
            }
        if isinstance(generated.get('blog'), dict):
            return {'blogs': [generated['blog']], 'emails': []}

    raise RuntimeError('Gemini did not return valid blog content JSON.')


def _map_advanced_blog_to_legacy(advanced_blog):
    """Map the rich advanced blog schema back to the legacy shape."""
    # Build body from sections
    body_parts = []
    if advanced_blog.get('intro'):
        body_parts.append(advanced_blog['intro'])

    for section in advanced_blog.get('sections', []):
        if section.get('heading'):
            body_parts.append(f"\n## {section['heading']}")
        if section.get('content'):
            body_parts.append(section['content'])

    if advanced_blog.get('faq'):
        body_parts.append("\n## Frequently Asked Questions")
        for qa in advanced_blog['faq']:
            body_parts.append(f"**Q: {qa.get('question')}**")
            body_parts.append(f"A: {qa.get('answer')}")

    if advanced_blog.get('cta'):
        body_parts.append(f"\n{advanced_blog['cta']}")

    return {
        'title': advanced_blog.get('title', 'Untitled Blog'),
        'excerpt': advanced_blog.get('meta_description', advanced_blog.get('intro', '')[:160]),
        'body': '\n\n'.join(body_parts),
        'cover_image_prompt': advanced_blog.get('featured_image_prompt', ''),
        'inline_image_prompt': advanced_blog.get('inline_image_prompt', ''),
        'meta_title': advanced_blog.get('meta_title', ''),
        'meta_description': advanced_blog.get('meta_description', ''),
        'slug': advanced_blog.get('slug', ''),
        'keywords': advanced_blog.get('keywords', []),
    }


def schedule_dates(count):
    start = date.today()
    return [start + timedelta(days=i) for i in range(count)]
