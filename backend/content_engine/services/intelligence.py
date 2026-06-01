import re
import json
from collections import Counter
from io import BytesIO
from urllib.parse import parse_qs, unquote, urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup
from django.db import IntegrityError
from django.utils import timezone
from PIL import Image
from playwright.sync_api import sync_playwright

from auth_user.models import ImageUrl
from utils.automation import launch_browser
from utils.chatbot import gemini_json

from content_engine.models import MediaAsset

from .website import normalize_url, render_profile_markdown


SOCIAL_HOSTS = ('facebook.com', 'instagram.com', 'linkedin.com', 'x.com', 'twitter.com', 'youtube.com', 'tiktok.com')
INFO_TERMS = ('about', 'contact', 'pricing', 'price', 'shop', 'product', 'products', 'services', 'solutions', 'catalog', 'collection', 'store')
COMPANY_FORCED_PATHS = ('/', '/about', '/about-us', '/about-company', '/contact', '/services', '/careers', '/jobs')
ECOMMERCE_FORCED_PATHS = ('/shop', '/products', '/product', '/collections', '/collections/all', '/store', '/catalog')
TINY_IMAGE_LIMIT = 56
BAD_PAGE_TEXT_TERMS = (
    '[get]', ' 404', ': 404', 'not found', 'request failed', 'network error',
    'your browser does not support the video tag', 'page - ', 'api/page',
    'no categories available', 'browse all our categories',
)
BAD_BODY_TEXT_TERMS = (
    'sorry this page isn’t available',
    "sorry this page isn't available",
    "it seems we can't find what you're looking for",
    'it seems we can’t find what you’re looking for',
    'nothing found',
    'no results found',
)
BAD_TITLE_TERMS = ('page not found', '404', 'not found')
GENERIC_WORDPRESS_TITLES = (
    'mój blog – kolejna witryna wordpress',
    'moj blog – kolejna witryna wordpress',
    'mój blog - kolejna witryna wordpress',
    'moj blog - kolejna witryna wordpress',
    'just another wordpress site',
    'my blog',
)
NAV_TEMPLATE_TERMS = {
    'home', 'about', 'about our company', 'meet our team', 'employers', 'overview',
    'place job order', 'faqs', 'testimonials', 'solutions', 'job seekers',
    'job openings', 'apply now', 'contact us', 'appointment', 'learn more',
}
RECRUITMENT_SERVICE_LABELS = (
    'Direct Hire',
    'Contract to Hire',
    'Contract-to-Hire',
    'Payrolling',
    'Executive Search',
    'Candidate Sourcing',
    'Market Research & Talent Mapping',
    'Interview Coordination',
    'Candidate Evaluation & Shortlisting',
    'Shortlisting',
    'Offer Management',
    'Post-Hire Follow-Up',
)
RECRUITMENT_TERMS = (
    'recruitment', 'staffing', 'candidate', 'candidates', 'hire', 'hiring',
    'talent', 'job seekers', 'employers', 'career opportunities', 'direct hire',
    'contract to hire', 'payrolling', 'executive search', 'shortlisting',
)
AUTOMATION_POLLUTION_TERMS = (
    'reliable automation for customer conversations',
    'localized ai support for real business workflows',
    'simple way to improve response speed',
    'ai inbox',
    'customer conversation automation',
)
UTILITY_IMAGE_TERMS = (
    'pixel', 'spacer', 'tracking', 'transparent', 'blank', 'placeholder', 'loader', 'loading',
    'spinner', 'sprite', 'favicon', 'apple-touch-icon', 'icon-', '/icons/', 'social-icon',
    'facebook', 'instagram', 'twitter', 'linkedin', 'youtube', 'tiktok', 'whatsapp',
    'payment', 'visa', 'mastercard', 'amex', 'sslcommerz', 'bkash', 'nagad', 'rocket',
    'play-store', 'app-store', 'badge', 'flag', 'language', 'arrow', 'chevron', 'close',
)
RESIZE_QUERY_KEYS = {
    'w', 'width', 'h', 'height', 'q', 'quality', 'fit', 'crop', 'auto', 'format', 'fm',
    'ixlib', 'dpr', 'resize', 'size', 's', 'ssl', 'tr', 'transform', 'v',
}
MEANINGFUL_LABELS = {'logo', 'product', 'hero', 'team', 'workspace', 'testimonial'}


def clean_url(url):
    value = normalize_url(url)
    parsed = urlparse(value)
    path = re.sub(r'/+', '/', parsed.path or '/')
    normalized = parsed._replace(path=path.rstrip('/') or '/', fragment='')
    return urlunparse(normalized)


def image_fingerprint(url):
    parsed = urlparse(clean_url(url))
    if parsed.path.endswith('/_next/image') or parsed.path.endswith('/image'):
        target = (parse_qs(parsed.query or '').get('url') or [''])[0]
        if target:
            return image_fingerprint(unquote(target))
    query = []
    for part in (parsed.query or '').split('&'):
        if not part:
            continue
        key = part.split('=', 1)[0].lower()
        if key in RESIZE_QUERY_KEYS or key.startswith(('utm_', 'fbclid', 'gclid')):
            continue
        query.append(part)
    path = re.sub(r'[-_](?:\d{2,5}x\d{2,5}|\d{2,5}w|\d{2,5}h|scaled|copy)(?=\.)', '', parsed.path, flags=re.I)
    path = re.sub(r'@\d+x(?=\.)', '', path, flags=re.I)
    return urlunparse(parsed._replace(path=path, query='&'.join(query), fragment='')).lower()


def canonical_image_url(src, page_url):
    raw = str(src or '').strip()
    if not raw:
        return ''
    absolute = urljoin(page_url, raw)
    parsed = urlparse(absolute)
    if parsed.path.endswith('/_next/image') or parsed.path.endswith('/image'):
        target = (parse_qs(parsed.query or '').get('url') or [''])[0]
        if target:
            absolute = urljoin(page_url, unquote(target))
    return clean_url(absolute)


def is_utility_image(url, blob='', width=0, height=0, label=''):
    lowered = f'{url} {blob}'.lower()
    if lowered.startswith('data:'):
        return True
    if any(term in lowered for term in UTILITY_IMAGE_TERMS) and label != 'logo':
        return True
    if label != 'logo':
        if width and height and (width < TINY_IMAGE_LIMIT or height < TINY_IMAGE_LIMIT):
            return True
        if width and height and (width * height < 9000):
            return True
    return False


