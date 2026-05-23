import re
from collections import Counter
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from utils.chatbot import ChatGPT

ENGLISH_PROFILE_INSTRUCTION = (
    "Always write the final business profile in English. If the website source "
    "uses Bengali, Polish, Arabic, Spanish, or any other language, translate the "
    "meaning into natural business English. Keep brand names, product names, "
    "addresses, and proper nouns unchanged unless the site itself provides an "
    "English version."
)


def normalize_url(url):
    value = (url or '').strip()
    if value and not value.startswith(('http://', 'https://')):
        value = f'https://{value}'
    return value


def analyse_website(url):
    normalized = normalize_url(url)
    response = requests.get(
        normalized,
        timeout=20,
        headers={'User-Agent': 'VoiceSparkAI/1.0 local website analyzer'},
    )
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    for tag in soup(['script', 'style', 'noscript', 'svg']):
        tag.decompose()

    title = (soup.title.string if soup.title else '') or ''
    meta_description = ''
    meta_keywords = ''
    for meta in soup.find_all('meta'):
        name = (meta.get('name') or meta.get('property') or '').lower()
        if name in {'description', 'og:description'} and not meta_description:
            meta_description = meta.get('content') or ''
        if name == 'keywords':
            meta_keywords = meta.get('content') or ''

    headings = [h.get_text(' ', strip=True) for h in soup.find_all(['h1', 'h2', 'h3']) if h.get_text(strip=True)]
    paragraphs = [p.get_text(' ', strip=True) for p in soup.find_all('p') if len(p.get_text(strip=True)) > 30]
    list_items = [li.get_text(' ', strip=True) for li in soup.find_all('li') if 12 < len(li.get_text(strip=True)) < 180]
    buttons = [
        item.get_text(' ', strip=True)
        for item in soup.find_all(['a', 'button'])
        if 3 < len(item.get_text(strip=True)) < 90
    ]
    text_blob = ' '.join([title, meta_description, *headings, *paragraphs[:20], *list_items[:20], *buttons[:12]])
    words = re.findall(r'[A-Za-z][A-Za-z0-9-]{3,}', text_blob.lower())
    stop = {'that', 'with', 'from', 'this', 'your', 'have', 'will', 'about', 'into', 'their', 'they', 'them', 'more', 'for', 'and'}
    keywords = [word for word, _ in Counter(w for w in words if w not in stop).most_common(12)]
    if meta_keywords:
        keywords = [item.strip().lower() for item in meta_keywords.split(',') if item.strip()][:12] or keywords

    domain = urlparse(normalized).netloc.replace('www.', '')
    tone = infer_tone(text_blob)
    services = extract_services(headings, paragraphs, list_items, keywords, text_blob)
    audience = infer_audience(text_blob, domain)
    profile = {
        'name': title.strip() or domain,
        'positioning': meta_description.strip() or (paragraphs[0] if paragraphs else ''),
        'tone': tone,
        'services': services,
        'audience': audience,
        'keywords': keywords,
        'domain': domain,
        'headings': headings[:20],
        'paragraphs': paragraphs[:20],
        'proof_points': extract_proof_points(text_blob, paragraphs, list_items),
        'competitors': infer_competitors(text_blob, domain),
        'brand_personality': infer_brand_personality(text_blob, tone),
    }
    markdown = generate_ai_profile_markdown(profile) or render_profile_markdown(profile)
    return {
        'url': normalized,
        'tone': tone,
        'services': services,
        'audience': audience,
        'keywords': keywords,
        'profile': profile,
        'markdown': markdown,
        'source_snapshot': {
            'title': title,
            'meta_description': meta_description,
            'headings': headings[:20],
            'paragraphs': paragraphs[:20],
            'list_items': list_items[:20],
            'buttons': buttons[:12],
        },
    }


def infer_tone(text):
    lower = (text or '').lower()
    if any(term in lower for term in ['enterprise', 'compliance', 'security', 'scalable']):
        return 'professional and authoritative'
    if any(term in lower for term in ['friendly', 'community', 'family', 'local']):
        return 'warm and conversational'
    if any(term in lower for term in ['luxury', 'premium', 'exclusive']):
        return 'premium and refined'
    return 'clear, helpful, and confident'


