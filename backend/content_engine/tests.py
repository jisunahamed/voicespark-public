from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate
from unittest.mock import patch

from auth_user.models import UserProfile
from workspace.models import Workspace

from .models import BrandSetting, BusinessProfile, CompetitorAnalysis, SourceMatrixEntry
from .services.context_builder import build_generation_context
from .services.intelligence import (
    brand_analysis_is_ready,
    crawl_website_static,
    discover_links_from_html,
    fast_brand_analysis_from_crawl,
)
from .services.prompt_builder import build_advanced_image_prompt
from .services.website import render_profile_markdown
from .tasks import analyze_competitor_source
from .views import BrandSettingsView, CompetitorsView, run_brand_intelligence_side_effects, sync_user_profile_from_business_profile


class FakeResponse:
    def __init__(self, url, text='', status_code=200):
        self.url = url
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f'HTTP {self.status_code}')


class FakeSession:
    def __init__(self, pages):
        self.pages = pages
        self.headers = {}

    def get(self, url, *args, **kwargs):
        key = url.rstrip('/') or url
        page = self.pages.get(url) or self.pages.get(key)
        if page:
            return page
        return FakeResponse(url, WORDPRESS_404_HTML, 404)


STAFFINIT_HOME_HTML = """
<html>
  <head><title>Mój Blog – Kolejna witryna WordPress</title><meta name="robots" content="noindex,nofollow"></head>
  <body>
    <nav>Home About Our Company Employers Job Seekers Contact Us</nav>
    <main>
      <h1>StaffInIT</h1>
      <a href="/about-company/">About Company</a>
      <a href="/contact/">Contact</a>
      StaffInIT helps employers and HR teams hire technology professionals through a success-fee IT recruitment model.
    </main>
  </body>
</html>
"""

STAFFINIT_ABOUT_HTML = """
<html>
  <head><title>StaffInIT - Success-Fee IT Recruitment Agency</title></head>
  <body>
    <main>
      <h1>StaffInIT - Success-Fee IT Recruitment Agency</h1>
      <p>StaffInIT is an IT recruitment agency serving employers, HR teams, hiring managers, and skilled technology professionals.</p>
      <p>The agency supports tech hiring with Direct Hire, Contract-to-Hire, Payrolling, Executive Search, Candidate Sourcing, Interview Coordination, Candidate Evaluation & Shortlisting, Offer Management, and Post-Hire Follow-Up.</p>
      <p>StaffInIT combines recruitment expertise and technology to shortlist qualified candidates, coordinate interviews, support offer management, and help companies hire reliable IT talent on a success-fee basis.</p>
      <p>Employers use StaffInIT when they need staffing support for software engineers, developers, IT teams, and technical roles without wasting time on weak candidate pipelines.</p>
    </main>
  </body>
</html>
"""

STAFFINIT_CONTACT_HTML = """
<html>
  <head><title>Contact StaffInIT</title></head>
  <body>
    <main>
      <h1>Contact StaffInIT</h1>
      <p>Contact the StaffInIT recruitment team for employer hiring support, candidate sourcing, IT staffing, and recruitment coordination.</p>
      <p>Email: hello@staffinit.com</p>
    </main>
  </body>
</html>
"""

WORDPRESS_404_HTML = """
<html>
  <head><title>Page not found - Mój Blog</title></head>
  <body>
    <h1>Sorry this page isn’t available</h1>
    <p>It seems we can't find what you're looking for. Nothing found.</p>
  </body>
</html>
"""


class ContentEngineConsistencyTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(username='content-user', password='pass')
        self.workspace = Workspace.objects.create(name='Content Workspace', owner=self.user)
        self.profile = UserProfile.objects.create(user=self.user, workspace=self.workspace)

    def authenticated(self, request):
        force_authenticate(request, user=self.user)
        request.user = self.user
        return request

    def test_manual_competitor_requires_real_url(self):
        request = self.factory.post(
            '/content-engine/competitors/',
            {'workspace_id': str(self.workspace.id), 'website_url': 'https://competitor.com'},
            format='json',
        )
        response = CompetitorsView.as_view()(self.authenticated(request))

        self.assertEqual(response.status_code, 400)
        self.assertIn('real competitor website URL', response.data['error'])
        self.assertFalse(CompetitorAnalysis.objects.exists())

    def test_manual_competitor_starts_async_analysis(self):
        request = self.factory.post(
            '/content-engine/competitors/',
            {'workspace_id': str(self.workspace.id), 'website_url': 'https://pressway.com/'},
            format='json',
        )

        with patch('content_engine.views.analyze_competitor_source.delay') as delay:
            response = CompetitorsView.as_view()(self.authenticated(request))

        self.assertEqual(response.status_code, 202)
        source = SourceMatrixEntry.objects.get(workspace=self.workspace, source_type='competitor')
        self.assertEqual(source.status, 'analyzing')
        delay.assert_called_once_with(str(source.id))
        self.assertFalse(CompetitorAnalysis.objects.exists())

    def test_competitor_source_task_saves_valid_competitor(self):
        source = SourceMatrixEntry.objects.create(
            user=self.user,
            workspace=self.workspace,
            url='https://pressway.com',
            source_type='competitor',
            status='analyzing',
        )
        payload = {
            'name': 'Pressway',
            'website_url': 'https://pressway.com',
            'key_features': ['Publishing'],
            'differentiators': ['Fast workflow'],
        }

        with patch('content_engine.tasks.analyze_competitor_url', return_value=(payload, {'pages': []})):
            result = analyze_competitor_source.run(str(source.id))

        self.assertEqual(result['status'], 'completed')
        source.refresh_from_db()
        self.assertEqual(source.status, 'analyzed')
        self.assertTrue(CompetitorAnalysis.objects.filter(workspace=self.workspace, website_url='https://pressway.com').exists())

    def test_invalid_existing_competitor_is_returned_as_needs_review(self):
        CompetitorAnalysis.objects.create(
            user=self.user,
            workspace=self.workspace,
            name='Placeholder',
            website_url='',
        )
        CompetitorAnalysis.objects.create(
            user=self.user,
            workspace=self.workspace,
            name='Real Rival',
            website_url='https://real-rival.com',
        )
        request = self.factory.get('/content-engine/competitors/', {'workspace_id': str(self.workspace.id)})
        response = CompetitorsView.as_view()(self.authenticated(request))

        self.assertEqual(len(response.data['competitors']), 1)
        self.assertEqual(response.data['competitors'][0]['name'], 'Real Rival')
        self.assertEqual(len(response.data['needs_review']), 1)
        self.assertTrue(response.data['needs_review'][0]['needs_review'])

    def test_brand_settings_visual_style_syncs_content_preferences(self):
        style = {'id': 'product-studio', 'name': 'Product Studio', 'label': 'Product Studio'}
        request = self.factory.post(
            '/content-engine/brand-settings/',
            {'workspace_id': str(self.workspace.id), 'recommended_visual_style': style},
            format='json',
        )
        response = BrandSettingsView.as_view()(self.authenticated(request))

        self.assertEqual(response.status_code, 200)
        self.profile.refresh_from_db()
        brand_voice = self.profile.brand_voice
        self.assertEqual(brand_voice['brand_style']['visual_style']['id'], 'product_studio')
        self.assertEqual(brand_voice['content_preferences']['content_style']['id'], 'product_studio')

    def test_generation_context_and_prompt_use_saved_font_and_style(self):
        BrandSetting.objects.create(
            user=self.user,
            workspace=self.workspace,
            font={'displayName': 'Montserrat', 'family': 'Montserrat'},
            recommended_visual_style={'id': 'editorial-lifestyle', 'name': 'Editorial Lifestyle'},
        )
        context = build_generation_context(self.user, self.workspace, topic='Launch offer')
        prompt = build_advanced_image_prompt(context, topic='Launch offer')

        self.assertEqual(context['visual_style']['id'], 'editorial_lifestyle')
        self.assertEqual(context['font'], 'Montserrat')
        self.assertIn('selected brand font "Montserrat"', prompt)

    def test_staffinit_analysis_filters_placeholder_and_keeps_recruitment_identity(self):
        pages = {
            'https://staffinit.com/': FakeResponse('https://staffinit.com/', STAFFINIT_HOME_HTML, 200),
            'https://staffinit.com/about-company': FakeResponse('https://staffinit.com/about-company/', STAFFINIT_ABOUT_HTML, 200),
            'https://staffinit.com/about-company/': FakeResponse('https://staffinit.com/about-company/', STAFFINIT_ABOUT_HTML, 200),
            'https://staffinit.com/contact': FakeResponse('https://staffinit.com/contact/', STAFFINIT_CONTACT_HTML, 200),
            'https://staffinit.com/contact/': FakeResponse('https://staffinit.com/contact/', STAFFINIT_CONTACT_HTML, 200),
        }

        with patch('content_engine.services.intelligence.requests.Session', return_value=FakeSession(pages)):
            crawl = crawl_website_static('https://staffinit.com/', max_pages=8)

        analysis = fast_brand_analysis_from_crawl(crawl)
        rendered = render_profile_markdown({
            'name': analysis['name'],
            'positioning': analysis['market_positioning'],
            'industry': analysis['industry'],
            'business_type': analysis['business_type'],
            'services': analysis['services'],
            'audience': analysis['audience'],
            'keywords': analysis['keywords'],
            'domain': 'https://staffinit.com/',
            'proof_points': analysis['services'],
            'about': analysis.get('about', {}),
            'intelligence_status': analysis.get('intelligence_status'),
            'source_confidence': analysis.get('source_confidence'),
        })
        output = f'{analysis} {rendered}'

        self.assertEqual(analysis['name'], 'StaffInIT')
        self.assertIn('recruit', analysis['industry'].lower())
        self.assertTrue(any('Direct Hire' == service for service in analysis['services']))
        self.assertTrue(brand_analysis_is_ready(analysis))
        for forbidden in (
            'Mój Blog',
            'Kolejna witryna WordPress',
            'Sorry this page isn’t available',
            "It seems we can't find what you're looking for",
            'Reliable automation for customer conversations',
            'AI inbox',
            'customer conversation automation',
        ):
            self.assertNotIn(forbidden, output)

    def test_wordpress_404_page_is_excluded_from_brand_analysis(self):
        pages = {
            'https://example.com/': FakeResponse('https://example.com/', '<html><body><a href="/missing">Missing</a><p>Real but thin page.</p></body></html>', 200),
            'https://example.com/missing': FakeResponse('https://example.com/missing', WORDPRESS_404_HTML, 404),
            'https://example.com/missing/': FakeResponse('https://example.com/missing/', WORDPRESS_404_HTML, 404),
        }

        with patch('content_engine.services.intelligence.requests.Session', return_value=FakeSession(pages)):
            crawl = crawl_website_static('https://example.com/', max_pages=2)

        self.assertTrue(any(page['type'] == 'excluded' for page in crawl['pages']))

        crawl = {
            'root_url': 'https://example.com/',
            'pages': [{
                'url': 'https://example.com/missing',
                'type': 'excluded',
                'title': 'Page not found - Mój Blog',
                'text': "Sorry this page isn’t available. It seems we can't find what you're looking for.",
                'source_quality': 0,
            }],
            'images': [],
        }
        analysis = fast_brand_analysis_from_crawl(crawl)

        self.assertFalse(brand_analysis_is_ready(analysis))
        self.assertNotIn("It seems we can't find what you're looking for", ' '.join(analysis.get('services', [])))

    def test_non_ecommerce_homepage_does_not_force_ecommerce_paths(self):
        links = discover_links_from_html(
            """
            <html><body>
              <a href="/about">About</a>
              <a href="/services">Services</a>
              <p>Staffing, hiring, careers, and recruitment support for employers.</p>
            </body></html>
            """,
            'https://staffinit.com/',
        )
        joined = ' '.join(links)

        self.assertIn('https://staffinit.com/about', links)
        self.assertIn('https://staffinit.com/services', links)
        self.assertNotIn('/shop', joined)
        self.assertNotIn('/product', joined)
        self.assertNotIn('/products', joined)
        self.assertNotIn('/collections', joined)

    def test_low_confidence_analysis_is_marked_for_review(self):
        analysis = fast_brand_analysis_from_crawl({
            'root_url': 'https://thin.example/',
            'pages': [],
            'images': [],
        })

        self.assertEqual(analysis['intelligence_status'], 'needs_review')
        self.assertFalse(brand_analysis_is_ready(analysis))

    def test_corrected_background_context_replaces_stale_markdown(self):
        stale_markdown = 'Mój Blog – Kolejna witryna WordPress\nReliable automation for customer conversations'
        business_profile = BusinessProfile.objects.create(
            user=self.user,
            workspace=self.workspace,
            website_url='https://staffinit.com/',
            editable_markdown=stale_markdown,
            profile={'name': 'Mój Blog', 'services': ['AI inbox'], 'source_confidence': {'status': 'needs_review'}},
        )
        brand = BrandSetting.objects.create(
            user=self.user,
            workspace=self.workspace,
            business_profile=business_profile,
            brand_context={'name': 'Mój Blog', 'services': ['AI inbox']},
        )
        corrected = fast_brand_analysis_from_crawl({
            'root_url': 'https://staffinit.com/',
            'pages': [{
                'url': 'https://staffinit.com/about-company/',
                'type': 'about',
                'title': 'StaffInIT - Success-Fee IT Recruitment Agency',
                'text': STAFFINIT_ABOUT_HTML,
                'source_quality': 95,
            }],
            'images': [],
        })
        business_profile.profile = corrected
        business_profile.services = corrected['services']
        business_profile.audience = corrected['audience']
        business_profile.keywords = corrected['keywords']
        business_profile.editable_markdown = render_profile_markdown({
            'name': corrected['name'],
            'positioning': corrected['market_positioning'],
            'industry': corrected['industry'],
            'business_type': corrected['business_type'],
            'services': corrected['services'],
            'audience': corrected['audience'],
            'keywords': corrected['keywords'],
            'domain': 'https://staffinit.com/',
            'proof_points': corrected['services'],
            'about': corrected.get('about', {}),
            'intelligence_status': corrected.get('intelligence_status'),
            'source_confidence': corrected.get('source_confidence'),
        })
        business_profile.save()

        with patch('content_engine.views.discover_competitors', return_value=[]):
            run_brand_intelligence_side_effects(
                self.user,
                self.workspace,
                business_profile,
                brand,
                {'root_url': 'https://staffinit.com/', 'pages': [], 'images': []},
                corrected,
            )
        sync_user_profile_from_business_profile(self.user, self.workspace, business_profile, brand, corrected)

        brand.refresh_from_db()
        self.profile.refresh_from_db()
        self.assertEqual(brand.brand_context['name'], 'StaffInIT')
        self.assertIn('StaffInIT', self.profile.markdown)
        self.assertNotIn('Mój Blog', self.profile.markdown)
        self.assertNotIn('Reliable automation for customer conversations', self.profile.markdown)