def image_score(image):
    label = image.get('label') or 'section'
    score = {
        'product': 110,
        'logo': 95,
        'team': 82,
        'workspace': 76,
        'hero': 70,
        'testimonial': 62,
        'section': 35,
    }.get(label, 20)
    width = int(image.get('width') or 0)
    height = int(image.get('height') or 0)
    if width and height:
        score += min(35, (width * height) // 80000)
    alt = (image.get('alt') or image.get('description') or '').strip()
    if alt:
        score += 8
    return score


def filter_meaningful_images(images):
    best_by_key = {}
    for image in images or []:
        url = image.get('url')
        if not url:
            continue
        blob = ' '.join(str(image.get(key) or '') for key in ('url', 'alt', 'description', 'source_page'))
        label = image.get('label') or infer_image_label(blob, page_type_for_url(image.get('source_page') or ''), image.get('width') or 0, image.get('height') or 0)
        image = {**image, 'label': label}
        if is_utility_image(url, blob, int(image.get('width') or 0), int(image.get('height') or 0), label):
            continue
        key = image_fingerprint(url)
        existing = best_by_key.get(key)
        if not existing or image_score(image) > image_score(existing):
            best_by_key[key] = image
    deduped = list(best_by_key.values())
    products = [item for item in deduped if item.get('label') == 'product']
    logos = [item for item in deduped if item.get('label') == 'logo']
    if products:
        allowed = {'logo', 'product', 'hero'}
    else:
        allowed = {'logo', 'team', 'workspace', 'hero', 'testimonial'}
    filtered = [item for item in deduped if item.get('label') in allowed]
    if not filtered:
        filtered = sorted(deduped, key=image_score, reverse=True)[:24]
    filtered.sort(key=image_score, reverse=True)
    # Keep all meaningful product imagery, but cap generic hero/section spillover.
    product_count = sum(1 for item in filtered if item.get('label') == 'product')
    cap = max(36, product_count + len(logos) + 8)
    return filtered[:cap]


def same_host(url, root):
    return urlparse(url).netloc.lower().removeprefix('www.') == urlparse(root).netloc.lower().removeprefix('www.')


def is_internal_api_url(url):
    parsed = urlparse(url or '')
    host = parsed.netloc.lower()
    path = (parsed.path or '').lower()
    return host.startswith('api.') or '/api/' in path or path.startswith('/api')


def is_useful_profile_line(line):
    text = re.sub(r'\s+', ' ', line or '').strip()
    lower = text.lower()
    if not text or any(term in lower for term in BAD_PAGE_TEXT_TERMS):
        return False
    if re.search(r'https?://', text) and re.search(r'\b(?:404|api|error|failed)\b', lower):
        return False
    # Business profiles must stay clean English; non-English source snippets are
    # kept in the raw crawl snapshot/media metadata, not surfaced as services.
    ascii_letters = sum(1 for char in text if char.isascii() and char.isalpha())
    non_ascii = sum(1 for char in text if not char.isascii())
    if non_ascii > ascii_letters:
        return False
    return True


def page_type_for_url(url, text=''):
    lower = f'{url} {text}'.lower()
    if any(term in lower for term in ('shop', 'product', 'products', 'catalog')):
        return 'shop'
    if 'pricing' in lower or 'price' in lower:
        return 'pricing'
    if 'about' in lower or 'mission' in lower or 'vision' in lower:
        return 'about'
    if 'contact' in lower or 'address' in lower:
        return 'contact'
    return 'homepage'


def infer_image_label(blob, page_type='homepage', width=0, height=0):
    blob = (blob or '').lower()
    if any(term in blob for term in ('logo', 'brandmark', 'favicon')):
        return 'logo'
    if page_type == 'shop' or any(term in blob for term in (
        'product', 'shop', 'cart', 'price', 'buy', 'sku', 'collection', 'catalog',
        'dress', 'shirt', 'shoe', 'bag', 'fashion', 'wear', 'apparel', 'item',
        'sale', 'new-arrival', 'new arrival', 'variation', 'stock', 'quick view',
    )):
        return 'product'
    if any(term in blob for term in (
        'team', 'founder', 'co-founder', 'cofounder', 'people', 'person', 'staff',
        'director', 'owner', 'ceo', 'portrait', 'about',
    )):
        return 'team'
    if any(term in blob for term in ('testimonial', 'review', 'client', 'customer')):
        return 'testimonial'
    if any(term in blob for term in ('hero', 'banner', 'cover')) or width >= 900 or height >= 420:
        return 'hero'
    return 'section'


def extract_colors(page):
    colors = page.evaluate(
        """() => {
            const values = [];
            const push = (value) => {
              if (!value || value === 'transparent' || value === 'rgba(0, 0, 0, 0)') return;
              values.push(value);
            };
            for (const el of Array.from(document.querySelectorAll('body *')).slice(0, 900)) {
              const style = getComputedStyle(el);
              push(style.color);
              push(style.backgroundColor);
              push(style.borderColor);
            }
            return values;
        }"""
    )
    def to_hex(value):
        match = re.search(r'rgba?\((\d+),\s*(\d+),\s*(\d+)', value or '')
        if not match:
            return ''
        r, g, b = [max(0, min(255, int(part))) for part in match.groups()]
        if (r, g, b) in ((255, 255, 255), (0, 0, 0)):
            return ''
        return f'#{r:02x}{g:02x}{b:02x}'
    counts = Counter(filter(None, (to_hex(value) for value in colors)))
    return [color for color, _ in counts.most_common(8)]


def text_from_html(html):
    soup = BeautifulSoup(html or '', 'html.parser')
    for tag in soup(['script', 'style', 'noscript', 'svg', 'iframe']):
        tag.decompose()
    return '\n'.join(line.strip() for line in soup.get_text('\n').splitlines() if line.strip())


def normalized_text(value):
    return re.sub(r'\s+', ' ', str(value or '').strip()).lower()


def title_is_generic_placeholder(title):
    value = normalized_text(title)
    if not value:
        return False
    return value in GENERIC_WORDPRESS_TITLES


def title_is_bad(title):
    value = normalized_text(title)
    return bool(value and (any(term in value for term in BAD_TITLE_TERMS) or title_is_generic_placeholder(value)))


def text_has_bad_body(text):
    value = normalized_text(text)
    return any(term in value for term in BAD_BODY_TEXT_TERMS)


def meaningful_lines(text):
    lines = []
    seen = set()
    for raw in (text or '').splitlines():
        line = re.sub(r'\s+', ' ', raw).strip()
        key = line.lower()
        if not line or key in seen or key in NAV_TEMPLATE_TERMS:
            continue
        if not is_useful_profile_line(line):
            continue
        seen.add(key)
        lines.append(line)
    return lines


def source_quality_for_page(status_code, title, text, url=''):
    reasons = []
    score = 100
    try:
        status_int = int(status_code or 0)
    except (TypeError, ValueError):
        status_int = 0
    if status_int and status_int >= 400:
        reasons.append(f'bad_http_status:{status_int}')
        score -= 90
    if title_is_bad(title):
        reasons.append('bad_or_placeholder_title')
        score -= 45
    if text_has_bad_body(text):
        reasons.append('404_or_empty_result_body')
        score -= 75
    word_count = len(re.findall(r'\b[\w-]+\b', text or ''))
    if word_count < 80:
        reasons.append('too_little_text')
        score -= 35
    lines = meaningful_lines(text)
    if len(lines) < 3:
        reasons.append('too_few_meaningful_lines')
        score -= 25
    nav_count = sum(1 for raw in (text or '').splitlines() if normalized_text(raw) in NAV_TEMPLATE_TERMS)
    if nav_count >= max(10, len(lines) * 2):
        reasons.append('mostly_nav_or_template')
        score -= 20
    if is_internal_api_url(url):
        reasons.append('internal_api_url')
        score = 0
    score = max(0, min(100, score))
    return {
        'score': score,
        'is_valid': score >= 45 and not any(reason.startswith('bad_http_status') for reason in reasons) and '404_or_empty_result_body' not in reasons and not title_is_bad(title),
        'reasons': reasons,
        'word_count': word_count,
        'meaningful_line_count': len(lines),
    }


def build_page_record(url, html, status_code=200, final_url='', fallback_type='homepage'):
    soup = BeautifulSoup(html or '', 'html.parser')
    title = (soup.title.string if soup.title and soup.title.string else '') or ''
    text = text_from_html(html)
    page_url = clean_url(final_url or url)
    quality = source_quality_for_page(status_code, title, text, page_url)
    kind = page_type_for_url(page_url, text[:1200])
    if not quality['is_valid']:
        kind = 'excluded'
    return {
        'url': page_url,
        'type': kind or fallback_type,
        'title': title,
        'text': text[:12000],
        'http_status': status_code,
        'final_url': page_url,
        'source_quality': quality['score'],
        'quality_reasons': quality['reasons'],
        'word_count': quality['word_count'],
        'contact': extract_contact(text, html) if kind == 'contact' and quality['is_valid'] else {},
    }


def valid_analysis_pages(pages):
    return [
        page for page in pages or []
        if page.get('type') not in {'failed', 'excluded'}
        and int(page.get('source_quality') if page.get('source_quality') is not None else 100) >= 45
        and not is_internal_api_url(page.get('url') or '')
    ]


def site_appears_ecommerce_text(text):
    lower = normalized_text(text)
    ecommerce_terms = ('add to cart', 'cart', 'checkout', 'shop now', 'product category', 'sku', 'woocommerce', 'sale price')
    return any(term in lower for term in ecommerce_terms)


def extract_colors_from_html(html):
    values = re.findall(r'#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b', html or '')
    normalized = []
    for value in values:
        value = value.lower()
        if len(value) == 4:
            value = '#' + ''.join(ch * 2 for ch in value[1:])
        if value not in {'#ffffff', '#000000'}:
            normalized.append(value)
    return [color for color, _ in Counter(normalized).most_common(8)]


def dedupe_preserve(values, limit=12):
    result = []
    seen = set()
    for value in values or []:
        text = str(value or '').strip()
        key = text.lower()
        if not text or key in seen:
            continue
        seen.add(key)
        result.append(text)
        if len(result) >= limit:
            break
    return result


def is_brand_color(rgb):
    r, g, b = rgb
    if max(rgb) < 28 or min(rgb) > 235:
        return False
    if max(rgb) - min(rgb) < 18:
        return False
    return True


def dominant_colors_from_image(url, max_colors=5):
    try:
        response = requests.get(url, timeout=8, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        if len(response.content) > 4_000_000:
            return []
        image = Image.open(BytesIO(response.content)).convert('RGB')
        image.thumbnail((96, 96))
        counts = Counter()
        for r, g, b in image.getdata():
            if not is_brand_color((r, g, b)):
                continue
            # Quantize slightly so antialiasing does not split one brand color
            key = (round(r / 24) * 24, round(g / 24) * 24, round(b / 24) * 24)
            counts[key] += 1
        return [f'#{r:02x}{g:02x}{b:02x}' for (r, g, b), _ in counts.most_common(max_colors)]
    except Exception:
        return []


def derived_brand_colors(crawl):
    images = crawl.get('images', []) if isinstance(crawl, dict) else []
    priority_images = [
        image.get('url')
        for image in images
        if image.get('url') and image.get('label') in {'logo', 'product', 'hero'}
    ][:10]
    sampled = []
    for url in priority_images[:6]:
        sampled.extend(dominant_colors_from_image(url))
    return dedupe_preserve([*(crawl.get('colors') or []), *sampled], limit=12)


def visual_identity_fallback(analysis, crawl):
    name = analysis.get('name') or urlparse(crawl.get('root_url') or '').netloc.replace('www.', '') or 'The brand'
    industry = analysis.get('industry') or analysis.get('business_type') or 'its category'
    services = analysis.get('services') if isinstance(analysis.get('services'), list) else []
    products = analysis.get('product_structure') if isinstance(analysis.get('product_structure'), list) else []
    colors = derived_brand_colors(crawl)[:5]
    labels = Counter(image.get('label') for image in (crawl.get('images') or []) if image.get('label'))
    visual_sources = []
    if labels.get('logo'):
        visual_sources.append('consistent logo assets')
    if labels.get('product'):
        visual_sources.append('real product imagery')
    if labels.get('team'):
        visual_sources.append('people-led trust signals')
    if labels.get('hero'):
        visual_sources.append('homepage hero visuals')
    offer = ', '.join(services[:3] or products[:3]) or 'its primary offer'
    palette = ', '.join(colors) if colors else 'the extracted website palette'
    source_text = ', '.join(visual_sources) if visual_sources else 'website photography and brand interface details'
    return (
        f'{name} should feel specific to {industry}: practical, recognizable, and rooted in {offer}. '
        f'The visual system should use {palette} as recurring accents, keep the logo exact, and use {source_text} as reference material. '
        'Content should look like it belongs to this brand rather than generic stock marketing: clear product/service context, clean compositions, confident spacing, and visual proof that matches the website positioning.'
    )


def personalized_channel_voice(analysis):
    name = analysis.get('name') or 'the brand'
    industry = analysis.get('industry') or analysis.get('business_type') or 'the market'
    positioning = analysis.get('market_positioning') or f'{name} helps its audience solve a specific problem.'
    audience = analysis.get('audience') if isinstance(analysis.get('audience'), list) else []
    audience_text = ', '.join(audience[:3]) or 'the target customer'
    return {
        'facebook': {
            'tone': f'Warm, helpful, conversational, and commercially clear for {name}; explain the offer like a trusted local advisor.',
            'emotion': f'Reassurance, curiosity, and practical confidence for {audience_text}.',
            'character': f'A friendly brand operator who understands {industry} problems and makes the next step feel easy.',
            'syntax': 'Use a strong opening line, short paragraphs, clear benefits, one relatable example, and a comment-friendly question or CTA.',
            'language': f'Plain English matched to {audience_text}; avoid jargon unless the website positioning already uses it. Core positioning: {positioning[:220]}',
        },
        'instagram': {
            'tone': f'Visual, expressive, concise, and brand-proud for {name}; make each caption feel tied to the image.',
            'emotion': f'Aspirational but believable: desire, lifestyle fit, trust, and momentum for {audience_text}.',
            'character': 'A visual storyteller who turns products, people, and brand moments into scroll-stopping micro-stories.',
            'syntax': 'Lead with a vivid hook, use sensory details, keep lines compact, add a clear CTA, and use hashtags sparingly when useful.',
            'language': f'Natural English with brand-specific nouns from {industry}; keep it human and specific to the shown product or scene.',
        },
        'linkedin': {
            'tone': f'Professional, evidence-led, and authority-building for {name}; position the brand as a serious solution in {industry}.',
            'emotion': f'Credibility, clarity, ambition, and business confidence for decision makers in {audience_text}.',
            'character': 'A category expert who explains the business case, operational value, and strategic takeaway without sounding corporate-generic.',
            'syntax': 'Start with a clear thesis, add context or proof, explain the implication, then close with a practical takeaway or CTA.',
            'language': f'Business English grounded in the brand profile and positioning: {positioning[:220]}',
        },
        'x': {
            'tone': f'Sharp, direct, and high-signal for {name}; one clear idea per post.',
            'emotion': f'Urgency, curiosity, and confident usefulness for {audience_text}.',
            'character': 'A concise operator who spots friction, names the point quickly, and pushes the reader toward action.',
            'syntax': 'Short hook, tight sentence rhythm, no filler, no thread unless necessary, one CTA or memorable line.',
            'language': f'Plain, punchy English with brand-specific terms from {industry}; avoid vague hype.',
        },
    }


def pick_srcset(srcset):
    if not srcset:
        return ''
    parts = [part.strip() for part in str(srcset).split(',') if part.strip()]
    return parts[-1].split()[0] if parts else ''


def collect_json_images(value, result):
    if not value:
        return
    if isinstance(value, str):
        result.append(value)
    elif isinstance(value, list):
        for item in value:
            collect_json_images(item, result)
    elif isinstance(value, dict):
        if value.get('url') or value.get('contentUrl'):
            collect_json_images(value.get('url') or value.get('contentUrl'), result)
        for key, item in value.items():
            if re.search(r'image|logo|thumbnail', str(key), re.I):
                collect_json_images(item, result)


def extract_images_from_html(html, page_url, page_type):
    soup = BeautifulSoup(html or '', 'html.parser')
    candidates = []
    attrs = ('src', 'data-src', 'data-original', 'data-lazy-src', 'data-image', 'data-bg', 'data-zoom-image')
    for img in soup.find_all('img'):
        urls = [img.get(attr) for attr in attrs]
        urls.append(pick_srcset(img.get('srcset') or img.get('data-srcset')))
        parent_text = img.find_parent(['a', 'section', 'article', 'div'])
        for src in filter(None, urls):
            candidates.append({
                'src': src,
                'alt': img.get('alt') or img.get('aria-label') or '',
                'className': ' '.join(img.get('class') or []),
                'parentText': parent_text.get_text(' ', strip=True)[:220] if parent_text else '',
                'width': int(img.get('width') or 0) if str(img.get('width') or '').isdigit() else 0,
                'height': int(img.get('height') or 0) if str(img.get('height') or '').isdigit() else 0,
            })
    for source in soup.find_all('source'):
        src = pick_srcset(source.get('srcset') or source.get('data-srcset'))
        if src:
            candidates.append({'src': src, 'alt': source.get('aria-label') or '', 'className': ' '.join(source.get('class') or []), 'parentText': '', 'width': 0, 'height': 0})
    for meta in soup.find_all('meta'):
        name = (meta.get('property') or meta.get('name') or '').lower()
        if name in {'og:image', 'twitter:image'} and meta.get('content'):
            candidates.append({'src': meta['content'], 'alt': 'social preview image', 'className': 'meta-image', 'parentText': '', 'width': 1200, 'height': 630})
    for tag in soup.find_all(style=True):
        for match in re.findall(r'url\((["\']?)(.*?)\1\)', tag.get('style') or '', flags=re.I):
            src = match[1] if isinstance(match, tuple) else match
            if src:
                candidates.append({
                    'src': src,
                    'alt': tag.get('aria-label') or '',
                    'className': ' '.join(tag.get('class') or []),
                    'parentText': tag.get_text(' ', strip=True)[:220],
                    'width': 0,
                    'height': 0,
                })
    structured_urls = []
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            collect_json_images(json.loads(script.get_text() or '{}'), structured_urls)
        except Exception:
            continue
    for src in structured_urls:
        candidates.append({'src': src, 'alt': 'structured image', 'className': 'json-ld-image', 'parentText': '', 'width': 0, 'height': 0})

    result = []
    for item in candidates:
        src = canonical_image_url(item.get('src') or '', page_url)
        if not src.startswith(('http://', 'https://')):
            continue
        lowered_src = src.lower()
        if lowered_src.startswith('data:') or any(term in lowered_src for term in ('pixel', 'spacer', 'tracking', 'transparent')):
            continue
        blob = ' '.join(str(item.get(key) or '') for key in ('src', 'alt', 'className', 'parentText')).lower()
        width = int(item.get('width') or 0)
        height = int(item.get('height') or 0)
        label = infer_image_label(blob, page_type, width, height)
        if lowered_src.endswith('.svg') and label != 'logo':
            continue
        if label in ('logo', 'product', 'hero', 'team', 'testimonial') or width >= TINY_IMAGE_LIMIT or height >= TINY_IMAGE_LIMIT or width == 0:
            result.append({
                'url': clean_url(src),
                'source_page': page_url,
                'label': label,
                'alt': item.get('alt') or '',
                'width': width,
                'height': height,
            })
    seen = set()
    deduped = []
    for image in result:
        if image['url'] in seen:
            continue
        seen.add(image['url'])
        deduped.append(image)
    return deduped


def extract_contact(text, html):
    emails = sorted(set(re.findall(r'[\w.\-+]+@[\w.\-]+\.\w+', text or '')))
    phones = sorted(set(re.findall(r'(?:\+?\d[\d\s().-]{7,}\d)', text or '')))[:8]
    soup = BeautifulSoup(html or '', 'html.parser')
    socials = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        host = urlparse(href).netloc.lower()
        if any(social in host for social in SOCIAL_HOSTS):
            socials.append(href)
    address_lines = [
        line for line in (text or '').splitlines()
        if any(term in line.lower() for term in ('road', 'street', 'avenue', 'floor', 'dhaka', 'bangladesh', 'address'))
    ][:5]
    return {
        'emails': emails[:8],
        'phones': phones,
        'address': '\n'.join(address_lines),
        'social_links': sorted(set(socials))[:12],
    }


def extract_images(page, root_url, page_url, page_type):
    images = page.evaluate(
        """() => {
          const pickSrcset = (srcset) => {
            if (!srcset) return '';
            const parts = String(srcset).split(',').map(x => x.trim()).filter(Boolean);
            return parts.length ? parts[parts.length - 1].split(/\\s+/)[0] : '';
          };
          const imageAttrs = ['src', 'data-src', 'data-original', 'data-lazy-src', 'data-image', 'data-bg', 'data-zoom-image'];
          const fromImages = Array.from(document.images).flatMap(img => {
            const urls = [
              img.currentSrc,
              img.src,
              ...imageAttrs.map(attr => img.getAttribute(attr)),
              pickSrcset(img.getAttribute('srcset') || img.getAttribute('data-srcset')),
            ].filter(Boolean);
            return urls.map(src => ({
              src,
              srcset: '',
              alt: img.alt || img.getAttribute('aria-label') || '',
              width: img.naturalWidth || img.width || 0,
              height: img.naturalHeight || img.height || 0,
              className: img.className || '',
              parentText: img.closest('a, section, article, div')?.innerText?.slice(0, 220) || ''
            }));
          }).filter(item => item.src || item.srcset);
          const sourceSets = Array.from(document.querySelectorAll('source[srcset]')).map(el => ({
            src: pickSrcset(el.getAttribute('srcset')),
            srcset: '',
            alt: el.getAttribute('aria-label') || '',
            width: 0,
            height: 0,
            className: el.className || '',
            parentText: el.closest('picture, section, article, div')?.innerText?.slice(0, 220) || ''
          })).filter(item => item.src);
          const backgrounds = Array.from(document.querySelectorAll('body *')).map(el => {
            const style = getComputedStyle(el);
            const match = /url\\(["']?([^"')]+)["']?\\)/.exec(style.backgroundImage || '');
            const rect = el.getBoundingClientRect();
            return match ? {
              src: match[1],
              srcset: '',
              alt: el.getAttribute('aria-label') || '',
              width: Math.round(rect.width || 0),
              height: Math.round(rect.height || 0),
              className: el.className || '',
              parentText: (el.innerText || '').slice(0, 180)
            } : null;
          }).filter(Boolean);
          const linkedImages = Array.from(document.querySelectorAll('a[href]')).map(a => ({
            src: a.href,
            srcset: '',
            alt: (a.innerText || a.getAttribute('aria-label') || '').trim(),
            width: 0,
            height: 0,
            className: a.className || '',
            parentText: a.closest('section, article, div')?.innerText?.slice(0, 220) || ''
          })).filter(item => /\\.(png|jpe?g|webp|avif|gif|svg)(\\?|$)/i.test(item.src));
          const meta = Array.from(document.querySelectorAll('meta[property="og:image"], meta[name="twitter:image"]')).map(el => ({
            src: el.getAttribute('content') || '',
            srcset: '',
            alt: 'social preview image',
            width: 1200,
            height: 630,
            className: 'meta-image',
            parentText: ''
          })).filter(item => item.src);
          const jsonImages = [];
          const collect = (value) => {
            if (!value) return;
            if (typeof value === 'string') {
              jsonImages.push(value);
            } else if (Array.isArray(value)) {
              value.forEach(collect);
            } else if (typeof value === 'object') {
              if (value.url || value.contentUrl) collect(value.url || value.contentUrl);
              Object.keys(value).forEach(key => {
                if (/image|logo|thumbnail/i.test(key)) collect(value[key]);
              });
            }
          };
          Array.from(document.querySelectorAll('script[type="application/ld+json"]')).forEach(script => {
            try {
              const parsed = JSON.parse(script.textContent || '{}');
              collect(parsed);
            } catch (e) {}
          });
          const structured = jsonImages.map(src => ({
            src,
            srcset: '',
            alt: 'structured image',
            width: 0,
            height: 0,
            className: 'json-ld-image',
            parentText: ''
          }));
          return [...fromImages, ...sourceSets, ...backgrounds, ...linkedImages, ...meta, ...structured];
        }"""
    )
    result = []
    for item in images:
        src = item.get('src') or ''
        if not src and item.get('srcset'):
            src = str(item.get('srcset')).split(',')[-1].strip().split(' ')[0]
        src = urljoin(page_url, src)
        if not src.startswith(('http://', 'https://')):
            continue
        lowered_src = src.lower()
        if lowered_src.startswith('data:') or any(term in lowered_src for term in ('pixel', 'spacer', 'tracking', 'transparent')):
            continue
        blob = ' '.join(str(item.get(key) or '') for key in ('src', 'alt', 'className', 'parentText')).lower()
        width = int(item.get('width') or 0)
        height = int(item.get('height') or 0)
        label = infer_image_label(blob, page_type, width, height)
        if lowered_src.endswith('.svg') and label != 'logo':
            continue
        if label in ('logo', 'product', 'hero', 'team', 'testimonial') or width >= TINY_IMAGE_LIMIT or height >= TINY_IMAGE_LIMIT or (width == 0 and height == 0 and page_type in ('shop', 'home')):
            result.append({
                'url': clean_url(src),
                'source_page': page_url,
                'label': label,
                'alt': item.get('alt') or '',
                'width': width,
                'height': height,
            })
    seen = set()
    deduped = []
    for image in result:
        if image['url'] in seen:
            continue
        seen.add(image['url'])
        deduped.append(image)
    return deduped


def scroll_page(page):
    try:
        page.evaluate(
            """async () => {
              await new Promise(resolve => {
                let steps = 0;
                const timer = setInterval(() => {
                  window.scrollBy(0, Math.max(500, Math.floor(window.innerHeight * 0.85)));
                  steps += 1;
                  if (steps >= 10 || window.scrollY + window.innerHeight >= document.body.scrollHeight - 8) {
                    clearInterval(timer);
                    resolve();
                  }
                }, 180);
              });
              window.scrollTo(0, 0);
            }"""
        )
        page.wait_for_timeout(500)
    except Exception:
        pass


def discover_links(page, root_url):
    anchors = page.evaluate(
        """() => Array.from(document.querySelectorAll('a[href]')).map(a => ({
            href: a.href,
            text: (a.innerText || a.ariaLabel || '').trim()
        }))"""
    )
    page_text = ''
    try:
        page_text = page.evaluate("() => document.body?.innerText || ''")
    except Exception:
        page_text = ''
    found = {clean_url(root_url)}
    scored = []
    for item in anchors:
        href = item.get('href') or ''
        if not href.startswith(('http://', 'https://')) or is_internal_api_url(href) or not same_host(href, root_url):
            continue
        cleaned = clean_url(href)
        if is_internal_api_url(cleaned):
            continue
        if cleaned in found:
            continue
        label = f'{cleaned} {item.get("text", "")}'.lower()
        score = sum(1 for term in INFO_TERMS if term in label)
        if score:
            scored.append((score, len(cleaned), cleaned))
            found.add(cleaned)
    forced_paths = list(COMPANY_FORCED_PATHS)
    if site_appears_ecommerce_text(page_text):
        forced_paths.extend(ECOMMERCE_FORCED_PATHS)
    for path in forced_paths:
        forced = clean_url(urljoin(root_url, path))
        if same_host(forced, root_url) and forced not in found:
            score = 3 if any(term in path for term in ('about', 'contact', 'services', 'careers', 'jobs')) else 1
            scored.append((score, len(forced), forced))
            found.add(forced)
    scored.sort(key=lambda row: (-row[0], row[1]))
    return [root_url] + [url for _, _, url in scored[:18]]


def discover_links_from_html(html, root_url):
    soup = BeautifulSoup(html or '', 'html.parser')
    page_text = text_from_html(html)
    found = {clean_url(root_url)}
    scored = []
    for a in soup.find_all('a', href=True):
        href = urljoin(root_url, a.get('href') or '')
        if not href.startswith(('http://', 'https://')) or is_internal_api_url(href) or not same_host(href, root_url):
            continue
        cleaned = clean_url(href)
        if is_internal_api_url(cleaned):
            continue
        if cleaned in found:
            continue
        label = f'{cleaned} {a.get_text(" ", strip=True)}'.lower()
        score = sum(1 for term in INFO_TERMS if term in label)
        if score:
            scored.append((score, len(cleaned), cleaned))
            found.add(cleaned)
    forced_paths = list(COMPANY_FORCED_PATHS)
    if site_appears_ecommerce_text(page_text):
        forced_paths.extend(ECOMMERCE_FORCED_PATHS)
    for path in forced_paths:
        forced = clean_url(urljoin(root_url, path))
        if same_host(forced, root_url) and forced not in found:
            score = 3 if any(term in path for term in ('about', 'contact', 'services', 'careers', 'jobs')) else 1
            scored.append((score, len(forced), forced))
            found.add(forced)
    scored.sort(key=lambda row: (-row[0], row[1]))
    return [root_url] + [url for _, _, url in scored[:18]]


def crawl_website_static(url, max_pages=6):
    root_url = clean_url(url)
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    })
    pages = []
    images = []
    response = session.get(root_url, timeout=(5, 8), allow_redirects=True)
    response.raise_for_status()
    if is_internal_api_url(response.url):
        raise ValueError(f'Skipping internal API redirect: {response.url}')
    root_url = clean_url(response.url)
    root_html = response.text
    discovered_urls = [item for item in discover_links_from_html(root_html, root_url) if item != root_url]
    urls = [root_url, *discovered_urls][:max_pages]
    colors = extract_colors_from_html(root_html)
    for index, page_url in enumerate(urls):
        try:
            if is_internal_api_url(page_url):
                continue
            page_response = response if index == 0 else session.get(page_url, timeout=(4, 6), allow_redirects=True)
            html = page_response.text
            record = build_page_record(page_url, html, page_response.status_code, page_response.url)
            pages.append(record)
            if record['type'] != 'excluded':
                images.extend(extract_images_from_html(html, record['url'], record['type']))
                colors = list(dict.fromkeys([*colors, *extract_colors_from_html(html)]))[:12]
        except Exception as exc:
            pages.append({'url': page_url, 'type': 'failed', 'title': '', 'text': '', 'error': str(exc)})
    seen = set()
    deduped_images = []
    for image in images:
        key = image_fingerprint(image.get('url'))
        if not key or key in seen:
            continue
        seen.add(key)
        deduped_images.append(image)
    return {'root_url': root_url, 'pages': pages, 'images': filter_meaningful_images(deduped_images), 'colors': colors}


