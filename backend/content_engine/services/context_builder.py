"""
context_builder.py — Workspace Intelligence Context Aggregator

Aggregates all 12 dimensions of workspace context before any AI generation.
Brand kit is the primary source of truth. Competitors are differentiation-only.
Every call verifies workspace_id + user_id ownership.
"""

import hashlib
import json
import logging
import re
import uuid
from datetime import datetime

from django.utils import timezone

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROMPT_VERSION = '1.0.0'
PIPELINE_VERSION = '5.0.0'

CONTEXT_TOKEN_BUDGET = {
    'brand_identity': 400,
    'business_profile': 500,
    'campaign_context': 300,
    'competitor_intel': 200,
    'audience_intel': 150,
    'platform_rules': 100,
    'existing_post': 200,
    'total_max': 2500,
}

REFERENCE_TYPES = {'product', 'logo', 'style', 'general'}

QUALITY_CHECKS = [
    'reference_preserved',
    'brand_colors_followed',
    'brand_tone_followed',
    'visual_style_followed',
    'caption_platform_specific',
    'caption_not_generic',
    'cta_matches_goal',
    'user_instruction_followed',
    'identity_preserved_in_edit',
    'regeneration_coherent',
]

STYLE_ID_ALIASES = {
    'ultra-realistic': 'ultra_realistic',
    'ultra realistic': 'ultra_realistic',
    'cartoon-animation': 'cartoon_animated',
    'cartoon animated': 'cartoon_animated',
    'cartoon / animated': 'cartoon_animated',
    'product-studio': 'product_studio',
    'product studio': 'product_studio',
    'editorial-lifestyle': 'editorial_lifestyle',
    'editorial lifestyle': 'editorial_lifestyle',
}


def normalize_style_id(value):
    raw = str(value or '').strip().lower().replace('_', ' ')
    return STYLE_ID_ALIASES.get(raw) or STYLE_ID_ALIASES.get(str(value or '').strip().lower()) or raw.replace(' ', '_')

# State machine transitions — terminal-safe
ALLOWED_TRANSITIONS = {
    'queued': {'running', 'failed'},
    'running': {'completed', 'failed'},
    'completed': set(),   # terminal
    'failed': set(),      # terminal
}


# ---------------------------------------------------------------------------
# Context building
# ---------------------------------------------------------------------------

