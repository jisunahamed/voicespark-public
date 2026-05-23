from datetime import timedelta
from decimal import Decimal, InvalidOperation
import logging
import os
import re
import threading
from urllib.parse import urlparse

from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from utils.chatbot import gemini_error_payload

from workspace.models import Workspace
from auth_user.models import ScheduledPost, UserProfile
from nano_banana.models import NanoBananaImage

from .models import (
    AudienceProfile,
    BlogEmailPlan,
    BrandManualData,
    BrandSetting,
    BusinessProfile,
    CampaignWeek,
    ChannelVoiceConfig,
    CompetitorAnalysis,
    ContentPlan,
    GeneratedPost,
    GenerationJob,
    MediaAsset,
    SourceMatrixEntry,
    Topic,
    WorkspaceIntelligenceJob,
)
from .services.generation import generate_first_week
from .tasks import analyze_competitor_source, generate_campaign_plan_job, generate_content_job, run_workspace_intelligence_job
from .services.intelligence import (
    analyze_brand_from_crawl,
    analyze_competitor_url,
    brand_analysis_is_ready,
    clean_url,
    crawl_website,
    crawl_website_static,
    discover_competitors,
    fast_brand_analysis_from_crawl,
    personalized_channel_voice,
    store_extracted_images,
)
from .services.planner import (
    apply_campaign_timing,
    generate_blog_email_plan,
    generate_campaign_batch,
    generate_campaign_weeks,
    generate_style_previews,
    generate_weekly_topics,
    normalize_blog_email_plan,
    normalize_campaign_item_plan,
    regenerate_campaign_plan,
    regenerate_campaign_prompt,
)

logger = logging.getLogger(__name__)
from .services.website import analyse_website, normalize_url, render_profile_markdown

CAMPAIGN_JOB_TIMEOUT_MINUTES = int(os.getenv('CONTENT_ENGINE_CAMPAIGN_JOB_TIMEOUT_MINUTES', '15') or 15)
GENERATION_JOB_TIMEOUT_MINUTES = int(os.getenv('CONTENT_ENGINE_GENERATION_JOB_TIMEOUT_MINUTES', '30') or 30)
INTELLIGENCE_JOB_TIMEOUT_MINUTES = int(os.getenv('CONTENT_ENGINE_INTELLIGENCE_JOB_TIMEOUT_MINUTES', '20') or 20)


def minimal_website_analysis(website_url):
    domain = clean_url(website_url).replace('https://', '').replace('http://', '').split('/')[0].replace('www.', '')
    profile = {
        'name': domain or 'Business',
        'positioning': 'Website analysis could not fully load this site. The profile can be edited manually and enriched from Source Materials later.',
        'tone': 'clear, helpful, and confident',
        'services': ['Core product and service offering'],
        'audience': ['potential customers'],
        'keywords': [item for item in re.split(r'[^a-zA-Z0-9]+', domain) if item][:8],
        'domain': domain,
        'headings': [],
        'paragraphs': [],
        'proof_points': [],
        'competitors': {'local': [], 'national': []},
        'brand_personality': {'archetype': 'The Trusted Guide', 'voice': 'Clear and helpful', 'values': ['clarity', 'trust', 'service']},
    }
    return {
        'url': normalize_url(website_url),
        'tone': profile['tone'],
        'services': profile['services'],
        'audience': profile['audience'],
        'keywords': profile['keywords'],
        'profile': profile,
        'markdown': render_profile_markdown(profile),
        'source_snapshot': {'pages': [], 'images': []},
    }


def request_user(request):
    user_id = request.data.get('user_id') or request.query_params.get('user_id')
    if request.user and request.user.is_authenticated:
        return request.user
    return User.objects.filter(id=user_id).first()


def request_workspace(request):
    workspace_id = request.data.get('workspace_id') or request.query_params.get('workspace_id')
    if not workspace_id:
        return None
    user = request_user(request)
    if not user:
        return None
    return (
        Workspace.objects
        .filter(id=workspace_id)
        .filter(Q(owner=user) | Q(memberships__user=user))
        .distinct()
        .first()
    )


def validated_workspace(request):
    workspace_id = request.data.get('workspace_id') or request.query_params.get('workspace_id')
    if not workspace_id:
        return None
    user = request_user(request)
    return Workspace.objects.filter(id=workspace_id, owner=user).first() or Workspace.objects.filter(id=workspace_id, memberships__user=user).first()


def workspace_required_response():
    return Response({'error': 'workspace_id is required.'}, status=status.HTTP_400_BAD_REQUEST)


def find_business_profile(user, workspace=None):
    if not user:
        return None
    if workspace:
        return BusinessProfile.objects.filter(user=user, workspace=workspace).first()
    return None


def find_brand_setting(user, workspace=None, profile=None):
    if not user:
        return None
    brand = None
    if workspace:
        brand = BrandSetting.objects.filter(user=user, workspace=workspace).first()
    if not brand and profile:
        brand = BrandSetting.objects.create(
            user=user,
            workspace=workspace,
            business_profile=profile,
            tone=profile.tone,
            brand_context=profile.profile,
        )
    elif brand and profile and not brand.business_profile:
        brand.business_profile = profile
        if not brand.tone:
            brand.tone = profile.tone
        if not brand.brand_context:
            brand.brand_context = profile.profile
        brand.save(update_fields=['business_profile', 'tone', 'brand_context', 'updated_at'])
    return brand


def normalize_platforms(value):
    allowed = {'facebook', 'instagram', 'linkedin', 'x'}
    if isinstance(value, dict):
        platforms = [key for key, enabled in value.items() if enabled and key in allowed]
    elif isinstance(value, list):
        platforms = [item for item in value if item in allowed]
    else:
        platforms = []
    return platforms or ['facebook', 'instagram', 'linkedin', 'x']


def positive_int(value, default=1, minimum=1):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, parsed)


def nonnegative_int(value, default=0):
    return positive_int(value, default=default, minimum=0)


def find_or_create_draft_plan(user, workspace=None, request_data=None):
    if not user:
        return None
    plan = ContentPlan.objects.filter(user=user, workspace=workspace, status='draft').order_by('-updated_at').first()
    if plan:
        expected_profile = find_business_profile(user, workspace)
        expected_brand = find_brand_setting(user, workspace, expected_profile)
        update_fields = []
        if expected_profile and plan.business_profile_id != expected_profile.id:
            plan.business_profile = expected_profile
            update_fields.append('business_profile')
        if expected_brand and plan.brand_setting_id != expected_brand.id:
            plan.brand_setting = expected_brand
            update_fields.append('brand_setting')
        if update_fields:
            plan.save(update_fields=[*update_fields, 'updated_at'])
        return plan
    profile = find_business_profile(user, workspace)
    if not profile:
        return None
    brand = find_brand_setting(user, workspace, profile)
    return ContentPlan.objects.create(
        user=user,
        workspace=workspace,
        business_profile=profile,
        brand_setting=brand,
        platforms=normalize_platforms((request_data or {}).get('platforms')),
        posts_per_week=positive_int((request_data or {}).get('posts_per_week'), 5, 1),
        blog_posts_per_week=nonnegative_int((request_data or {}).get('blog_posts_per_week'), 0),
        emails_per_week=0,
        status='draft',
    )


def profile_payload(profile):
    return {
        'id': str(profile.id),
        'full_name': profile.full_name,
        'monthly_marketing_budget': str(profile.monthly_marketing_budget or ''),
        'business_category': profile.business_category,
        'website_url': profile.website_url,
        'tone': profile.tone,
        'services': profile.services,
        'audience': profile.audience,
        'keywords': profile.keywords,
        'profile': profile.profile,
        'markdown': profile.editable_markdown,
    }


def brand_payload(brand):
    return {
        'id': str(brand.id),
        'visual_style': brand.visual_style,
        'recommended_visual_style': brand.recommended_visual_style,
        'font': brand.font,
        'tone': brand.tone,
        'image_style': brand.image_style,
        'colors': brand.colors,
        'logos': brand.logos,
        'brand_context': brand.brand_context,
    }


def media_url_from_payload(item):
    if isinstance(item, dict):
        return item.get('image_url') or item.get('url') or ''
    return getattr(item, 'image_url', None) or getattr(item, 'url', None) or ''


def source_payload(entry):
    status_value = entry.status
    extracted = entry.extracted_data if isinstance(entry.extracted_data, dict) else {}
    if status_value == 'analyzing' and (extracted.get('brand_analysis') or extracted.get('image_count') or extracted.get('pages')):
        status_value = 'analyzed'
    return {
        'id': str(entry.id),
        'url': entry.url,
        'source_type': entry.source_type,
        'status': status_value,
        'last_analyzed_at': entry.last_analyzed_at.isoformat() if entry.last_analyzed_at else None,
        'extracted_data': entry.extracted_data,
        'error': entry.error,
    }


def competitor_payload(item):
    review_reason = competitor_review_reason({
        'name': item.name,
        'website_url': item.website_url,
    })
    return {
        'id': str(item.id),
        'name': item.name,
        'website_url': item.website_url,
        'needs_review': bool(review_reason),
        'review_reason': review_reason,
        'pricing_model': item.pricing_model,
        'key_features': item.key_features,
        'differentiators': item.differentiators,
        'swot': item.swot,
        'objection_handling': item.objection_handling,
        'raw_analysis': item.raw_analysis,
        'source_id': str(item.source_id) if item.source_id else None,
    }


def intelligence_job_payload(item):
    return {
        'id': str(item.id),
        'job_type': item.job_type,
        'status': item.status,
        'attempts': item.attempts,
        'error': item.error,
        'result': item.result or {},
        'updated_at': item.updated_at.isoformat() if item.updated_at else None,
    }