def crawl_website(url, max_pages=8):
    root_url = clean_url(url)
    pages = []
    images = []
    try:
        with sync_playwright() as playwright:
            browser = launch_browser(playwright)
            try:
                context = browser.new_context(ignore_https_errors=True, viewport={'width': 1440, 'height': 1100})
                context.set_default_timeout(12000)
                context.set_default_navigation_timeout(18000)
                page = context.new_page()
                page.goto(root_url, wait_until='domcontentloaded', timeout=18000)
                scroll_page(page)
                urls = discover_links(page, root_url)[:max_pages]
                colors = extract_colors(page)
                for page_url in urls:
                    try:
                        if is_internal_api_url(page_url):
                            continue
                        nav_response = page.goto(page_url, wait_until='domcontentloaded', timeout=18000)
                        scroll_page(page)
                        html = page.content()
                        status_code = nav_response.status if nav_response else 200
                        record = build_page_record(page_url, html, status_code, page.url)
                        pages.append(record)
                        if record['type'] != 'excluded':
                            images.extend(extract_images(page, root_url, record['url'], record['type']))
                        if page_url == root_url and record['type'] != 'excluded':
                            colors = list(dict.fromkeys([*colors, *extract_colors(page)]))[:12]
                    except Exception as exc:
                        pages.append({'url': page_url, 'type': 'failed', 'title': '', 'text': '', 'error': str(exc)})
            finally:
                browser.close()
    except Exception:
        return crawl_website_static(url, max_pages=min(max_pages, 6))
    seen = set()
    deduped_images = []
    for image in images:
        key = image_fingerprint(image.get('url'))
        if not key or key in seen:
            continue
        seen.add(key)
        deduped_images.append(image)
    return {'root_url': root_url, 'pages': pages, 'images': filter_meaningful_images(deduped_images), 'colors': colors}