def build_generation_context(
    user,
    workspace,
    topic='',
    campaign_context=None,
    existing_post=None,
    user_instruction='',
    target_platform='multi-platform',
    content_type='social',
    correlation_id=None,
    reference_image_url=None,
):
    """Aggregate all 12 workspace intelligence dimensions.

    Returns a dict consumed by prompt_builder functions.
    """
    if not user or not workspace:
        raise ValueError('user and workspace are required for context building.')

    correlation_id = correlation_id or generate_correlation_id('context', workspace)

    # 1. Brand kit (primary source of truth) + 2. Workspace identity
    user_profile = _load_user_profile(user, workspace)
    business_profile = _load_business_profile(user, workspace)
    brand_setting = _load_brand_setting(user, workspace, business_profile)

    # 3. Content preferences
    content_prefs = _extract_content_preferences(user_profile)

    # 4. Visual identity
    visual_identity = _extract_visual_identity(brand_setting, content_prefs)

    # 5. Audience intelligence
    audience = _load_audience_intelligence(user, workspace)

    # 6. Competitor intelligence (differentiation only)
    competitors = _load_competitor_intelligence(user, workspace)

    # 6.1 Workspace-level reference images
    workspace_refs = _load_workspace_references(user, workspace)

    # 7. Campaign context
    campaign = campaign_context if isinstance(campaign_context, dict) else {}

    # 10. Platform context
    platform_voice = _load_platform_voice(user, workspace, target_platform)

    # 11. Scheduling context
    scheduling = _extract_scheduling(content_prefs)

    # 12. Language
    language = (content_prefs.get('language') or {}).get('label') or 'English'

    brand_name = _extract_brand_name(business_profile, user_profile, workspace)
    colors = _extract_colors(brand_setting)
    logos = _extract_logos(brand_setting)
    font = _extract_font(brand_setting)

    context = {
        'correlation_id': correlation_id,
        'prompt_version': PROMPT_VERSION,
        'pipeline_version': PIPELINE_VERSION,
        'timestamp': timezone.now().isoformat(),

        # Identity
        'workspace_id': str(workspace.id),
        'workspace_name': getattr(workspace, 'name', '') or '',
        'user_id': user.id,
        'brand_name': brand_name,

        # Brand kit
        'colors': colors,
        'logos': logos,
        'logo_available': bool(logos),
        'font': font,
        'tone': getattr(brand_setting, 'tone', '') or '' if brand_setting else '',
        'image_style': getattr(brand_setting, 'image_style', '') or '' if brand_setting else '',
        'visual_style': visual_identity,

        # Content preferences
        'language': language,
        'content_style': content_prefs.get('content_style') or {},
        'smart_captions': content_prefs.get('smart_captions', {}).get('enabled', True),

        # Business
        'services': _extract_services(business_profile),
        'audience_text': _extract_audience_text(business_profile),
        'keywords': _extract_keywords(business_profile),
        'profile_summary': _summarize_profile(user_profile, CONTEXT_TOKEN_BUDGET['business_profile']),

        # Audience intelligence
        'audience_profiles': audience,

        # Competitor intelligence
        'competitors': competitors,

        # Campaign
        'campaign_theme': campaign.get('theme', ''),
        'campaign_cta': campaign.get('call_to_action', ''),
        'campaign_funnel': campaign.get('funnel_goal', ''),
        'campaign_week': campaign.get('week_number', ''),

        # Existing post (for edits/regen)
        'existing_caption': '',
        'existing_image_url': '',
        'existing_references': [],

        # User instruction
        'user_instruction': user_instruction,

        # Platform
        'target_platform': target_platform,
        'platform_voice': platform_voice,
        'content_type': content_type,

        # Scheduling
        'scheduling': scheduling,

        # Topic
        'topic': topic,
    }

    # 8. Existing post context (for regeneration/editing)
    context['existing_references'] = workspace_refs
    
    # Inject post-specific reference image as high priority product anchor
    if reference_image_url:
        ref_obj = {'url': reference_image_url, 'type': 'product', 'source': 'post_specific'}
        # Prepend to make it first priority, remove if already in workspace_refs (dedup)
        filtered_refs = [r for r in workspace_refs if (r.get('url') if isinstance(r, dict) else r) != reference_image_url]
        context['existing_references'] = [ref_obj] + filtered_refs

    if existing_post and isinstance(existing_post, dict):
        context['existing_caption'] = existing_post.get('caption', '')
        context['existing_image_url'] = existing_post.get('image_url', '')
        
        # Combine and deduplicate
        provided_refs = existing_post.get('references', [])
        # Ensure provided_refs are objects
        provided_objs = []
        for r in provided_refs:
            if isinstance(r, dict):
                provided_objs.append(r)
            else:
                provided_objs.append({'url': r, 'type': 'product', 'source': 'provided'})
                
        combined = provided_objs + context['existing_references']
        # Simple deduplication by URL
        seen_urls = set()
        unique_refs = []
        for r in combined:
            url = r.get('url') if isinstance(r, dict) else r
            if url not in seen_urls:
                unique_refs.append(r)
                seen_urls.add(url)
        context['existing_references'] = unique_refs

    # Budget the context
    context = _budget_context(context)

    return context


# ---------------------------------------------------------------------------
# Data loaders (workspace-isolated)
# ---------------------------------------------------------------------------

def _load_user_profile(user, workspace):
    try:
        from auth_user.models import UserProfile
        return UserProfile.objects.filter(user=user, workspace=workspace).first()
    except Exception:
        return None


def _load_business_profile(user, workspace):
    try:
        from content_engine.models import BusinessProfile
        return BusinessProfile.objects.filter(
            user=user, workspace=workspace
        ).order_by('-updated_at').first()
    except Exception:
        return None


def _load_brand_setting(user, workspace, business_profile=None):
    try:
        from content_engine.models import BrandSetting
        from django.db.models import Q
        qs = BrandSetting.objects.filter(user=user, workspace=workspace)
        if business_profile:
            qs = qs.filter(
                Q(business_profile=business_profile) | Q(business_profile__isnull=True)
            )
        return qs.order_by('-business_profile_id', '-updated_at').first()
    except Exception:
        return None


def _load_audience_intelligence(user, workspace):
    try:
        from content_engine.models import AudienceProfile
        profiles = AudienceProfile.objects.filter(
            user=user, workspace=workspace
        )[:3]
        return [
            {
                'name': p.name,
                'pain_points': (p.pain_points or [])[:3],
                'goals': (p.goals or [])[:3],
                'awareness_level': p.awareness_level or '',
            }
            for p in profiles
        ]
    except Exception:
        return []