def infer_audience(text, domain):
    lower = (text or '').lower()
    audiences = []
    if any(term in lower for term in ['startup', 'founder', 'saas']):
        audiences.append('startup founders')
    if any(term in lower for term in ['business', 'company', 'team']):
        audiences.append('business teams')
    if any(term in lower for term in ['customer', 'client']):
        audiences.append('potential customers')
    return audiences or [f'visitors and buyers interested in {domain}']


def extract_services(headings, paragraphs, list_items, keywords, text):
    candidates = []
    service_terms = (
        'automation', 'chatbot', 'messenger', 'instagram', 'whatsapp', 'reply',
        'lead', 'order', 'support', 'inbox', 'crm', 'campaign', 'integration',
        'analytics', 'ai', 'customer', 'message'
    )
    for item in [*headings, *list_items, *paragraphs]:
        lower = item.lower()
        if any(term in lower for term in service_terms):
            cleaned = re.sub(r'\s+', ' ', item).strip(' -–|')
            if cleaned and cleaned not in candidates:
                candidates.append(cleaned)
    if candidates:
        return candidates[:8]

    lower = (text or '').lower()
    inferred = []
    if 'messenger' in lower:
        inferred.append('Messenger automation for customer conversations')
    if 'instagram' in lower:
        inferred.append('Instagram DM automation and response workflows')
    if 'whatsapp' in lower:
        inferred.append('WhatsApp automation for Bangla and Banglish customer replies')
    if 'chatbot' in lower or 'ai' in lower:
        inferred.append('AI chatbot setup for sales, support, and lead handling')
    if 'reply' in lower or 'customer' in lower:
        inferred.append('Automated customer reply management across social channels')
    if inferred:
        return inferred

    return [f'{keyword.title()} support and marketing workflow' for keyword in keywords[:5]]


def extract_proof_points(text, paragraphs, list_items):
    source = ' '.join([text or '', *paragraphs, *list_items])
    proof = []
    for match in re.findall(r'[^.]*\b(?:#\s*1|number\s*1|free|trial|bangla|banglish|24/7|automate|instant|customer)[^.]*[.]?', source, flags=re.I):
        cleaned = re.sub(r'\s+', ' ', match).strip(' .-')
        if 20 < len(cleaned) < 180 and cleaned not in proof:
            proof.append(cleaned)
    return proof[:6]


def infer_competitors(text, domain):
    lower = (text or '').lower()
    if any(term in lower for term in ['messenger', 'instagram', 'whatsapp', 'chatbot', 'automation']):
        return {
            'local': [
                'Bangladesh-based chatbot automation agencies',
                'Local social media management teams offering manual inbox support',
                'Freelance Messenger and WhatsApp automation providers',
            ],
            'national': [
                'International chatbot platforms such as Manychat and Chatfuel',
                'CRM and support automation tools with social messaging features',
                'AI customer support platforms serving ecommerce and service businesses',
            ],
        }
    return {
        'local': [f'Local providers serving customers around {domain}', 'Small agencies with similar service packages'],
        'national': ['Larger SaaS platforms in the same category', 'Established agencies with broader marketing automation offers'],
    }


def infer_brand_personality(text, tone):
    lower = (text or '').lower()
    values = ['clarity', 'speed', 'customer focus']
    if 'bangla' in lower or 'bangladesh' in lower:
        values = ['local relevance', 'fast response', 'practical automation']
    if 'ai' in lower or 'automation' in lower:
        archetype = 'The Efficient Innovator'
        voice = 'Direct, helpful, modern, and outcome-focused'
    else:
        archetype = 'The Trusted Guide'
        voice = f'{tone.title()}, practical, and easy to understand'
    return {'archetype': archetype, 'voice': voice, 'values': values}


def sentence_list(items, fallback):
    cleaned = []
    for item in items or []:
        if isinstance(item, dict):
            item = item.get('name') or item.get('title') or item.get('label') or item.get('url') or item.get('description') or ''
        text = re.sub(r'\s+', ' ', str(item or '')).strip()
        if text:
            cleaned.append(text)
    return cleaned or fallback