def compact_pages(pages):
    return [
        {
            'url': page.get('url'),
            'type': page.get('type'),
            'title': page.get('title'),
            'text': (page.get('text') or '')[:3500],
            'contact': page.get('contact') or {},
            'source_quality': page.get('source_quality'),
        }
        for page in valid_analysis_pages(pages)
    ]


def analyze_image_catalog(images, brand_context=''):
    if not images:
        return images
    sample = [
        {
            'url': image.get('url'),
            'source_page': image.get('source_page'),
            'alt': image.get('alt'),
            'current_label': image.get('label'),
            'width': image.get('width'),
            'height': image.get('height'),
        }
        for image in images[:80]
    ]
    try:
        payload = gemini_json(
            f"""
Classify website images for a brand media library.

Brand/page context:
{brand_context[:4000]}

Images:
{sample}

Return JSON only:
{{"images": [{{"url": "same url", "label": "product|logo|hero|team|workspace|testimonial|section", "description": "short useful description"}}]}}
""".strip(),
            system_prompt='You classify website images for marketing reference use. Return strict JSON only.',
            fallback={'images': []},
        )
    except Exception:
        payload = {'images': []}
    rows = payload.get('images') if isinstance(payload, dict) else []
    by_url = {row.get('url'): row for row in rows if isinstance(row, dict) and row.get('url')}
    result = []
    for image in images:
        row = by_url.get(image.get('url')) or {}
        label = row.get('label')
        if label in {'product', 'logo', 'hero', 'team', 'workspace', 'testimonial', 'section'}:
            image = {**image, 'label': label, 'description': row.get('description') or image.get('alt') or ''}
        result.append(image)
    return filter_meaningful_images(result)


