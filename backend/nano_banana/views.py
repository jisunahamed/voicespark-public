import os
import logging
import base64
import re
import mimetypes
import uuid
from io import BytesIO
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from django.http import HttpResponse, JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
import requests
import time
import threading

import nano_banana
import workspace
from fb_auth.models import FacebookPage, FacebookToken, InstagramToken
from linkedin_auth.models import LinkedinToken
from utils.celery.tasks import make_posts

from auth_user.models import UserProfile, ImageUrl
from workspace.models import Workspace
from x_auth.models import Auth1Xtoken, XToken
from .models import NanoBananaImage, NanoGenerationJob
from django.contrib.auth.models import User
from django.db.models import Q
from utils.chatbot import ChatGPT, gemini_text, gemini_error_payload
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from rest_framework import status
from utils.automation import analyse_link

logger = logging.getLogger(__name__)
from datetime import datetime, timedelta, timezone
from django.utils import timezone as timezone2
from django.test import RequestFactory
import json
from auth_user.models import ScheduledPost, UploadImages
from celery import current_app
from django.core.files.temp import NamedTemporaryFile
from django.core.files import File
from django.core.files.base import ContentFile
from content_engine.services.gemini_image import (
    business_name_from_profile,
    first_reference_url,
    generate_image,
    placeholder_image,
)
# GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

PLATFORM_CAPTION_KEYS = ('instagram', 'facebook', 'linkedin', 'twitter')
APPROVAL_TASK_PREFIX = 'approval:'


ASYNC_NANO_JOB_TYPES = {'create_post', 'regenerate_image', 'edit_generated_image'}
NANO_JOB_TIMEOUT_MINUTES = int(os.getenv('NANO_GENERATION_JOB_TIMEOUT_MINUTES', '20') or 20)

# Feature flag: advanced AI pipeline. Toggle via env var. Old pipeline remains default.
ADVANCED_PIPELINE = os.getenv('ADVANCED_PIPELINE_ENABLED', '').lower() in ('1', 'true', 'yes')


def should_enqueue_generation(request):
    return not parse_request_bool(request.data.get('force_sync', False))


def enqueue_nano_generation_job(request, job_type, user, workspace=None, nano_banana=None, payload=None):
    if job_type not in ASYNC_NANO_JOB_TYPES:
        return None
    from .tasks import run_nano_generation_job

    clean_payload = dict(payload or request.data)
    clean_payload.pop('force_sync', None)
    if workspace is not None:
        clean_payload['workspace_id'] = str(workspace.id)
    if nano_banana is not None:
        clean_payload['nano_banana_id'] = str(nano_banana.id)
    job = NanoGenerationJob.objects.create(
        user=user,
        workspace=workspace,
        nano_banana=nano_banana,
        job_type=job_type,
        status='queued',
        payload=clean_payload,
    )
    try:
        run_nano_generation_job.apply_async(args=[str(job.id)], queue='make_posts')
    except Exception as exc:
        logger.warning("Nano generation Celery enqueue failed job=%s type=%s: %s. Falling back to inline thread.", job.id, job_type, exc)
        worker = threading.Thread(target=run_nano_generation_job.run, args=(str(job.id),), daemon=True)
        worker.start()
    return Response({
        'job_id': str(job.id),
        'status': job.status,
        'poll_url': f'/nano-banana/generation-job/{job.id}/',
    }, status=status.HTTP_202_ACCEPTED)


def mark_stale_nano_generation_job(job):
    if job.status not in ('queued', 'running'):
        return job
    cutoff = timezone2.now() - timedelta(minutes=NANO_JOB_TIMEOUT_MINUTES)
    if job.updated_at and job.updated_at < cutoff:
        job.status = 'failed'
        job.error = f'Generation timed out after {NANO_JOB_TIMEOUT_MINUTES} minutes. Please retry.'
        job.result = {
            'error': job.error,
            'error_type': 'timeout',
            'retryable': True,
        }
        job.save(update_fields=['status', 'error', 'result', 'updated_at'])
        logger.warning("Marked stale Nano generation job failed job=%s type=%s", job.id, job.job_type)
    return job


class NanoGenerationJobStatus(APIView):
    def get(self, request, job_id):
        job = NanoGenerationJob.objects.filter(id=job_id).first()
        if job is None:
            return Response({'error': 'Generation job was not found.'}, status=status.HTTP_404_NOT_FOUND)
        if request.user.is_authenticated and job.user_id != request.user.id:
            return Response({'error': 'Generation job was not found.'}, status=status.HTTP_404_NOT_FOUND)
        job = mark_stale_nano_generation_job(job)
        is_terminal = job.status in ('completed', 'failed')
        return Response({
            'job_id': str(job.id),
            'status': job.status,
            'job_type': job.job_type,
            'result': job.result or {},
            'error': job.error,
            'updated_at': job.updated_at.isoformat() if job.updated_at else None,
            'is_terminal': is_terminal,
            'retryable': job.status == 'failed',
        })


def get_by_numeric_id(model, raw_id):
    if raw_id in (None, ''):
        return None
    try:
        return model.objects.filter(id=int(raw_id)).first()
    except (TypeError, ValueError):
        return None


def get_user_by_id(raw_id):
    return get_by_numeric_id(User, raw_id)


def get_workspace_by_id(raw_id):
    if raw_id in (None, ''):
        return None
    return Workspace.objects.filter(id=str(raw_id)).first()


def get_nano_by_id(raw_id, user=None):
    if raw_id in (None, ''):
        return None
    try:
        nano_id = uuid.UUID(str(raw_id))
    except (TypeError, ValueError):
        return None
    qs = NanoBananaImage.objects.filter(id=nano_id)
    if user is not None:
        qs = qs.filter(user=user)
    return qs.first()


def get_platform_captions(nano_banana):
    captions = nano_banana.platform_captions or {}
    base_caption = nano_banana.caption or ''
    return {
        key: captions.get(key) or base_caption
        for key in PLATFORM_CAPTION_KEYS
    }


def set_default_platform_captions(nano_banana, caption):
    nano_banana.platform_captions = {key: caption or '' for key in PLATFORM_CAPTION_KEYS}


def smart_captions_enabled(user_profile):
    return profile_content_preferences(user_profile).get('smart_captions', {}).get('enabled', True)


def set_platform_captions_for_profile(nano_banana, user_profile, caption, topic='', target_platform='multi-platform'):
    if not smart_captions_enabled(user_profile):
        set_default_platform_captions(nano_banana, caption)
        return
    if target_platform == 'multi-platform' and nano_banana.platform_captions:
        current = get_platform_captions(nano_banana)
        nano_banana.platform_captions = {key: current.get(key) or caption or '' for key in PLATFORM_CAPTION_KEYS}
        return
    captions = {}
    for platform in PLATFORM_CAPTION_KEYS:
        captions[platform] = safe_generate_caption(
            user_profile,
            previous_caption=caption,
            topic=topic,
            target_platform=platform,
        )
    nano_banana.platform_captions = captions


def get_nano_meta(nano_banana):
    captions = nano_banana.platform_captions or {}
    meta = captions.get('__meta__') or captions.get('__meta')
    return meta if isinstance(meta, dict) else {}


def save_nano_meta(nano_banana, patch):
    captions = nano_banana.platform_captions or {}
    meta = get_nano_meta(nano_banana)
    meta.update(patch or {})
    captions['__meta'] = meta
    nano_banana.platform_captions = captions
    nano_banana.save(update_fields=['platform_captions'])
    return meta


PLATFORM_ALIASES = {
    'x': 'twitter',
    'twitter': 'twitter',
    'fb': 'facebook',
    'facebook': 'facebook',
    'ig': 'instagram',
    'insta': 'instagram',
    'instagram': 'instagram',
    'li': 'linkedin',
    'linkedin': 'linkedin',
    'wp': 'wordpress',
    'wordpress': 'wordpress',
}


def normalize_platform_list(value):
    if value is None:
        return []
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, (list, tuple, set)):
        return []
    normalized = []
    for item in value:
        key = PLATFORM_ALIASES.get(str(item).strip().lower())
        if key and key not in normalized:
            normalized.append(key)
    return normalized


def celery_task_id_for_control(task_id):
    if task_id and task_id.startswith(APPROVAL_TASK_PREFIX):
        return task_id[len(APPROVAL_TASK_PREFIX):]
    return task_id


def profile_content_preferences(user_profile):
    brand_voice = user_profile.brand_voice if user_profile and isinstance(user_profile.brand_voice, dict) else {}
    preferences = brand_voice.get('content_preferences') if isinstance(brand_voice.get('content_preferences'), dict) else {}
    smart_captions = preferences.get('smart_captions') if isinstance(preferences.get('smart_captions'), dict) else {}
    return {
        'timezone': str(preferences.get('timezone') or 'Asia/Dhaka'),
        'default_schedule_time': str(preferences.get('default_schedule_time') or '09:00'),
        'smart_captions': {'enabled': bool(smart_captions.get('enabled', True))},
    }


def user_timezone(user, workspace=None):
    profile = get_generation_profile(user, workspace)
    prefs = profile_content_preferences(profile)
    try:
        return ZoneInfo(prefs['timezone'])
    except Exception:
        return ZoneInfo('Asia/Dhaka')


def default_schedule_parts(user, workspace=None):
    profile = get_generation_profile(user, workspace)
    prefs = profile_content_preferences(profile)
    raw = prefs.get('default_schedule_time') or '09:00'
    match = re.match(r'^(\d{1,2}):(\d{2})$', raw)
    if not match:
        return 9, 0
    hour = min(23, max(0, int(match.group(1))))
    minute = min(59, max(0, int(match.group(2))))
    return hour, minute


def local_now(user, workspace=None):
    return timezone2.now().astimezone(user_timezone(user, workspace))


def default_run_at_for_day(user, workspace=None, day_offset=0):
    now_local = local_now(user, workspace)
    hour, minute = default_schedule_parts(user, workspace)
    run_at = now_local.replace(hour=hour, minute=minute, second=0, microsecond=0) + timedelta(days=day_offset)
    if day_offset == 0 and run_at <= now_local:
        run_at = now_local + timedelta(minutes=5)
    return run_at


def safe_generation_run_at(value, user, workspace=None):
    if not value:
        return default_run_at_for_day(user, workspace)
    try:
        text = str(value).strip()
        if re.match(r'^\d{4}-\d{2}-\d{2}$', text):
            date_value = datetime.fromisoformat(text).date()
            hour, minute = default_schedule_parts(user, workspace)
            parsed = datetime.combine(date_value, datetime.min.time()).replace(hour=hour, minute=minute)
        else:
            parsed = datetime.fromisoformat(text.replace('Z', '+00:00'))
        if timezone2.is_naive(parsed):
            parsed = timezone2.make_aware(parsed, user_timezone(user, workspace))
        if parsed <= timezone2.now():
            return timezone2.now() + timedelta(minutes=5)
        return parsed
    except Exception as exc:
        logger.warning("Invalid generation run_at %r, using default: %s", value, exc)
        return default_run_at_for_day(user, workspace)


def parse_schedule_iso(value):
    if not value:
        return None
    aware_dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if aware_dt.tzinfo is None:
        aware_dt = timezone2.make_aware(aware_dt)
    return aware_dt


def enqueue_publish_task(schedule_obj, user, post_now=False):
    if schedule_obj.task_id:
        current_app.control.revoke(celery_task_id_for_control(schedule_obj.task_id), terminate=True)
    eta = timezone2.now() if post_now else schedule_obj.scheduled_at
    task_id = str(uuid.uuid4())
    result = make_posts.apply_async(
        args=[{
            'user_id': user.id,
            'text': schedule_obj.nano_banana.caption,
            'nano_banana_id': str(schedule_obj.nano_banana.id),
            'expected_task_id': task_id,
        }],
        eta=eta,
        task_id=task_id,
    )
    schedule_obj.task_id = str(result.id)
    schedule_obj.save(update_fields=['task_id'])
    return result


def get_generation_profile(user, workspace=None):
    if workspace:
        return UserProfile.objects.filter(user=user, workspace=workspace).first()
    return UserProfile.objects.filter(user=user).first()


def approval_required_for_workspace(user, workspace):
    profile = UserProfile.objects.filter(user=user, workspace=workspace).first()
    if profile is None:
        return True
    return bool(profile.approval_toggle)


def initial_generated_approval(user, workspace, queue='calendar'):
    if queue == 'approval':
        return 'ready'
    return 'not_approved' if approval_required_for_workspace(user, workspace) else 'approved'


def get_generation_business_profile(user, workspace=None):
    try:
        from content_engine.models import BusinessProfile
        qs = BusinessProfile.objects.filter(user=user)
        if workspace:
            qs = qs.filter(workspace=workspace)
        return qs.order_by('-updated_at').first()
    except Exception:
        return None


def get_generation_brand_setting(user, workspace=None, business_profile=None):
    try:
        from content_engine.models import BrandSetting
        qs = BrandSetting.objects.filter(user=user)
        if workspace:
            qs = qs.filter(workspace=workspace)
        if business_profile:
            qs = qs.filter(Q(business_profile=business_profile) | Q(business_profile__isnull=True))
        return qs.order_by('-business_profile_id', '-updated_at').first()
    except Exception:
        return None


def resolve_generation_context(user, workspace=None):
    business_profile = get_generation_business_profile(user, workspace)
    return {
        'user_profile': get_generation_profile(user, workspace),
        'business_profile': business_profile,
        'brand_setting': get_generation_brand_setting(user, workspace, business_profile),
    }


def generation_brand_name(context, workspace=None):
    return (
        business_name_from_profile((context or {}).get('business_profile'))
        if (context or {}).get('business_profile')
        else business_name_from_profile((context or {}).get('user_profile') or workspace)
    )