def compact_context(profile):
    return {
        'business_name': profile.get('name'),
        'website_domain': profile.get('domain'),
        'website_positioning': profile.get('positioning'),
        'tone': profile.get('tone'),
        'services': profile.get('services', [])[:10],
        'audience': profile.get('audience', [])[:8],
        'keywords': profile.get('keywords', [])[:15],
        'headings': profile.get('headings', [])[:20],
        'paragraphs': profile.get('paragraphs', [])[:14],
        'proof_points': profile.get('proof_points', [])[:8],
        'about': profile.get('about', {}),
        'contact': profile.get('contact', {}),
        'product_structure': profile.get('product_structure', [])[:12],
    }


def generate_ai_profile_markdown(profile):
    try:
        context = compact_context(profile)
        cg = ChatGPT()
        cg.create_client()
        cg.create_system_prompt(
            "You are a senior brand strategist. Return only clean Markdown. "
            "Use the supplied website facts only; do not invent unsupported statistics or fake testimonials. "
            "Every point must be personalized to this exact company. "
            + ENGLISH_PROFILE_INSTRUCTION
        )
        cg.send_users_message(f"""
Analyze this website extraction and generate a detailed editable brand profile.

Language requirement:
- {ENGLISH_PROFILE_INSTRUCTION}
- All section headings and all generated analysis must be English.
- Translate non-English website copy into English instead of copying it verbatim.
- Do not output mixed-language paragraphs unless preserving a proper noun or address.

Prioritize About and Contact page evidence. Use about.mission, about.vision,
about.brand_story, contact address/socials, product/category signals, and website
prominence wherever available. If mission or vision is not explicit, infer a
careful mission/vision from the company's own website facts and mark it as an
inferred statement without sounding generic.

The output must be rich and specific, not a short summary. Use these exact
section headings and do not add, remove, or rename sections:

## Business Name

Business name only.

## Business Overview & Positioning

**Core Identity:** specific company overview.

## Market Positioning

- **Primary Positioning:** "statement" - explanation.
- **Secondary Positioning:** "statement" - explanation.
- **Tertiary Positioning:** "statement" - explanation.

## Direct Competitors

- **Local Competitors:**
  - competitor
- **National Competitors:**
  - competitor

## Competitive Advantages

1. **Bold phrase** explanation.
2. **Bold phrase** explanation.
3. **Bold phrase** explanation.
4. **Bold phrase** explanation.

## Primary Customer Segments

- **Segment Name**
  - What they are seeking.
  - Decision makers.
  - Pain points.

## Top Revenue Generators (based on website prominence)

1. Product/service - why it appears important.

## Emerging Growth Areas

- Area 1
- Area 2
- Area 3

## Primary Value Drivers

- **Driver:** meaning for the customer.

## Emotional Benefits

- **Benefit:** what the customer feels.

## Brand Story

**The Journey:** narrative paragraph grounded in About page/company history if available.

**Mission Statement:** "one sentence"

**Vision Statement:** "one sentence"

## Brand Personality

- **Archetype:** archetype
- **Voice:** voice description
- **Values:** value1, value2, value3

Website extraction:
{context}
""")
        cg.create_chat_completion()
        message = cg.get_generated_message()
        if message and len(message.strip()) > 1400:
            return message.strip()
    except Exception as exc:
        print('Gemini business profile generation failed', type(exc).__name__)
    return ''


