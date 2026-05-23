import logging

from celery import shared_task
from django.utils import timezone

from .models import BrandSetting, BusinessProfile, CampaignWeek, ContentPlan, GenerationJob, SourceMatrixEntry, WorkspaceIntelligenceJob
from .services.generation import generate_first_week
from .services.intelligence import analyze_brand_from_crawl, analyze_competitor_url, brand_analysis_is_ready, crawl_website, crawl_website_static, discover_competitors
from .services.website import render_profile_markdown
from .services.planner import generate_campaign_weeks
from utils.chatbot import gemini_error_payload

logger = logging.getLogger(__name__)


@shared_task(bind=True, name='content_engine.generate_campaign_plan_job')
def generate_campaign_plan_job(self, plan_id):
    """Generate campaign weeks with the configured AI pipeline outside the request/response path."""
    plan = (
        ContentPlan.objects
        .filter(id=plan_id)
        .select_related('user', 'workspace', 'business_profile', 'brand_setting')
        .first()
    )
    if not plan:
        logger.warning('ContentPlan %s was not found for campaign planning.', plan_id)
        return {'status': 'missing'}

    placeholders = list(plan.campaign_weeks.order_by('week_number')[:4])
    for week in placeholders:
        item_plan = week.item_plan if isinstance(week.item_plan, dict) else {}
        item_plan['generation_status'] = 'running'
        item_plan.pop('generation_error', None)
        week.item_plan = item_plan
        week.save(update_fields=['item_plan', 'updated_at'])

    try:
        generated = generate_campaign_weeks(plan.business_profile, plan.brand_setting, plan, allow_fallback=False)
        for index, item in enumerate(generated[:4]):
            number = index + 1
            item_plan = item.get('item_plan') if isinstance(item.get('item_plan'), dict) else {}
            item_plan['generation_status'] = 'completed'
            CampaignWeek.objects.update_or_create(
                content_plan=plan,
                week_number=number,
                defaults={
                    'theme': item_plan.get('title') or item.get('theme', ''),
                    'funnel_goal': item.get('funnel_goal', ''),
                    'item_plan': item_plan,
                    'status': 'approved' if number == 1 else 'draft',
                },
            )
        return {'status': 'completed', 'plan_id': str(plan.id)}
    except Exception as exc:
        logger.exception('Campaign plan generation failed for ContentPlan %s.', plan_id)
        error_payload = gemini_error_payload(exc)
        for number in range(1, 5):
            week, _ = CampaignWeek.objects.get_or_create(
                content_plan=plan,
                week_number=number,
                defaults={'status': 'approved' if number == 1 else 'draft'},
            )
            item_plan = week.item_plan if isinstance(week.item_plan, dict) else {}
            item_plan['generation_status'] = 'failed'
            item_plan['generation_error'] = error_payload['message']
            item_plan['error_type'] = error_payload['error_type']
            item_plan['retryable'] = error_payload['retryable']
            week.item_plan = item_plan
            week.save(update_fields=['item_plan', 'updated_at'])
        return {'status': 'failed', 'error': error_payload, 'plan_id': str(plan.id)}


@shared_task(bind=True, name='content_engine.generate_content_job')
def generate_content_job(self, job_id):
    job = GenerationJob.objects.filter(id=job_id).select_related(
        'user',
        'workspace',
        'content_plan',
        'campaign_week',
    ).first()
    if not job:
        logger.warning('GenerationJob %s was not found.', job_id)
        return {'status': 'missing'}
    try:
        generate_first_week(job)
    except Exception as exc:
        logger.exception('GenerationJob %s failed in Celery.', job_id)
        error_payload = gemini_error_payload(exc)
        job.refresh_from_db()
        if job.status not in ('completed', 'failed'):
            job.status = 'failed'
            job.error = error_payload['message']
            job.save(update_fields=['status', 'error', 'updated_at'])
        return {'status': 'failed', 'error': error_payload}
    return {'status': 'completed'}