def keyword_fallback(text):
    words = re.findall(r'[A-Za-z][A-Za-z0-9-]{3,}', (text or '').lower())
    stop = {'that', 'with', 'from', 'this', 'your', 'have', 'will', 'about', 'into', 'their', 'they', 'them', 'more', 'business'}
    return [word for word, _ in Counter(w for w in words if w not in stop).most_common(16)]


def extract_about_statements(pages):
    about_text = '\n'.join(
        page.get('text') or ''
        for page in pages
        if page.get('type') == 'about' or any(term in (page.get('url') or '').lower() for term in ('about', 'mission', 'vision'))
    )
    lines = [
        re.sub(r'\s+', ' ', line).strip()
        for line in about_text.splitlines()
        if 24 < len(line.strip()) < 260 and is_useful_profile_line(line)
    ]
    def first_matching(*terms):
        for line in lines:
            lower = line.lower()
            if any(term in lower for term in terms):
                return line
        return ''
    story_lines = [
        line for line in lines
        if any(term in line.lower() for term in ('founded', 'started', 'journey', 'established', 'since', 'history', 'story'))
    ][:3]
    description = lines[0] if lines else ''
    return {
        'mission': first_matching('mission', 'purpose', 'we aim', 'we help', 'our goal'),
        'vision': first_matching('vision', 'future', 'become', 'to be the', 'aspire'),
        'brand_story': ' '.join(story_lines) or description,
        'company_description': description,
    }