def _load_competitor_intelligence(user, workspace):
    """Load competitors for differentiation only. Never copy."""
    try:
        from content_engine.models import CompetitorAnalysis
        items = CompetitorAnalysis.objects.filter(
            user=user, workspace=workspace
        ).exclude(website_url='').order_by('-updated_at')[:5]
        return [
            {
                'name': item.name,
                'website_url': item.website_url,
                'key_features': (item.key_features or [])[:3],
                'differentiators': (item.differentiators or [])[:3],
                'usage': 'differentiation_only',
            }
            for item in items if item.name and item.website_url
        ]
    except Exception:
        return []


def _load_workspace_references(user, workspace):
    """Load uploaded product/reference images for the workspace."""
    try:
        from auth_user.models import UploadImages
        images = UploadImages.objects.filter(workspace=workspace).order_by('-updated_at')[:10]
        refs = []
        for img in images:
            if img.image:
                try:
                    refs.append({
                        'url': img.image.url,
                        'type': 'product',
                        'source': 'workspace_library'
                    })
                except Exception:
                    continue
        return refs
    except Exception:
        return []


def _load_platform_voice(user, workspace, platform):
    try:
        from content_engine.models import ChannelVoiceConfig
        canonical = platform.lower().replace('x', 'twitter') if platform else ''
        config = ChannelVoiceConfig.objects.filter(
            user=user, workspace=workspace, platform=canonical
        ).first()
        if config:
            return {
                'tone': config.tone or '',
                'emotion': config.emotion or '',
                'character': config.character or '',
            }
    except Exception:
        pass
    return {}


# ---------------------------------------------------------------------------
# Extractors
# ---------------------------------------------------------------------------

def _extract_brand_name(business_profile, user_profile, workspace):
    from content_engine.services.gemini_image import business_name_from_profile
    if business_profile:
        return business_name_from_profile(business_profile)
    if user_profile:
        return business_name_from_profile(user_profile)
    return getattr(workspace, 'name', '') or 'the brand'


def _extract_colors(brand_setting):
    if not brand_setting:
        return []
    from content_engine.services.gemini_image import normalize_reference_list
    return normalize_reference_list(brand_setting.colors)[:8]


def _extract_logos(brand_setting):
    if not brand_setting:
        return []
    from content_engine.services.gemini_image import normalize_reference_list
    return normalize_reference_list(brand_setting.logos)[:4]


def _extract_font(brand_setting):
    if not brand_setting or not brand_setting.font:
        return 'selected brand font'
    font_data = brand_setting.font if isinstance(brand_setting.font, dict) else {}
    return font_data.get('displayName') or font_data.get('family') or 'selected brand font'


def _extract_content_preferences(user_profile):
    if not user_profile:
        return {'language': {'label': 'English'}, 'content_style': {}, 'smart_captions': {'enabled': True}}
    brand_voice = user_profile.brand_voice if isinstance(getattr(user_profile, 'brand_voice', None), dict) else {}
    preferences = brand_voice.get('content_preferences') if isinstance(brand_voice.get('content_preferences'), dict) else {}
    language = preferences.get('language') if isinstance(preferences.get('language'), dict) else {'label': 'English'}
    content_style = preferences.get('content_style') if isinstance(preferences.get('content_style'), dict) else {}
    smart_captions = preferences.get('smart_captions') if isinstance(preferences.get('smart_captions'), dict) else {}
    return {
        'language': language,
        'content_style': content_style,
        'smart_captions': {'enabled': bool(smart_captions.get('enabled', True))},
        'timezone': str(preferences.get('timezone') or 'Asia/Dhaka'),
        'default_schedule_time': str(preferences.get('default_schedule_time') or '09:00'),
    }


def _extract_visual_identity(brand_setting, content_prefs):
    style_data = {}
    if brand_setting and isinstance(getattr(brand_setting, 'recommended_visual_style', None), dict):
        style_data = dict(brand_setting.recommended_visual_style)
    pref_style = content_prefs.get('content_style') if isinstance(content_prefs.get('content_style'), dict) else {}
    if pref_style.get('id'):
        style_data = {**style_data, **pref_style}
    return {
        'id': normalize_style_id(style_data.get('id', '')),
        'name': style_data.get('name') or style_data.get('label') or '',
        'prompt': style_data.get('prompt') or style_data.get('description') or '',
    }