def reference_meta_patch(image_urls, extra=None):
    refs = dedupe_reference_urls(image_urls or [], limit=12)
    patch = {
        'reference_images': refs,
        'primary_reference_url': refs[0] if refs else '',
        'reference_lock': bool(refs),
    }
    if isinstance(extra, dict):
        patch.update(extra)
    return patch


def get_brand_style(user_profile):
    brand_voice = user_profile.brand_voice if isinstance(user_profile.brand_voice, dict) else {}
    brand_style = brand_voice.get("brand_style", {})
    return brand_style if isinstance(brand_style, dict) else {}


def approval_generation_key(workspace):
    return str(workspace.id) if workspace else 'default'


def approval_generation_dates(user_profile):
    brand_voice = user_profile.brand_voice if isinstance(user_profile.brand_voice, dict) else {}
    dates = brand_voice.get('approval_generation_dates', {})
    return dates if isinstance(dates, dict) else {}


def mark_approval_generation_date(user_profile, workspace, date_value):
    brand_voice = user_profile.brand_voice if isinstance(user_profile.brand_voice, dict) else {}
    dates = brand_voice.get('approval_generation_dates', {})
    if not isinstance(dates, dict):
        dates = {}
    dates[approval_generation_key(workspace)] = date_value.isoformat()
    brand_voice['approval_generation_dates'] = dates
    user_profile.brand_voice = brand_voice
    user_profile.save(update_fields=['brand_voice'])


def clear_approval_generation_date(user_profile, workspace, date_value):
    brand_voice = user_profile.brand_voice if isinstance(user_profile.brand_voice, dict) else {}
    dates = brand_voice.get('approval_generation_dates', {})
    key = approval_generation_key(workspace)
    if isinstance(dates, dict) and dates.get(key) == date_value.isoformat():
        dates.pop(key, None)
        brand_voice['approval_generation_dates'] = dates
        user_profile.brand_voice = brand_voice
        user_profile.save(update_fields=['brand_voice'])


def compact_json(value):
    try:
        return json.dumps(value or {}, ensure_ascii=False)
    except TypeError:
        return "{}"


def build_brand_context(user_profile):
    brand_voice = user_profile.brand_voice if isinstance(user_profile.brand_voice, dict) else {}
    brand_style = get_brand_style(user_profile)
    content_preferences = brand_voice.get("content_preferences", {}) if isinstance(brand_voice.get("content_preferences", {}), dict) else {}
    logos = [item.get("url") for item in brand_style.get("logos", []) if isinstance(item, dict) and item.get("url")]
    colors = brand_style.get("colors", [])
    fonts = brand_style.get("fonts", [])
    visual_style = brand_style.get("visual_style", {})
    visual_identity = brand_style.get("visual_identity", "")
    intelligence = {}
    try:
        from content_engine.models import AudienceProfile, BrandManualData, ChannelVoiceConfig, CompetitorAnalysis
        intelligence = {
            "channel_voice": [
                {
                    "platform": item.platform,
                    "tone": item.tone,
                    "emotion": item.emotion,
                    "character": item.character,
                    "syntax": item.syntax,
                    "language": item.language,
                }
                for item in ChannelVoiceConfig.objects.filter(user=user_profile.user, workspace=user_profile.workspace)
            ],
            "audience_profiles": [
                {
                    "name": item.name,
                    "age_range": item.age_range,
                    "location": item.location,
                    "occupation": item.occupation,
                    "pain_points": item.pain_points,
                    "frustrations": item.frustrations,
                    "goals": item.goals,
                    "behaviors": item.behaviors,
                    "buying_patterns": item.buying_patterns,
                    "awareness_level": item.awareness_level,
                }
                for item in AudienceProfile.objects.filter(user=user_profile.user, workspace=user_profile.workspace)[:8]
            ],
            "manual_business_data": (
                {
                    "processes": manual.processes,
                    "methodology": manual.methodology,
                    "deliverables": manual.deliverables,
                    "pricing": manual.pricing,
                    "onboarding": manual.onboarding,
                }
                if (manual := BrandManualData.objects.filter(user=user_profile.user, workspace=user_profile.workspace).first())
                else {}
            ),
            "competitors": [
                {
                    "name": item.name,
                    "website_url": item.website_url,
                    "pricing_model": item.pricing_model,
                    "key_features": item.key_features,
                    "differentiators": item.differentiators,
                }
                for item in CompetitorAnalysis.objects.filter(user=user_profile.user, workspace=user_profile.workspace)[:8]
            ],
        }
    except Exception:
        intelligence = {}
    return f"""
Business profile markdown:
{user_profile.markdown}

Brand voice JSON:
{compact_json({key: value for key, value in brand_voice.items() if key != "brand_style"})}

Brand style:
- Logo references: {", ".join(logos) if logos else "No logo available"}
- Brand colors: {", ".join(colors) if colors else "No colors available"}
- Brand fonts: {compact_json(fonts)}
- Visual style: {compact_json(visual_style)}
- Visual identity description: {visual_identity or "No visual identity description available"}
- Content preferences: {compact_json(content_preferences)}

Workspace brand intelligence:
{compact_json(intelligence)}
""".strip()


def build_caption_request(user_profile, topic="", previous_caption="", user_instruction="", target_platform="multi-platform"):
    task = "Create one short social media caption."
    if previous_caption:
        task = "Rewrite the existing caption into a fresh brand-aligned caption."
    return f"""
You are writing social content for one specific brand. Use the brand context below as mandatory direction.

{build_brand_context(user_profile)}

Task:
{task}

Target platform:
{target_platform}

Topic or campaign direction:
{topic or "Use the strongest relevant angle from the business profile."}

Existing caption, if any:
{previous_caption or "None"}

User edit instruction, if any:
{user_instruction or "None"}

Rules:
- Return only the caption as plain text.
- No markdown, no bullet list, no emojis.
- Make it sound specific to this brand, not generic.
- Reflect the brand voice, audience, offer, and positioning.
- Keep it concise enough for social media.
- Do not mention logo, font names, or hex colors in the caption unless the user explicitly asked.
""".strip()


def build_image_prompt_request(user_profile, caption, topic="", user_instruction="", target_platform="multi-platform", aspect_ratio="1:1", source_mode="text-to-image"):
    return f"""
You are creating the final image-generation prompt for Gemini native image generation. Use the brand context below as mandatory creative direction.

{build_brand_context(user_profile)}

Caption the image must support:
{caption}

Topic or campaign direction:
{topic or "None"}

User edit instruction, if any:
{user_instruction or "None"}

Target platform:
{target_platform}

Aspect ratio:
{aspect_ratio}

Generation mode:
{source_mode}

Write one detailed image prompt that tells the image model exactly what to create.

Write it like a production-grade "super prompt": concrete, visual, brand-specific, and ready to send directly to the image model. The prompt must include:
- Brand-specific subject matter tied to the business profile.
- The saved Visual style is mandatory. If it says Ultra Realistic, use real humans/places and do not create illustration. If it says Infographic, create a clean structured infographic. If it says Cartoon / Animated, create a polished illustrated animated look. If it says Product Studio or Editorial Lifestyle, follow that exact content style.
- Composition and framing suitable for the target platform and aspect ratio.
- Brand color direction using the available colors.
- Visual identity direction using the saved visual identity and visual style.
- Photography or illustration style, camera/lens or illustration treatment, lighting, background, mood, depth, texture, and level of realism.
- Clear subject hierarchy: main subject, supporting objects, background, negative space, and where the viewer's eye should go first.
- Platform fit: make the image work natively for the selected platform and aspect ratio.
- If source images are provided, instruct the model to preserve the brand/product/person identity and use them as concrete visual references, not loose inspiration.
- If brand logo references are provided, the exact supplied logo is mandatory in the final image as a clean corner lockup, product mark, packaging mark, signage, or natural UI mark.
- Preserve the brand logo exactly: no redesign, no altered letters, no changed colors, no warped shape, no invented replacement mark, no translation, and no stylized reinterpretation.
- If a product reference is provided, treat it as the immutable main product reference: keep the same product category, silhouette, cut, material, pattern, color family, scale, and recognizable details. Do not redesign or replace the product.
- If multiple references are provided, combine them intentionally: product as the main subject, logo as the brand mark, and other brand media as environment/style context.
- Text/no-text rule: avoid large readable text in the image unless the user explicitly requested text; if text is needed, keep it minimal and clean.
- Avoid generic stock-photo output.
- Avoid unrelated objects, fake UI, watermarks, clutter, malformed hands/faces, and random text.
- Negative constraints must be part of the prompt.

Return only the image-generation prompt as plain text. No markdown, no heading, no quotes.
""".strip()


GENERIC_MARKETING_LABEL_RE = re.compile(
    r'\b(?:campaign\s+week\s+\d+|week\s+\d+|practical\s+post\s+\d+|social\s+post\s+idea\s+\d+|blog\s+idea\s+\d+|caption\s*(?:number)?\s*\d+|prompt\s+\d+)\b',
    re.I,
)


def clean_generation_topic(value, fallback='brand update'):
    text = re.sub(r'\s+', ' ', str(value or '').strip())
    text = GENERIC_MARKETING_LABEL_RE.sub('', text).strip(' :-')
    if not text or text.lower() in {'awareness', 'engagement', 'conversion', 'retention', 'brand awareness'}:
        return fallback
    return text


def fallback_caption_text(previous_caption='', instruction='', topic=''):
    base = str(previous_caption or topic or '').strip()
    base = clean_generation_topic(base, 'Here is a practical update from our brand.')
    if not base:
        base = 'Create a clear, brand-aligned social post for this campaign.'
    if instruction:
        return f'{base}\n\nUpdated direction: {instruction}'.strip()
    return base


def safe_generate_caption(user_profile, previous_caption='', user_instruction='', topic='', target_platform='multi-platform'):
    if not user_profile or not user_profile.markdown:
        raise RuntimeError('Workspace brand profile is required before generating captions.')
    prompt = build_caption_request(
        user_profile,
        topic=topic,
        previous_caption=previous_caption,
        user_instruction=user_instruction,
        target_platform=target_platform,
    )
    generated = (gemini_text(
        prompt,
        system_prompt='You are a senior social media copywriter. Return only the caption as plain text.',
    ) or '').strip()
    generated = clean_generation_topic(generated, '')
    if not generated:
        raise RuntimeError('Gemini returned an empty caption.')
    return generated


def safe_generate_image_prompt(user_profile, caption, topic='', user_instruction='', target_platform='multi-platform', aspect_ratio='1:1', source_mode='text-to-image'):
    if not user_profile or not user_profile.markdown:
        raise RuntimeError('Workspace brand profile is required before generating image prompts.')
    prompt = build_image_prompt_request(
        user_profile,
        caption=caption,
        topic=topic,
        user_instruction=user_instruction,
        target_platform=target_platform,
        aspect_ratio=aspect_ratio,
        source_mode=source_mode,
    )
    generated = (gemini_text(
        prompt,
        system_prompt=(
            'You are an expert image prompt engineer. Return one final Gemini image prompt only, '
            'with no markdown and no explanation.'
        ),
    ) or '').strip()
    if not generated:
        raise RuntimeError('Gemini returned an empty image prompt.')
    return generated


def serialize_nano_banana(nano_banana, scheduled_post=None):
    if scheduled_post is None:
        scheduled_post = ScheduledPost.objects.filter(nano_banana=nano_banana).first()
    captions = nano_banana.platform_captions or {}
    meta = get_nano_meta(nano_banana)
    approved_platforms = normalize_platform_list(meta.get('approved_platforms'))
    caption_platforms = [
        key for key in captions.keys()
        if key in PLATFORM_CAPTION_KEYS and captions.get(key)
    ]
    
    imageurl = nano_banana.picture_url
    if imageurl and str(imageurl).startswith('/media/'):
        # On VPS, it serves media under /media/.
        # We prepend a default if BACKEND_URL is set, else we use the VPS domain.
        import os
        backend_url = os.getenv('BACKEND_URL', 'https://134-209-146-170.sslip.io')
        imageurl = f"{backend_url.rstrip('/')}{imageurl}"
        
    return {
        "nano_banana_id": str(nano_banana.id),
        "imageurl": imageurl,
        "title": nano_banana.caption,
        "platform_captions": get_platform_captions(nano_banana),
        "meta": meta,
        "content_type": meta.get('content_type', 'social'),
        "content_title": meta.get('title', ''),
        "approved_platforms": approved_platforms,
        "platforms": approved_platforms or caption_platforms,
        "scheduled_at": str(scheduled_post.scheduled_at) if scheduled_post else None,
        "approval": scheduled_post.approval if scheduled_post else None,
    }

def save_image_from_url(result_url, user, workspace=None):
    """
    Download an image from a URL and save it to the UploadImages model

    Args:
        result_url (str): URL of the image to download
        user (User): User instance to associate with the image

    Returns:
        UploadImages: The created instance or None if failed
    """
    try:
        # Download the image
        response = requests.get(result_url, stream=True, timeout=30)
        response.raise_for_status()  # Raise an error for bad status codes

        # Extract filename from URL or generate one
        if '?' in result_url:
            filename = result_url.split('/')[-1].split('?')[0]
        else:
            filename = result_url.split('/')[-1]

        # Ensure filename has an extension
        if not '.' in filename:
            content_type = response.headers.get('content-type', '')
            if 'jpeg' in content_type or 'jpg' in content_type:
                filename += '.jpg'
            elif 'png' in content_type:
                filename += '.png'
            elif 'gif' in content_type:
                filename += '.gif'
            else:
                filename += '.jpg'  # Default to jpg

        image_instance = UploadImages.objects.create(user=user, workspace=workspace)
        image_instance.image.save(filename, ContentFile(response.content), save=True)

        return image_instance

    except requests.RequestException as e:
        logger.warning("Error downloading image: %s", e)
        return None
    except Exception as e:
        logger.warning("Error saving image: %s", e)
        return None