def strip_brand_suffix(title):
    value = re.sub(r'\s+', ' ', str(title or '')).strip()
    if title_is_generic_placeholder(value) or title_is_bad(value):
        return ''
    value = re.sub(r'^(contact|about|services|careers|jobs)\s+', '', value, flags=re.I).strip()
    return re.sub(r'\s*[-–|]\s*.*$', '', value).strip()


def derive_business_name(pages, domain):
    domain_stem = re.sub(r'[^a-z0-9]+', '', (domain or '').split('.')[0].lower())
    title_name = strip_brand_suffix((pages[0] or {}).get('title') if pages else '')
    title_key = re.sub(r'[^a-z0-9]+', '', title_name.lower())
    if title_name and title_key not in {'myblog', 'mojblog', 'company', 'contact', 'about', 'services', 'careers', 'jobs'}:
        return title_name
    for line in meaningful_lines('\n'.join(page.get('text') or '' for page in pages)):
        for word in re.findall(r"[A-Z][A-Za-z0-9]*(?:[A-Z][A-Za-z0-9]*)?", line):
            if domain_stem and re.sub(r'[^a-z0-9]+', '', word.lower()) == domain_stem:
                return word
        match = re.search(r'\b([A-Z][A-Za-z]+(?:In|IT|AI|CRM|HR)[A-Za-z]*)\b', line)
        if match:
            return match.group(1)
    return domain or 'Business'


def recruitment_signal(text):
    lower = normalized_text(text)
    return sum(1 for term in RECRUITMENT_TERMS if term in lower)


def derive_services(pages, all_text, product_labels=None):
    product_labels = product_labels or []
    services = []
    if recruitment_signal(all_text) >= 2:
        lower = normalized_text(all_text)
        for label in RECRUITMENT_SERVICE_LABELS:
            if normalized_text(label).replace('-', ' ') in lower.replace('-', ' '):
                services.append('Contract-to-Hire' if label == 'Contract to Hire' else label)
        return dedupe_preserve(services, limit=10) or ['IT recruitment and staffing support']
    for page in pages:
        kind = page.get('type') or ''
        page_lines = [
            line.strip()
            for line in meaningful_lines(page.get('text') or '')
            if 20 < len(line.strip()) < 150
        ]
        if kind in {'shop', 'pricing', 'homepage', 'services', 'about'}:
            services.extend(page_lines[:8])
    services = dedupe_preserve(services, limit=8)
    if services:
        return services
    return dedupe_preserve(product_labels, limit=6) or ['Needs manual review']


def derive_industry_and_type(all_text, product_labels=None):
    product_labels = product_labels or []
    if recruitment_signal(all_text) >= 2:
        if any(term in normalized_text(all_text) for term in ('tech industry', 'technology', 'it staffing', 'it recruitment')):
            return 'IT recruitment and staffing', 'Recruitment agency'
        return 'Recruitment and staffing', 'Recruitment agency'
    if product_labels:
        return 'retail and ecommerce', 'online store'
    return 'service business', 'service business'


def derive_audience(all_text):
    if recruitment_signal(all_text) >= 2:
        return [
            'employers hiring tech talent',
            'HR teams and hiring managers',
            'companies needing IT recruitment support',
            'skilled technology professionals and job seekers',
        ]
    audience = ['website visitors and potential buyers']
    lower = normalized_text(all_text)
    if any(term in lower for term in ('wholesale', 'business', 'company', 'corporate')):
        audience.append('business buyers and decision makers')
    if site_appears_ecommerce_text(all_text):
        audience.append('online shoppers')
    return dedupe_preserve(audience, limit=6)