def _extract_services(business_profile):
    if not business_profile:
        return []
    profile_data = business_profile.profile if isinstance(getattr(business_profile, 'profile', None), dict) else {}
    return (profile_data.get('services') or [])[:6]


def _extract_audience_text(business_profile):
    if not business_profile:
        return ''
    profile_data = business_profile.profile if isinstance(getattr(business_profile, 'profile', None), dict) else {}
    return str(profile_data.get('audience') or profile_data.get('target_audience') or '')


def _extract_keywords(business_profile):
    if not business_profile:
        return []
    profile_data = business_profile.profile if isinstance(getattr(business_profile, 'profile', None), dict) else {}
    return (profile_data.get('keywords') or [])[:10]


def _extract_scheduling(content_prefs):
    return {
        'timezone': content_prefs.get('timezone', 'Asia/Dhaka'),
        'default_time': content_prefs.get('default_schedule_time', '09:00'),
    }


def _summarize_profile(user_profile, budget_chars):
    """Summarize profile markdown within token budget."""
    if not user_profile:
        return ''
    markdown = getattr(user_profile, 'editable_markdown', '') or getattr(user_profile, 'markdown', '') or ''
    if not markdown:
        return ''
    # Truncate to budget (rough: 1 token ≈ 4 chars)
    max_chars = budget_chars * 4
    if len(markdown) <= max_chars:
        return markdown
    return markdown[:max_chars] + '\n[... profile truncated for context budget ...]'


# ---------------------------------------------------------------------------
# Context budgeting — prevent token explosion
# ---------------------------------------------------------------------------

def _budget_context(context):
    """Score relevance, trim low-value data, prevent prompt bloat."""
    # Trim competitors to summary only
    if context.get('competitors'):
        trimmed = []
        for comp in context['competitors'][:3]:
            trimmed.append({
                'name': comp.get('name', ''),
                'differentiators': comp.get('differentiators', [])[:2],
                'usage': 'differentiation_only',
            })
        context['competitors'] = trimmed

    # Trim audience profiles
    if context.get('audience_profiles'):
        context['audience_profiles'] = context['audience_profiles'][:2]

    # Trim existing references
    if context.get('existing_references'):
        context['existing_references'] = context['existing_references'][:5]

    return context


# ---------------------------------------------------------------------------
# Reference classification
# ---------------------------------------------------------------------------

def classify_reference(url, metadata=None):
    """Classify a reference URL into: product, logo, style, general."""
    if not url:
        return 'general'

    meta = metadata if isinstance(metadata, dict) else {}
    explicit = str(meta.get('type') or meta.get('label') or meta.get('category') or '').lower()
    if explicit in REFERENCE_TYPES:
        return explicit

    url_lower = str(url).lower()
    if any(kw in url_lower for kw in ('logo', 'brand-mark', 'brandmark', 'watermark')):
        return 'logo'
    if any(kw in url_lower for kw in ('product', 'item', 'package', 'packaging')):
        return 'product'
    if any(kw in url_lower for kw in ('style', 'mood', 'aesthetic', 'inspiration')):
        return 'style'
    return 'general'


def order_references_by_priority(references, brand_logos=None):
    """Order: product first → logo → style → general. Deduplicate."""
    if not references:
        return []

    classified = []
    seen = set()
    for ref in references:
        url = ref if isinstance(ref, str) else (ref.get('url') or '')
        if not url or url in seen:
            continue
        seen.add(url)
        meta = ref if isinstance(ref, dict) else {}
        ref_type = classify_reference(url, meta)
        priority = {'product': 0, 'logo': 1, 'style': 2, 'general': 3}.get(ref_type, 3)
        classified.append((priority, url, ref_type))

    # Inject brand logos if not already present
    for logo_url in (brand_logos or []):
        if logo_url and logo_url not in seen:
            seen.add(logo_url)
            classified.append((1, logo_url, 'logo'))

    classified.sort(key=lambda x: x[0])
    return [{'url': url, 'type': ref_type} for _, url, ref_type in classified]


# ---------------------------------------------------------------------------
# Context snapshots — stored in nano_banana metadata for regen consistency
# ---------------------------------------------------------------------------