@shared_task(bind=True, name='content_engine.enrich_business_profile_intelligence')
def enrich_business_profile_intelligence(self, profile_id):
    """Run the slower website intelligence pass outside the request worker."""
    profile = (
        BusinessProfile.objects
        .filter(id=profile_id)
        .select_related('user', 'workspace')
        .first()
    )
    if not profile:
        logger.warning('BusinessProfile %s was not found for enrichment.', profile_id)
        return {'status': 'missing'}

    from .views import run_brand_intelligence_side_effects, sync_user_profile_from_business_profile

    brand, _ = BrandSetting.objects.get_or_create(
        user=profile.user,
        workspace=profile.workspace,
        defaults={'business_profile': profile, 'tone': profile.tone, 'brand_context': profile.profile},
    )
    if not brand.business_profile_id:
        brand.business_profile = profile
        brand.save(update_fields=['business_profile', 'updated_at'])

    try:
        try:
            crawl = crawl_website(profile.website_url, max_pages=8)
        except Exception as exc:
            logger.warning('Playwright crawl failed for %s, falling back to static crawl: %s', profile.website_url, exc)
            crawl = crawl_website_static(profile.website_url, max_pages=8)
        brand_analysis = analyze_brand_from_crawl(crawl)
        if isinstance(brand_analysis, dict) and brand_analysis:
            ready = brand_analysis_is_ready(brand_analysis)
            if not ready and brand_analysis_is_ready(profile.profile):
                return {
                    'status': 'failed',
                    'error': 'New website intelligence failed source validation; preserved existing valid profile.',
                }
            profile.profile = {**(profile.profile or {}), **brand_analysis}
            profile.tone = brand_analysis.get('tone') or profile.tone
            profile.services = brand_analysis.get('services') or profile.services
            profile.audience = brand_analysis.get('audience') or profile.audience
            profile.keywords = brand_analysis.get('keywords') or profile.keywords
            if ready:
                profile.editable_markdown = render_profile_markdown({
                    'name': brand_analysis.get('name'),
                    'positioning': brand_analysis.get('market_positioning'),
                    'tone': brand_analysis.get('tone'),
                    'services': brand_analysis.get('services', []),
                    'audience': brand_analysis.get('audience', []),
                    'keywords': brand_analysis.get('keywords', []),
                    'domain': profile.website_url,
                    'proof_points': brand_analysis.get('product_structure', []) or brand_analysis.get('services', []),
                    'about': brand_analysis.get('about', {}),
                    'brand_personality': {
                        'archetype': 'The Trusted Guide',
                        'voice': brand_analysis.get('tone', ''),
                        'values': (brand_analysis.get('keywords') or [])[:3],
                    },
                    'intelligence_status': brand_analysis.get('intelligence_status'),
                    'source_confidence': brand_analysis.get('source_confidence'),
                })
            snapshot = profile.source_snapshot if isinstance(profile.source_snapshot, dict) else {}
            snapshot.update(crawl or {})
            profile.source_snapshot = snapshot
            profile.save(update_fields=['profile', 'tone', 'services', 'audience', 'keywords', 'editable_markdown', 'source_snapshot', 'updated_at'])
            run_brand_intelligence_side_effects(profile.user, profile.workspace, profile, brand, crawl, brand_analysis)
            sync_user_profile_from_business_profile(profile.user, profile.workspace, profile, brand, brand_analysis)
        return {'status': 'completed', 'profile_id': str(profile.id), 'finished_at': timezone.now().isoformat()}
    except Exception as exc:
        logger.exception('BusinessProfile %s enrichment failed.', profile_id)
        return {'status': 'failed', 'error': str(exc)}