def validate_brand_analysis(analysis, crawl):
    analysis = analysis if isinstance(analysis, dict) else {}
    pages = valid_analysis_pages((crawl or {}).get('pages', []))
    text = '\n'.join(page.get('text') or '' for page in pages)
    lower_blob = normalized_text(' '.join([
        str(analysis.get('name') or ''),
        str(analysis.get('industry') or ''),
        str(analysis.get('business_type') or ''),
        str(analysis.get('market_positioning') or ''),
        ' '.join(str(item) for item in analysis.get('services', []) if item),
        ' '.join(str(item) for item in analysis.get('product_structure', []) if item),
    ]))
    warnings = []
    if not pages:
        warnings.append('no_valid_pages')
    if len(re.findall(r'\b[\w-]+\b', text)) < 120:
        warnings.append('insufficient_valid_source_text')
    if any(term in lower_blob for term in (*BAD_BODY_TEXT_TERMS, *GENERIC_WORDPRESS_TITLES, *AUTOMATION_POLLUTION_TERMS)):
        warnings.append('placeholder_or_polluted_profile_content')
    name = str(analysis.get('name') or '').strip()
    domain = urlparse((crawl or {}).get('root_url') or '').netloc.replace('www.', '')
    domain_stem = re.sub(r'[^a-z0-9]+', '', domain.split('.')[0].lower())
    name_key = re.sub(r'[^a-z0-9]+', '', name.lower())
    if not name or title_is_generic_placeholder(name) or name_key in {'business', 'myblog', 'mojblog'}:
        warnings.append('unsupported_business_name')
    elif name_key != domain_stem and name.lower() not in normalized_text(text):
        warnings.append('business_name_not_supported_by_source')
    services = [str(item).strip() for item in analysis.get('services', []) if str(item).strip()]
    if not services or services == ['Needs manual review']:
        warnings.append('missing_supported_services')
    if recruitment_signal(text) >= 2:
        category_blob = normalized_text(' '.join([str(analysis.get('industry') or ''), str(analysis.get('business_type') or ''), str(analysis.get('market_positioning') or ''), *services]))
        if not any(term in category_blob for term in ('recruit', 'staffing', 'hire', 'talent')):
            warnings.append('category_not_supported_by_recruitment_source')
    status_value = 'valid' if not warnings else 'needs_review'
    score = max(0, 100 - len(warnings) * 18)
    return {'status': status_value, 'score': score, 'warnings': warnings}


def apply_confidence(analysis, crawl):
    validation = validate_brand_analysis(analysis, crawl)
    analysis['source_confidence'] = validation
    analysis['intelligence_status'] = validation['status']
    analysis['source_warnings'] = validation['warnings']
    return analysis


def brand_analysis_is_ready(analysis):
    if not isinstance(analysis, dict):
        return False
    confidence = analysis.get('source_confidence') if isinstance(analysis.get('source_confidence'), dict) else {}
    if analysis.get('intelligence_status') == 'needs_review' or confidence.get('status') == 'needs_review':
        return False
    if competitor_review_text := normalized_text(' '.join(str(item) for item in analysis.get('services', []) if item)):
        if any(term in competitor_review_text for term in (*BAD_BODY_TEXT_TERMS, *AUTOMATION_POLLUTION_TERMS)):
            return False
    return bool(analysis.get('name') and analysis.get('services'))


def fast_brand_analysis_from_crawl(crawl):
    """Build a usable brand profile without blocking on an LLM call."""
    pages = valid_analysis_pages(crawl.get('pages', []))
    all_text = '\n'.join(page.get('text') or '' for page in pages)
    domain = urlparse(crawl.get('root_url') or '').netloc.replace('www.', '')
    lines = [
        line.strip()
        for line in all_text.splitlines()
        if len(line.strip()) > 24 and is_useful_profile_line(line)
    ]
    positioning = lines[0] if lines else 'Needs manual review: the submitted website did not provide enough high-quality source text.'
    keywords = keyword_fallback(all_text or domain)
    contact = {'emails': [], 'phones': [], 'address': '', 'social_links': []}
    for page in pages:
        page_contact = page.get('contact') or {}
        for key in ('emails', 'phones', 'social_links'):
            contact[key] = sorted(set([*contact[key], *page_contact.get(key, [])]))
        if page_contact.get('address') and not contact['address']:
            contact['address'] = page_contact['address']
    logo_urls = [image['url'] for image in crawl.get('images', []) if image.get('label') == 'logo'][:6]
    product_labels = [
        image.get('alt') or image.get('description') or image.get('label')
        for image in crawl.get('images', [])
        if image.get('label') == 'product'
    ][:8]
    name = derive_business_name(pages, domain)
    industry, business_type = derive_industry_and_type(all_text, product_labels)
    services = derive_services(pages, all_text, product_labels)
    audience = derive_audience(all_text)
    about = extract_about_statements(pages)
    base = {
        'name': name,
        'industry': industry,
        'business_type': business_type,
        'market_positioning': positioning,
        'tone': 'clear, helpful, and confident',
        'services': services,
        'audience': list(dict.fromkeys(audience)),
        'keywords': keywords,
        'about': {**about, 'company_description': about.get('company_description') or positioning},
        'contact': contact,
        'product_structure': list(dict.fromkeys(product_labels))[:8],
        'brand_style': {
            'colors': derived_brand_colors(crawl)[:10],
            'logos': logo_urls,
            'visual_identity': '',
        },
        'audience_profiles': [],
        'channel_voice': {},
        'competitor_seed_keywords': keywords[:6],
    }
    base['brand_style']['visual_identity'] = visual_identity_fallback(base, crawl)
    base['channel_voice'] = personalized_channel_voice(base)
    return apply_confidence(base, crawl)


def analyze_brand_from_crawl(crawl):
    pages = valid_analysis_pages(crawl.get('pages', []))
    all_text = '\n'.join(page.get('text') or '' for page in pages)
    domain = urlparse(crawl.get('root_url') or '').netloc.replace('www.', '')
    prompt = f"""
Analyze this crawled website and return a detailed brand intelligence JSON object.
Return all human-readable content in English only. Do not include failed crawl
URLs, API endpoints, 404 messages, browser fallback text, or diagnostic logs in
services, positioning, audience, keywords, or about fields.
If source pages are written in any non-English language, translate the meaning
into natural business English. Preserve brand names, addresses, product names,
and proper nouns, but do not copy non-English marketing paragraphs into the
saved profile, channel voice, or campaign context.

About/contact requirements:
- Prioritize About, About Us, Mission, Vision, Contact, store-location, and footer contact pages.
- Extract mission and vision when explicit.
- If mission or vision is not explicit, infer carefully from the company's own website copy and make it specific to the company.
- Use contact address, phone/email, social links, and location signals to ground market positioning and audience.

Brand style requirements:
- Extract brand colors from the website UI, logo colors, hero/product visuals, and repeated accents.
- Identify exact logo image URLs when present.
- Write visual_identity as a detailed personalized brand identity guide, not a generic one-line summary.

Channel voice requirements:
- Facebook, Instagram, LinkedIn, and X must be different and platform-native.
- Each field must be specific to this business, its audience, market positioning, and offer.
- Avoid copying the same tone/emotion/syntax across platforms.

Pages:
{compact_pages(pages)}

Return JSON only:
{{
  "name": "business name",
  "industry": "industry",
  "business_type": "business type",
  "market_positioning": "specific positioning",
  "tone": "tone",
  "services": ["service/product"],
  "audience": ["audience segment"],
  "keywords": ["keyword"],
  "about": {{"mission": "", "vision": "", "brand_story": "", "company_description": ""}},
  "contact": {{"emails": [], "phones": [], "address": "", "social_links": []}},
  "product_structure": ["product/service category"],
  "brand_style": {{"colors": ["#hex"], "logos": ["logo image url"], "visual_identity": "detailed personalized brand visual identity guide"}},
  "audience_profiles": [
    {{"name": "ICP name", "age_range": "", "location": "", "occupation": "", "pain_points": [], "frustrations": [], "goals": [], "behaviors": [], "buying_patterns": [], "awareness_level": ""}}
  ],
  "channel_voice": {{
    "facebook": {{"tone": "", "emotion": "", "character": "", "syntax": "", "language": ""}},
    "instagram": {{"tone": "", "emotion": "", "character": "", "syntax": "", "language": ""}},
    "linkedin": {{"tone": "", "emotion": "", "character": "", "syntax": "", "language": ""}},
    "x": {{"tone": "", "emotion": "", "character": "", "syntax": "", "language": ""}}
  }},
  "competitor_seed_keywords": ["search keyword"]
}}
""".strip()
    try:
        analysed = gemini_json(
            prompt,
            system_prompt=(
                'You are a senior website intelligence analyst. Extract only supported facts and return strict JSON. '
                'All human-readable values in the JSON must be written in English, translating source meaning when needed.'
            ),
            fallback=None,
        )
    except Exception:
        analysed = {}
    if not isinstance(analysed, dict):
        analysed = {}
    contact = {'emails': [], 'phones': [], 'address': '', 'social_links': []}
    for page in pages:
        page_contact = page.get('contact') or {}
        for key in ('emails', 'phones', 'social_links'):
            contact[key] = sorted(set(contact[key] + page_contact.get(key, [])))
        if page_contact.get('address') and not contact['address']:
            contact['address'] = page_contact['address']
    analysed.setdefault('name', domain or 'Business')
    analysed.setdefault('industry', '')
    analysed.setdefault('business_type', '')
    analysed.setdefault('market_positioning', '')
    analysed.setdefault('tone', 'clear, helpful, and confident')
    analysed.setdefault('services', [])
    analysed.setdefault('audience', [])
    analysed.setdefault('keywords', keyword_fallback(all_text))
    extracted_about = extract_about_statements(pages)
    analysed.setdefault('about', {})
    if not isinstance(analysed.get('about'), dict):
        analysed['about'] = {}
    for key, value in extracted_about.items():
        if value and not analysed['about'].get(key):
            analysed['about'][key] = value
    analysed.setdefault('contact', contact)
    brand_style = analysed.get('brand_style') if isinstance(analysed.get('brand_style'), dict) else {}
    logos = brand_style.get('logos') if isinstance(brand_style.get('logos'), list) else []
    image_logos = [image['url'] for image in crawl.get('images', []) if image.get('label') == 'logo']
    brand_style['logos'] = dedupe_preserve([*logos, *image_logos], limit=8)
    colors = brand_style.get('colors') if isinstance(brand_style.get('colors'), list) else []
    brand_style['colors'] = dedupe_preserve([*colors, *derived_brand_colors(crawl)], limit=12)
    visual_identity = str(brand_style.get('visual_identity') or '').strip()
    if len(visual_identity) < 120 or 'website-derived visual identity' in visual_identity.lower():
        brand_style['visual_identity'] = visual_identity_fallback(analysed, crawl)
    analysed['brand_style'] = brand_style
    channel_voice = analysed.get('channel_voice') if isinstance(analysed.get('channel_voice'), dict) else {}
    fallback_voice = personalized_channel_voice(analysed)
    normalized_voice = {}
    signatures = []
    for platform, defaults in fallback_voice.items():
        values = channel_voice.get(platform) if isinstance(channel_voice.get(platform), dict) else {}
        normalized = {
            key: str(values.get(key) or defaults[key]).strip()
            for key in ('tone', 'emotion', 'character', 'syntax', 'language')
        }
        if sum(len(normalized[key]) for key in normalized) < 120:
            normalized = defaults
        normalized_voice[platform] = normalized
        signatures.append(json.dumps(normalized, sort_keys=True))
    if len(set(signatures)) < len(normalized_voice):
        normalized_voice = fallback_voice
    analysed['channel_voice'] = normalized_voice
    if not analysed.get('contact'):
        analysed['contact'] = contact
    return apply_confidence(analysed, crawl)