def create_context_snapshot(context):
    """Lightweight snapshot for regeneration context preservation."""
    return {
        'snapshot_version': '1.0.0',
        'prompt_version': context.get('prompt_version', PROMPT_VERSION),
        'pipeline_version': context.get('pipeline_version', PIPELINE_VERSION),
        'timestamp': context.get('timestamp', timezone.now().isoformat()),
        'brand_name': context.get('brand_name', ''),
        'colors': context.get('colors', [])[:4],
        'visual_style': context.get('visual_style', {}),
        'campaign_theme': context.get('campaign_theme', ''),
        'campaign_cta': context.get('campaign_cta', ''),
        'campaign_funnel': context.get('campaign_funnel', ''),
        'topic': context.get('topic', ''),
        'target_platform': context.get('target_platform', ''),
        'language': context.get('language', 'English'),
        'existing_references': [r.get('url') if isinstance(r, dict) else r for r in (context.get('existing_references') or [])[:5]],
    }


def merge_snapshot_with_current(snapshot, current_context):
    """Merge original generation snapshot with current workspace state + user delta."""
    if not snapshot or not isinstance(snapshot, dict):
        return current_context

    merged = dict(current_context)
    # Campaign continuity: prefer original snapshot for campaign theme/CTA
    for key in ('campaign_theme', 'campaign_cta', 'campaign_funnel'):
        original = snapshot.get(key, '')
        if original and not merged.get(key):
            merged[key] = original

    # Reference continuity: keep original references
    original_refs = snapshot.get('existing_references', [])
    if original_refs and not merged.get('existing_references'):
        merged['existing_references'] = original_refs

    return merged


# ---------------------------------------------------------------------------
# Quality validation (diagnostic, non-blocking)
# ---------------------------------------------------------------------------

def validate_generation_quality(context, outputs, generation_type='create_post'):
    """10-point quality checklist. Logged, not blocking."""
    results = {}
    brand_name = context.get('brand_name', '')
    colors = context.get('colors', [])

    caption = outputs.get('caption', '') if isinstance(outputs, dict) else ''
    image_prompt = outputs.get('image_prompt', '') if isinstance(outputs, dict) else ''
    logo_available = context.get('logo_available', False)

    # 1. Reference preserved
    refs = context.get('existing_references', [])
    results['reference_preserved'] = 'pass' if not refs or any(
        (r.get('url') if isinstance(r, dict) else r) in image_prompt
        for r in refs
    ) else 'warn'

    # 2. Brand colors followed
    results['brand_colors_followed'] = 'pass' if not colors or any(
        c.lower() in image_prompt.lower() for c in colors[:3]
    ) else 'warn'

    # 3. Brand tone followed
    tone = context.get('tone', '')
    results['brand_tone_followed'] = 'pass' if not tone or tone.lower() in caption.lower() else 'info'

    # 4. Visual style followed
    style_name = (context.get('visual_style') or {}).get('name', '')
    results['visual_style_followed'] = 'pass' if not style_name or style_name.lower() in image_prompt.lower() else 'warn'

    # 5. Caption platform-specific
    results['caption_platform_specific'] = 'pass'  # validated at output time

    # 6. Caption not generic
    results['caption_not_generic'] = 'pass' if brand_name.lower() in caption.lower() or len(caption) > 30 else 'warn'

    # 7. CTA matches goal
    cta = context.get('campaign_cta', '')
    results['cta_matches_goal'] = 'pass' if not cta else 'info'

    # 8. User instruction followed
    instruction = context.get('user_instruction', '')
    results['user_instruction_followed'] = 'pass' if not instruction else 'info'

    # 9. Identity preserved in edit
    results['identity_preserved_in_edit'] = 'pass' if generation_type not in ('edit', 'regenerate') or refs else 'info'

    # 10. Regeneration coherent
    results['regeneration_coherent'] = 'pass' if generation_type != 'regenerate' or context.get('topic') else 'warn'

    logger.info(
        'quality_validation correlation_id=%s flow=%s results=%s',
        context.get('correlation_id', ''),
        generation_type,
        json.dumps(results),
        extra={'logo_available': logo_available},
    )
    return results


# ---------------------------------------------------------------------------
# Gemini response validation & sanitization
# ---------------------------------------------------------------------------