@shared_task(bind=True, name='content_engine.run_workspace_intelligence_job')
def run_workspace_intelligence_job(self, job_id):
    job = (
        WorkspaceIntelligenceJob.objects
        .filter(id=job_id)
        .select_related('user', 'workspace', 'business_profile')
        .first()
    )
    if not job:
        logger.warning('WorkspaceIntelligenceJob %s was not found.', job_id)
        return {'status': 'missing'}
    job.status = 'running'
    job.attempts += 1
    job.error = ''
    job.save(update_fields=['status', 'attempts', 'error', 'updated_at'])

    profile = job.business_profile or BusinessProfile.objects.filter(user=job.user, workspace=job.workspace).order_by('-updated_at').first()
    if not profile:
        job.status = 'failed'
        job.error = 'Business profile is required before intelligence analysis can run.'
        job.result = {'error_type': 'missing_profile', 'retryable': True}
        job.save(update_fields=['status', 'error', 'result', 'updated_at'])
        return {'status': 'failed', 'error': job.error}

    try:
        if job.job_type == 'brand_enrichment':
            result = enrich_business_profile_intelligence.run(str(profile.id))
            if isinstance(result, dict) and result.get('status') == 'failed':
                raise RuntimeError(result.get('error') or 'Brand enrichment failed.')
            job.status = 'completed'
            job.result = result if isinstance(result, dict) else {'result': result}
        elif job.job_type == 'competitor_discovery':
            from .views import upsert_competitor
            brand_analysis = profile.profile if isinstance(profile.profile, dict) else {}
            if not brand_analysis_is_ready(brand_analysis):
                raise RuntimeError('Competitor discovery pending review because brand intelligence did not pass source validation.')
            competitors = []
            try:
                competitors = discover_competitors(brand_analysis)[:8]
            except Exception:
                raise
            if not competitors:
                raise RuntimeError('Voice Spark AI did not return competitor analysis for this workspace.')
            saved = [
                item for item in (
                    upsert_competitor(job.user, job.workspace, competitor)
                    for competitor in competitors
                ) if item
            ]
            if not saved:
                raise RuntimeError('Voice Spark AI did not return competitors with real names and website URLs.')
            job.status = 'completed'
            job.result = {'competitor_count': len(saved)}
        else:
            raise RuntimeError(f'Unsupported intelligence job type: {job.job_type}')
        job.error = ''
        job.save(update_fields=['status', 'result', 'error', 'updated_at'])
        return {'status': job.status, 'job_id': str(job.id), **(job.result or {})}
    except Exception as exc:
        logger.exception('Workspace intelligence job %s failed.', job.id)
        job.status = 'failed'
        job.error = str(exc)
        job.result = gemini_error_payload(exc) if job.job_type == 'competitor_discovery' else {'error': str(exc), 'retryable': True}
        job.save(update_fields=['status', 'error', 'result', 'updated_at'])
        SourceMatrixEntry.objects.filter(
            user=job.user,
            workspace=job.workspace,
            source_type='my_website',
        ).update(status='failed', error=str(exc), updated_at=timezone.now())
        return {'status': 'failed', 'error': str(exc)}


@shared_task(bind=True, name='content_engine.analyze_competitor_source')
def analyze_competitor_source(self, source_id):
    source = (
        SourceMatrixEntry.objects
        .filter(id=source_id, source_type='competitor')
        .select_related('user', 'workspace')
        .first()
    )
    if not source:
        logger.warning('SourceMatrixEntry %s was not found for competitor analysis.', source_id)
        return {'status': 'missing'}

    source.status = 'analyzing'
    source.error = ''
    source.save(update_fields=['status', 'error', 'updated_at'])

    try:
        data, crawl = analyze_competitor_url(source.url)
        from .views import upsert_competitor
        competitor = upsert_competitor(source.user, source.workspace, data, source=source)
        if not competitor:
            raise RuntimeError('Competitor analysis did not include a real name and website URL.')
        source.status = 'analyzed'
        source.last_analyzed_at = timezone.now()
        source.extracted_data = {'crawl': crawl, 'competitor': data}
        source.error = ''
        source.save(update_fields=['status', 'last_analyzed_at', 'extracted_data', 'error', 'updated_at'])
        return {'status': 'completed', 'source_id': str(source.id), 'competitor_id': str(competitor.id)}
    except Exception as exc:
        logger.exception('Competitor source analysis %s failed.', source.id)
        source.status = 'failed'
        source.error = str(exc)
        source.save(update_fields=['status', 'error', 'updated_at'])
        return {'status': 'failed', 'source_id': str(source.id), 'error': str(exc)}