def parse_request_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return bool(value)


def infer_edit_targets(prompt):
    text = (prompt or "").lower()
    caption_terms = (
        "caption", "copy", "text", "wording", "headline", "title", "description",
        "ক্যাপশন", "লেখা", "টেক্সট", "শিরোনাম",
    )
    image_terms = (
        "image", "photo", "picture", "visual", "design", "background", "color",
        "shirt", "logo", "layout", "lighting", "ছবি", "ইমেজ", "কালার", "রং",
        "ব্যাকগ্রাউন্ড", "ডিজাইন", "লোগো",
    )
    wants_caption = any(term in text for term in caption_terms)
    wants_image = any(term in text for term in image_terms)
    if not wants_caption and not wants_image:
        wants_image = True
    return wants_image, wants_caption


def get_logo_reference_urls(user_profile):
    if user_profile is None:
        return []
    brand_style = get_brand_style(user_profile)
    return [
        item.get("url")
        for item in brand_style.get("logos", [])
        if isinstance(item, dict) and item.get("url")
    ]


def dedupe_reference_urls(values, limit=9):
    refs = []
    seen = set()
    for value in values or []:
        if isinstance(value, dict):
            value = value.get('url') or value.get('image_url') or value.get('src')
        if not value:
            continue
        url = str(value).strip()
        if not url or url.lower() in {'none', 'null', 'undefined'}:
            continue
        key = url.split('?')[0].rstrip('/').lower()
        if key in seen:
            continue
        seen.add(key)
        refs.append(url)
        if len(refs) >= limit:
            break
    return refs


def get_nano_reference_urls(nano_banana):
    if nano_banana is None:
        return []
    meta = get_nano_meta(nano_banana)
    refs = []
    for key in ('reference_image_url', 'reference_image', 'reference_images', 'reference_media', 'image_assets'):
        value = meta.get(key)
        if isinstance(value, list):
            refs.extend(value)
        elif value:
            refs.append(value)
    return dedupe_reference_urls(refs, limit=12)


def media_reference_score(url, metadata, topic='', content_type='social'):
    text = ' '.join([
        str(topic or ''),
        str(metadata.get('label') or ''),
        str(metadata.get('detected_type') or ''),
        str(metadata.get('asset_type') or ''),
        str(metadata.get('alt') or ''),
        str(metadata.get('context_label') or ''),
        str(metadata.get('source_page') or ''),
    ]).lower()
    score = 0
    if any(token in text for token in ('product', 'shop', 'sku', 'shirt', 'pant', 'dress', 'shoe', 'price', 'catalog')):
        score += 80
    if any(token in str(topic or '').lower() for token in ('product', 'offer', 'sale', 'collection', 'launch', 'feature', 'shirt', 'pant', 'dress')):
        score += 30
    if any(token in text for token in ('hero', 'lifestyle', 'team', 'founder', 'workspace', 'about')):
        score += 25
    if any(token in text for token in ('logo', 'brand mark', 'favicon')):
        score += 15
    if content_type == 'blog' and any(token in text for token in ('hero', 'lifestyle', 'about', 'product')):
        score += 20
    if any(token in text for token in ('icon', 'sprite', 'tracking', 'placeholder', 'loader')):
        score -= 100
    return score


def get_brand_reference_urls(user_profile, topic='', content_type='social', include_existing=None, limit=9):
    if user_profile is None:
        return dedupe_reference_urls(include_existing or [], limit=limit)
    workspace = getattr(user_profile, 'workspace', None)
    user = getattr(user_profile, 'user', None)
    selected_refs = dedupe_reference_urls(include_existing or [], limit=limit)
    logo_refs = dedupe_reference_urls(get_logo_reference_urls(user_profile), limit=3)

    refs = []
    # The first existing reference is usually the selected product/source image.
    if selected_refs:
        refs.append(selected_refs[0])
    for logo in logo_refs:
        if logo not in refs:
            refs.append(logo)
    for selected in selected_refs[1:]:
        if selected not in refs:
            refs.append(selected)

    media_candidates = []
    try:
        from content_engine.models import MediaAsset
        qs = MediaAsset.objects.filter(user=user, workspace=workspace, asset_type='image').exclude(source__in=['generated', 'gemini', 'local-placeholder'])
        for asset in qs.order_by('-created_at')[:80]:
            if asset.url:
                media_candidates.append((media_reference_score(asset.url, asset.metadata or {}, topic, content_type), asset.url))
    except Exception:
        pass

    try:
        image_qs = ImageUrl.objects.filter(user=user, workspace=workspace)
        for image in image_qs.order_by('-created_at')[:80]:
            if image.image_url:
                media_candidates.append((media_reference_score(image.image_url, {}, topic, content_type), image.image_url))
    except Exception:
        pass

    for _score, url in sorted(media_candidates, key=lambda item: item[0], reverse=True):
        if len(refs) >= limit:
            break
        if _score < -20:
            continue
        if url and url not in refs:
            refs.append(url)
    return dedupe_reference_urls(refs, limit=limit)


def workspace_has_connected_platform(user, workspace):
    if user is None or workspace is None:
        return False
    return (
        FacebookPage.objects.filter(user=user, workspace=workspace).exists()
        or FacebookToken.objects.filter(user=user, workspace=workspace).exists()
        or InstagramToken.objects.filter(user=user, workspace=workspace).exists()
        or LinkedinToken.objects.filter(user=user, workspace=workspace).exists()
        or XToken.objects.filter(user=user, workspace=workspace).exists()
        or Auth1Xtoken.objects.filter(user=user, workspace=workspace).exists()
    )


def workspace_connected_platforms(user, workspace):
    if user is None or workspace is None:
        return []
    connected = []
    if FacebookPage.objects.filter(user=user, workspace=workspace).exists() or FacebookToken.objects.filter(user=user, workspace=workspace).exists():
        connected.append('facebook')
    if InstagramToken.objects.filter(user=user, workspace=workspace).exists():
        connected.append('instagram')
    if LinkedinToken.objects.filter(user=user, workspace=workspace).exists():
        connected.append('linkedin')
    if XToken.objects.filter(user=user, workspace=workspace).exists() or Auth1Xtoken.objects.filter(user=user, workspace=workspace).exists():
        connected.append('twitter')
    return connected


def bangladesh_now():
    return timezone2.now().astimezone(ZoneInfo("Asia/Dhaka"))


def calendar_run_at_for_day(day_offset=0, user=None, workspace=None):
    if user:
        return default_run_at_for_day(user, workspace, day_offset)
    now_local = bangladesh_now()
    run_at = now_local.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=day_offset)
    if day_offset == 0 and run_at <= now_local:
        run_at = now_local + timedelta(minutes=5)
    return run_at


def build_nanobanana_fallback_prompt(original_prompt, error_message="", attempt=1, mode="text-to-image", aspect_ratio="1:1"):
    original_prompt = (original_prompt or "").strip()
    error_message = (error_message or "The image provider rejected the previous prompt.").strip()
    source_rule = (
        "Use the provided source image only as a reference. Preserve real brand assets, logos, products, and people without redesigning them."
        if mode == "image-to-image"
        else "Create the image from scratch without needing a source image."
    )
    if attempt == 1:
        return f"""
Create a safe, brand-aligned social media image for aspect ratio {aspect_ratio}.

Previous prompt failed with this provider error:
{error_message}

Use this creative brief, but simplify anything that may be hard or unsafe for the model:
{original_prompt}

Fallback rules:
- {source_rule}
- Use a realistic commercial photography or polished editorial style.
- Keep the scene simple: one clear subject, clean background, natural lighting, professional composition.
- Avoid readable text, UI screenshots, watermarks, copyrighted characters, confusing instructions, clutter, or complex multi-panel layouts.
- If a logo reference is provided, keep the exact logo unchanged; otherwise do not invent a logo.
- Make the result specific to the brand and campaign, but prioritize successful image generation over complexity.
Return one finished image only.
""".strip()
    return f"""
Create a reliable fallback social media visual for aspect ratio {aspect_ratio}.

The image provider rejected earlier prompts. Make a simpler alternate concept inspired by this brief:
{original_prompt}

Hard constraints:
- {source_rule}
- No readable text in the image.
- No fake interface screens, no tiny typography, no complex hands, no crowded background, no copyrighted characters.
- Use a clean brand-colored studio scene, product/service metaphor, or lifestyle moment with one main subject.
- Professional lighting, sharp focus, balanced composition, high quality.
- If brand logo/source image exists, preserve it exactly and place it naturally; if not, use abstract brand colors and shapes only.
Return one finished image only.
""".strip()


def submit_and_poll_nanobanana(generate_url, task_url, headers, payload):
    try:
        submit_resp = requests.post(generate_url, json=payload, headers=headers, timeout=30)
        submit_resp.raise_for_status()
    except requests.RequestException as exc:
        return {
            "ok": False,
            "error": f"Failed to submit task: {str(exc)}",
            "status": 502,
            "task_id": None,
        }

    submit_data = submit_resp.json()
    if submit_data.get("code") not in (None, 200):
        return {
            "ok": False,
            "error": submit_data.get("msg") or "Nano Banana rejected the request.",
            "status": 402 if submit_data.get("code") == 402 else 502,
            "task_id": None,
        }

    task_id = (submit_data.get("data") or {}).get("taskId")
    if not task_id:
        return {
            "ok": False,
            "error": submit_data.get("msg") or "No taskId returned by API.",
            "status": 502,
            "task_id": None,
        }

    for _ in range(30):
        time.sleep(2)
        try:
            task_resp = requests.get(
                task_url,
                headers=headers,
                params={"taskId": task_id},
                timeout=10,
            )
            task_resp.raise_for_status()
        except requests.RequestException as exc:
            return {
                "ok": False,
                "error": f"Failed to poll task: {str(exc)}",
                "status": 502,
                "task_id": task_id,
            }

        task_data = task_resp.json()
        if task_data.get("code") not in (None, 200):
            return {
                "ok": False,
                "error": task_data.get("msg") or "Nano Banana task failed.",
                "status": 502,
                "task_id": task_id,
            }

        data = task_data.get("data") or {}
        success_flag = data.get("successFlag")
        if success_flag == 1:
            return {
                "ok": True,
                "data": data,
                "task_id": task_id,
                "error": None,
            }
        if success_flag in (2, 3):
            return {
                "ok": False,
                "error": data.get("errorMessage", "Generation failed."),
                "status": 502,
                "task_id": task_id,
            }

    return {
        "ok": False,
        "error": "Timed out waiting for image.",
        "status": 504,
        "task_id": task_id,
    }


def assign_placeholder_image(nano_banana, prompt):
    if not nano_banana:
        return None
    reference_url = first_reference_url(get_nano_reference_urls(nano_banana))
    if reference_url and reference_url != nano_banana.picture_url:
        nano_banana.picture_url = reference_url
        nano_banana.save(update_fields=["picture_url"])
    return nano_banana.picture_url