def validate_and_sanitize_json(raw_response, required_fields=None):
    """Validate and sanitize Gemini JSON output before saving.

    Returns (is_valid, cleaned_data).
    """
    if raw_response is None:
        return False, {}

    if isinstance(raw_response, str):
        # Try to extract JSON from markdown code blocks
        cleaned = re.sub(r'^```(?:json)?\s*', '', raw_response.strip())
        cleaned = re.sub(r'\s*```$', '', cleaned)
        try:
            raw_response = json.loads(cleaned)
        except (json.JSONDecodeError, ValueError):
            return False, {}

    if not isinstance(raw_response, dict):
        return False, {}

    # Sanitize values
    sanitized = {}
    for key, value in raw_response.items():
        if isinstance(value, str):
            # Fix invalid unicode
            value = value.encode('utf-8', errors='replace').decode('utf-8')
            # Remove markdown artifacts
            value = value.strip('`').strip()
        if isinstance(value, list):
            # Remove None/empty from arrays
            value = [v for v in value if v is not None and v != '']
            # Deduplicate hashtags
            if key in ('hashtags', 'tags'):
                value = list(dict.fromkeys(value))
        sanitized[key] = value

    # Check required fields
    if required_fields:
        missing = [f for f in required_fields if not sanitized.get(f)]
        if missing:
            return False, sanitized

    return True, sanitized


def validate_caption_output(caption_text):
    """Validate a caption string is not empty/garbage."""
    if not caption_text or not isinstance(caption_text, str):
        return False
    text = caption_text.strip()
    if len(text) < 5:
        return False
    # Check for common Gemini garbage
    if text.startswith('{') or text.startswith('['):
        return False
    if text.lower().startswith('here is') or text.lower().startswith('sure,'):
        # Strip Gemini meta-commentary
        lines = text.split('\n')
        if len(lines) > 1:
            return len(lines[1].strip()) > 5
        return False
    return True


def sanitize_caption(caption_text):
    """Clean up common Gemini caption issues."""
    if not caption_text:
        return ''
    text = str(caption_text).strip()
    # Remove markdown formatting
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)
    # Remove bullet points
    text = re.sub(r'^\s*[-•]\s+', '', text, flags=re.MULTILINE)
    # Remove Gemini meta-commentary prefix
    text = re.sub(r'^(?:Here(?:\'s| is) (?:a |the )?(?:caption|post).*?:\s*)', '', text, flags=re.IGNORECASE)
    # Clean excessive whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------

def validate_state_transition(current_status, new_status):
    """Returns True if transition is allowed."""
    allowed = ALLOWED_TRANSITIONS.get(current_status, set())
    return new_status in allowed


def safe_transition_job(job, new_status, error='', result=None):
    """Safely transition a job to a new state. Returns True if successful."""
    if not validate_state_transition(job.status, new_status):
        logger.error(
            'invalid_state_transition current=%s target=%s job=%s type=%s',
            job.status, new_status, job.id, getattr(job, 'job_type', ''),
        )
        return False

    job.status = new_status
    update_fields = ['status', 'updated_at']

    if error:
        job.error = error
        update_fields.append('error')

    if result is not None and hasattr(job, 'result'):
        job.result = result
        update_fields.append('result')

    job.save(update_fields=update_fields)
    return True


# ---------------------------------------------------------------------------
# Correlation IDs & Idempotency
# ---------------------------------------------------------------------------

def generate_correlation_id(flow, workspace=None):
    ws_id = str(getattr(workspace, 'id', ''))[:8]
    return f"{flow}:{ws_id}:{uuid.uuid4().hex[:8]}"


def generate_idempotency_key(user, workspace, flow, topic=''):
    """Deterministic key to prevent duplicate generation."""
    parts = [
        str(user.id),
        str(getattr(workspace, 'id', '')),
        flow,
        hashlib.md5(str(topic or '').encode()).hexdigest()[:8],
        datetime.now().strftime('%Y-%m-%d'),
    ]
    return ':'.join(parts)


# ---------------------------------------------------------------------------
# Observability helpers
# ---------------------------------------------------------------------------

def structured_log(logger_instance, event, **kwargs):
    """Emit a structured log entry with standard fields."""
    logger_instance.info(
        '%s %s',
        event,
        ' '.join(f'{k}={v}' for k, v in kwargs.items() if v is not None),
    )


def compact_json(data, max_length=1500):
    """Compact JSON serialization with length cap."""
    if not data:
        return '{}'
    try:
        text = json.dumps(data, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        text = str(data)
    if len(text) > max_length:
        return text[:max_length] + '...'
    return text