def render_profile_markdown(profile):
    """Render a fallback profile in English when AI enrichment is unavailable."""
    name = profile.get('name') or 'Business Profile'
    confidence = profile.get('source_confidence') if isinstance(profile.get('source_confidence'), dict) else {}
    if profile.get('intelligence_status') == 'needs_review' or confidence.get('status') == 'needs_review':
        warnings = confidence.get('warnings') or profile.get('source_warnings') or ['source confidence validation failed']
        return f"""## Business Name

{name}

## Analysis Status

Needs manual review.

## Why Review Is Needed

{chr(10).join(f'- {item}' for item in warnings)}

## Next Step

Review the submitted website URL and source pages, then rerun analysis after the website returns clear brand content.
""".strip()
    positioning = profile.get('positioning') or 'A focused business profile built from the submitted website.'
    services = sentence_list(profile.get('services', [])[:8], ['Service details should be refined by the user.'])
    audience = sentence_list(profile.get('audience', []), ['potential customers'])
    keywords = profile.get('keywords', [])
    proof_points = sentence_list(profile.get('proof_points', []), [
        f'The website positions {name} around a clear customer problem and a direct solution.',
        'The offer is designed to create a clear, useful outcome for its audience.',
    ])
    competitors = profile.get('competitors') or infer_competitors('', profile.get('domain', 'the market'))
    personality = profile.get('brand_personality') or infer_brand_personality('', profile.get('tone') or 'clear and helpful')
    primary_service = services[0]
    category = profile.get('industry') or profile.get('business_type') or 'its category'

    product_structure = sentence_list(profile.get('product_structure', [])[:8], services)
    about = profile.get('about') if isinstance(profile.get('about'), dict) else {}
    mission = about.get('mission') or f'Help customers choose {name} with confidence through quality, relevance, and dependable service.'
    vision = about.get('vision') or f'Become the most trusted choice in its category by staying close to customer needs and brand values.'
    story = about.get('brand_story') or (
        f'{name} serves its market by turning website-visible products, services, and proof points into a recognizable customer promise. '
        'The brand story should stay rooted in the real offer, the audience it serves, and the trust signals found on the website.'
    )
    audience_markdown = '\n'.join(
        f'- **{item}**\n  - Seeking {primary_service.lower()} and related support.\n  - Needs clear proof, fit, and a simple next step.'
        for item in audience[:5]
    )
    growth_markdown = '\n'.join(f'- {item}' for item in (product_structure[1:4] or services[1:4] or [primary_service]))

    return f"""## Business Name

{name}

## Business Overview & Positioning

**Core Identity:** {name} is positioned around {primary_service.lower()}. The business focuses on helping customers solve a specific operational or marketing problem with a clear, accessible offer. Based on the website, the brand should be presented as practical, direct, and focused on measurable customer outcomes.

**Website Positioning Summary:** {positioning}

## Market Positioning

- **Primary Positioning:** "{primary_service}" - positions the brand around a website-supported offer in {category}.
- **Secondary Positioning:** "{positioning[:140]}" - keeps the message grounded in the submitted website copy.
- **Tertiary Positioning:** "Practical support for {audience[0]}" - frames the offer around the audience identified from valid source pages.

## Direct Competitors

- **Local Competitors:**
{chr(10).join(f'  - {item}' for item in competitors.get('local', [])[:4])}
- **National and Global Competitors:**
{chr(10).join(f'  - {item}' for item in competitors.get('national', [])[:4])}

## Competitive Advantages

1. **Clear customer problem focus:** The website communicates a direct pain point and frames the product around reducing friction for customers and teams.
2. **Source-backed service clarity:** The offer can be explained through the actual services, categories, and proof points visible on the website.
3. **Practical implementation angle:** The brand can speak to speed, simplicity, and day-to-day usability using its real delivery model.
4. **Market fit:** The positioning can lean into buyer behavior and regional or industry needs only where those signals appear on the website.

## Primary Customer Segments

{audience_markdown}

## Top Revenue Generators (based on website prominence)
{chr(10).join(f'{index}. {item} - appears prominently in the website offer and should be treated as a priority content/revenue theme.' for index, item in enumerate(product_structure[:6], start=1))}

## Emerging Growth Areas

{growth_markdown}

## Primary Value Drivers

{chr(10).join(f'- **{item.split()[0].title() if item.split() else "Proof"}:** {item}' for item in proof_points[:5])}

## Emotional Benefits

- **Confidence:** Customers feel they are choosing a provider with a clear, relevant offer.
- **Relief:** Buyers can understand the service without sorting through vague claims.
- **Momentum:** The audience can move from research to action with less uncertainty.

## Brand Story

**The Journey:** {story}

**Mission Statement:** "{mission}"

**Vision Statement:** "{vision}"

## Brand Personality

- **Archetype:** {personality.get('archetype')}
- **Voice:** {personality.get('voice')}
- **Values:** {', '.join(personality.get('values', []))}
""".strip()