def store_extracted_images(user, workspace, images):
    stored = []
    existing_by_key = {}
    duplicate_image_ids = []
    for existing in ImageUrl.objects.filter(user=user, workspace=workspace).order_by('id'):
        key = image_fingerprint(existing.image_url)
        if not key:
            continue
        if key in existing_by_key:
            duplicate_image_ids.append(existing.id)
        else:
            existing_by_key[key] = existing
    if duplicate_image_ids:
        ImageUrl.objects.filter(id__in=duplicate_image_ids).delete()

    existing_assets = {
        image_fingerprint(asset.url): asset
        for asset in MediaAsset.objects.filter(user=user, workspace=workspace, asset_type='image')
        if asset.url
    }
    for image in filter_meaningful_images(images):
        url = image.get('url')
        if not url:
            continue
        key = image_fingerprint(url)
        if not key:
            continue
        obj = existing_by_key.get(key)
        if not obj:
            try:
                obj = ImageUrl.objects.create(user=user, workspace=workspace, image_url=url)
                existing_by_key[key] = obj
            except IntegrityError:
                obj = ImageUrl.objects.filter(user=user, workspace=workspace, image_url=url).first()
        if obj:
            metadata = {
                'source_page': image.get('source_page') or '',
                'label': image.get('label') or '',
                'alt': image.get('alt') or '',
                'description': image.get('description') or '',
                'width': image.get('width') or 0,
                'height': image.get('height') or 0,
                'fingerprint': key,
            }
            asset = existing_assets.get(key) or MediaAsset.objects.filter(user=user, workspace=workspace, url=obj.image_url).first()
            if asset:
                asset.asset_type = 'image'
                asset.source = 'website'
                asset.url = obj.image_url
                asset.metadata = metadata
                asset.save(update_fields=['asset_type', 'source', 'url', 'metadata', 'updated_at'])
            else:
                asset = MediaAsset.objects.create(user=user, workspace=workspace, url=obj.image_url, asset_type='image', source='website', metadata=metadata)
            existing_assets[key] = asset
            stored.append({'id': str(obj.id), 'url': obj.image_url, 'source_page': image.get('source_page') or '', 'metadata': {key: value for key, value in image.items() if key != 'url'}})
    return stored


def competitor_prompt_from_context(brand_analysis, crawl=None, url=''):
    return f"""
Build a competitor analysis JSON from this business/competitor context.

URL:
{url}

Brand or scraped analysis:
{brand_analysis}

Crawled pages:
{compact_pages((crawl or {}).get('pages', []))}

Return JSON only:
{{
  "competitors": [
    {{
      "name": "competitor name",
      "website_url": "https://...",
      "pricing_model": "summary",
      "key_features": ["feature"],
      "differentiators": ["differentiator"],
      "swot": {{"strengths": [], "weaknesses": [], "opportunities": [], "threats": []}},
      "objection_handling": {{"why_users_choose_them": [], "counter_positioning": []}}
    }}
  ]
}}
""".strip()


def discover_competitors(brand_analysis):
    prompt = competitor_prompt_from_context(brand_analysis)
    try:
        payload = gemini_json(
            prompt,
            system_prompt=(
                'You are a competitive intelligence analyst. Return strict JSON only. '
                'Use well-known real competitors with real website URLs; never return placeholders.'
            ),
            google_search=False,
            fallback={'competitors': []},
        )
    except Exception:
        payload = {'competitors': []}
    competitors = payload.get('competitors') if isinstance(payload, dict) else []
    competitors = [item for item in competitors if isinstance(item, dict)]
    if competitors:
        return competitors
    try:
        payload = gemini_json(
            prompt,
            system_prompt='You are a competitive intelligence analyst. Use current market knowledge and Google Search grounding when useful. Return strict JSON only.',
            google_search=True,
            fallback={'competitors': []},
        )
    except Exception:
        payload = {'competitors': []}
    competitors = payload.get('competitors') if isinstance(payload, dict) else []
    competitors = [item for item in competitors if isinstance(item, dict)]
    if competitors:
        return competitors
    return []


def analyze_competitor_url(url):
    crawl = crawl_website(url, max_pages=8)
    brand_analysis = analyze_brand_from_crawl(crawl)
    try:
        payload = gemini_json(
            competitor_prompt_from_context(brand_analysis, crawl=crawl, url=url),
            system_prompt='You are a competitive intelligence analyst. Return one strict JSON competitor object inside competitors[].',
            google_search=True,
            fallback={'competitors': []},
        )
    except Exception:
        payload = {'competitors': []}
    competitors = payload.get('competitors') if isinstance(payload, dict) else []
    if competitors and isinstance(competitors[0], dict):
        return competitors[0], crawl
    return {
        'name': brand_analysis.get('name') or urlparse(url).netloc.replace('www.', ''),
        'website_url': clean_url(url),
        'pricing_model': '',
        'key_features': brand_analysis.get('services', []),
        'differentiators': [],
        'swot': {'strengths': [], 'weaknesses': [], 'opportunities': [], 'threats': []},
        'objection_handling': {'why_users_choose_them': [], 'counter_positioning': []},
    }, crawl