def audience_payload(item):
    return {
        'id': str(item.id),
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


def channel_voice_payload(item):
    return {
        'id': str(item.id),
        'platform': item.platform,
        'tone': item.tone,
        'emotion': item.emotion,
        'character': item.character,
        'syntax': item.syntax,
        'language': item.language,
    }


def manual_data_payload(item):
    return {
        'processes': item.processes,
        'methodology': item.methodology,
        'deliverables': item.deliverables,
        'pricing': item.pricing,
        'onboarding': item.onboarding,
    }


def clean_list(value):
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [line.strip() for line in value.splitlines() if line.strip()]
    return []


PLACEHOLDER_COMPETITOR_HOSTS = {
    'competitor.com',
    'example.com',
    'example.org',
    'example.net',
    'website.com',
    'yourcompetitor.com',
}


def validate_competitor_name(value):
    name = str(value or '').strip()
    if not name or name.lower() in {'competitor', 'website', 'unknown', 'n/a', 'none'}:
        return '', 'Competitor name is required.'
    return name[:255], ''


def validate_competitor_url(value):
    raw = str(value or '').strip()
    if not raw:
        return '', 'A valid competitor website URL is required.'
    if raw.lower() in {'website', 'url', 'competitor.com', 'https://competitor.com', 'http://competitor.com'}:
        return '', 'A real competitor website URL is required.'
    url = normalize_url(raw)
    parsed = urlparse(url)
    host = (parsed.netloc or '').lower().strip()
    clean_host = host[4:] if host.startswith('www.') else host
    if parsed.scheme not in {'http', 'https'} or not clean_host or '.' not in clean_host:
        return '', 'A valid competitor website URL is required.'
    if clean_host in PLACEHOLDER_COMPETITOR_HOSTS or clean_host.endswith('.invalid') or clean_host.endswith('.test'):
        return '', 'A real competitor website URL is required.'
    return url, ''


def competitor_review_reason(data):
    name, name_error = validate_competitor_name((data or {}).get('name'))
    if name_error:
        return name_error
    _, url_error = validate_competitor_url((data or {}).get('website_url') or (data or {}).get('url'))
    return url_error


def upsert_competitor(user, workspace, data, source=None):
    if not isinstance(data, dict):
        return None
    name, name_error = validate_competitor_name(data.get('name'))
    url, url_error = validate_competitor_url(data.get('website_url') or data.get('url'))
    if name_error or url_error:
        logger.info("Skipping invalid competitor: %s %s", name_error, url_error)
        return None
    clean_website_url = clean_url(url) if url else ''
    defaults = {
        'name': name,
        'pricing_model': str(data.get('pricing_model') or ''),
        'key_features': clean_list(data.get('key_features')),
        'differentiators': clean_list(data.get('differentiators')),
        'swot': data.get('swot') if isinstance(data.get('swot'), dict) else {'strengths': [], 'weaknesses': [], 'opportunities': [], 'threats': []},
        'objection_handling': data.get('objection_handling') if isinstance(data.get('objection_handling'), dict) else {'why_users_choose_them': [], 'counter_positioning': []},
        'raw_analysis': data,
        'source': source,
    }
    existing = None
    if clean_website_url:
        existing = (
            CompetitorAnalysis.objects
            .filter(user=user, workspace=workspace)
            .filter(website_url__icontains=clean_website_url.replace('https://', '').replace('http://', '').rstrip('/'))
            .first()
        )
    if not existing and defaults['name']:
        existing = CompetitorAnalysis.objects.filter(user=user, workspace=workspace, name__iexact=defaults['name']).first()
    if existing:
        for key, value in defaults.items():
            setattr(existing, key, value)
        if url:
            existing.website_url = url
        existing.save()
        competitor = existing
    elif url:
        competitor = CompetitorAnalysis.objects.create(user=user, workspace=workspace, website_url=url, **defaults)
    else:
        competitor = CompetitorAnalysis.objects.create(user=user, workspace=workspace, website_url='', **defaults)
    return competitor


def next_onboarding_route(user, workspace):
    profile = find_business_profile(user, workspace)
    if not profile:
        source = SourceMatrixEntry.objects.filter(user=user, workspace=workspace, source_type='my_website').order_by('-updated_at').first()
        return {
            'complete': False,
            'step': 'business_profile',
            'route': '/business-profile-builder',
            'website_url': source.url if source else '',
        }
    brand = find_brand_setting(user, workspace, profile)
    plan = ContentPlan.objects.filter(user=user, workspace=workspace, status='draft').order_by('-updated_at').first()
    if ScheduledPost.objects.filter(user=user, workspace=workspace).exists() or NanoBananaImage.objects.filter(user=user, workspace=workspace).exists():
        return {'complete': True, 'step': 'dashboard', 'route': '/home', 'website_url': profile.website_url}
    if plan:
        has_campaign = CampaignWeek.objects.filter(content_plan=plan).exists()
        has_topics = Topic.objects.filter(content_plan=plan).exists()
        has_generated = GeneratedPost.objects.filter(content_plan=plan).exists()
        has_scheduled = ScheduledPost.objects.filter(
            user=user,
            workspace=workspace,
            task_id__startswith=f'content_engine:{plan.id}:',
        ).exists()
        if has_campaign and (has_topics or has_generated or has_scheduled):
            return {'complete': True, 'step': 'dashboard', 'route': '/home', 'website_url': profile.website_url}
    if not brand or not brand.recommended_visual_style:
        if brand:
            user_profile = UserProfile.objects.filter(user=user, workspace=workspace).first()
            brand_voice = user_profile.brand_voice if user_profile and isinstance(user_profile.brand_voice, dict) else {}
            brand_style = brand_voice.get('brand_style') if isinstance(brand_voice.get('brand_style'), dict) else {}
            preferences = brand_voice.get('content_preferences') if isinstance(brand_voice.get('content_preferences'), dict) else {}
            visual_style = brand_style.get('visual_style') if isinstance(brand_style.get('visual_style'), dict) else {}
            content_style = preferences.get('content_style') if isinstance(preferences.get('content_style'), dict) else {}
            fallback_style = visual_style if visual_style.get('id') else content_style
            if isinstance(fallback_style, dict) and fallback_style.get('id'):
                brand.recommended_visual_style = fallback_style
                brand.save(update_fields=['recommended_visual_style', 'updated_at'])
                return next_onboarding_route(user, workspace)
        return {'complete': False, 'step': 'recommended_visual_style', 'route': '/recommended-visual-style', 'website_url': profile.website_url}
    if not brand.font:
        user_profile = UserProfile.objects.filter(user=user, workspace=workspace).first()
        brand_voice = user_profile.brand_voice if user_profile and isinstance(user_profile.brand_voice, dict) else {}
        brand_style = brand_voice.get('brand_style') if isinstance(brand_voice.get('brand_style'), dict) else {}
        fonts = brand_style.get('fonts') if isinstance(brand_style.get('fonts'), list) else []
        first_font = next((font for font in fonts if isinstance(font, dict) and font.get('family')), None)
        if first_font:
            brand.font = {
                'id': str(first_font.get('id') or first_font.get('family', '')).lower().replace(' ', '-'),
                'displayName': first_font.get('displayName') or first_font.get('family'),
                'family': first_font.get('family'),
                'weight': first_font.get('weight') or '700',
            }
            brand.save(update_fields=['font', 'updated_at'])
            return next_onboarding_route(user, workspace)
        return {'complete': False, 'step': 'brand_font', 'route': '/brand-font', 'website_url': profile.website_url}
    if not plan:
        return {'complete': False, 'step': 'content_plan', 'route': '/content-plan-register', 'website_url': profile.website_url}
    if not CampaignWeek.objects.filter(content_plan=plan).exists():
        return {'complete': False, 'step': 'campaign_planner', 'route': '/campaign-planner', 'website_url': profile.website_url}
    if not Topic.objects.filter(content_plan=plan).exists():
        return {'complete': False, 'step': 'review_topic', 'route': '/review-topic', 'website_url': profile.website_url}
    return {'complete': True, 'step': 'dashboard', 'route': '/home', 'website_url': profile.website_url}


def user_profile_for(user, workspace):
    profile, _ = UserProfile.objects.get_or_create(user=user, workspace=workspace)
    return profile


def sync_user_profile_from_business_profile(user, workspace, profile, brand=None, brand_analysis=None):
    if not user or not workspace or not profile:
        return None
    user_profile = user_profile_for(user, workspace)
    user_profile.website_url = profile.website_url or user_profile.website_url
    user_profile.markdown = profile.editable_markdown or user_profile.markdown
    brand_voice = user_profile.brand_voice if isinstance(user_profile.brand_voice, dict) else {}
    brand_voice['brand_profile'] = profile.profile or {}
    brand_voice['brand_profile_markdown'] = profile.editable_markdown or ''
    if isinstance(brand_analysis, dict):
        if brand_analysis.get('channel_voice'):
            brand_voice['channel_voice'] = brand_analysis.get('channel_voice')
        style = brand_voice.get('brand_style') if isinstance(brand_voice.get('brand_style'), dict) else {}
        analysis_style = brand_analysis.get('brand_style') if isinstance(brand_analysis.get('brand_style'), dict) else {}
        if analysis_style:
            style.update({key: value for key, value in analysis_style.items() if value})
        brand_voice['brand_style'] = style
    if brand:
        style = brand_voice.get('brand_style') if isinstance(brand_voice.get('brand_style'), dict) else {}
        if isinstance(brand.colors, list) and brand.colors:
            style['colors'] = brand.colors
        if isinstance(brand.logos, list) and brand.logos:
            style['logos'] = brand.logos
        if isinstance(brand.font, dict) and brand.font:
            family = brand.font.get('family') or brand.font.get('displayName')
            weight = brand.font.get('weight') or 'Bold'
            if family:
                style['fonts'] = [
                    {'role': 'title', 'family': str(family), 'weight': str(weight)},
                    {'role': 'body', 'family': str(family), 'weight': 'Regular'},
                ]
        if brand.image_style:
            style['visual_identity'] = brand.image_style
        brand_voice['brand_style'] = style
    user_profile.brand_voice = brand_voice
    user_profile.save(update_fields=['website_url', 'markdown', 'brand_voice'])
    return user_profile


def sync_brand_style_from_analysis(user, workspace, brand, brand_analysis):
    if not brand or not isinstance(brand_analysis, dict):
        return
    style = brand_analysis.get('brand_style') if isinstance(brand_analysis.get('brand_style'), dict) else {}
    colors = [str(item).strip() for item in style.get('colors', []) if str(item).strip()]
    logos = []
    for item in style.get('logos', []):
        url = item.get('url') if isinstance(item, dict) else item
        if str(url or '').strip():
            logos.append({'url': str(url).strip(), 'source': 'website'})
    if colors:
        brand.colors = list(dict.fromkeys([*(brand.colors or []), *colors]))[:12]
    if logos:
        existing = [item.get('url') for item in (brand.logos or []) if isinstance(item, dict)]
        brand.logos = [*(brand.logos or []), *[item for item in logos if item['url'] not in existing]][:12]
    if style.get('visual_identity'):
        brand.image_style = style.get('visual_identity')
    brand.save()

    user_profile = user_profile_for(user, workspace)
    brand_voice = user_profile.brand_voice if isinstance(user_profile.brand_voice, dict) else {}
    current_style = brand_voice.get('brand_style') if isinstance(brand_voice.get('brand_style'), dict) else {}
    current_style['colors'] = brand.colors or current_style.get('colors', [])
    current_style['logos'] = brand.logos or current_style.get('logos', [])
    if isinstance(brand.font, dict):
        family = brand.font.get('family') or brand.font.get('displayName')
        weight = brand.font.get('weight') or 'Bold'
        if family:
            current_style['fonts'] = [
                {'role': 'title', 'family': str(family), 'weight': str(weight)},
                {'role': 'body', 'family': str(family), 'weight': 'Regular'},
            ]
    if style.get('visual_identity'):
        current_style['visual_identity'] = style.get('visual_identity')
    brand_voice['brand_style'] = current_style
    user_profile.brand_voice = brand_voice
    user_profile.save(update_fields=['brand_voice'])


def sync_audiences_from_analysis(user, workspace, brand_analysis):
    if not isinstance(brand_analysis, dict):
        return
    raw = brand_analysis.get('audience_profiles')
    if not isinstance(raw, list) or not raw:
        audience = brand_analysis.get('audience') if isinstance(brand_analysis.get('audience'), list) else []
        services = brand_analysis.get('services') if isinstance(brand_analysis.get('services'), list) else []
        market = brand_analysis.get('market_positioning') or brand_analysis.get('business_type') or brand_analysis.get('industry') or 'the business'
        primary = audience[0] if audience else 'Potential customers'
        secondary = audience[1] if len(audience) > 1 else 'Decision makers'
        raw = [
            {
                'name': f'{primary} ICP',
                'age_range': '25-54',
                'location': 'Primary service market',
                'occupation': str(primary),
                'pain_points': [f'Needs a reliable solution for {services[0] if services else market}', 'Wants clear proof before choosing a vendor'],
                'frustrations': ['Too many generic offers', 'Unclear pricing or outcomes'],
                'goals': ['Find a trusted provider', 'Save time and reduce risk'],
                'behaviors': ['Researches online before contacting sales', 'Compares alternatives and proof points'],
                'buying_patterns': ['Responds to clear use cases, testimonials, and easy next steps'],
                'awareness_level': 'problem-aware',
            },
            {
                'name': f'{secondary} ICP',
                'age_range': '28-60',
                'location': 'Primary service market',
                'occupation': str(secondary),
                'pain_points': ['Needs confidence that the offer fits their exact business context', 'Needs fast implementation with low operational friction'],
                'frustrations': ['Generic marketing claims', 'No clear differentiation'],
                'goals': ['Choose a vendor that can deliver measurable value', 'Improve current workflow or customer experience'],
                'behaviors': ['Looks for demos, examples, pricing signals, and competitor comparisons'],
                'buying_patterns': ['Moves faster when messaging is specific to their industry and use case'],
                'awareness_level': 'solution-aware',
            },
        ]
    for index, item in enumerate(raw[:6]):
        if not isinstance(item, dict):
            continue
        name = re.sub(r'\s+', ' ', str(item.get('name') or f'ICP {index + 1}').strip())
        if len(name) > 120:
            name = name[:117].rstrip() + '...'
        defaults = {
            'age_range': str(item.get('age_range') or ''),
            'location': str(item.get('location') or ''),
            'occupation': str(item.get('occupation') or ''),
            'pain_points': item.get('pain_points') if isinstance(item.get('pain_points'), list) else [],
            'frustrations': item.get('frustrations') if isinstance(item.get('frustrations'), list) else [],
            'goals': item.get('goals') if isinstance(item.get('goals'), list) else [],
            'behaviors': item.get('behaviors') if isinstance(item.get('behaviors'), list) else [],
            'buying_patterns': item.get('buying_patterns') if isinstance(item.get('buying_patterns'), list) else [],
            'awareness_level': str(item.get('awareness_level') or ''),
        }
        AudienceProfile.objects.update_or_create(user=user, workspace=workspace, name=name, defaults=defaults)


def sync_channel_voice_from_analysis(user, workspace, brand_analysis):
    if not isinstance(brand_analysis, dict):
        return
    raw = brand_analysis.get('channel_voice') if isinstance(brand_analysis.get('channel_voice'), dict) else {}
    fallback = personalized_channel_voice(brand_analysis)
    for platform, defaults in fallback.items():
        values = raw.get(platform) if isinstance(raw.get(platform), dict) else {}
        merged = {key: str(values.get(key) or defaults[key]).strip() for key in ('tone', 'emotion', 'character', 'syntax', 'language')}
        if sum(len(merged[key]) for key in merged) < 120:
            merged = defaults
        voice, _ = ChannelVoiceConfig.objects.get_or_create(
            workspace=workspace,
            platform=platform,
            defaults={'user': user, **merged},
        )
        changed = False
        if voice.user_id != user.id:
            voice.user = user
            changed = True
        for key, value in merged.items():
            if getattr(voice, key) != value:
                setattr(voice, key, value)
                changed = True
        if changed:
            voice.save(update_fields=['user', 'tone', 'emotion', 'character', 'syntax', 'language', 'updated_at'])


def run_brand_intelligence_side_effects(user, workspace, profile, brand, crawl, brand_analysis):
    ready = brand_analysis_is_ready(brand_analysis)
    SourceMatrixEntry.objects.update_or_create(
        workspace=workspace,
        url=profile.website_url,
        source_type='my_website',
        defaults={
            'user': user,
            'status': 'analyzed' if ready else 'failed',
            'last_analyzed_at': timezone.now(),
            'extracted_data': {
                'brand_analysis': brand_analysis,
                'pages': [
                    {
                        'url': page.get('url'),
                        'type': page.get('type'),
                        'title': page.get('title'),
                        'source_quality': page.get('source_quality'),
                        'quality_reasons': page.get('quality_reasons', []),
                    }
                    for page in (crawl or {}).get('pages', [])
                ],
                'image_count': len((crawl or {}).get('images', [])),
            },
            'error': '' if ready else '; '.join((brand_analysis or {}).get('source_warnings') or ['source confidence validation failed']),
        },
    )
    stored_media = store_extracted_images(user, workspace, (crawl or {}).get('images', []))
    sync_brand_style_from_analysis(user, workspace, brand, brand_analysis or {})
    if ready and brand:
        brand.brand_context = brand_analysis or {}
        brand.save(update_fields=['brand_context', 'updated_at'])
    sync_audiences_from_analysis(user, workspace, brand_analysis or {})
    sync_channel_voice_from_analysis(user, workspace, brand_analysis or {})
    competitors = []
    if ready:
        for competitor in discover_competitors(brand_analysis or profile.profile or {})[:8]:
            saved = upsert_competitor(user, workspace, competitor)
            if saved:
                competitors.append(saved)
    return {'media_count': len(stored_media), 'competitor_count': len(competitors)}


def content_plan_payload(plan):
    return {
        'id': str(plan.id),
        'platforms': plan.platforms,
        'posts_per_week': plan.posts_per_week,
        'blog_posts_per_week': plan.blog_posts_per_week,
        'emails_per_week': plan.emails_per_week,
        'status': plan.status,
        'topics': [
            {
                'id': str(topic.id),
                'week_number': topic.week_number,
                'position': topic.position,
                'title': topic.title,
                'kind': topic.kind,
                'metadata': topic.metadata,
            }
            for topic in plan.topics.all()
        ],
    }


def connected_social_accounts(user, workspace):
    if not user or not workspace:
        return []
    connected = []
    try:
        from fb_auth.models import FacebookPage, InstagramToken
        from linkedin_auth.models import LinkedinToken
        from x_auth.models import Auth1Xtoken, XToken
        if FacebookPage.objects.filter(user=user, workspace=workspace).exists():
            connected.append('facebook')
        if InstagramToken.objects.filter(user=user, workspace=workspace).exists():
            connected.append('instagram')
        if LinkedinToken.objects.filter(user=user, workspace=workspace).exists():
            connected.append('linkedin')
        if XToken.objects.filter(user=user, workspace=workspace).exists() or Auth1Xtoken.objects.filter(user=user, workspace=workspace).exists():
            connected.append('x')
    except Exception:
        return []
    return connected


def hydrate_campaign_prompt_state(item_plan, week):
    prompts = item_plan.get('post_prompts') if isinstance(item_plan.get('post_prompts'), list) else []
    connected = connected_social_accounts(week.content_plan.user, week.content_plan.workspace)
    for prompt in prompts:
        if not isinstance(prompt, dict):
            continue
        content_type = str(prompt.get('type') or 'social').lower()
        if content_type == 'blog':
            prompt['accounts'] = 0
            prompt['connected_accounts'] = 0
            prompt['connected_platforms'] = []
        else:
            selected = prompt.get('platforms') if isinstance(prompt.get('platforms'), list) else week.content_plan.platforms
            connected_for_prompt = [platform for platform in connected if platform in selected]
            prompt['accounts'] = len(connected_for_prompt)
            prompt['connected_accounts'] = len(connected_for_prompt)
            prompt['connected_platforms'] = connected_for_prompt
        if week.status == 'generated':
            generated = GeneratedPost.objects.filter(
                content_plan=week.content_plan,
                topic__metadata__campaign_week_id=str(week.id),
                topic__title=prompt.get('topic') or '',
            ).order_by('-updated_at').first()
            prompt['status'] = generated.status if generated else 'generated'
        else:
            prompt['status'] = prompt.get('status') or week.status or 'draft'
    item_plan['post_prompts'] = prompts
    return item_plan


def campaign_week_payload(week):
    raw_item_plan = week.item_plan if isinstance(week.item_plan, dict) else {}
    generation_status = raw_item_plan.get('generation_status')
    if generation_status in ('queued', 'running', 'failed') and not (raw_item_plan.get('title') or week.theme):
        return {
            'id': str(week.id),
            'content_plan_id': str(week.content_plan_id),
            'week_number': week.week_number,
            'theme': week.theme,
            'funnel_goal': week.funnel_goal,
            'status': week.status,
            'item_plan': raw_item_plan,
            'generated_at': week.generated_at.isoformat() if week.generated_at else None,
        }
    item_plan = normalize_campaign_item_plan(
        {
            'theme': week.theme,
            'funnel_goal': week.funnel_goal,
            'item_plan': week.item_plan,
        },
        week.content_plan.business_profile,
        week.content_plan.brand_setting,
        week.content_plan,
        max(0, int(week.week_number or 1) - 1),
    )
    if item_plan != week.item_plan:
        week.item_plan = item_plan
        if week.theme != item_plan.get('title'):
            week.theme = item_plan.get('title', week.theme)
        week.save(update_fields=['theme', 'item_plan', 'updated_at'])
    item_plan = hydrate_campaign_prompt_state(item_plan, week)
    return {
        'id': str(week.id),
        'content_plan_id': str(week.content_plan_id),
        'week_number': week.week_number,
        'theme': week.theme,
        'funnel_goal': week.funnel_goal,
        'status': week.status,
        'item_plan': item_plan,
        'generated_at': week.generated_at.isoformat() if week.generated_at else None,
    }


def topics_from_campaign_prompts(plan, week_number=1):
    week = CampaignWeek.objects.filter(content_plan=plan, week_number=week_number).first()
    if not week:
        return []
    item_plan = normalize_campaign_item_plan(
        {'theme': week.theme, 'funnel_goal': week.funnel_goal, 'item_plan': week.item_plan},
        plan.business_profile,
        plan.brand_setting,
        plan,
        max(0, int(week_number or 1) - 1),
    )
    prompts = item_plan.get('post_prompts') if isinstance(item_plan.get('post_prompts'), list) else []
    result = []
    positions = {'social': 0, 'blog': 0}
    for prompt in prompts:
        if not isinstance(prompt, dict):
            continue
        kind = str(prompt.get('type') or 'social').strip().lower()
        if kind == 'email':
            continue
        if kind not in ('blog',):
            kind = 'social'
        positions[kind] += 1
        references = []
        if isinstance(prompt.get('reference_images'), list):
            references.extend(prompt.get('reference_images'))
        if isinstance(prompt.get('reference_media'), list):
            references.extend(prompt.get('reference_media'))
        if prompt.get('reference_image'):
            references.insert(0, prompt.get('reference_image'))
        references = list(dict.fromkeys([str(item).strip() for item in references if str(item or '').strip()]))
        result.append({
            'week_number': week_number,
            'position': positions[kind],
            'kind': kind,
            'title': prompt.get('topic') or prompt.get('title') or item_plan.get('title') or week.theme,
            'metadata': {
                'source': 'campaign_planner',
                'campaign_week_id': str(week.id),
                'campaign_title': item_plan.get('title') or week.theme,
                'campaign_type': item_plan.get('campaign_type', ''),
                'prompt': prompt,
                'reference_media': references,
                'theme': item_plan.get('theme', ''),
                'call_to_action': item_plan.get('call_to_action', ''),
                'audience': item_plan.get('audience', ''),
            },
        })
    return result


def parse_budget(value):
    if value in (None, ''):
        return None
    try:
        return Decimal(str(value).replace(',', ''))
    except (InvalidOperation, ValueError):
        digits = ''.join(ch for ch in str(value) if ch.isdigit() or ch == '.')
        if not digits:
            return None
        try:
            return Decimal(digits)
        except (InvalidOperation, ValueError):
            return None


class BusinessProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request_user(request)
        workspace = request_workspace(request)
        if not workspace:
            return workspace_required_response()
        if not user:
            return Response({'error': 'User not found.'}, status=status.HTTP_400_BAD_REQUEST)

        profile = find_business_profile(user, workspace)
        if not profile:
            return Response({'business_profile': None}, status=status.HTTP_200_OK)

        brand = find_brand_setting(user, workspace, profile)
        media_assets = MediaAsset.objects.filter(
            user=user,
            workspace=workspace,
            asset_type='image',
        ).order_by('-created_at')[:24]
        return Response({
            'business_profile': profile_payload(profile),
            'brand': brand_payload(brand) if brand else None,
            'brand_style': {
                'visual_identity': brand.image_style if brand else '',
                'colors': brand.colors if brand else [],
                'logos': brand.logos if brand else [],
                'fonts': (
                    [{'role': 'title', 'family': brand.font.get('family') or brand.font.get('displayName'), 'weight': brand.font.get('weight') or 'Bold'}]
                    if brand and isinstance(brand.font, dict) and brand.font else []
                ),
            },
            'images': [asset.url for asset in media_assets if asset.url],
        })

    def post(self, request):
        user = request_user(request)
        workspace = request_workspace(request)
        if not workspace:
            return workspace_required_response()
        if not user:
            return Response({'error': 'User not found.'}, status=status.HTTP_400_BAD_REQUEST)
        website_url = normalize_url(request.data.get('website_url') or request.data.get('link'))
        if not website_url:
            return Response({'error': 'website_url is required.'}, status=status.HTTP_400_BAD_REQUEST)

        existing_profile = BusinessProfile.objects.filter(user=user, workspace=workspace).first()
        try:
            try:
                crawl = crawl_website_static(website_url, max_pages=3)
            except Exception as static_exc:
                print('static website intelligence failed', type(static_exc).__name__, str(static_exc))
                crawl = {'root_url': website_url, 'pages': [], 'images': [], 'colors': []}
            brand_analysis = fast_brand_analysis_from_crawl(crawl)
            analysed = {
                'url': crawl['root_url'],
                'tone': brand_analysis.get('tone', 'clear, helpful, and confident'),
                'services': brand_analysis.get('services', []),
                'audience': brand_analysis.get('audience', []),
                'keywords': brand_analysis.get('keywords', []),
                'profile': {
                    **brand_analysis,
                    'domain': clean_url(crawl['root_url']).replace('https://', '').replace('http://', '').split('/')[0].replace('www.', ''),
                    'pages_analyzed': [{'url': page.get('url'), 'type': page.get('type'), 'title': page.get('title')} for page in crawl.get('pages', [])],
                    'intelligence_status': 'enriching',
                },
                'markdown': render_profile_markdown({
                    'name': brand_analysis.get('name'),
                    'positioning': brand_analysis.get('market_positioning'),
                    'tone': brand_analysis.get('tone'),
                    'services': brand_analysis.get('services', []),
                    'audience': brand_analysis.get('audience', []),
                    'keywords': brand_analysis.get('keywords', []),
                    'domain': clean_url(crawl['root_url']).replace('https://', '').replace('http://', '').split('/')[0].replace('www.', ''),
                    'proof_points': brand_analysis.get('product_structure', []),
                    'brand_personality': {'archetype': 'The Trusted Guide', 'voice': brand_analysis.get('tone', ''), 'values': brand_analysis.get('keywords', [])[:3]},
                }),
                'source_snapshot': crawl,
            }
        except Exception as exc:
            print('fast website intelligence failed', type(exc).__name__, str(exc))
            crawl = None
            brand_analysis = None
            try:
                analysed = analyse_website(website_url)
            except Exception as fallback_exc:
                print('basic website analysis failed', type(fallback_exc).__name__, str(fallback_exc))
                analysed = minimal_website_analysis(website_url)

        analysis_profile = analysed.get('profile') if isinstance(analysed.get('profile'), dict) else {}
        if (
            existing_profile
            and not brand_analysis_is_ready(analysis_profile)
            and brand_analysis_is_ready(existing_profile.profile)
        ):
            brand = find_brand_setting(user, workspace, existing_profile)
            return Response({
                'business_profile': profile_payload(existing_profile),
                'brand': brand_payload(brand) if brand else None,
                'images': [],
                'intelligence': {
                    'status': 'needs_review',
                    'warnings': analysis_profile.get('source_warnings') or ['new_analysis_failed_confidence_validation'],
                    'preserved_existing_profile': True,
                },
            })

        def apply_profile_fields(target):
            target.full_name = request.data.get('full_name', '')
            target.monthly_marketing_budget = parse_budget(request.data.get('monthly_marketing_budget'))
            target.business_category = request.data.get('business_category', '')
            target.website_url = analysed['url']
            target.tone = analysed['tone']
            target.services = analysed['services']
            target.audience = analysed['audience']
            target.keywords = analysed['keywords']
            target.profile = analysed['profile']
            target.editable_markdown = request.data.get('markdown') or analysed['markdown']
            target.source_snapshot = analysed['source_snapshot']

        profile = existing_profile
        if not profile:
            profile = BusinessProfile(user=user, workspace=workspace)
        apply_profile_fields(profile)
        try:
            profile.save()
        except IntegrityError:
            profile = BusinessProfile.objects.get(user=user, workspace=workspace)
            apply_profile_fields(profile)
            profile.save()

        brand = BrandSetting.objects.filter(user=user, workspace=workspace).first()
        if not brand:
            brand = BrandSetting(user=user, workspace=workspace)
        if not brand.business_profile:
            brand.business_profile = profile
        if not brand.tone:
            brand.tone = profile.tone
        if brand_analysis_is_ready(profile.profile):
            brand.brand_context = profile.profile
        elif not brand.brand_context:
            brand.brand_context = profile.profile
        try:
            brand.save()
        except IntegrityError:
            brand = BrandSetting.objects.get(user=user, workspace=workspace)
            if not brand.business_profile:
                brand.business_profile = profile
            if not brand.tone:
                brand.tone = profile.tone
            if not brand.brand_context:
                brand.brand_context = profile.profile
            brand.save()
        if crawl:
            stored_media = []
            sync_warnings = []
            try:
                SourceMatrixEntry.objects.update_or_create(
                    workspace=workspace,
                    url=profile.website_url,
                    source_type='my_website',
                    defaults={
                        'user': user,
                        'status': 'analyzed',
                        'last_analyzed_at': timezone.now(),
                        'extracted_data': {
                            'brand_analysis': brand_analysis or {},
                            'pages': [{'url': page.get('url'), 'type': page.get('type'), 'title': page.get('title')} for page in crawl.get('pages', [])],
                            'image_count': len(crawl.get('images', [])),
                        },
                        'error': '',
                    },
                )
            except Exception as exc:
                sync_warnings.append(f'source_matrix:{type(exc).__name__}')
                print('source matrix sync failed', type(exc).__name__, str(exc))
            try:
                stored_media = store_extracted_images(user, workspace, crawl.get('images', []))
            except Exception as exc:
                sync_warnings.append(f'media:{type(exc).__name__}')
                print('website media sync failed', type(exc).__name__, str(exc))
            for sync_name, sync_func in (
                ('brand_style', sync_brand_style_from_analysis),
                ('audiences', sync_audiences_from_analysis),
                ('channel_voice', sync_channel_voice_from_analysis),
            ):
                try:
                    if sync_name == 'brand_style':
                        sync_func(user, workspace, brand, brand_analysis or {})
                    else:
                        sync_func(user, workspace, brand_analysis or {})
                except Exception as exc:
                    sync_warnings.append(f'{sync_name}:{type(exc).__name__}')
                    print(f'{sync_name} sync failed', type(exc).__name__, str(exc))
            try:
                sync_user_profile_from_business_profile(user, workspace, profile, brand, brand_analysis or {})
            except Exception as exc:
                sync_warnings.append(f'user_profile:{type(exc).__name__}')
                print('user profile sync failed', type(exc).__name__, str(exc))
            counts = {
                'media_count': len(stored_media),
                'competitor_count': CompetitorAnalysis.objects.filter(user=user, workspace=workspace).count(),
                'status': 'enriching',
            }
            if sync_warnings:
                counts['warnings'] = sync_warnings
            def enqueue_intelligence():
                try:
                    queue_workspace_intelligence_job(user, workspace, profile, 'brand_enrichment')
                    if brand_analysis_is_ready(profile.profile):
                        queue_workspace_intelligence_job(user, workspace, profile, 'competitor_discovery')
                except Exception as exc:
                    logger.exception('background intelligence enqueue failed workspace=%s: %s', workspace.id, exc)
                    SourceMatrixEntry.objects.filter(
                        user=user,
                        workspace=workspace,
                        source_type='my_website',
                    ).update(status='failed', error=str(exc), updated_at=timezone.now())
            transaction.on_commit(enqueue_intelligence)
        else:
            fallback_analysis = analysed.get('profile', {}) if isinstance(analysed.get('profile'), dict) else analysed
            try:
                sync_audiences_from_analysis(user, workspace, fallback_analysis)
            except Exception as exc:
                print('audiences sync failed', type(exc).__name__, str(exc))
            try:
                sync_channel_voice_from_analysis(user, workspace, fallback_analysis)
            except Exception as exc:
                print('channel voice sync failed', type(exc).__name__, str(exc))
            try:
                sync_user_profile_from_business_profile(user, workspace, profile, brand, fallback_analysis)
            except Exception as exc:
                print('user profile sync failed', type(exc).__name__, str(exc))
            counts = {'media_count': 0, 'competitor_count': 0}
        return Response({
            'business_profile': profile_payload(profile),
            'brand': brand_payload(brand) if brand else None,
            'brand_style': {
                'visual_identity': brand.image_style if brand else '',
                'colors': brand.colors if brand else [],
                'logos': brand.logos if brand else [],
                'fonts': (
                    [{'role': 'title', 'family': brand.font.get('family') or brand.font.get('displayName'), 'weight': brand.font.get('weight') or 'Bold'}]
                    if brand and isinstance(brand.font, dict) and brand.font else []
                ),
            },
            'images': [url for url in (media_url_from_payload(item) for item in stored_media) if url] if 'stored_media' in locals() else [],
            'intelligence': counts,
        })

    def patch(self, request):
        user = request_user(request)
        workspace = request_workspace(request)
        if not workspace:
            return workspace_required_response()
        if not user:
            return Response({'error': 'User not found.'}, status=status.HTTP_400_BAD_REQUEST)
        data = request.data
        profile = find_business_profile(user, workspace)
        if not profile:
            website_url = normalize_url(data.get('website_url') or data.get('link'))
            if not website_url:
                return Response(
                    {'error': 'Business profile not found and website_url is required to create it.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            profile = BusinessProfile.objects.create(
                user=user,
                workspace=workspace,
                website_url=website_url,
                full_name=data.get('full_name', ''),
                monthly_marketing_budget=parse_budget(data.get('monthly_marketing_budget')),
                business_category=data.get('business_category', ''),
                tone=data.get('tone', ''),
                editable_markdown=data.get('markdown', ''),
            )
        if 'markdown' in data:
            profile.editable_markdown = data['markdown']
        for field in ['full_name', 'business_category', 'tone']:
            if field in data:
                setattr(profile, field, data[field])
        if 'monthly_marketing_budget' in data:
            profile.monthly_marketing_budget = parse_budget(data.get('monthly_marketing_budget'))
        if data.get('website_url') or data.get('link'):
            profile.website_url = normalize_url(data.get('website_url') or data.get('link')) or profile.website_url
        if 'profile' in data and isinstance(data['profile'], dict):
            profile.profile = data['profile']
            profile.editable_markdown = render_profile_markdown(data['profile'])
        profile.save()

        brand = BrandSetting.objects.filter(user=user, workspace=workspace).first()
        if not brand:
            brand = BrandSetting(user=user, workspace=workspace, business_profile=profile)
        elif not brand.business_profile:
            brand.business_profile = profile
        brand_style = data.get('brand_style') if isinstance(data.get('brand_style'), dict) else {}
        if brand_style:
            if brand_style.get('colors') is not None:
                brand.colors = brand_style.get('colors') or []
            if brand_style.get('logos') is not None:
                brand.logos = brand_style.get('logos') or []
            if brand_style.get('visual_identity') is not None:
                brand.image_style = brand_style.get('visual_identity') or brand.image_style
            if brand_style.get('fonts') is not None:
                fonts = brand_style.get('fonts') or []
                if isinstance(fonts, list):
                    title_font = next((font for font in fonts if isinstance(font, dict) and font.get('role') == 'title'), None)
                    title_font = title_font or next((font for font in fonts if isinstance(font, dict)), None)
                    if title_font:
                        brand.font = {
                            'family': title_font.get('family') or title_font.get('displayName') or 'Inter',
                            'displayName': title_font.get('family') or title_font.get('displayName') or 'Inter',
                            'weight': title_font.get('weight') or 'Bold',
                        }
                elif isinstance(fonts, dict):
                    brand.font = fonts
            if brand_style.get('visual_identity') and not brand.tone:
                brand.tone = brand_style.get('visual_identity')
        if profile.tone and not brand.tone:
            brand.tone = profile.tone
        if profile.profile and not brand.brand_context:
            brand.brand_context = profile.profile
        brand.save()
        try:
            sync_user_profile_from_business_profile(user, workspace, profile, brand, profile.profile if isinstance(profile.profile, dict) else {})
        except Exception as exc:
            print('user profile sync failed', type(exc).__name__, str(exc))
        return Response({'business_profile': profile_payload(profile)})


class BrandSettingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request_user(request)
        workspace = request_workspace(request)
        if not workspace:
            return workspace_required_response()
        brand = BrandSetting.objects.filter(user=user, workspace=workspace).first()
        return Response({'brand': brand_payload(brand) if brand else None})

    def post(self, request):
        user = request_user(request)
        workspace = request_workspace(request)
        if not workspace:
            return workspace_required_response()
        profile = BusinessProfile.objects.filter(user=user, workspace=workspace).first()
        brand, _ = BrandSetting.objects.get_or_create(user=user, workspace=workspace, defaults={'business_profile': profile})
        for field in ['visual_style', 'recommended_visual_style', 'font', 'tone', 'image_style', 'colors', 'logos', 'brand_context']:
            if field in request.data:
                setattr(brand, field, request.data[field])
        if isinstance(brand.recommended_visual_style, dict) and brand.recommended_visual_style:
            from auth_user.views import normalize_visual_style
            brand.recommended_visual_style = normalize_visual_style(brand.recommended_visual_style)
        if profile and not brand.business_profile:
            brand.business_profile = profile
        brand.save()
        try:
            user_profile = user_profile_for(user, workspace)
            brand_voice = user_profile.brand_voice if isinstance(user_profile.brand_voice, dict) else {}
            style = brand_voice.get('brand_style') if isinstance(brand_voice.get('brand_style'), dict) else {}
            if isinstance(brand.font, dict) and brand.font:
                family = brand.font.get('family') or brand.font.get('displayName')
                weight = brand.font.get('weight') or 'Bold'
                if family:
                    style['fonts'] = [
                        {'role': 'title', 'family': str(family), 'weight': str(weight)},
                        {'role': 'body', 'family': str(family), 'weight': 'Regular'},
                    ]
            if isinstance(brand.logos, list) and brand.logos:
                style['logos'] = brand.logos
            if isinstance(brand.colors, list) and brand.colors:
                style['colors'] = brand.colors
            if isinstance(brand.recommended_visual_style, dict) and brand.recommended_visual_style:
                from auth_user.views import normalize_visual_style
                style['visual_style'] = normalize_visual_style(brand.recommended_visual_style)
                preferences = brand_voice.get('content_preferences') if isinstance(brand_voice.get('content_preferences'), dict) else {}
                preferences['content_style'] = style['visual_style']
                brand_voice['content_preferences'] = preferences
            if brand.image_style:
                style['visual_identity'] = brand.image_style
            brand_voice['brand_style'] = style
            user_profile.brand_voice = brand_voice
            user_profile.save(update_fields=['brand_voice'])
        except Exception:
            pass
        return Response({'brand': brand_payload(brand)})


class OnboardingStateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request_user(request)
        workspace = request_workspace(request)
        if not workspace:
            return workspace_required_response()
        state = next_onboarding_route(user, workspace)
        return Response({'onboarding': state})

    def post(self, request):
        user = request_user(request)
        workspace = request_workspace(request)
        if not workspace:
            return workspace_required_response()
        website_url = normalize_url(request.data.get('website_url') or request.data.get('link'))
        if website_url:
            SourceMatrixEntry.objects.update_or_create(
                workspace=workspace,
                url=clean_url(website_url),
                source_type='my_website',
                defaults={'user': user, 'status': 'pending', 'error': ''},
            )
        state = next_onboarding_route(user, workspace)
        if website_url and not state.get('website_url'):
            state['website_url'] = website_url
        return Response({'onboarding': state})


class SourceMatrixView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request_user(request)
        workspace = request_workspace(request)
        if not workspace:
            return workspace_required_response()
        entries = SourceMatrixEntry.objects.filter(user=user, workspace=workspace).order_by('-updated_at')
        return Response({'sources': [source_payload(entry) for entry in entries]})

    def post(self, request):
        user = request_user(request)
        workspace = request_workspace(request)
        if not workspace:
            return workspace_required_response()
        url = normalize_url(request.data.get('url'))
        source_type = request.data.get('source_type')
        if source_type not in ('my_website', 'competitor'):
            return Response({'error': 'source_type must be my_website or competitor.'}, status=status.HTTP_400_BAD_REQUEST)
        if not url:
            return Response({'error': 'url is required.'}, status=status.HTTP_400_BAD_REQUEST)
        entry, created = SourceMatrixEntry.objects.update_or_create(
            workspace=workspace,
            url=clean_url(url),
            source_type=source_type,
            defaults={'user': user, 'status': 'pending', 'error': ''},
        )
        if entry.user_id != user.id:
            entry.user = user
            entry.save(update_fields=['user', 'updated_at'])
        return Response({'source': source_payload(entry), 'duplicate': not created}, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class SourceMatrixAnalyzeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request_user(request)
        workspace = request_workspace(request)
        if not workspace:
            return workspace_required_response()
        url = normalize_url(request.data.get('url'))
        source_type = request.data.get('source_type')
        if source_type not in ('my_website', 'competitor'):
            return Response({'error': 'source_type must be my_website or competitor.'}, status=status.HTTP_400_BAD_REQUEST)
        if not url:
            return Response({'error': 'url is required.'}, status=status.HTTP_400_BAD_REQUEST)
        existing = SourceMatrixEntry.objects.filter(workspace=workspace, url=clean_url(url), source_type=source_type).first()
        if existing and existing.status == 'analyzed' and existing.extracted_data and not request.data.get('force'):
            response = {'source': source_payload(existing), 'duplicate': True}
            if source_type == 'competitor':
                competitor = CompetitorAnalysis.objects.filter(user=user, workspace=workspace, source=existing).first()
                if not competitor:
                    competitor = CompetitorAnalysis.objects.filter(user=user, workspace=workspace, website_url__icontains=clean_url(url).replace('https://', '').replace('http://', '').rstrip('/')).first()
                if competitor:
                    response['competitor'] = competitor_payload(competitor)
            return Response(response, status=status.HTTP_200_OK)

        entry, _ = SourceMatrixEntry.objects.update_or_create(
            workspace=workspace,
            url=clean_url(url),
            source_type=source_type,
            defaults={'user': user, 'status': 'analyzing', 'error': ''},
        )
        if entry.user_id != user.id:
            entry.user = user
            entry.save(update_fields=['user', 'updated_at'])
        try:
            if source_type == 'competitor':
                competitor_data, crawl = analyze_competitor_url(url)
                entry.status = 'analyzed'
                entry.last_analyzed_at = timezone.now()
                entry.extracted_data = {'crawl': crawl, 'competitor': competitor_data}
                entry.error = ''
                entry.save(update_fields=['status', 'last_analyzed_at', 'extracted_data', 'error', 'updated_at'])
                competitor = upsert_competitor(user, workspace, competitor_data, source=entry)
                if not competitor:
                    return Response({'source': source_payload(entry), 'error': 'Competitor analysis did not include a real name and website URL.'}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
                return Response({'source': source_payload(entry), 'competitor': competitor_payload(competitor)})
            crawl = crawl_website(url)
            brand_analysis = analyze_brand_from_crawl(crawl)
            ready = brand_analysis_is_ready(brand_analysis)
            entry.status = 'analyzed' if ready else 'failed'
            entry.last_analyzed_at = timezone.now()
            entry.extracted_data = {'brand_analysis': brand_analysis, 'crawl': crawl}
            entry.error = '' if ready else '; '.join(brand_analysis.get('source_warnings') or ['source confidence validation failed'])
            entry.save(update_fields=['status', 'last_analyzed_at', 'extracted_data', 'error', 'updated_at'])
            if not ready:
                return Response(
                    {
                        'source': source_payload(entry),
                        'error': 'Website analysis needs manual review because source confidence validation failed.',
                        'warnings': brand_analysis.get('source_warnings') or [],
                    },
                    status=status.HTTP_422_UNPROCESSABLE_ENTITY,
                )
            profile = find_business_profile(user, workspace)
            if profile:
                profile.source_snapshot = crawl
                profile.profile = {**(profile.profile if isinstance(profile.profile, dict) else {}), **brand_analysis}
                profile.services = brand_analysis.get('services', profile.services)
                profile.audience = brand_analysis.get('audience', profile.audience)
                profile.keywords = brand_analysis.get('keywords', profile.keywords)
                profile.tone = brand_analysis.get('tone', profile.tone)
                profile.save(update_fields=['source_snapshot', 'profile', 'services', 'audience', 'keywords', 'tone', 'updated_at'])
                brand = find_brand_setting(user, workspace, profile)
                counts = run_brand_intelligence_side_effects(user, workspace, profile, brand, crawl, brand_analysis)
                stored_media = []
            else:
                stored_media = store_extracted_images(user, workspace, crawl.get('images', []))
                sync_audiences_from_analysis(user, workspace, brand_analysis)
                sync_channel_voice_from_analysis(user, workspace, brand_analysis)
                competitors = [
                    item for item in (
                        upsert_competitor(user, workspace, competitor)
                        for competitor in discover_competitors(brand_analysis)[:8]
                    ) if item
                ]
                counts = {'media_count': len(stored_media), 'competitor_count': len(competitors)}
            return Response({'source': source_payload(entry), 'media': stored_media, 'intelligence': counts})
        except Exception as exc:
            entry.status = 'failed'
            entry.error = str(exc)
            entry.save(update_fields=['status', 'error', 'updated_at'])
            return Response({'source': source_payload(entry), 'error': str(exc)}, status=status.HTTP_502_BAD_GATEWAY)


class CompetitorsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request_user(request)
        workspace = request_workspace(request)
        if not workspace:
            return workspace_required_response()
        mark_stale_intelligence_jobs(user=user, workspace=workspace)
        items = CompetitorAnalysis.objects.filter(user=user, workspace=workspace).order_by('name')
        confirmed = []
        needs_review = []
        for item in items:
            payload = competitor_payload(item)
            if payload.get('needs_review'):
                needs_review.append(payload)
            else:
                confirmed.append(payload)
        jobs = WorkspaceIntelligenceJob.objects.filter(
            user=user,
            workspace=workspace,
        ).order_by('-updated_at')[:8]
        return Response({
            'competitors': confirmed,
            'needs_review': needs_review,
            'intelligence_jobs': [intelligence_job_payload(item) for item in jobs],
        })

    def post(self, request):
        user = request_user(request)
        workspace = request_workspace(request)
        if not workspace:
            return workspace_required_response()
        url, url_error = validate_competitor_url(request.data.get('website_url') or request.data.get('url'))
        if url_error:
            return Response({'error': url_error}, status=status.HTTP_400_BAD_REQUEST)
        if url:
            existing = (
                CompetitorAnalysis.objects
                .filter(user=user, workspace=workspace)
                .filter(website_url__icontains=clean_url(url).replace('https://', '').replace('http://', '').rstrip('/'))
                .first()
            )
            if existing and not request.data.get('force'):
                return Response({'competitor': competitor_payload(existing), 'duplicate': True}, status=status.HTTP_200_OK)
            source, _ = SourceMatrixEntry.objects.update_or_create(
                workspace=workspace,
                url=clean_url(url),
                source_type='competitor',
                defaults={'user': user, 'status': 'analyzing', 'error': ''},
            )
            if source.user_id != user.id:
                source.user = user
                source.save(update_fields=['user', 'updated_at'])
            try:
                analyze_competitor_source.delay(str(source.id))
            except Exception:
                worker = threading.Thread(target=analyze_competitor_source.run, args=(str(source.id),), daemon=True)
                worker.start()
        return Response(
            {
                'source': source_payload(source),
                'competitor': None,
                'status': 'analyzing',
                'message': 'Competitor analysis started.',
            },
            status=status.HTTP_202_ACCEPTED,
        )


class CompetitorDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, competitor_id):
        user = request_user(request)
        workspace = request_workspace(request)
        if not workspace:
            return workspace_required_response()
        item = CompetitorAnalysis.objects.filter(id=competitor_id, user=user, workspace=workspace).first()
        if not item:
            return Response({'error': 'Competitor not found.'}, status=status.HTTP_404_NOT_FOUND)
        next_name = request.data.get('name', item.name)
        next_url = request.data.get('website_url', item.website_url)
        _, name_error = validate_competitor_name(next_name)
        normalized_url, url_error = validate_competitor_url(next_url)
        if name_error or url_error:
            return Response({'error': name_error or url_error}, status=status.HTTP_400_BAD_REQUEST)
        for field in ['name', 'website_url', 'pricing_model', 'key_features', 'differentiators', 'swot', 'objection_handling']:
            if field in request.data:
                setattr(item, field, request.data[field])
        item.name = str(next_name).strip()[:255]
        item.website_url = normalized_url
        item.save()
        return Response({'competitor': competitor_payload(item)})

    def delete(self, request, competitor_id):
        user = request_user(request)
        workspace = request_workspace(request)
        if not workspace:
            return workspace_required_response()
        item = CompetitorAnalysis.objects.filter(id=competitor_id, user=user, workspace=workspace).first()
        if not item:
            return Response({'error': 'Competitor not found.'}, status=status.HTTP_404_NOT_FOUND)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CompetitorReanalyzeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, competitor_id):
        user = request_user(request)
        workspace = request_workspace(request)
        if not workspace:
            return workspace_required_response()
        item = CompetitorAnalysis.objects.filter(id=competitor_id, user=user, workspace=workspace).first()
        if not item or not item.website_url:
            return Response({'error': 'Competitor with website_url was not found.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            data, crawl = analyze_competitor_url(item.website_url)
        except Exception as exc:
            logger.exception("Competitor re-analysis failed for %s: %s", item.website_url, exc)
            if item.source:
                item.source.status = 'failed'
                item.source.error = str(exc)
                item.source.save(update_fields=['status', 'error', 'updated_at'])
            return Response(
                {'competitor': competitor_payload(item), 'error': 'Competitor re-analysis failed.', 'detail': str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        source = item.source
        if source:
            source.status = 'analyzed'
            source.last_analyzed_at = timezone.now()
            source.extracted_data = {'crawl': crawl, 'competitor': data}
            source.error = ''
            source.save(update_fields=['status', 'last_analyzed_at', 'extracted_data', 'error', 'updated_at'])
        updated = upsert_competitor(user, workspace, data, source=source)
        if not updated:
            return Response({'competitor': competitor_payload(item), 'error': 'Competitor analysis did not include a real name and website URL.'}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        return Response({'competitor': competitor_payload(updated)})


class ChannelVoiceView(APIView):
    permission_classes = [IsAuthenticated]
    platforms = ['facebook', 'instagram', 'linkedin', 'x']

    def get(self, request):
        user = request_user(request)
        workspace = request_workspace(request)
        if not workspace:
            return workspace_required_response()
        profile = find_business_profile(user, workspace)
        brand = find_brand_setting(user, workspace, profile)
        analysis = {}
        if profile and isinstance(profile.profile, dict):
            analysis.update(profile.profile)
        if profile and profile.editable_markdown:
            analysis.setdefault('market_positioning', profile.editable_markdown[:700])
        if brand:
            analysis.setdefault('tone', brand.tone or '')
            analysis.setdefault('brand_style', {'visual_identity': brand.image_style or ''})
        fallback = personalized_channel_voice(analysis)
        for platform in self.platforms:
            voice, created = ChannelVoiceConfig.objects.get_or_create(
                workspace=workspace,
                platform=platform,
                defaults={'user': user, **fallback.get(platform, {})},
            )
            if not created and voice.user_id != user.id:
                voice.user = user
                voice.save(update_fields=['user', 'updated_at'])
        items = ChannelVoiceConfig.objects.filter(workspace=workspace).order_by('platform')
        return Response({'channels': [channel_voice_payload(item) for item in items]})

    def patch(self, request):
        user = request_user(request)
        workspace = request_workspace(request)
        if not workspace:
            return workspace_required_response()
        platform = str(request.data.get('platform') or '').lower()
        if not platform:
            return Response({'error': 'platform is required.'}, status=status.HTTP_400_BAD_REQUEST)
        item, _ = ChannelVoiceConfig.objects.get_or_create(user=user, workspace=workspace, platform=platform)
        for field in ['tone', 'emotion', 'character', 'syntax', 'language']:
            if field in request.data:
                setattr(item, field, request.data[field])
        item.save()
        return Response({'channel': channel_voice_payload(item)})


class AudienceProfilesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request_user(request)
        workspace = request_workspace(request)
        if not workspace:
            return workspace_required_response()
        items = AudienceProfile.objects.filter(user=user, workspace=workspace).order_by('created_at')
        return Response({'audiences': [audience_payload(item) for item in items]})

    def post(self, request):
        user = request_user(request)
        workspace = request_workspace(request)
        if not workspace:
            return workspace_required_response()
        item = AudienceProfile.objects.create(
            user=user,
            workspace=workspace,
            name=request.data.get('name') or 'New ICP',
            age_range=request.data.get('age_range', ''),
            location=request.data.get('location', ''),
            occupation=request.data.get('occupation', ''),
            pain_points=clean_list(request.data.get('pain_points')),
            frustrations=clean_list(request.data.get('frustrations')),
            goals=clean_list(request.data.get('goals')),
            behaviors=clean_list(request.data.get('behaviors')),
            buying_patterns=clean_list(request.data.get('buying_patterns')),
            awareness_level=request.data.get('awareness_level', ''),
        )
        return Response({'audience': audience_payload(item)}, status=status.HTTP_201_CREATED)


class AudienceProfileDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, audience_id):
        user = request_user(request)
        workspace = request_workspace(request)
        if not workspace:
            return workspace_required_response()
        item = AudienceProfile.objects.filter(id=audience_id, user=user, workspace=workspace).first()
        if not item:
            return Response({'error': 'Audience profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        for field in ['name', 'age_range', 'location', 'occupation', 'awareness_level']:
            if field in request.data:
                setattr(item, field, request.data[field])
        for field in ['pain_points', 'frustrations', 'goals', 'behaviors', 'buying_patterns']:
            if field in request.data:
                setattr(item, field, clean_list(request.data[field]))
        item.save()
        return Response({'audience': audience_payload(item)})

    def delete(self, request, audience_id):
        user = request_user(request)
        workspace = request_workspace(request)
        if not workspace:
            return workspace_required_response()
        item = AudienceProfile.objects.filter(id=audience_id, user=user, workspace=workspace).first()
        if not item:
            return Response({'error': 'Audience profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ManualDataView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request_user(request)
        workspace = request_workspace(request)
        if not workspace:
            return workspace_required_response()
        item, _ = BrandManualData.objects.get_or_create(user=user, workspace=workspace)
        return Response({'manual_data': manual_data_payload(item)})

    def patch(self, request):
        user = request_user(request)
        workspace = request_workspace(request)
        if not workspace:
            return workspace_required_response()
        item, _ = BrandManualData.objects.get_or_create(user=user, workspace=workspace)
        for field in ['processes', 'methodology', 'deliverables', 'pricing', 'onboarding']:
            if field in request.data:
                setattr(item, field, str(request.data[field] or ''))
        item.save()
        return Response({'manual_data': manual_data_payload(item)})


class RecommendedVisualStylesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request_user(request)
        workspace = request_workspace(request)
        if not workspace:
            return workspace_required_response()
        profile = BusinessProfile.objects.filter(user=user, workspace=workspace).first()
        visual_style = request.query_params.get('visual_style', '')
        return Response({'styles': generate_style_previews(profile, visual_style)})


class ContentPlanView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request_user(request)
        workspace = request_workspace(request)
        if not workspace:
            return workspace_required_response()
        plan = find_or_create_draft_plan(user, workspace, request.query_params)
        if not plan:
            return Response({'content_plan': None})
        return Response({'content_plan': content_plan_payload(plan)})

    def post(self, request):
        user = request_user(request)
        workspace = request_workspace(request)
        if not workspace:
            return workspace_required_response()
        profile = find_business_profile(user, workspace)
        brand = find_brand_setting(user, workspace, profile)
        platforms = normalize_platforms(request.data.get('platforms'))
        plan, _ = ContentPlan.objects.update_or_create(
            user=user,
            workspace=workspace,
            status='draft',
            defaults={
                'business_profile': profile,
                'brand_setting': brand,
                'platforms': platforms,
                'posts_per_week': positive_int(request.data.get('posts_per_week'), 5, 1),
                'blog_posts_per_week': nonnegative_int(request.data.get('blog_posts_per_week'), 0),
                'emails_per_week': 0,
            },
        )
        return Response({'content_plan': content_plan_payload(plan)})


def use_celery_workers():
    return os.getenv('CONTENT_ENGINE_USE_CELERY', 'false').strip().lower() in ('1', 'true', 'yes', 'on')


def start_campaign_plan_job(plan):
    if use_celery_workers():
        try:
            generate_campaign_plan_job.delay(str(plan.id))
            return
        except Exception as exc:
            print('campaign plan celery enqueue failed', type(exc).__name__, str(exc))
    worker = threading.Thread(target=generate_campaign_plan_job.run, args=(str(plan.id),), daemon=True)
    worker.start()


def mark_stale_campaign_weeks(plan):
    cutoff = timezone.now() - timedelta(minutes=CAMPAIGN_JOB_TIMEOUT_MINUTES)
    stale = []
    for week in plan.campaign_weeks.filter(updated_at__lt=cutoff).order_by('week_number')[:4]:
        item_plan = week.item_plan if isinstance(week.item_plan, dict) else {}
        if item_plan.get('generation_status') not in ('queued', 'running'):
            continue
        item_plan['generation_status'] = 'failed'
        item_plan['generation_error'] = f'Campaign generation timed out after {CAMPAIGN_JOB_TIMEOUT_MINUTES} minutes. Please retry.'
        item_plan['error_type'] = 'timeout'
        item_plan['retryable'] = True
        week.item_plan = item_plan
        week.save(update_fields=['item_plan', 'updated_at'])
        stale.append(str(week.id))
    if stale:
        logger.warning("Marked stale campaign generation weeks failed plan=%s weeks=%s", plan.id, stale)


def mark_stale_generation_jobs(plan=None, user=None, workspace=None):
    cutoff = timezone.now() - timedelta(minutes=GENERATION_JOB_TIMEOUT_MINUTES)
    qs = GenerationJob.objects.filter(status__in=['queued', 'running'], updated_at__lt=cutoff)
    if plan:
        qs = qs.filter(content_plan=plan)
    if user:
        qs = qs.filter(user=user)
    if workspace:
        qs = qs.filter(workspace=workspace)
    count = qs.update(
        status='failed',
        error=f'Content generation timed out after {GENERATION_JOB_TIMEOUT_MINUTES} minutes. Please retry.',
        updated_at=timezone.now(),
    )
    if count:
        logger.warning("Marked stale content generation jobs failed count=%s plan=%s workspace=%s", count, getattr(plan, 'id', None), getattr(workspace, 'id', None))


def read_campaign_weeks(plan):
    mark_stale_campaign_weeks(plan)
    return list(plan.campaign_weeks.order_by('week_number')[:4])


def ensure_campaign_weeks(plan, enqueue=False):
    mark_stale_campaign_weeks(plan)
    existing = list(plan.campaign_weeks.order_by('week_number'))
    if not enqueue:
        return existing[:4]
    if len(existing) >= 4 and not all(week.status == 'generated' for week in existing[-4:]):
        pending = [
            week for week in existing[:4]
            if isinstance(week.item_plan, dict)
            and week.item_plan.get('generation_status') in ('queued', 'running')
            and not (week.item_plan.get('title') or week.theme)
        ]
        if pending:
            logger.info("Campaign generation already active plan=%s", plan.id)
            return existing[:4]
        failed_placeholders = [
            week for week in existing[:4]
            if isinstance(week.item_plan, dict)
            and week.item_plan.get('generation_status') == 'failed'
            and not (week.item_plan.get('title') or week.theme)
        ]
        if failed_placeholders:
            for week in failed_placeholders:
                item_plan = week.item_plan if isinstance(week.item_plan, dict) else {}
                item_plan['generation_status'] = 'queued'
                item_plan['task_requested'] = True
                item_plan['generation_requested_at'] = timezone.now().isoformat()
                item_plan.pop('generation_error', None)
                item_plan.pop('error_type', None)
                item_plan.pop('retryable', None)
                week.item_plan = item_plan
                week.save(update_fields=['item_plan', 'updated_at'])
            start_campaign_plan_job(plan)
            return list(plan.campaign_weeks.order_by('week_number')[:4])
        result = []
        for week in existing[:4]:
            normalized = normalize_campaign_item_plan(
                {'theme': week.theme, 'funnel_goal': week.funnel_goal, 'item_plan': week.item_plan},
                plan.business_profile,
                plan.brand_setting,
                plan,
                max(0, int(week.week_number or 1) - 1),
            )
            if normalized != week.item_plan:
                week.item_plan = normalized
                week.theme = week.item_plan.get('title') or week.theme
                week.save(update_fields=['theme', 'item_plan', 'updated_at'])
            result.append(week)
        return result

    if existing and all(week.status == 'generated' for week in existing[-4:]):
        start_number = existing[-1].week_number + 1
    else:
        start_number = 1

    existing_by_number = {week.week_number: week for week in existing}
    result = []
    for index in range(4):
        number = start_number + index
        week = existing_by_number.get(number)
        if week:
            item_plan = week.item_plan if isinstance(week.item_plan, dict) else {}
            if item_plan.get('generation_status') == 'failed':
                item_plan['generation_status'] = 'queued'
                item_plan['task_requested'] = True
                item_plan['generation_requested_at'] = timezone.now().isoformat()
                item_plan.pop('generation_error', None)
                item_plan.pop('error_type', None)
                item_plan.pop('retryable', None)
                week.item_plan = item_plan
                week.save(update_fields=['item_plan', 'updated_at'])
            result.append(week)
            continue
        result.append(CampaignWeek.objects.create(
            content_plan=plan,
            week_number=number,
            theme='',
            funnel_goal=['awareness', 'engagement', 'conversion', 'retention'][index],
            item_plan={'generation_status': 'queued', 'task_requested': True, 'generation_requested_at': timezone.now().isoformat()},
            status='draft',
        ))
    start_campaign_plan_job(plan)
    return result


def trigger_due_approved_campaign_weeks(user, workspace):
    if not user:
        return
    today = timezone.localdate()
    plans = ContentPlan.objects.filter(user=user, workspace=workspace, status='draft')
    for plan in plans:
        mark_stale_generation_jobs(plan=plan, user=user, workspace=workspace)
        start_date = timezone.localtime(plan.created_at).date()
        for week in plan.campaign_weeks.exclude(status='generated').order_by('week_number'):
            due_date = start_date + timedelta(days=(week.week_number - 1) * 7)
            if due_date > today:
                continue
            active = GenerationJob.objects.filter(content_plan=plan, campaign_week=week, status__in=['queued', 'running']).exists()
            if active:
                continue
            job = GenerationJob.objects.create(user=user, workspace=workspace, content_plan=plan, campaign_week=week, status='queued')
            start_generation_job(job)


def start_generation_job(job):
    if use_celery_workers():
        try:
            generate_content_job.delay(str(job.id))
            return
        except Exception as exc:
            print('generation celery enqueue failed', type(exc).__name__, str(exc))
    def run_inline_generation():
        try:
            generate_first_week(job)
        except Exception as exc:
            logger.exception('inline content generation failed job=%s: %s', job.id, exc)
            payload = gemini_error_payload(exc)
            job.refresh_from_db()
            if job.status not in ('completed', 'failed'):
                job.status = 'failed'
                job.error = payload['message']
                job.save(update_fields=['status', 'error', 'updated_at'])
    worker = threading.Thread(target=run_inline_generation, daemon=True)
    worker.start()


def mark_stale_intelligence_jobs(user=None, workspace=None):
    cutoff = timezone.now() - timedelta(minutes=INTELLIGENCE_JOB_TIMEOUT_MINUTES)
    qs = WorkspaceIntelligenceJob.objects.filter(status__in=['queued', 'running'], updated_at__lt=cutoff)
    if user:
        qs = qs.filter(user=user)
    if workspace:
        qs = qs.filter(workspace=workspace)
    count = qs.update(
        status='failed',
        error=f'Workspace intelligence timed out after {INTELLIGENCE_JOB_TIMEOUT_MINUTES} minutes. Please retry.',
        result={'error_type': 'timeout', 'retryable': True},
        updated_at=timezone.now(),
    )
    if count:
        logger.warning("Marked stale workspace intelligence jobs failed count=%s workspace=%s", count, getattr(workspace, 'id', None))


def start_workspace_intelligence_job(job):
    if use_celery_workers():
        try:
            run_workspace_intelligence_job.delay(str(job.id))
            return
        except Exception as exc:
            logger.warning('workspace intelligence celery enqueue failed job=%s: %s', job.id, exc)
    worker = threading.Thread(target=run_workspace_intelligence_job.run, args=(str(job.id),), daemon=True)
    worker.start()


def queue_workspace_intelligence_job(user, workspace, profile, job_type):
    if not user or not workspace or not profile:
        return None
    mark_stale_intelligence_jobs(user=user, workspace=workspace)
    active = WorkspaceIntelligenceJob.objects.filter(
        user=user,
        workspace=workspace,
        job_type=job_type,
        status__in=['queued', 'running'],
    ).order_by('-updated_at').first()
    if active:
        return active
    job = WorkspaceIntelligenceJob.objects.create(
        user=user,
        workspace=workspace,
        business_profile=profile,
        job_type=job_type,
        status='queued',
    )
    start_workspace_intelligence_job(job)
    return job


class CampaignPlanView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request_user(request)
        workspace = request_workspace(request)
        if not workspace:
            return workspace_required_response()
        plan = find_or_create_draft_plan(user, workspace, request.query_params)
        if not plan:
            return Response({'weeks': [], 'content_plan': None})
        try:
            mark_stale_generation_jobs(plan=plan, user=user, workspace=workspace)
            weeks = read_campaign_weeks(plan)
        except Exception as exc:
            logger.exception('campaign plan read failed plan=%s: %s', plan.id, exc)
            weeks = list(plan.campaign_weeks.order_by('week_number')[:4])
        return Response({'content_plan': content_plan_payload(plan), 'weeks': [campaign_week_payload(week) for week in weeks]})

    def post(self, request):
        user = request_user(request)
        workspace = request_workspace(request)
        if not workspace:
            return workspace_required_response()
        plan = find_or_create_draft_plan(user, workspace, request.data)
        if not plan:
            return Response({'error': 'Business profile is required before planning campaigns.'}, status=status.HTTP_400_BAD_REQUEST)
        incoming = request.data.get('weeks')
        if not isinstance(incoming, list) or not incoming:
            weeks = ensure_campaign_weeks(plan, enqueue=True)
            return Response(
                {
                    'content_plan': content_plan_payload(plan),
                    'weeks': [campaign_week_payload(week) for week in weeks],
                    'generation_status': 'queued',
                },
                status=status.HTTP_202_ACCEPTED,
            )
        with transaction.atomic():
            for index, item in enumerate(incoming[:4]):
                if not isinstance(item, dict):
                    continue
                number = int(item.get('week_number') or index + 1)
                week, _ = CampaignWeek.objects.update_or_create(
                    content_plan=plan,
                    week_number=number,
                    defaults={
                        'theme': item.get('theme', ''),
                        'funnel_goal': item.get('funnel_goal', ''),
                        'item_plan': normalize_campaign_item_plan(item, plan.business_profile, plan.brand_setting, plan, index),
                        'status': item.get('status') if item.get('status') in ('draft', 'approved', 'generated') else 'draft',
                    },
                )
            weeks = read_campaign_weeks(plan)
        return Response({'content_plan': content_plan_payload(plan), 'weeks': [campaign_week_payload(week) for week in weeks]})


class CampaignPlanCreateBatchView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request_user(request)
        workspace = request_workspace(request)
        if not workspace:
            return workspace_required_response()
        plan = find_or_create_draft_plan(user, workspace, request.data)
        if not plan:
            return Response({'error': 'Business profile is required before planning campaigns.'}, status=status.HTTP_400_BAD_REQUEST)
        count = positive_int(request.data.get('count'), 1, 1)
        count = min(count, 24)
        latest = plan.campaign_weeks.order_by('-week_number').first()
        start_number = (latest.week_number + 1) if latest else 1
        try:
            batch = generate_campaign_batch(plan.business_profile, plan.brand_setting, plan, start_number=start_number, count=count)
        except Exception as exc:
            logger.exception('campaign batch generation failed plan=%s: %s', plan.id, exc)
            payload = gemini_error_payload(exc)
            return Response({'error': payload['message'], **payload}, status=status.HTTP_502_BAD_GATEWAY)
        with transaction.atomic():
            created = []
            for item in batch:
                normalized = item['item_plan']
                created.append(CampaignWeek.objects.create(
                    content_plan=plan,
                    week_number=item['week_number'],
                    theme=normalized.get('title') or item.get('theme', ''),
                    funnel_goal=item.get('funnel_goal', ''),
                    item_plan=normalized,
                    status='draft',
                ))
        return Response({'weeks': [campaign_week_payload(week) for week in created]}, status=status.HTTP_201_CREATED)


class CampaignPlanReorderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request_user(request)
        workspace = request_workspace(request)
        if not workspace:
            return workspace_required_response()
        plan = find_or_create_draft_plan(user, workspace, request.data)
        if not plan:
            return Response({'error': 'Content plan was not found.'}, status=status.HTTP_400_BAD_REQUEST)
        ordered_ids = request.data.get('ordered_ids')
        if not isinstance(ordered_ids, list) or not ordered_ids:
            return Response({'error': 'ordered_ids is required.'}, status=status.HTTP_400_BAD_REQUEST)
        weeks = list(CampaignWeek.objects.filter(content_plan=plan, id__in=ordered_ids))
        by_id = {str(week.id): week for week in weeks}
        if len(by_id) != len(set(str(item) for item in ordered_ids)):
            return Response({'error': 'One or more campaigns were not found.'}, status=status.HTTP_400_BAD_REQUEST)
        ordered = [by_id[str(item)] for item in ordered_ids]
        with transaction.atomic():
            # Move away from unique week_number values first, then assign final order.
            for offset, week in enumerate(ordered):
                week.week_number = 10000 + offset
                week.save(update_fields=['week_number', 'updated_at'])
            for index, week in enumerate(ordered, start=1):
                week.week_number = index
                week.item_plan = apply_campaign_timing(week.item_plan, index)
                week.theme = week.item_plan.get('title') or week.theme
                week.save(update_fields=['week_number', 'theme', 'item_plan', 'updated_at'])
        return Response({'weeks': [campaign_week_payload(week) for week in CampaignWeek.objects.filter(content_plan=plan).order_by('week_number')]})


class CampaignWeekView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, week_id):
        user = request_user(request)
        workspace = request_workspace(request)
        if not workspace:
            return workspace_required_response()
        week = CampaignWeek.objects.filter(id=week_id, content_plan__user=user, content_plan__workspace=workspace).first()
        if not week:
            return Response({'error': 'Campaign week not found.'}, status=status.HTTP_404_NOT_FOUND)
        for field in ['theme', 'funnel_goal', 'item_plan']:
            if field in request.data:
                setattr(week, field, request.data[field])
        if isinstance(request.data.get('item_plan'), dict):
            week.item_plan = normalize_campaign_item_plan(
                {'theme': request.data.get('theme') or week.theme, 'funnel_goal': request.data.get('funnel_goal') or week.funnel_goal, 'item_plan': request.data['item_plan']},
                week.content_plan.business_profile,
                week.content_plan.brand_setting,
                week.content_plan,
                max(0, int(week.week_number or 1) - 1),
            )
            week.theme = week.item_plan.get('title') or week.theme
        if request.data.get('status') in ('draft', 'approved', 'generated'):
            week.status = request.data['status']
        week.save()
        return Response({'week': campaign_week_payload(week)})

    def delete(self, request, week_id):
        user = request_user(request)
        workspace = request_workspace(request)
        if not workspace:
            return workspace_required_response()
        week = CampaignWeek.objects.filter(id=week_id, content_plan__user=user, content_plan__workspace=workspace).first()
        if not week:
            return Response({'error': 'Campaign week not found.'}, status=status.HTTP_404_NOT_FOUND)
        plan = week.content_plan
        week.delete()
        remaining = list(CampaignWeek.objects.filter(content_plan=plan).order_by('week_number', 'created_at'))
        with transaction.atomic():
            for index, item in enumerate(remaining, start=1):
                if item.week_number == index:
                    continue
                item.week_number = index
                item.item_plan = apply_campaign_timing(item.item_plan, index)
                item.save(update_fields=['week_number', 'item_plan', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class CampaignWeekRegenerateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, week_id):
        user = request_user(request)
        workspace = request_workspace(request)
        if not workspace:
            return workspace_required_response()
        week = CampaignWeek.objects.filter(id=week_id, content_plan__user=user, content_plan__workspace=workspace).first()
        if not week:
            return Response({'error': 'Campaign week not found.'}, status=status.HTTP_404_NOT_FOUND)
        instruction = str(request.data.get('instruction') or '').strip()
        if not instruction:
            return Response({'error': 'instruction is required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            updated = regenerate_campaign_plan(
                week.content_plan.business_profile,
                week.content_plan.brand_setting,
                week.content_plan,
                week.item_plan,
                instruction,
            )
        except Exception as exc:
            logger.exception('campaign week regeneration failed week=%s: %s', week.id, exc)
            payload = gemini_error_payload(exc)
            return Response({'week': campaign_week_payload(week), 'error': payload['message'], **payload}, status=status.HTTP_502_BAD_GATEWAY)
        week.item_plan = normalize_campaign_item_plan(
            {'theme': week.theme, 'funnel_goal': week.funnel_goal, 'item_plan': updated},
            week.content_plan.business_profile,
            week.content_plan.brand_setting,
            week.content_plan,
            max(0, int(week.week_number or 1) - 1),
        )
        week.item_plan = apply_campaign_timing(week.item_plan, week.week_number)
        week.theme = week.item_plan.get('title') or week.theme
        week.save(update_fields=['theme', 'item_plan', 'updated_at'])
        return Response({'week': campaign_week_payload(week)})


class CampaignPromptRegenerateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, week_id):
        user = request_user(request)
        workspace = request_workspace(request)
        if not workspace:
            return workspace_required_response()
        week = CampaignWeek.objects.filter(id=week_id, content_plan__user=user, content_plan__workspace=workspace).first()
        if not week:
            return Response({'error': 'Campaign week not found.'}, status=status.HTTP_404_NOT_FOUND)
        prompt_id = str(request.data.get('prompt_id') or '').strip()
        instruction = str(request.data.get('instruction') or '').strip()
        if not prompt_id or not instruction:
            return Response({'error': 'prompt_id and instruction are required.'}, status=status.HTTP_400_BAD_REQUEST)
        item_plan = week.item_plan if isinstance(week.item_plan, dict) else {}
        prompts = item_plan.get('post_prompts') if isinstance(item_plan.get('post_prompts'), list) else []
        updated_prompts = []
        found = False
        for prompt_item in prompts:
            if isinstance(prompt_item, dict) and str(prompt_item.get('id')) == prompt_id:
                found = True
                try:
                    updated_prompts.append(regenerate_campaign_prompt(
                        week.content_plan.business_profile,
                        week.content_plan.brand_setting,
                        week.content_plan,
                        item_plan,
                        prompt_item,
                        instruction,
                    ))
                except Exception as exc:
                    logger.exception('campaign prompt regeneration failed week=%s prompt=%s: %s', week.id, prompt_id, exc)
                    payload = gemini_error_payload(exc)
                    return Response({'week': campaign_week_payload(week), 'error': payload['message'], **payload}, status=status.HTTP_502_BAD_GATEWAY)
            else:
                updated_prompts.append(prompt_item)
        if not found:
            return Response({'error': 'Prompt was not found.'}, status=status.HTTP_404_NOT_FOUND)
        item_plan['post_prompts'] = updated_prompts
        week.item_plan = normalize_campaign_item_plan(
            {'theme': week.theme, 'funnel_goal': week.funnel_goal, 'item_plan': item_plan},
            week.content_plan.business_profile,
            week.content_plan.brand_setting,
            week.content_plan,
            max(0, int(week.week_number or 1) - 1),
        )
        week.save(update_fields=['item_plan', 'updated_at'])
        return Response({'week': campaign_week_payload(week)})


class CampaignWeekApproveView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, week_id):
        user = request_user(request)
        workspace = request_workspace(request)
        if not workspace:
            return workspace_required_response()
        week = CampaignWeek.objects.filter(id=week_id, content_plan__user=user, content_plan__workspace=workspace).first()
        if not week:
            return Response({'error': 'Campaign week not found.'}, status=status.HTTP_404_NOT_FOUND)

        logger.info(
            'Week approval received plan=%s week=%s user=%s workspace=%s current_status=%s',
            week.content_plan_id,
            week.id,
            user.id if user else None,
            workspace.id if workspace else None,
            week.status,
        )
        if week.status != 'generated':
            week.status = 'approved'
            week.save(update_fields=['status', 'updated_at'])

        # Idempotency: check if posts already exist for this week
        from .models import GeneratedPost
        generated_post_exists = GeneratedPost.objects.filter(
            user=user,
            workspace=workspace,
            content_plan=week.content_plan,
            topic__metadata__campaign_week_id=str(week.id),
        ).exists()
        
        if generated_post_exists or week.status == 'generated':
            logger.info(
                'Week already generated plan=%s week=%s user=%s workspace=%s',
                week.content_plan_id,
                week.id,
                user.id if user else None,
                workspace.id if workspace else None,
            )
            if week.status != 'generated':
                week.status = 'generated'
                week.generated_at = timezone.now()
                week.save(update_fields=['status', 'generated_at', 'updated_at'])
            return Response({
                'week': campaign_week_payload(week),
                'job': None,
                'generation_status': 'already_generated',
            })

        # Idempotency: check if a job is already active
        active = GenerationJob.objects.filter(
            user=user,
            workspace=workspace,
            content_plan=week.content_plan,
            campaign_week=week,
            status__in=['queued', 'running']
        ).order_by('-updated_at').first()
        
        if active:
            logger.info(
                'Existing campaign week generation job found job=%s status=%s plan=%s week=%s',
                active.id,
                active.status,
                week.content_plan_id,
                week.id,
            )
            return Response({
                'week': campaign_week_payload(week),
                'job': {'id': str(active.id), 'status': active.status, 'error': active.error},
                'generation_status': 'job_active',
            }, status=status.HTTP_202_ACCEPTED)

        # Trigger generation job
        logger.info(
            'Triggering campaign week generation plan=%s week=%s week_number=%s',
            week.content_plan_id,
            week.id,
            week.week_number
        )
        job = GenerationJob.objects.create(
            user=user,
            workspace=workspace,
            content_plan=week.content_plan,
            campaign_week=week,
            status='queued'
        )
        start_generation_job(job)

        return Response({
            'week': campaign_week_payload(week),
            'job': {'id': str(job.id), 'status': job.status, 'error': job.error},
            'generation_status': 'job_created',
        }, status=status.HTTP_202_ACCEPTED)


class CampaignWeekGenerateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, week_id):
        user = request_user(request)
        workspace = request_workspace(request)
        if not workspace:
            return workspace_required_response()
        week = CampaignWeek.objects.filter(id=week_id, content_plan__user=user, content_plan__workspace=workspace).first()
        if not week:
            return Response({'error': 'Campaign week not found.'}, status=status.HTTP_404_NOT_FOUND)
        mark_stale_generation_jobs(plan=week.content_plan, user=user, workspace=workspace)
        active = GenerationJob.objects.filter(content_plan=week.content_plan, campaign_week=week, status__in=['queued', 'running']).first()
        if active:
            return Response({'job': {'id': str(active.id), 'status': active.status, 'error': active.error}}, status=status.HTTP_202_ACCEPTED)
        job = GenerationJob.objects.create(user=user, workspace=workspace, content_plan=week.content_plan, campaign_week=week, status='queued')
        start_generation_job(job)
        return Response({'job': {'id': str(job.id), 'status': job.status, 'error': job.error}}, status=status.HTTP_202_ACCEPTED)


class TopicsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request_user(request)
        workspace = request_workspace(request)
        if not workspace:
            return workspace_required_response()
        plan = find_or_create_draft_plan(user, workspace, request.data)
        if not plan:
            return Response({'error': 'Business profile is required before generating topics.'}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            if isinstance(request.data.get('topics'), list) and request.data.get('topics'):
                plan.topics.all().delete()
                topics = [item for item in request.data['topics'] if isinstance(item, dict) and item.get('kind', 'social') != 'email']
            else:
                week = CampaignWeek.objects.filter(content_plan=plan, week_number=1).first()
                if week and isinstance(week.item_plan, dict) and week.item_plan.get('generation_status') in ('queued', 'running'):
                    return Response(
                        {
                            'generation_status': week.item_plan.get('generation_status'),
                            'content_plan': content_plan_payload(plan),
                        },
                        status=status.HTTP_202_ACCEPTED,
                    )
                if week and isinstance(week.item_plan, dict) and week.item_plan.get('generation_status') == 'failed':
                    return Response(
                        {
                            'error': week.item_plan.get('generation_error') or 'Campaign generation failed. Please retry.',
                            'error_type': week.item_plan.get('error_type') or 'unknown_error',
                            'retryable': week.item_plan.get('retryable', True),
                            'content_plan': content_plan_payload(plan),
                        },
                        status=status.HTTP_502_BAD_GATEWAY,
                    )
                topics = topics_from_campaign_prompts(plan, 1)
                if not topics:
                    try:
                        topics = generate_weekly_topics(plan.business_profile, plan.brand_setting, plan)
                    except Exception as exc:
                        logger.exception('weekly topics generation failed plan=%s: %s', plan.id, exc)
                        payload = gemini_error_payload(exc)
                        return Response({'error': payload['message'], **payload}, status=status.HTTP_502_BAD_GATEWAY)
                plan.topics.filter(kind__in=['social', 'blog', 'email']).delete()
                topics = [item for item in topics if item.get('kind', 'social') != 'email']
            for item in topics:
                Topic.objects.create(
                    content_plan=plan,
                    week_number=item.get('week_number', 1),
                    position=item.get('position', 1),
                    kind=item.get('kind', 'social'),
                    title=item.get('title') or item.get('text') or '',
                    metadata=item.get('metadata', {}),
                )
        return Response({'content_plan': content_plan_payload(plan)})


class BlogEmailPlanView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request_user(request)
        workspace = request_workspace(request)
        if not workspace:
            return workspace_required_response()
        plan = find_or_create_draft_plan(user, workspace, request.data)
        if not plan:
            return Response({'error': 'Business profile is required before generating a blog plan.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            payload = normalize_blog_email_plan(
                request.data.get('plan') or generate_blog_email_plan(plan.business_profile, plan.brand_setting, plan),
                plan.business_profile,
                plan,
            )
        except Exception as exc:
            logger.exception('blog plan generation failed plan=%s: %s', plan.id, exc)
            error_payload = gemini_error_payload(exc)
            return Response({'error': error_payload['message'], **error_payload}, status=status.HTTP_502_BAD_GATEWAY)
        blog_email, _ = BlogEmailPlan.objects.update_or_create(
            content_plan=plan,
            defaults={'blog_plan': payload.get('blog_plan', {}), 'email_plan': {}},
        )
        return Response({'blog_plan': blog_email.blog_plan, 'email_plan': {}})


class GenerateFirstWeekView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request_user(request)
        workspace = request_workspace(request)
        if not workspace:
            return workspace_required_response()
        plan = find_or_create_draft_plan(user, workspace, request.data)
        if not plan:
            return Response({'error': 'Business profile is required before generating first week content.'}, status=status.HTTP_400_BAD_REQUEST)
        week = CampaignWeek.objects.filter(content_plan=plan, week_number=1).first()
        if week and week.status == 'draft':
            week.status = 'approved'
            week.save(update_fields=['status', 'updated_at'])
        mark_stale_generation_jobs(plan=plan, user=user, workspace=workspace)
        active = GenerationJob.objects.filter(content_plan=plan, campaign_week=week, status__in=['queued', 'running']).first()
        if active:
            return Response({
                'job': {'id': str(active.id), 'status': active.status, 'error': active.error},
                'posts': [],
            }, status=status.HTTP_202_ACCEPTED)
        job = GenerationJob.objects.create(user=user, workspace=workspace, content_plan=plan, campaign_week=week, status='queued')
        start_generation_job(job)
        return Response({
            'job': {'id': str(job.id), 'status': job.status, 'error': job.error},
            'posts': [],
        }, status=status.HTTP_202_ACCEPTED)