class GenerateImageView(APIView):

    GENERATE_URL = "https://api.nanobananaapi.ai/api/v1/nanobanana/generate"
    TASK_URL     = "https://api.nanobananaapi.ai/api/v1/nanobanana/record-info"

    def post(self, request):
        prompt = request.data.get("prompt", "").strip()
        user_id = request.data.get("user_id", "1")
        nano_banana_id = request.data.get("nano_banana_id", "")
        image_urls = request.data.get("image_urls", [])
        if not prompt:
            return Response({"error": "A 'prompt' field is required."}, status=400)

        user = User.objects.filter(id=int(user_id)).first()
        if user is None:
            return Response({"error": "User not found."}, status=404)
        if isinstance(image_urls, str):
            image_urls = [image_urls] if image_urls.strip() else []
        image_urls = dedupe_reference_urls(image_urls, limit=9)

        try:
            image_url, provider = generate_image(
                prompt,
                inspiration_images=image_urls,
                reference_mode='required' if image_urls else 'optional',
            )
        except Exception as exc:
            logger.exception("Gemini image generation failed: %s", exc)
            payload = gemini_error_payload(exc)
            return Response({'error': payload['message'], **payload}, status=status.HTTP_502_BAD_GATEWAY)
        if not image_url:
            return Response(
                {"error": "Voice Spark AI did not return an image.", "provider": provider, "error_type": "invalid_response", "retryable": True},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        if nano_banana_id:
            nano_banana = get_nano_by_id(nano_banana_id, user=user)
            if nano_banana:
                nano_banana.picture_url = image_url
                nano_banana.save(update_fields=["picture_url"])
                if image_urls:
                    save_nano_meta(nano_banana, reference_meta_patch(image_urls))
        else:
            nano_banana = NanoBananaImage.objects.create(user=user, picture_url=image_url)
            if image_urls:
                save_nano_meta(nano_banana, reference_meta_patch(image_urls))
        return Response({
            "imageUrl": image_url,
            "provider": provider,
            "data": serialize_nano_banana(nano_banana) if 'nano_banana' in locals() and nano_banana else None,
        })

        api_key = os.environ.get("NANOBANANA_API_KEY")
        if not api_key:
            return Response({"error": "NANOBANANA_API_KEY is not set."}, status=500)

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        # payload = {
        #     "prompt": prompt,
        #     "imageUrls": [],
        #     "aspectRatio": request.data.get("aspectRatio", "1:1"),
        #     "resolution": request.data.get("resolution", "1K"),
        #     "googleSearch": request.data.get("googleSearch", False),
        #     "outputFormat": request.data.get("outputFormat", "jpg"),
        # }
        payload = {
            "prompt": prompt,
            "type": "TEXTTOIAMGE",                                  # note: their typo, not ours
            "numImages": request.data.get("numImages", 1),
            "image_size": request.data.get("image_size", "1:1"),    # 1:1 | 16:9 | 9:16 | etc.
        }
        last_error = None
        for attempt in range(3):
            attempt_prompt = prompt if attempt == 0 else build_nanobanana_fallback_prompt(
                prompt,
                error_message=last_error,
                attempt=attempt,
                mode="text-to-image",
                aspect_ratio=payload.get("image_size", "1:1"),
            )
            attempt_payload = {**payload, "prompt": attempt_prompt}
            result = submit_and_poll_nanobanana(self.GENERATE_URL, self.TASK_URL, headers, attempt_payload)
            if result["ok"]:
                image_url = result["data"].get("response", {}).get("resultImageUrl")
                user = User.objects.get(id=int(user_id))
                image_instance = save_image_from_url(image_url, user)
                if not image_instance:
                    last_error = "Generated image could not be saved."
                    continue
                saved_url = image_instance.image.url.split('?')[0]
                if nano_banana_id:
                    nano_banana = get_nano_by_id(nano_banana_id)
                    if nano_banana:
                        nano_banana.picture_url = saved_url
                        nano_banana.save()
                else:
                    NanoBananaImage.objects.create(user=user, picture_url=saved_url)
                return Response({
                    "imageUrl": image_url,
                    "taskId": result.get("task_id"),
                    "attempt": attempt + 1,
                    "usedFallbackPrompt": attempt > 0,
                })
            last_error = result.get("error") or "Generation failed."
            print(f"Nano Banana text-to-image attempt {attempt + 1} failed: {last_error}")

        return Response({
            "error": last_error or "Image generation failed after fallback retries.",
            "attempts": 3,
        }, status=502)
        # Step 1 — submit the generation task
        try:
            submit_resp = requests.post(
                self.GENERATE_URL, json=payload, headers=headers, timeout=30
            )
            submit_resp.raise_for_status()
        except requests.RequestException as e:
            return Response({"error": f"Failed to submit task: {str(e)}"}, status=502)

        task_id = submit_resp.json().get("data", {}).get("taskId")
        if not task_id:
            return Response({"error": "No taskId returned by API."}, status=502)

        # Step 2 — poll for the result
        for _ in range(30):  # max ~60 seconds
            time.sleep(2)
            try:
                task_resp = requests.get(
                    self.TASK_URL,
                    headers=headers,
                    params={"taskId": task_id},  # ✅ query param, not path param
                    timeout=10,
                )
                task_resp.raise_for_status()
            except requests.RequestException as e:
                return Response({"error": f"Failed to poll task: {str(e)}"}, status=502)

            data = task_resp.json().get("data", {})
            success_flag = data.get("successFlag")

            if success_flag == 1:  # ✅ SUCCESS
                image_url = data.get("response", {}).get("resultImageUrl")
                user = User.objects.get(id=int(user_id))
                image_instance = save_image_from_url(image_url, user)
                if not image_instance:
                    return Response({"error": "Generated image could not be saved."}, status=502)
                ########

                if nano_banana_id:
                    nano_banana = get_nano_by_id(nano_banana_id)
                    nano_banana.picture_url=image_instance.image.url.split('?')[0]
                    nano_banana.save()
                else:
                    NanoBananaImage.objects.create(
                        user=user,
                        picture_url= image_instance.image.url.split('?')[0]
                    )




                return Response({"imageUrl": image_url, "taskId": task_id})

            if success_flag in (2, 3):  # ✅ FAILED
                error_msg = data.get("errorMessage", "Generation failed.")
                return Response({"error": error_msg}, status=502)

            # successFlag == 0 → still generating, keep polling

        return Response({"error": "Timed out waiting for image."}, status=504)


class GetGeneratedImage(APIView):
    def post(self, request):
        user_id = request.data.get("user_id", "1")
        see = request.data.get('see', '')
        last_id = request.data.get('last_id', '')
        first_id = request.data.get('first_id', '')
        workspace_id = request.data.get('workspace_id', '')
        workspace = get_workspace_by_id(workspace_id)
        user = get_user_by_id(user_id)
        if user is None:
            return JsonResponse({"data": [], "error": "Valid user_id is required."}, status=400)
        if workspace_id and workspace is None:
            return JsonResponse({"data": [], "error": "Valid workspace_id is required."}, status=400)
        active_jobs = []
        failed_jobs = []
        if workspace:
            for job in NanoGenerationJob.objects.filter(
                user=user,
                workspace=workspace,
                job_type__in=['create_post', 'regenerate_image'],
                status__in=['queued', 'running'],
            ).order_by('-created_at')[:5]:
                job = mark_stale_nano_generation_job(job)
                if job.status in ('queued', 'running'):
                    active_jobs.append({
                        'job_id': str(job.id),
                        'status': job.status,
                        'job_type': job.job_type,
                        'updated_at': job.updated_at.isoformat() if job.updated_at else None,
                    })
            for job in NanoGenerationJob.objects.filter(
                user=user,
                workspace=workspace,
                job_type__in=['create_post', 'regenerate_image'],
                status='failed',
                updated_at__gte=timezone2.now() - timedelta(minutes=30),
            ).order_by('-updated_at')[:3]:
                failed_jobs.append({
                    'job_id': str(job.id),
                    'status': job.status,
                    'job_type': job.job_type,
                    'error': job.error or (job.result or {}).get('error') or 'Generation failed.',
                    'retryable': True,
                    'updated_at': job.updated_at.isoformat() if job.updated_at else None,
                })
        if see == 'next':
            last_obj = ScheduledPost.objects.get(nano_banana__id=last_id, user=user)
            schedule_objs = ScheduledPost.objects.filter(
                user=user,
                scheduled_at__gt=last_obj.scheduled_at,
                workspace = workspace
            ).order_by('scheduled_at')[:5]
        elif see == 'previous':
            first_obj = ScheduledPost.objects.get(nano_banana__id=first_id, user=user)
            schedule_objs = ScheduledPost.objects.filter(
                user=user,
                scheduled_at__lt=first_obj.scheduled_at,
                workspace = workspace,
            ).order_by('-scheduled_at')[:5]
            schedule_objs = sorted(schedule_objs, key=lambda x: x.scheduled_at)
        if not see:
            today = local_now(user, workspace).replace(hour=0, minute=0, second=0, microsecond=0)
            start_date = today - timedelta(days=30)
            end_date = today + timedelta(days=60)
            schedule_objs = ScheduledPost.objects.filter(
                user=user,
                scheduled_at__gte=start_date,
                scheduled_at__lt=end_date,
            ).filter(
                Q(workspace=workspace) |
                Q(workspace__isnull=True, nano_banana__workspace=workspace)
            ).order_by("scheduled_at", "created_at")
        # nano_banana_image = NanoBananaImage.objects.filter(user=user)[:5]

        # today = datetime.today()

        # future_dates = [(today + timedelta(days=i)).strftime("%b %d %y") for i in range(0, len(schedule_objs))]

        data = []
        if schedule_objs:
            for index, sch  in enumerate(schedule_objs):
                # pass
                # scheduled_at = future_dates[index]
                # print(scheduled_at)
                if sch.nano_banana_id:
                    data.append(serialize_nano_banana(sch.nano_banana, sch))
        #
        return JsonResponse({
            "data": data,
            "active_generation_jobs": active_jobs,
            "recent_failed_generation_jobs": failed_jobs,
        })
class ReturnNextPreviousId(APIView):
    def post(self, request):
        user_id = request.data.get('user_id', "")
        nano_banana_id = request.data.get("nano_banana_id").strip()
        see = request.data.get('see','next')
        workspace_id = request.data.get('workspace_id', '')
        workspace = get_workspace_by_id(workspace_id)

        user = User.objects.get(id=int(user_id))
        nano_banana = None
        if see == "next":
            curr_obj = ScheduledPost.objects.get(nano_banana__id=nano_banana_id, user=user)
            schedule_objs = ScheduledPost.objects.filter(
                user=user,
                scheduled_at__gt=curr_obj.scheduled_at,
                nano_banana__picture_url__isnull=False,
                workspace=workspace
            ).order_by('scheduled_at').first()
            # nano_banana = NanoBananaImage.objects.filter(
            #     user=user,
            #     scheduled_at__gt=curr_obj.scheduled_at,
            #     picture_url__isnull=False
            # ).exclude(picture_url='').order_by('scheduled_at').first()
        else:
            curr_obj = ScheduledPost.objects.get(nano_banana__id=nano_banana_id, user=user)
            schedule_objs = ScheduledPost.objects.filter(
                user=user,
                scheduled_at__lt=curr_obj.scheduled_at,
                nano_banana__picture_url__isnull = False,
                workspace=workspace
            ).order_by('-scheduled_at').first()
            # nano_banana = NanoBananaImage.objects.filter(
            #     user=user,
            #     scheduled_at__lt=curr_obj.scheduled_at,
            #     picture_url__isnull=False
            # ).exclude(picture_url='').order_by('scheduled_at').first()
        if schedule_objs:
            return JsonResponse({'nano_banana_id': str(schedule_objs.nano_banana.id)})
        else:
            return JsonResponse({'nano_banana_id': None})

class GetGeneratedImageById(APIView):
    def post(self, request):
        # print('here')
        nano_banana_id = request.data.get("nano_banana_id").strip()

        # user = User.objects.get(id=int(user_id))
        nano_banana = get_nano_by_id(nano_banana_id)
        scheduled_obj = ScheduledPost.objects.filter(nano_banana=nano_banana).first()
        scheduled_at = None
        approval = None
        if scheduled_obj:
            scheduled_at = str(scheduled_obj.scheduled_at)
            approval = scheduled_obj.approval
        data = serialize_nano_banana(nano_banana, scheduled_obj)
        workspace = scheduled_obj.workspace if scheduled_obj else nano_banana.workspace
        connected = workspace_connected_platforms(nano_banana.user, workspace)
        x_bool = 'twitter' in connected
        facebook_bool = 'facebook' in connected
        insta_bool = 'instagram' in connected
        linkedin_bool = 'linkedin' in connected

        return JsonResponse({"data": data, 'social_media':{"x":x_bool, 'fb':facebook_bool, 'insta':insta_bool, 'linkedin':linkedin_bool}})

class AnalyseWebsiteLink(APIView):
    def post(self, request):
        user_id = request.data.get('user_id', '')
        link = (request.data.get("link") or "").strip()

        if not user_id:
            return Response({"error": "user_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        if not link:
            return Response({"error": "Website link is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user_id = int(user_id)
        except (TypeError, ValueError):
            return Response({"error": "A valid user_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        user = get_user_by_id(user_id)
        if not user:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            print('analysing website link')
            html_images = analyse_link(link, user.first_name, user.last_name)
            print('analysis images count', len(html_images.get('images', [])))
            html = html_images.get('html', '')
            if not html.strip():
                return Response(
                    {"error": "Could not extract readable content from this website."},
                    status=status.HTTP_422_UNPROCESSABLE_ENTITY,
                )

            cg = ChatGPT()
            cg.create_client()
            cg.create_base_system_prompt()
            cg.create_chat_completion()
            message = cg.get_generated_message()
            if not message:
                return Response(
                    {"error": "Could not initialize the analysis model."},
                    status=status.HTTP_502_BAD_GATEWAY,
                )
            cg.send_assistant_message(message)
            cg.send_users_message(f"""You are a brand analyst. I will give you the HTML content of a person's or business's website.
                                Dont add percentages
                                Analyze the content and generate a structured business profile in Markdown format. Be specific, extract real details from the HTML, and do not make up information that isn't implied by the website.
                                
                                Return ONLY valid Markdown, no explanation, no code blocks wrapping it.
                                
                                Use this exact structure:
                                
                                # [Full name or business name]'s Business Profile
                                
                                ## Business Overview & Positioning
                                
                                **Core Identity:** [2-3 sentence summary of who they are, what they do, and who they serve.]
                                
                                **Market Positioning:**
                                
                                - **Primary Positioning:** "[Positioning statement]" - [explanation of the angle]
                                - **Secondary Positioning:** "[Positioning statement]" - [explanation]
                                - **Tertiary Positioning:** "[Positioning statement]" - [explanation]
                                
                                ## Direct Competitors
                                
                                - **Local Competitors:**
                                  - [Competitor type 1]
                                  - [Competitor type 2]
                                - **National Competitors:**
                                  - [Competitor type 1]
                                  - [Competitor type 2]
                                
                                ## Competitive Advantages
                                
                                1. **[Bold phrase]** [rest of the sentence]
                                2. **[Bold phrase]** [rest of the sentence]
                                3. **[Bold phrase]** [rest of the sentence]
                                
                                ## Customer Demographics & Psychographics
                                
                                ### Primary Customer Segments
                                
                                - **[Segment Name] ([X]%)**
                                  - [What they are seeking]
                                  - [Decision makers]
                                  - Pain points: [key pain points]
                                
                                ## Most Popular Products & Services
                                
                                ### Top Revenue Generators
                                
                                1. [Service name] - [brief description]
                                2. [Service name] - [brief description]
                                
                                ### Emerging Growth Areas
                                
                                - [Area 1]
                                - [Area 2]
                                
                                ## Why Customers Choose [Name]
                                
                                ### Primary Value Drivers
                                
                                - **[Driver name]:** [What it means for the client]
                                
                                ### Emotional Benefits
                                
                                - **[Benefit]:** [What the client feels]
                                
                                ## The [Name] Brand Story
                                
                                **The Hero's Journey:** [Narrative paragraph about their journey and mission.]
                                
                                **Mission Statement:** "[Their mission in one sentence]"
                                
                                **Brand Personality:**
                                
                                - **Archetype:** [e.g. The Innovator]
                                - **Voice:** [Description of brand voice]
                                - **Values:** [value1], [value2], [value3]
                                
                                Here is the website HTML: {html}
                                remove links
                                """)
            cg.create_chat_completion()
            message = cg.get_generated_message()
            if not message:
                return Response(
                    {"error": "The analysis model did not return a profile."},
                    status=status.HTTP_502_BAD_GATEWAY,
                )
            print('analysis markdown length', len(message or ''))
            brand_style = html_images.get('brand_style', {})
            if not brand_style.get('visual_identity'):
                brand_style['visual_identity'] = "Use the website's extracted logo, colors, and typography as the base visual identity."
            screenshot = html_images.get('screenshot')
            screenshot_data_url = ""
            if screenshot:
                screenshot_data_url = "data:image/png;base64," + base64.b64encode(screenshot).decode("utf-8")

            # Persist the link to the user profile if possible
            try:
                from auth_user.models import UserProfile
                # We try to find a profile for this user. Since we don't have a workspace_id here yet,
                # we update all profiles for this user with this website_url as a base.
                UserProfile.objects.filter(user=user).update(website_url=link)
            except Exception as e:
                print('failed to persist website link to user profile', str(e))

            return JsonResponse(data={
                'markdown': message,
                'images': html_images.get('images', []),
                'brand_style': brand_style,
                'screenshot': screenshot_data_url,
                'link': link,
            })
        except Exception as e:
            print('website analysis failed', type(e).__name__, str(e))
            return Response(
                {"error": f"Website analysis failed: {str(e)}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        # except Exception as e:
        #     import subprocess
        #     result = subprocess.run(
        #         ["python", "-m", "playwright", "install", "--dry-run"],
        #         capture_output=True,
        #         text=True
        #     )
        #     return JsonResponse(data={'error':str(e), 'result':str(result)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class EditImageView(APIView):
    EDIT_URL = "https://api.nanobananaapi.ai/api/v1/nanobanana/generate"
    TASK_URL = "https://api.nanobananaapi.ai/api/v1/nanobanana/record-info"

    def post(self, request):
        print('edit image')
        prompt   = request.data.get("prompt", "").strip()
        image_urls = request.data.get("image_urls", [])
        image_url = request.data.get("image_url", "")
        user_id  = request.data.get("user_id", "1")
        nano_banana_id = request.data.get("nano_banana_id", "")
        # if not prompt:
        #     return Response({"error": "A 'prompt' field is required."}, status=400)
        user = get_user_by_id(user_id)
        if user is None:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        nano_banana = None
        workspace = None
        if nano_banana_id:
            nano_banana = get_nano_by_id(nano_banana_id, user=user)
            if nano_banana:
                workspace = nano_banana.workspace
        if isinstance(image_urls, str):
            image_urls = [image_urls] if image_urls.strip() else []
        if image_url:
            image_urls.append(image_url)
        meta = get_nano_meta(nano_banana) if nano_banana else {}
        context = resolve_generation_context(user, workspace) if workspace else {}
        user_profile = context.get('user_profile')
        image_urls = get_brand_reference_urls(
            user_profile,
            topic=prompt,
            content_type=meta.get('content_type', 'social'),
            include_existing=[
                *image_urls,
                *(get_nano_reference_urls(nano_banana) if nano_banana else []),
                nano_banana.picture_url if nano_banana else None,
            ],
            limit=9,
        )

        try:
            image_url, provider = generate_image(
                prompt or "Create a new brand-aligned marketing image.",
                inspiration_images=image_urls,
                brand_name=generation_brand_name(context, workspace) if context else None,
                reference_mode='required' if image_urls else 'optional',
            )
        except Exception as exc:
            logger.exception("Gemini image edit failed: %s", exc)
            payload = gemini_error_payload(exc)
            return Response({'error': payload['message'], **payload}, status=status.HTTP_502_BAD_GATEWAY)
        if not image_url:
            return Response(
                {"error": "Voice Spark AI did not return an image.", "provider": provider, "error_type": "invalid_response", "retryable": True},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        if nano_banana:
            nano_banana.picture_url = image_url
            nano_banana.save(update_fields=["picture_url"])
            save_nano_meta(nano_banana, reference_meta_patch(image_urls))
        else:
            nano_banana = NanoBananaImage.objects.create(
                user=user,
                picture_url=image_url,
                workspace=workspace,
            )
            save_nano_meta(nano_banana, reference_meta_patch(image_urls))
        return Response({
            "imageUrl": image_url,
            "sourceImageUrl": image_urls,
            "provider": provider,
            "data": serialize_nano_banana(nano_banana),
        })

        api_key = os.environ.get("NANOBANANA_API_KEY")
        if not api_key:
            return Response({"error": "NANOBANANA_API_KEY is not set."}, status=500)

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "prompt": prompt,
            "type": "IMAGETOIAMGE",                               # edit/img2img mode
            "imageUrls": image_urls,                             # source image(s)
            "numImages": request.data.get("numImages", 1),
            "image_size": request.data.get("image_size", "1:1"),  # 1:1 | 16:9 | 9:16 | etc.
        }
        last_error = None
        for attempt in range(3):
            attempt_prompt = prompt if attempt == 0 else build_nanobanana_fallback_prompt(
                prompt,
                error_message=last_error,
                attempt=attempt,
                mode="image-to-image",
                aspect_ratio=payload.get("image_size", "1:1"),
            )
            attempt_payload = {**payload, "prompt": attempt_prompt}
            result = submit_and_poll_nanobanana(self.EDIT_URL, self.TASK_URL, headers, attempt_payload)
            if result["ok"]:
                result_url = result["data"].get("response", {}).get("resultImageUrl")
                image_instance = save_image_from_url(result_url, user, workspace=workspace)
                if not image_instance:
                    last_error = "Edited image could not be saved."
                    continue
                saved_url = image_instance.image.url.split('?')[0]
                if nano_banana:
                    nano_banana.picture_url = saved_url
                    nano_banana.save()
                else:
                    nano_banana = NanoBananaImage.objects.create(
                        user=user,
                        picture_url=saved_url,
                        workspace=workspace,
                    )
                return Response({
                    "imageUrl": saved_url,
                    "sourceImageUrl": image_urls,
                    "taskId": result.get("task_id"),
                    "attempt": attempt + 1,
                    "usedFallbackPrompt": attempt > 0,
                    "data": serialize_nano_banana(nano_banana),
                })
            last_error = result.get("error") or "Edit failed."
            print(f"Nano Banana image-to-image attempt {attempt + 1} failed: {last_error}")

        text_payload = {
            "prompt": build_nanobanana_fallback_prompt(
                prompt,
                error_message=last_error,
                attempt=2,
                mode="text-to-image",
                aspect_ratio=payload.get("image_size", "1:1"),
            ),
            "type": "TEXTTOIAMGE",
            "numImages": request.data.get("numImages", 1),
            "image_size": payload.get("image_size", "1:1"),
        }
        text_result = submit_and_poll_nanobanana(self.EDIT_URL, self.TASK_URL, headers, text_payload)
        if text_result["ok"]:
            result_url = text_result["data"].get("response", {}).get("resultImageUrl")
            image_instance = save_image_from_url(result_url, user, workspace=workspace)
            if image_instance:
                saved_url = image_instance.image.url.split('?')[0]
                if nano_banana:
                    nano_banana.picture_url = saved_url
                    nano_banana.save()
                else:
                    nano_banana = NanoBananaImage.objects.create(
                        user=user,
                        picture_url=saved_url,
                        workspace=workspace,
                    )
                return Response({
                    "imageUrl": saved_url,
                    "sourceImageUrl": image_urls,
                    "taskId": text_result.get("task_id"),
                    "attempt": 4,
                    "usedFallbackPrompt": True,
                    "usedTextFallback": True,
                    "data": serialize_nano_banana(nano_banana),
                })
        last_error = text_result.get("error") or last_error

        return Response({
            "error": last_error or "Image edit failed after fallback retries.",
            "attempts": 4,
        }, status=502)

        # Step 1 — submit the edit task
        try:
            submit_resp = requests.post(
                self.EDIT_URL, json=payload, headers=headers, timeout=30
            )
            submit_resp.raise_for_status()
            print(submit_resp.status_code)
            print(submit_resp.json())
        except requests.RequestException as e:
            return Response({"error": f"Failed to submit task: {str(e)}"}, status=502)

        task_id = submit_resp.json().get("data", {}).get("taskId")
        if not task_id:
            return Response({"error": "No taskId returned by API."}, status=502)

        # Step 2 — poll for the result
        for _ in range(30):  # max ~60 seconds
            time.sleep(2)
            try:
                task_resp = requests.get(
                    self.TASK_URL,
                    headers=headers,
                    params={"taskId": task_id},
                    timeout=10,
                )
                task_resp.raise_for_status()
            except requests.RequestException as e:
                return Response({"error": f"Failed to poll task: {str(e)}"}, status=502)

            data         = task_resp.json().get("data", {})
            success_flag = data.get("successFlag")

            if success_flag == 1:  # SUCCESS
                result_url = data.get("response", {}).get("resultImageUrl")
                image_instance = save_image_from_url(result_url, user, workspace=workspace)
                if not image_instance:
                    return Response({"error": "Edited image could not be saved."}, status=502)
                saved_url = image_instance.image.url.split('?')[0]
                if nano_banana:
                    nano_banana.picture_url = image_instance.image.url.split('?')[0]
                    nano_banana.save()
                    print(result_url)
                else:
                    nano_banana = NanoBananaImage.objects.create(
                        user=user,
                        picture_url=saved_url,
                        workspace=workspace,
                    )
                return Response({
                    "imageUrl":      saved_url,
                    "sourceImageUrl": image_urls,
                    "taskId":        task_id,
                    "data": serialize_nano_banana(nano_banana),
                })

            if success_flag in (2, 3):  # FAILED
                error_msg = data.get("errorMessage", "Edit failed.")
                return Response({"error": error_msg}, status=502)

            # successFlag == 0 → still processing, keep polling

        return Response({"error": "Timed out waiting for edited image."}, status=504)

class CreateNewPost(APIView):
    def make_request(self, user_id, run_at, request, topic, workspace_id, content_type='social', reference_image_url=None):
        payload = {
            'user_id': user_id,
            'run_at': str(run_at),
            'workspace_id': workspace_id,
            'queue': 'calendar',
            'content_type': content_type,
        }
        if topic:
            payload['topic'] = topic
        if reference_image_url:
            payload['reference_image_url'] = reference_image_url
        ############
        factory = RequestFactory()
        internal_request = factory.post(
            '/nano-banana/generate-post/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        internal_request.user = request.user  # pass current user
        generate_post = GenerateCaptionAndImagePost.as_view()
        try:
            response = generate_post(internal_request)
        except Exception as exc:
            logger.exception("Internal post generation failed for workspace %s: %s", workspace_id, exc)
            return Response({"error": str(exc)}, status=status.HTTP_200_OK)
        return response
    def post(self, request):
        try:
            user_id = int(request.data.get("user_id", "1"))
        except (TypeError, ValueError):
            user_id = 0
        user = get_user_by_id(user_id)
        workspace_id = request.data.get('workspace_id', "")
        workspace = get_workspace_by_id(workspace_id)
        if user is None:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        if workspace is None:
            return Response({'error': 'workspace_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        from_date = request.data.get("from_date", "")
        if from_date:
            from_date = safe_generation_run_at(from_date, user, workspace)
        to_date = request.data.get("to_date", "")
        if to_date:
            to_date = safe_generation_run_at(to_date, user, workspace)
        specific_date = request.data.get("specific_date", "")
        if specific_date:
            specific_date = safe_generation_run_at(specific_date, user, workspace)

        type_post = str(request.data.get("type_post", "") or "specific").strip().lower()
        if type_post not in ("specific", "range"):
            type_post = "specific"
        try:
            no_of_post = int(request.data.get('no_of_post') or 1)
        except (TypeError, ValueError):
            no_of_post = 1
        no_of_post = max(1, min(no_of_post, 30))
        topic = request.data.get("topic", "")
        reference_image_url = request.data.get("reference_image_url", "")
        content_type = str(request.data.get("content_type") or "social").strip().lower()
        if content_type not in ("social", "blog"):
            content_type = "social"
        if should_enqueue_generation(request):
            return enqueue_nano_generation_job(
                request,
                'create_post',
                user,
                workspace=workspace,
                payload=request.data,
            )
        results = []
        errors = []

        if type_post == 'specific':
            if not specific_date:
                specific_date = default_run_at_for_day(user, workspace)
            for _  in range(no_of_post):
                results.append(self.make_request(user_id, specific_date, request, topic, workspace_id, content_type, reference_image_url).status_code)
        elif type_post == 'range':
            if not from_date or not to_date:
                errors.append('Range dates were missing, so content was scheduled at the workspace default time.')
                run_at = default_run_at_for_day(user, workspace)
                for _ in range(no_of_post):
                    results.append(self.make_request(user_id, run_at, request, topic, workspace_id, content_type, reference_image_url).status_code)
            else:
                if to_date < from_date:
                    errors.append('End date was before start date, so the date range was swapped.')
                    from_date, to_date = to_date, from_date
        #     ########## make the date range
        #     date_range = 5
                days = [(from_date + timedelta(days=i)).date() for i in range((to_date - from_date).days + 1)]
                for day in days:
                    results.append(self.make_request(user_id, day, request, topic, workspace_id, content_type, reference_image_url).status_code)

        if not results:
            errors.append('No schedule was provided, so content was scheduled at the workspace default time.')
            results.append(self.make_request(user_id, default_run_at_for_day(user, workspace), request, topic, workspace_id, content_type).status_code)

        created_count = sum(1 for code in results if 200 <= code < 300)
        payload = {"statuses": results, "created": created_count, "errors": errors, "content_type": content_type, "mode": type_post}
        if any(code >= 400 for code in results):
            payload["warning"] = "Some posts used fallback generation or could not be created."
        return Response(payload, status=status.HTTP_200_OK)




class ScheduleGeneratePost(APIView):
    def post(self, request):
        user_id = request.data.get("user_id", "1")
        workspace_id = request.data.get('workspace_id', '')
        user = get_user_by_id(user_id)
        workspace = get_workspace_by_id(workspace_id)
        if user is None:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        if workspace is None:
            return Response({'error': 'workspace_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        count = int(request.data.get('count', 1) or 1)
        count = max(1, min(count, 7))
        queue = request.data.get('queue', 'calendar')
        if queue not in ('calendar', 'approval'):
            queue = 'calendar'

        responses = []
        for day_offset in range(count):
            run_at = calendar_run_at_for_day(day_offset, user=user, workspace=workspace)
            payload = {
                'user_id': user_id,
                'run_at': str(run_at),
                'workspace_id': workspace_id,
                'queue': queue,
            }
            factory = RequestFactory()
            internal_request = factory.post(
                '/nano-banana/generate-post/',
                data=json.dumps(payload),
                content_type='application/json'
            )
            internal_request.user = request.user
            generate_post = GenerateCaptionAndImagePost.as_view()
            response = generate_post(internal_request)
            responses.append(response.status_code)

        if all(code == 200 for code in responses):
            return Response(status=status.HTTP_200_OK)
        return Response({'statuses': responses}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
class EditGeneratedImage(APIView):
    def post(self, request):
        user_id = request.data.get("user_id", "1")
        prompt = request.data.get("prompt", "").strip()
        nano_banana_id = request.data.get('nano_banana_id')
        change_caption = parse_request_bool(request.data.get('change_caption', False))
        change_image = parse_request_bool(request.data.get('change_image', False))
        workspace_id = request.data.get('workspace_id', '')
        target_platform = request.data.get('target_platform', 'multi-platform')
        aspect_ratio = request.data.get('image_size', '1:1')
        image_urls = request.data.get('image_urls', [])

        if not prompt:
            return Response({'error': 'Prompt is required.'}, status=status.HTTP_400_BAD_REQUEST)
        user = get_user_by_id(user_id)
        if user is None:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        nano_banana = get_nano_by_id(nano_banana_id, user=user)
        if nano_banana is None:
            return Response({'error': 'Generated image was not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not change_caption and not change_image:
            change_image, change_caption = infer_edit_targets(prompt)
        workspace = nano_banana.workspace or get_workspace_by_id(workspace_id)
        if workspace is None:
            return Response({'error': 'workspace_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if should_enqueue_generation(request):
            return enqueue_nano_generation_job(
                request,
                'edit_generated_image',
                user,
                workspace=workspace,
                nano_banana=nano_banana,
                payload=request.data,
            )
        user_profile = get_generation_profile(user, workspace)

        # ── Advanced edit (feature-flagged) ──
        if ADVANCED_PIPELINE:
            try:
                from content_engine.services.generation_orchestrator import orchestrate_generation
                from content_engine.services.context_builder import generate_correlation_id
                corr_id = generate_correlation_id('edit_post', workspace)
                meta = get_nano_meta(nano_banana)
                snapshot = meta.get('__context_snapshot')

                orch_result = orchestrate_generation(
                    flow='edit_post',
                    user=user,
                    workspace=workspace,
                    topic=meta.get('title', '') or nano_banana.caption,
                    target_platform=target_platform,
                    user_instruction=prompt,
                    previous_caption=nano_banana.caption,
                    aspect_ratio=aspect_ratio,
                    existing_post=nano_banana,
                    context_snapshot=snapshot,
                    correlation_id=corr_id,
                )

                if orch_result.get('status') == 'completed':
                    change_caption = orch_result.get('change_caption', False)
                    change_image = orch_result.get('change_image', False)

                    if change_caption:
                        caption = orch_result.get('caption') or nano_banana.caption
                        nano_banana.caption = caption
                        adv_captions = orch_result.get('platform_captions', {})
                        if adv_captions:
                            nano_banana.platform_captions = adv_captions
                        else:
                            set_platform_captions_for_profile(nano_banana, user_profile, caption, topic=prompt, target_platform=target_platform)
                        nano_banana.save()

                    # Update meta with snapshot
                    new_snapshot = orch_result.get('context_snapshot', {})
                    new_snapshot['correlation_id'] = corr_id
                    new_snapshot['edit_instruction'] = prompt
                    save_nano_meta(nano_banana, {'__context_snapshot': new_snapshot})

                    if not change_image:
                        return JsonResponse({"data": serialize_nano_banana(nano_banana)})

                    # Proceed to image edit with advanced prompt
                    image_prompt = orch_result.get('image_prompt')
                    image_urls = get_brand_reference_urls(
                        user_profile,
                        topic=prompt or nano_banana.caption,
                        content_type=meta.get('content_type', 'social'),
                        include_existing=[*get_nano_reference_urls(nano_banana), nano_banana.picture_url],
                        limit=9,
                    )
                    save_nano_meta(nano_banana, {'reference_images': image_urls})
                    payload = {
                        'user_id': user_id, 'prompt': image_prompt, 'image_urls': image_urls,
                        'nano_banana_id': str(nano_banana.id), 'image_size': aspect_ratio,
                    }
                    factory = RequestFactory()
                    internal_request = factory.post('/nano-banana/edit-image/', data=json.dumps(payload), content_type='application/json')
                    internal_request.user = request.user
                    response = EditImageView.as_view()(internal_request)
                    if response.status_code >= 400:
                        return Response(response.data if hasattr(response, 'data') else {'error': 'Advanced image edit failed.'}, status=response.status_code)
                    nano_banana.refresh_from_db()
                    return JsonResponse({"data": serialize_nano_banana(nano_banana)})
                else:
                    logger.warning('advanced_edit_failed flow=edit_post corr=%s error=%s', corr_id, orch_result.get('error', ''))
            except Exception as adv_exc:
                logger.exception('advanced_edit_exception flow=edit_post: %s', adv_exc)

        try:
            if change_caption:
                caption = safe_generate_caption(
                    user_profile,
                    previous_caption=nano_banana.caption,
                    user_instruction=prompt,
                    target_platform=target_platform,
                ) or nano_banana.caption
                nano_banana.caption = caption
                set_platform_captions_for_profile(nano_banana, user_profile, caption, topic=prompt, target_platform=target_platform)
                nano_banana.save()
                if not change_image:
                    data = serialize_nano_banana(nano_banana)
                    return JsonResponse({"data": data})
            if not change_image:
                data = serialize_nano_banana(nano_banana)
                return JsonResponse({"data": data})

            image_prompt = prompt
            if not user_profile or not user_profile.markdown:
                return Response({'error': 'Workspace brand profile is required before editing images.'}, status=status.HTTP_400_BAD_REQUEST)
            image_prompt = safe_generate_image_prompt(
                user_profile,
                caption=nano_banana.caption,
                user_instruction=prompt,
                target_platform=target_platform,
                aspect_ratio=aspect_ratio,
                source_mode="image-to-image using the current generated design as source",
            )
            if isinstance(image_urls, str):
                image_urls = [image_urls] if image_urls.strip() else []
            image_urls = get_brand_reference_urls(
                user_profile,
                topic=prompt or nano_banana.caption,
                content_type=get_nano_meta(nano_banana).get('content_type', 'social'),
                include_existing=[
                    *image_urls,
                    *get_nano_reference_urls(nano_banana),
                    nano_banana.picture_url,
                ],
                limit=9,
            )
            save_nano_meta(nano_banana, {'reference_images': image_urls})
            payload = {
                'user_id': user_id,
                'prompt': image_prompt,
                'image_urls': image_urls,
                'nano_banana_id': str(nano_banana.id),
                'image_size': aspect_ratio,
            }
            factory = RequestFactory()
            internal_request = factory.post(
                '/nano-banana/edit-image/',
                data=json.dumps(payload),
                content_type='application/json'
            )
            internal_request.user = request.user
            edit_image_view = EditImageView.as_view()
            response = edit_image_view(internal_request)
            if response.status_code != 200:
                return Response(response.data if hasattr(response, 'data') else {'error': 'Voice Spark AI image edit failed.'}, status=response.status_code)
            nano_banana.refresh_from_db()
        except Exception as exc:
            logger.exception("Edit generated image failed: %s", exc)
            payload = gemini_error_payload(exc)
            return Response({'error': payload['message'], **payload}, status=status.HTTP_502_BAD_GATEWAY)
        # data = {
        #         "nano_banana_id": str(nano_banana.id),
        #         "imageurl":nano_banana.picture_url,
        #         "title":nano_banana.caption,
        #         "scheduled_at":str(scheduled_post.scheduled_at),
        #                         }
        data = serialize_nano_banana(nano_banana)
        return JsonResponse({"data": data})
        return Response(status=status.HTTP_200_OK)

class GenerateCaptionAndImagePost(APIView):
    def post(self, request):
        user_id = request.data.get("user_id", "1")
        run_at = request.data.get("run_at", "")
        topic = request.data.get('topic', '')
        workspace_id = request.data.get('workspace_id', '')
        queue = request.data.get('queue', 'calendar')
        if queue not in ('calendar', 'approval'):
            queue = 'calendar'
        workspace = get_workspace_by_id(workspace_id)
        # run_at = datetime.now(timezone.utc) + timedelta(seconds=5)
        user = get_user_by_id(user_id)
        if user is None:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        if workspace is None:
            return Response({'error': 'workspace_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        run_at = safe_generation_run_at(run_at, user, workspace)
        user_profile = get_generation_profile(user, workspace)
        target_platform = request.data.get('target_platform', 'multi-platform')
        aspect_ratio = request.data.get('image_size', '1:1')
        content_type = str(request.data.get('content_type') or 'social').strip().lower()
        if content_type not in ('social', 'blog'):
            content_type = 'social'
        fallback_brand = getattr(workspace, 'name', None) or 'your brand'
        fallback_topic = clean_generation_topic(topic, '')
        if not fallback_topic:
            return Response({'error': 'Topic or instruction is required to create new content.'}, status=status.HTTP_400_BAD_REQUEST)

        reference_image_url = request.data.get('reference_image_url')

        # ── Advanced pipeline (feature-flagged) ──
        if ADVANCED_PIPELINE:
            try:
                from content_engine.services.generation_orchestrator import orchestrate_generation
                from content_engine.services.context_builder import generate_correlation_id
                corr_id = generate_correlation_id('create_post', workspace)
                orch_result = orchestrate_generation(
                    flow='create_post',
                    user=user,
                    workspace=workspace,
                    topic=fallback_topic,
                    target_platform=target_platform,
                    content_type=content_type,
                    aspect_ratio=aspect_ratio,
                    correlation_id=corr_id,
                    reference_image_url=reference_image_url,
                )
                if orch_result.get('status') != 'completed':
                    logger.warning('advanced_pipeline_failed flow=create_post corr=%s error=%s', corr_id, orch_result.get('error', ''))
                    # Fall through to legacy pipeline
                else:
                    # Use orchestrator caption/prompt, continue with image generation
                    caption = orch_result.get('caption') or safe_generate_caption(user_profile, topic=fallback_topic, target_platform=target_platform)
                    prompt = orch_result.get('image_prompt') or safe_generate_image_prompt(
                        user_profile, caption=caption, topic=fallback_topic,
                        target_platform=target_platform, aspect_ratio=aspect_ratio,
                    )
                    nano_banana = NanoBananaImage()
                    nano_banana.user = user
                    nano_banana.caption = caption
                    # Use orchestrator platform captions if available
                    adv_captions = orch_result.get('platform_captions', {})
                    if adv_captions:
                        nano_banana.platform_captions = adv_captions
                    else:
                        set_platform_captions_for_profile(nano_banana, user_profile, caption, topic=fallback_topic, target_platform=target_platform)
                    nano_banana.workspace = workspace
                    # Save reference image URL in platform_captions metadata if provided
                    if reference_image_url:
                        if not isinstance(nano_banana.platform_captions, dict):
                            nano_banana.platform_captions = {}
                        if '__meta' not in nano_banana.platform_captions:
                            nano_banana.platform_captions['__meta'] = {}
                        nano_banana.platform_captions['__meta']['reference_image_url'] = reference_image_url
                    nano_banana.save()
                    # Store context snapshot + lineage
                    snapshot = orch_result.get('context_snapshot', {})
                    snapshot['correlation_id'] = corr_id
                    imageUrls = get_brand_reference_urls(user_profile, topic=fallback_topic, content_type=content_type, limit=9)
                    if reference_image_url:
                        # Prioritize post-specific reference image as anchor
                        imageUrls = [reference_image_url] + [u for u in imageUrls if u != reference_image_url]

                    save_nano_meta(nano_banana, reference_meta_patch(imageUrls, {
                        'content_type': content_type,
                        'title': topic or ('Blog post' if content_type == 'blog' else 'Social post'),
                        '__context_snapshot': snapshot,
                        'reference_image_url': reference_image_url,
                    }))
                    # Generate actual image via existing EditImageView/GenerateImageView
                    if imageUrls:
                        payload_img = {
                            'user_id': user_id, 'prompt': prompt, 'image_urls': imageUrls,
                            'nano_banana_id': str(nano_banana.id), 'image_size': aspect_ratio,
                            'reference_mode': 'required',
                        }
                        factory = RequestFactory()
                        internal_request = factory.post('/nano-banana/edit-image/', data=json.dumps(payload_img), content_type='application/json')
                        internal_request.user = request.user
                        response = EditImageView.as_view()(internal_request)
                        if response.status_code >= 400:
                            nano_banana.delete()
                            return Response(response.data if hasattr(response, 'data') else {'error': 'Image generation failed.'}, status=response.status_code)
                    else:
                        payload_img = {
                            'user_id': user_id, 'prompt': prompt, 'image_urls': [],
                            'nano_banana_id': str(nano_banana.id), 'image_size': aspect_ratio,
                        }
                        factory = RequestFactory()
                        internal_request = factory.post('/nano-banana/generate/', data=json.dumps(payload_img), content_type='application/json')
                        internal_request.user = request.user
                        response = GenerateImageView.as_view()(internal_request)
                        if response.status_code >= 400:
                            nano_banana.delete()
                            return Response(response.data if hasattr(response, 'data') else {'error': 'Image generation failed.'}, status=response.status_code)
                    # Schedule post
                    payload_pub = {'user_id': user_id, 'text': caption, 'nano_banana_id': str(nano_banana.id)}
                    task_id = None
                    try:
                        result = make_posts.apply_async(args=[payload_pub], eta=run_at)
                        task_id = str(result.id)
                    except Exception as exc:
                        logger.warning('celery schedule failed corr=%s: %s', corr_id, exc)
                    stored_task_id = f'{APPROVAL_TASK_PREFIX}{task_id}' if queue == 'approval' and task_id else task_id
                    initial_approval = initial_generated_approval(user, workspace, queue)
                    schedule_post, created = ScheduledPost.objects.get_or_create(
                        nano_banana=nano_banana, user=user,
                        defaults={'task_id': stored_task_id, 'scheduled_at': run_at, 'workspace': workspace, 'approval': initial_approval},
                    )
                    if not created:
                        schedule_post.task_id = stored_task_id
                        schedule_post.scheduled_at = run_at
                        schedule_post.workspace = workspace
                        schedule_post.approval = initial_approval
                        schedule_post.save(update_fields=['task_id', 'scheduled_at', 'workspace', 'approval'])
                    return Response(status=status.HTTP_200_OK)
            except Exception as exc:
                logger.exception('advanced_pipeline_exception flow=create_post: %s', exc)
                # Fall through to legacy pipeline

        try:
            caption = safe_generate_caption(
                user_profile,
                topic=fallback_topic,
                target_platform=target_platform,
            )
            prompt = safe_generate_image_prompt(
                user_profile,
                caption=caption,
                topic=fallback_topic,
                target_platform=target_platform,
                aspect_ratio=aspect_ratio,
                source_mode="image-to-image if media library images exist, otherwise text-to-image",
            )
        except Exception as exc:
            logger.exception("Create new content Gemini prompt generation failed: %s", exc)
            payload = gemini_error_payload(exc)
            return Response({'error': payload['message'], **payload}, status=status.HTTP_502_BAD_GATEWAY)
        nano_banana = NanoBananaImage()
        nano_banana.user = user
        nano_banana.caption = caption
        set_platform_captions_for_profile(nano_banana, user_profile, caption, topic=topic, target_platform=target_platform)
        nano_banana.workspace = workspace
        nano_banana.save()
        imageUrls = get_brand_reference_urls(
            user_profile,
            topic=fallback_topic,
            content_type=content_type,
            limit=9,
        )
        if reference_image_url:
            imageUrls = [reference_image_url] + [u for u in imageUrls if u != reference_image_url]

        save_nano_meta(nano_banana, reference_meta_patch(imageUrls, {
            'content_type': content_type,
            'title': topic or ('Blog post' if content_type == 'blog' else 'Social post'),
            'reference_image_url': reference_image_url,
        }))

        if imageUrls:
            ###########
            payload={
                'user_id': user_id,
                'prompt':prompt,
                'image_urls': imageUrls,
                'nano_banana_id': str(nano_banana.id),
                'image_size': aspect_ratio,
                'reference_mode': 'required',
            }
            ############
            factory = RequestFactory()
            internal_request = factory.post(
                '/nano-banana/edit-image/',
                data=json.dumps(payload),
                content_type='application/json'
            )
            internal_request.user = request.user  # pass current user
            edit_image_view = EditImageView.as_view()
            response = edit_image_view(internal_request)
            print(response.status_code)
            if response.status_code >= 400:
                nano_banana.delete()
                return Response(response.data if hasattr(response, 'data') else {'error': 'Image regeneration failed.'}, status=response.status_code)
        else:
            # class GenerateImageView(APIView):
            #
            #     GENERATE_URL = "https://api.nanobananaapi.ai/api/v1/nanobanana/generate"
            #     TASK_URL = "https://api.nanobananaapi.ai/api/v1/nanobanana/record-info"
            #
            #     def post(self, request):
            #         prompt = request.data.get("prompt", "").strip()
            #         user_id = request.data.get("user_id", "1")
            #         nano_banana_id = request.data.get("nano_banana_id", "")
            payload = {
                'user_id': user_id,
                'prompt': prompt,
                'image_urls': imageUrls,
                'nano_banana_id': str(nano_banana.id),
                'image_size': aspect_ratio,
            }
            ############
            factory = RequestFactory()
            internal_request = factory.post(
                '/nano-banana/generate/',
                data=json.dumps(payload),
                content_type='application/json'
            )
            internal_request.user = request.user  # pass current user
            generate_image_view = GenerateImageView.as_view()
            response = generate_image_view(internal_request)
            print(response.status_code)
            if response.status_code >= 400:
                nano_banana.delete()
                return Response(response.data if hasattr(response, 'data') else {'error': 'Image generation failed.'}, status=response.status_code)


        payload = {
            'user_id':user_id,
            "text":caption,
            "nano_banana_id":str(nano_banana.id)
        #     text = request.data.get("text", "")
        # nano_banana_id = request.data.get("nano_banana_id", "")
        }
        task_id = None
        try:
            result = make_posts.apply_async(
                args=[payload],
                eta=run_at
            )
            task_id = str(result.id)
        except Exception as exc:
            print('celery schedule failed', type(exc).__name__, str(exc))
        stored_task_id = f'{APPROVAL_TASK_PREFIX}{task_id}' if queue == 'approval' and task_id else task_id
        initial_approval = initial_generated_approval(user, workspace, queue)

        schedule_post, created = ScheduledPost.objects.get_or_create(
            nano_banana=nano_banana,
            user=user,
            defaults={
                'task_id': stored_task_id,
                'scheduled_at': run_at,
                'workspace':workspace,
                'approval': initial_approval,
            }
        )

        # If record already exists, update it
        if not created:
            schedule_post.task_id = stored_task_id
            schedule_post.scheduled_at = run_at
            schedule_post.workspace = workspace
            schedule_post.approval = initial_approval
            schedule_post.save(update_fields=['task_id', 'scheduled_at', 'workspace', 'approval'])
        return Response(status = status.HTTP_200_OK)


class ChangeScheduleTime(APIView):
    def post(self, request):
        nano_banana_id = request.data.get('nano_banana_id', '')
        schedule_time = request.data.get('schedule_time', '')
        schedule_time_iso = request.data.get('schedule_time_iso', '')
        user_id = request.data.get('user_id', '')

        user = get_user_by_id(user_id)
        nano_banana = get_nano_by_id(nano_banana_id)
        schedule_post = ScheduledPost.objects.filter(nano_banana=nano_banana).first()
        if user is None or nano_banana is None or schedule_post is None:
            return Response({'error': 'Scheduled post was not found.'}, status=status.HTTP_404_NOT_FOUND)

        if schedule_time_iso:
            aware_dt = parse_schedule_iso(schedule_time_iso)
        else:
            raw = schedule_time

            # Extract offset
            match = re.search(r'GMT([+-]\d+)', raw)
            offset_hours = int(match.group(1)) if match else 0

            # Strip timezone part and parse
            clean = re.sub(r'\s*GMT[+-]\d+', '', raw).strip()
            naive_dt = datetime.strptime(clean, "%a, %b %d · %I:%M%p")
            current_year = timezone2.now().year
            naive_dt = naive_dt.replace(year=current_year)

            # Make timezone-aware
            tz = timezone(timedelta(hours=offset_hours))
            aware_dt = naive_dt.replace(tzinfo=tz)
        if aware_dt <= timezone2.now():
            return Response({'error': 'Schedule time must be in the future. Use Post now to publish immediately.'}, status=status.HTTP_400_BAD_REQUEST)

        schedule_post.scheduled_at = aware_dt
        schedule_post.save(update_fields=['scheduled_at'])
        if schedule_post.approval == 'approved':
            enqueue_publish_task(schedule_post, user)
        return Response({'data': serialize_nano_banana(nano_banana, schedule_post)}, status=status.HTTP_200_OK)

class RegenerateImage(APIView):
    def post(self, request):
        nano_banana_ids = request.data.get('nano_banana_ids', [])
        user_id = request.data.get('user_id', '')
        workspace_id = request.data.get('workspace_id', '')
        target_platform = request.data.get('target_platform', 'multi-platform')
        aspect_ratio = request.data.get('image_size', '1:1')
        user = get_user_by_id(user_id)
        workspace = get_workspace_by_id(workspace_id)
        if user is None:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not nano_banana_ids:
            return Response({'error': 'No posts selected.'}, status=status.HTTP_400_BAD_REQUEST)
        first_nano = get_nano_by_id(nano_banana_ids[0], user=user)
        if first_nano is None:
            return Response({'error': 'Post image was not found.'}, status=status.HTTP_404_NOT_FOUND)
        if workspace is None:
            workspace = first_nano.workspace
        if workspace is None:
            return Response({'error': 'workspace_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if should_enqueue_generation(request):
            return enqueue_nano_generation_job(
                request,
                'regenerate_image',
                user,
                workspace=workspace,
                nano_banana=first_nano,
                payload=request.data,
            )

        # time.sleep(1000)
        last_data = None
        for nano_banana_id in nano_banana_ids:
            try:
                nano_banana = get_nano_by_id(nano_banana_id, user=user)
                if nano_banana is None:
                    return Response({'error': 'Post image was not found.'}, status=status.HTTP_404_NOT_FOUND)
                ws = workspace or nano_banana.workspace
                user_profile = get_generation_profile(user, ws)
                if user_profile is None:
                    return Response({'error': 'Workspace brand profile is required before regenerating images.'}, status=status.HTTP_400_BAD_REQUEST)

                # ── Advanced regeneration (feature-flagged) ──
                if ADVANCED_PIPELINE:
                    try:
                        from content_engine.services.generation_orchestrator import orchestrate_generation
                        from content_engine.services.context_builder import generate_correlation_id
                        corr_id = generate_correlation_id('regenerate_image', ws)
                        meta = get_nano_meta(nano_banana)
                        snapshot = meta.get('__context_snapshot')

                        orch_result = orchestrate_generation(
                            flow='regenerate_image',
                            user=user,
                            workspace=ws,
                            topic=meta.get('title', '') or nano_banana.caption,
                            target_platform=target_platform,
                            aspect_ratio=aspect_ratio,
                            existing_post=nano_banana,
                            context_snapshot=snapshot,
                            correlation_id=corr_id,
                            previous_caption=nano_banana.caption,
                        )

                        if orch_result.get('status') == 'completed':
                            caption = orch_result.get('caption') or nano_banana.caption
                            prompt = orch_result.get('image_prompt')
                            nano_banana.caption = caption
                            # Use advanced platform captions if returned
                            adv_captions = orch_result.get('platform_captions', {})
                            if adv_captions:
                                nano_banana.platform_captions = adv_captions
                            else:
                                set_platform_captions_for_profile(nano_banana, user_profile, caption, topic=caption, target_platform=target_platform)
                            nano_banana.save()

                            # Update meta with snapshot
                            new_snapshot = orch_result.get('context_snapshot', {})
                            new_snapshot['correlation_id'] = corr_id
                            save_nano_meta(nano_banana, {'__context_snapshot': new_snapshot})

                            # Proceed to image generation with advanced prompt
                            image_urls = get_brand_reference_urls(
                                user_profile,
                                topic=caption,
                                content_type=meta.get('content_type', 'social'),
                                include_existing=[*get_nano_reference_urls(nano_banana), nano_banana.picture_url],
                                limit=9,
                            )
                            save_nano_meta(nano_banana, reference_meta_patch(image_urls))
                            payload = {
                                'user_id': user_id, 'prompt': prompt, 'image_urls': image_urls,
                                'nano_banana_id': str(nano_banana.id), 'image_size': aspect_ratio,
                                'reference_mode': 'required' if image_urls else 'optional',
                            }
                            factory = RequestFactory()
                            internal_request = factory.post('/nano-banana/edit-image/', data=json.dumps(payload), content_type='application/json')
                            internal_request.user = request.user
                            response = EditImageView.as_view()(internal_request)
                            if response.status_code >= 400:
                                return Response(response.data if hasattr(response, 'data') else {'error': 'Advanced image regeneration failed.'}, status=response.status_code)
                            nano_banana.refresh_from_db()
                            last_data = serialize_nano_banana(nano_banana)
                            continue # Successfully handled via advanced flow
                        else:
                            logger.warning('advanced_image_regen_failed flow=regenerate_image corr=%s error=%s', corr_id, orch_result.get('error', ''))
                    except Exception as adv_exc:
                        logger.exception('advanced_image_regen_exception flow=regenerate_image: %s', adv_exc)

                caption = safe_generate_caption(
                    user_profile,
                    previous_caption=nano_banana.caption,
                    target_platform=target_platform,
                )
                nano_banana.caption = caption
                set_platform_captions_for_profile(nano_banana, user_profile, caption, topic=nano_banana.caption or '', target_platform=target_platform)
                nano_banana.save(update_fields=['caption', 'platform_captions'])
                prompt = safe_generate_image_prompt(
                    user_profile,
                    caption=caption,
                    target_platform=target_platform,
                    aspect_ratio=aspect_ratio,
                    source_mode="image-to-image using the previous generated design as source",
                )
                image_urls = get_brand_reference_urls(
                    user_profile,
                    topic=nano_banana.caption or caption,
                    content_type=get_nano_meta(nano_banana).get('content_type', 'social'),
                    include_existing=[
                        *get_nano_reference_urls(nano_banana),
                        nano_banana.picture_url,
                    ],
                    limit=9,
                )
                save_nano_meta(nano_banana, reference_meta_patch(image_urls))
                payload = {
                    'user_id': user_id,
                    'prompt': prompt,
                    'image_urls': image_urls,
                    'nano_banana_id': str(nano_banana.id),
                    'image_size': aspect_ratio,
                    'reference_mode': 'required' if image_urls else 'optional',
                }
                factory = RequestFactory()
                internal_request = factory.post(
                    '/nano-banana/edit-image/',
                    data=json.dumps(payload),
                    content_type='application/json'
                )
                internal_request.user = request.user
                edit_image_view = EditImageView.as_view()
                response = edit_image_view(internal_request)
                if response.status_code >= 400:
                    return Response(response.data if hasattr(response, 'data') else {'error': 'Voice Spark AI image regeneration failed.'}, status=response.status_code)
                nano_banana.refresh_from_db()
                last_data = serialize_nano_banana(nano_banana)
            except Exception as exc:
                logger.exception("Regenerate image failed: %s", exc)
                payload = gemini_error_payload(exc)
                return Response({'error': payload['message'], **payload}, status=status.HTTP_502_BAD_GATEWAY)
        return JsonResponse({"data": last_data}, status=status.HTTP_200_OK)


class SavePlatformCaptions(APIView):
    def post(self, request):
        user_id = request.data.get('user_id', '')
        nano_banana_id = request.data.get('nano_banana_id', '')
        captions = request.data.get('captions') or {}
        regenerate_platform = str(request.data.get('regenerate_platform') or '').strip().lower()
        instruction = str(request.data.get('instruction') or '').strip()

        user = get_user_by_id(user_id)
        nano_banana = get_nano_by_id(nano_banana_id, user=user)
        if user is None or nano_banana is None:
            return Response({'error': 'Post was not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not isinstance(captions, dict):
            return Response({'error': 'Captions must be an object.'}, status=status.HTTP_400_BAD_REQUEST)

        current = get_platform_captions(nano_banana)
        if regenerate_platform:
            platform_key = 'twitter' if regenerate_platform in ('x', 'twitter') else regenerate_platform
            if platform_key not in PLATFORM_CAPTION_KEYS:
                return Response({'error': 'Unsupported platform.'}, status=status.HTTP_400_BAD_REQUEST)
            user_profile = get_generation_profile(user, nano_banana.workspace)
            if user_profile is None or not user_profile.markdown:
                return Response({'error': 'Workspace brand profile is required before regenerating captions.'}, status=status.HTTP_400_BAD_REQUEST)

            # ── Advanced caption regeneration (feature-flagged) ──
            if ADVANCED_PIPELINE:
                try:
                    from content_engine.services.generation_orchestrator import orchestrate_generation
                    from content_engine.services.context_builder import generate_correlation_id
                    workspace = nano_banana.workspace
                    corr_id = generate_correlation_id('regenerate_caption', workspace)
                    topic = get_nano_meta(nano_banana).get('title', '') or nano_banana.caption
                    orch_result = orchestrate_generation(
                        flow='regenerate_caption',
                        user=user,
                        workspace=workspace,
                        topic=topic,
                        target_platform=platform_key,
                        user_instruction=instruction or f'Regenerate this caption for {platform_key}.',
                        previous_caption=current.get(platform_key) or nano_banana.caption,
                        correlation_id=corr_id,
                    )
                    if orch_result.get('status') == 'completed' and orch_result.get('caption'):
                        regenerated = orch_result['caption']
                        current[platform_key] = regenerated
                        captions = current
                    else:
                        logger.warning('advanced_caption_regen_failed corr=%s, falling back to legacy', corr_id)
                        raise RuntimeError('Advanced caption failed, using legacy.')
                except Exception as adv_exc:
                    logger.info('advanced_caption_fallback platform=%s: %s', platform_key, adv_exc)
                    # Fall through to legacy below
                    try:
                        regenerated = gemini_text(
                            build_caption_request(
                                user_profile,
                                previous_caption=current.get(platform_key) or nano_banana.caption,
                                user_instruction=instruction or f"Regenerate this caption for {platform_key}.",
                                target_platform=platform_key,
                            ),
                            system_prompt=(
                                'You are a senior social media copywriter. '
                                'Return only one finished caption as plain text. '
                                'No markdown, no explanation.'
                            ),
                        )
                    except Exception as exc:
                        logger.exception("Caption regeneration failed: %s", exc)
                        payload = gemini_error_payload(exc)
                        return Response({'error': payload['message'], **payload}, status=status.HTTP_502_BAD_GATEWAY)
                    if not regenerated:
                        return Response({'error': 'Voice Spark AI returned an empty caption.', 'error_type': 'invalid_response', 'retryable': True}, status=status.HTTP_502_BAD_GATEWAY)
                    current[platform_key] = regenerated
                    captions = current
            else:
                try:
                    regenerated = gemini_text(
                        build_caption_request(
                        user_profile,
                        previous_caption=current.get(platform_key) or nano_banana.caption,
                        user_instruction=instruction or f"Regenerate this caption for {platform_key}.",
                        target_platform=platform_key,
                        ),
                        system_prompt=(
                            'You are a senior social media copywriter. '
                            'Return only one finished caption as plain text. '
                            'No markdown, no explanation.'
                        ),
                    )
                except Exception as exc:
                    logger.exception("Caption regeneration failed: %s", exc)
                    payload = gemini_error_payload(exc)
                    return Response({'error': payload['message'], **payload}, status=status.HTTP_502_BAD_GATEWAY)
                if not regenerated:
                    return Response({'error': 'Voice Spark AI returned an empty caption.', 'error_type': 'invalid_response', 'retryable': True}, status=status.HTTP_502_BAD_GATEWAY)
                current[platform_key] = regenerated
                captions = current

        cleaned = {}
        for key in PLATFORM_CAPTION_KEYS:
            cleaned[key] = str(captions.get(key) if captions.get(key) is not None else current.get(key, '')).strip()

        nano_banana.platform_captions = cleaned
        nano_banana.caption = cleaned.get('facebook') or cleaned.get('instagram') or cleaned.get('linkedin') or cleaned.get('twitter') or nano_banana.caption
        nano_banana.save(update_fields=['platform_captions', 'caption'])

        return JsonResponse({"data": serialize_nano_banana(nano_banana)}, status=status.HTTP_200_OK)


class DeleteGeneratedImage(APIView):
    def post(self, request):
        user_id = request.data.get('user_id', '')
        nano_banana_id = request.data.get('nano_banana_id', '')

        user = get_user_by_id(user_id)
        nano_banana = get_nano_by_id(nano_banana_id, user=user)
        if user is None or nano_banana is None:
            return Response({'error': 'Post was not found.'}, status=status.HTTP_404_NOT_FOUND)

        nano_banana.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DownloadGeneratedImage(APIView):
    def post(self, request):
        user_id = request.data.get('user_id', '')
        nano_banana_id = request.data.get('nano_banana_id', '')

        user = get_user_by_id(user_id)
        nano_banana = get_nano_by_id(nano_banana_id, user=user)
        if user is None or nano_banana is None:
            return Response({'error': 'Post was not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not nano_banana.picture_url:
            return Response({'error': 'Design image was not found.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            image_response = requests.get(nano_banana.picture_url, timeout=30)
            image_response.raise_for_status()
        except requests.RequestException:
            return Response({'error': 'Failed to download design image.'}, status=status.HTTP_502_BAD_GATEWAY)

        content_type = image_response.headers.get('content-type') or 'application/octet-stream'
        extension = mimetypes.guess_extension(content_type.split(';')[0].strip()) or ''
        if extension == '.jpe':
            extension = '.jpg'

        parsed_name = os.path.basename(urlparse(nano_banana.picture_url).path)
        parsed_ext = os.path.splitext(parsed_name)[1]
        if not extension and parsed_ext:
            extension = parsed_ext
        if not extension:
            extension = '.png'

        filename = f'voice-spark-design-{nano_banana.id}{extension}'
        response = HttpResponse(image_response.content, content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Content-Length'] = str(len(image_response.content))
        return response


class GetApprovalPost(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        user_id = request.data.get('user_id', '')
        workspace_id = request.data.get('workspace_id', '')
        workspace = get_workspace_by_id(workspace_id)
        user = get_user_by_id(user_id)
        schedule_post = ScheduledPost.objects.filter(
            user=user,
            workspace=workspace,
            approval__in=['approved', 'posted'],
        ).select_related('nano_banana').order_by('scheduled_at', '-created_at')
        data = [serialize_nano_banana(sp.nano_banana, sp) for sp in schedule_post]
        return JsonResponse(data={'data':data})


class VisualFeedback(APIView):
    def post(self, request):
        user_id = request.data.get('user_id', '')
        workspace_id = request.data.get('workspace_id', '')
        nano_banana_id = request.data.get('nano_banana_id', '')
        reaction = request.data.get('reaction', '')

        if reaction not in ('like', 'dislike'):
            return Response({'error': 'Reaction must be like or dislike.'}, status=status.HTTP_400_BAD_REQUEST)

        user = get_user_by_id(user_id)
        workspace = get_workspace_by_id(workspace_id) if workspace_id else None
        nano_banana = get_nano_by_id(nano_banana_id, user=user)
        if user is None or nano_banana is None:
            return Response({'error': 'Post was not found.'}, status=status.HTTP_404_NOT_FOUND)

        profile_workspace = workspace or nano_banana.workspace
        if profile_workspace is None:
            return Response({'error': 'workspace_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        user_profile = UserProfile.objects.filter(user=user, workspace=profile_workspace).first()
        if user_profile is None:
            return Response({'error': 'Business profile is not ready.'}, status=status.HTTP_400_BAD_REQUEST)

        brand_voice = user_profile.brand_voice or {}
        feedback = brand_voice.get('visual_feedback', [])
        feedback = [item for item in feedback if item.get('nano_banana_id') != str(nano_banana.id)]
        feedback.append({
            'nano_banana_id': str(nano_banana.id),
            'reaction': reaction,
            'image_url': nano_banana.picture_url,
            'caption': nano_banana.caption,
        })
        brand_voice['visual_feedback'] = feedback[-50:]
        user_profile.brand_voice = brand_voice
        user_profile.save(update_fields=['brand_voice'])

        return Response({'reaction': reaction}, status=status.HTTP_200_OK)


class ChangeApproval(APIView):
    def post(self, request):
        user_id = request.data.get('user_id', '')

        nano_banana_id = request.data.get('nano_banana_id', '')
        action = request.data.get('action', 'approved')
        requested_platforms = normalize_platform_list(request.data.get('approved_platforms'))
        schedule_time_iso = request.data.get('schedule_time_iso', '')
        post_now = parse_request_bool(request.data.get('post_now', False))
        user = get_user_by_id(user_id)
        nano_banana = get_nano_by_id(nano_banana_id, user=user)
        if user is None or nano_banana is None:
            return Response({'error': 'Post was not found.'}, status=status.HTTP_404_NOT_FOUND)
        schedule_obj = ScheduledPost.objects.filter(nano_banana=nano_banana).first()
        if schedule_obj and schedule_obj.approval == 'posted':
            return Response({'data': serialize_nano_banana(nano_banana, schedule_obj)}, status=status.HTTP_200_OK)
        if action in ('reject', 'rejected'):
            if schedule_obj:
                schedule_obj.delete()
            nano_banana.delete()
            return Response(status=status.HTTP_200_OK)
        workspace = schedule_obj.workspace if schedule_obj else nano_banana.workspace
        meta = get_nano_meta(nano_banana)
        content_type = meta.get('content_type', 'social')
        requested_schedule = parse_schedule_iso(schedule_time_iso) if schedule_time_iso else None
        if content_type in ('blog', 'email') and not requested_platforms:
            if schedule_obj:
                schedule_obj.workspace = workspace
            else:
                schedule_obj = ScheduledPost(user=user, nano_banana=nano_banana, workspace=workspace)
                schedule_obj.scheduled_at = default_run_at_for_day(user, workspace)
            if requested_schedule:
                schedule_obj.scheduled_at = requested_schedule
            if not post_now and schedule_obj.scheduled_at <= timezone2.now():
                return Response({'error': 'Schedule time must be in the future. Use Post now to publish immediately.'}, status=status.HTTP_400_BAD_REQUEST)
            schedule_obj.approval = 'approved'
            schedule_obj.save()
            save_nano_meta(nano_banana, {'approved_platforms': [], 'content_type': content_type})
            return Response({'data': serialize_nano_banana(nano_banana, schedule_obj)}, status=status.HTTP_200_OK)
        connected_platforms = workspace_connected_platforms(user, workspace)
        selected_platforms = requested_platforms

        # If the user specifically requested platforms that aren't connected, we log a warning
        # but we allow the approval to proceed. The publish task will handle the actual connection checks.
        disconnected = [platform for platform in selected_platforms if platform not in connected_platforms]
        if disconnected:
            logger.warning('ChangeApproval: requested platforms %s are not connected. Connected: %s', disconnected, connected_platforms)
        if not selected_platforms:
            return Response(
                {'error': 'No approved platforms were selected for this post.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if schedule_obj:
            schedule_obj.workspace = workspace
        else:
            schedule_obj = ScheduledPost(user=user, nano_banana=nano_banana, workspace=workspace)
            schedule_obj.scheduled_at = default_run_at_for_day(user, workspace)
        if requested_schedule:
            schedule_obj.scheduled_at = requested_schedule
        if post_now:
            schedule_obj.scheduled_at = timezone2.now()
        if not post_now and schedule_obj.scheduled_at <= timezone2.now():
            return Response({'error': 'Schedule time must be in the future. Use Post now to publish immediately.'}, status=status.HTTP_400_BAD_REQUEST)
        schedule_obj.approval = 'approved'
        schedule_obj.save()
        save_nano_meta(nano_banana, {'approved_platforms': selected_platforms})
        enqueue_publish_task(schedule_obj, user, post_now=post_now)
        return Response({'data': serialize_nano_banana(nano_banana, schedule_obj)}, status=status.HTTP_200_OK)


