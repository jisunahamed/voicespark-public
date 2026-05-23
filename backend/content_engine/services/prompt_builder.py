"""
prompt_builder.py — Structured Prompt Templates

Consumes context dict from context_builder and produces production-grade
prompts for Gemini. Each prompt type has strict sections.

AI-first: no hardcoded templates, no static topic arrays.
"""

import json
import logging
import re

from .context_builder import (
    PROMPT_VERSION,
    PIPELINE_VERSION,
    compact_json,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Platform rules
# ---------------------------------------------------------------------------

PLATFORM_PSYCHOLOGY = {
    'instagram': {
        'tone': 'visual storytelling, emotional, aspirational',
        'cta_style': 'soft CTA — "tap link", "save this", "share with someone"',
        'structure': 'hook line → story → CTA. Use line breaks.',
        'hashtag_strategy': '8-15 mixed hashtags (3 broad + 5 niche + 2 branded)',
        'max_length': 2200,
    },
    'facebook': {
        'tone': 'casual, conversational, community-building',
        'cta_style': 'engagement CTA — "tell us", "have you tried", "what do you think"',
        'structure': 'question or hook → value → CTA. Conversational.',
        'hashtag_strategy': '2-4 relevant hashtags only',
        'max_length': 5000,
    },
    'linkedin': {
        'tone': 'professional, authoritative, research-backed',
        'cta_style': 'professional CTA — "learn more", "connect with us", "read the full article"',
        'structure': 'bold opening line → insight → proof → CTA. Professional paragraphs.',
        'hashtag_strategy': '3-5 industry hashtags',
        'max_length': 3000,
    },
    'twitter': {
        'tone': 'punchy, concise, high-engagement',
        'cta_style': 'short CTA — "check it out", "RT if you agree", "link in bio"',
        'structure': 'one punchy statement or question. No fluff.',
        'hashtag_strategy': '1-3 hashtags max, integrated naturally',
        'max_length': 280,
    },
}

STYLE_DIRECTIVES = {
    'ultra_realistic': 'Ultra realistic commercial photography. Real humans, real places, authentic surfaces, natural skin texture, believable lighting, lens depth, no illustration.',
    'ultra-realistic': 'Ultra realistic commercial photography. Real humans, real places, authentic surfaces, natural skin texture, believable lighting, lens depth, no illustration.',
    'infographic': 'Modern infographic design. Clean visual hierarchy, diagrams, icons, data blocks, minimal readable labels, brand color system.',
    'cartoon_animated': 'Polished cartoon or animated illustration. Expressive characters, clean forms, brand colors, friendly storytelling, no photorealism.',
    'cartoon-animation': 'Polished cartoon or animated illustration. Expressive characters, clean forms, brand colors, friendly storytelling, no photorealism.',
    'product_studio': 'Premium product studio image. Sharp hero subject, clean background, controlled reflections, soft shadows, high-end lighting.',
    'product-studio': 'Premium product studio image. Sharp hero subject, clean background, controlled reflections, soft shadows, high-end lighting.',
    'editorial_lifestyle': 'Editorial lifestyle photography. Real people in contextual scenes, candid but composed, cinematic natural light, brand-specific moment.',
    'editorial-lifestyle': 'Editorial lifestyle photography. Real people in contextual scenes, candid but composed, cinematic natural light, brand-specific moment.',
}


# ---------------------------------------------------------------------------
# Image prompt builder
# ---------------------------------------------------------------------------

def build_advanced_image_prompt(context, topic='', platform='instagram', aspect_ratio='1:1'):
    """Build a production-grade image generation prompt from full context."""

    topic = topic or context.get('topic', '')
    brand_name = context.get('brand_name', 'the brand')
    colors = context.get('colors', [])
    logos = context.get('logos', [])
    font = context.get('font') or 'selected brand font'
    visual_style = context.get('visual_style', {})
    style_name = visual_style.get('name', '')
    style_prompt = visual_style.get('prompt', '') or STYLE_DIRECTIVES.get(visual_style.get('id', ''), '')
    services = context.get('services', [])
    audience = context.get('audience_text', '')
    competitors = context.get('competitors', [])
    campaign_theme = context.get('campaign_theme', '')
    campaign_cta = context.get('campaign_cta', '')
    language = context.get('language', 'English')
    existing_refs = context.get('existing_references', [])
    profile_summary = context.get('profile_summary', '')

    # Reference lock section
    ref_lock = ''
    product_refs = [r for r in existing_refs if (r.get('type') if isinstance(r, dict) else '') == 'product']
    logo_refs = [r for r in existing_refs if (r.get('type') if isinstance(r, dict) else '') == 'logo']
    if product_refs:
        ref_lock = f"""
[REFERENCE LOCK — PRODUCT IDENTITY PRESERVATION]
The following product reference(s) are IMMUTABLE identity anchors:
{', '.join(r.get('url', r) if isinstance(r, dict) else r for r in product_refs)}
You MUST preserve:
1. Product shape and silhouette
2. Product color family
3. Packaging structure
4. Label/branding placement
5. Material and texture
6. Product identity (do NOT replace with a different object)
7. Visual focus — product is the hero subject
If you cannot faithfully reproduce the product, return NO image rather than inventing a substitute.
"""

    # Competitor differentiation
    comp_section = ''
    if competitors:
        comp_summary = '; '.join(
            f"{c['name']}: gaps={', '.join(c.get('differentiators', []))}"
            for c in competitors[:3]
        )
        comp_section = f"\nCompetitor landscape (use ONLY for differentiation, never copy): {comp_summary}"

    # Overlay text
    overlay = _concise_overlay(topic, brand_name)

    prompt = f"""Create one premium, brand-aligned image for {brand_name}.

[BRAND IDENTITY]
- Brand: {brand_name}
- Brand colors: {', '.join(colors[:6]) or 'brand palette'}
- Logo references: {', '.join(logos[:3]) or 'none supplied'}
- Brand typography: {font}
- Brand tone: {context.get('tone', '') or 'professional and brand-aligned'}
- Output language for text: {language}

[CONTENT BRIEF]
- Topic: {topic}
- Platform: {platform}
- Aspect ratio: {aspect_ratio}
- Campaign theme: {campaign_theme or 'standalone content'}
- Campaign CTA: {campaign_cta or 'brand-appropriate action'}
- Content type: {context.get('content_type', 'social')}

[BUSINESS CONTEXT]
- Services: {', '.join(services[:4]) or 'use brand profile'}
- Audience: {audience or 'brand target customers'}
{comp_section}

[VISUAL DIRECTIVE]
- Style: {style_name or 'Brand aligned'}
- Execution: {style_prompt or 'Use brand visual identity.'}
- Match the selected style exactly. Do not mix styles.

[SUBJECT & COMPOSITION]
- Main subject tied to topic and brand business
- Clear visual hierarchy: hero subject → supporting elements → background
- Platform-optimized framing for {platform} at {aspect_ratio}
- Suggested text overlay if the concept benefits from visible text: "{overlay}"
- If visible text is used, keep it short, high-contrast, and placed where it will not cover products or faces.
- Typography: use the selected brand font "{font}" for any visible text. If exact font rendering is unavailable, use a visually similar typeface. Do not use random fonts that conflict with the brand style.

{ref_lock}
[LOGO RULES]
- If logo references supplied, include exact logo in image
- No redesign, no altered letters, no color changes, no warped shape
- Place as corner lockup, packaging mark, or natural brand placement

[NEGATIVE CONSTRAINTS]
- No watermarks, no random text, no fake logos, no clutter
- No malformed hands/faces, no unrelated objects
- No generic stock-photo output
- No visible AI artifacts
- Avoid generic software examples unless business sells software

Return ONLY the image generation prompt. No markdown, no explanation.""".strip()

    return prompt


# ---------------------------------------------------------------------------
# Caption prompt builder
# ---------------------------------------------------------------------------

def build_advanced_caption_prompt(context, topic='', platform='instagram'):
    """Build a platform-specific caption prompt. Each platform gets its own call."""

    topic = topic or context.get('topic', '')
    brand_name = context.get('brand_name', 'the brand')
    platform_rules = PLATFORM_PSYCHOLOGY.get(platform, PLATFORM_PSYCHOLOGY.get('instagram'))
    language = context.get('language', 'English')
    tone = context.get('tone', '')
    platform_voice = context.get('platform_voice', {})
    campaign_theme = context.get('campaign_theme', '')
    campaign_cta = context.get('campaign_cta', '')
    services = context.get('services', [])
    audience = context.get('audience_text', '')

    # Platform-specific tone override
    effective_tone = platform_voice.get('tone') or tone or platform_rules['tone']

    prompt = f"""Write one finished social media caption for {brand_name} on {platform}.

Brand context:
- Business: {brand_name}
- Services: {', '.join(services[:4]) or 'see brand profile'}
- Audience: {audience or 'brand target customers'}
- Brand tone: {effective_tone}
- Campaign: {campaign_theme or 'standalone content'}
- CTA direction: {campaign_cta or 'brand-appropriate action'}

Topic: {topic}

Platform rules for {platform}:
- Tone: {platform_rules['tone']}
- CTA style: {platform_rules['cta_style']}
- Structure: {platform_rules['structure']}
- Hashtag strategy: {platform_rules['hashtag_strategy']}
- Max length: {platform_rules['max_length']} characters

STRICT rules:
- Write in: {language}
- Make it specific to THIS brand, not generic marketing copy
- Match the platform psychology exactly
- Do not describe the image or mention visual elements
- No markdown, no bullet lists
- No generic filler like "Check it out!" without brand context
- Include relevant hashtags following the platform strategy

Return JSON only:
{{"caption": "finished caption text", "cta": "the CTA phrase used", "hashtags": ["tag1", "tag2"], "tone": "tone used", "reasoning": "why this caption works for {platform}"}}"""

    return prompt


def build_caption_edit_prompt(context, platform, previous_caption, instruction):
    """Delta-focused caption edit: change only what's requested, preserve the rest."""

    brand_name = context.get('brand_name', 'the brand')
    language = context.get('language', 'English')
    platform_rules = PLATFORM_PSYCHOLOGY.get(platform, PLATFORM_PSYCHOLOGY.get('instagram'))

    prompt = f"""Edit this existing caption for {brand_name} on {platform}.

Existing caption:
{previous_caption}

User instruction (change ONLY what's requested):
{instruction}

Platform: {platform}
Platform rules: {platform_rules['tone']}, max {platform_rules['max_length']} chars
Language: {language}

CRITICAL RULES:
- Preserve the original brand voice, message, and context
- Change ONLY what the user explicitly asked to change
- Do not rewrite the entire caption unless asked
- Keep the same general structure unless asked to change it

Return JSON only:
{{"caption": "edited caption", "cta": "CTA phrase", "hashtags": ["tag1"], "tone": "tone used", "reasoning": "what was changed and why"}}"""

    return prompt


# ---------------------------------------------------------------------------
# Image edit/regeneration prompt builder
# ---------------------------------------------------------------------------

def build_image_edit_prompt(context, instruction, existing_image_url=''):
    """Delta-focused image edit: modify only requested dimensions."""

    brand_name = context.get('brand_name', 'the brand')
    colors = context.get('colors', [])
    visual_style = context.get('visual_style', {})
    style_name = visual_style.get('name', '')
    language = context.get('language', 'English')

    prompt = f"""Edit the existing generated image for {brand_name}.

User instruction (apply ONLY this change):
{instruction}

PRESERVE (do NOT change unless explicitly asked):
- Product identity (shape, color, packaging, label)
- Brand logo (no redesign)
- Brand colors: {', '.join(colors[:4]) or 'current palette'}
- Visual style: {style_name or 'current style'}
- Overall composition and layout
- Text overlay content

CHANGE only:
- What the user explicitly requested above

Typography: use the selected brand font "{context.get('font') or 'brand font'}" for any visible text. If exact font rendering is unavailable, use a visually similar typeface.
Language for text: {language}

Return ONLY the image edit prompt. No markdown.""".strip()

    return prompt


def build_image_regen_prompt(context, topic='', platform='instagram', aspect_ratio='1:1'):
    """Context-preserving image regeneration. Not a random new image."""

    campaign_theme = context.get('campaign_theme', '')
    brand_name = context.get('brand_name', 'the brand')

    base_prompt = build_advanced_image_prompt(context, topic, platform, aspect_ratio)

    regen_prefix = f"""Regenerate the image for {brand_name}. This is a REGENERATION, not a new creation.

REGENERATION RULES:
- Maintain the same campaign theme: {campaign_theme or 'current campaign'}
- Keep the same topic direction: {topic or 'original topic'}
- Preserve brand identity, colors, and visual style
- Create a fresh visual variation, NOT a completely different concept
- If product references exist, they are immutable — preserve them exactly

"""
    return regen_prefix + base_prompt


# ---------------------------------------------------------------------------
# Campaign prompt builder (AI-driven, no hardcoded templates)
# ---------------------------------------------------------------------------

def build_campaign_prompt(context, plan, previous_weeks=None):
    """Fully AI-driven campaign prompt. No static templates."""

    brand_name = context.get('brand_name', 'the brand')
    services = context.get('services', [])
    audience = context.get('audience_text', '')
    competitors = context.get('competitors', [])
    language = context.get('language', 'English')
    visual_style = context.get('visual_style', {})
    posts_per_week = max(1, int(getattr(plan, 'posts_per_week', 5) or 1)) if plan else 5
    blog_count = max(0, int(getattr(plan, 'blog_posts_per_week', 0) or 0)) if plan else 0
    platforms = plan.platforms if plan and hasattr(plan, 'platforms') else ['facebook', 'instagram']

    # Campaign continuity
    continuity_section = ''
    if previous_weeks:
        prev_summary = '\n'.join(
            f"- Week {w.get('week_number', '?')}: {w.get('theme', 'no theme')} (funnel: {w.get('funnel_goal', '?')})"
            for w in previous_weeks[:4]
        )
        continuity_section = f"""
CAMPAIGN CONTINUITY:
The following weeks have already been planned. Your new weeks MUST continue the narrative arc:
{prev_summary}
- Maintain emotional progression
- Build on previous CTAs
- Advance the funnel logically
- Do NOT repeat previous week themes
"""

    comp_section = ''
    if competitors:
        comp_summary = '; '.join(
            f"{c['name']}: gaps={', '.join(c.get('differentiators', []))}"
            for c in competitors[:3]
        )
        comp_section = f"\nCompetitor landscape (exploit their gaps, never copy): {comp_summary}"

    prompt = f"""Create a 4-week AI-driven marketing campaign for {brand_name}.

Brand intelligence:
- Business: {brand_name}
- Services: {', '.join(services[:6]) or 'see brand profile'}
- Audience: {audience or 'brand target customers'}
- Platforms: {', '.join(platforms)}
- Visual style: {visual_style.get('name', '') or 'Brand aligned'}
- Tone: {context.get('tone', '') or 'professional'}
{comp_section}
{continuity_section}

REQUIREMENTS:
- Generate exactly 4 weeks
- Week 1: immediate first-week content
- Weeks follow a strategic marketing arc (awareness → engagement → conversion → retention)
- Each campaign must feel like a real marketing team briefed it
- Every title, theme, CTA, audience, and post topic MUST be specific to {brand_name}
- Each week needs exactly {posts_per_week} social prompts and {blog_count} blog prompts
- Write visible text in: {language}
- post_prompts[].topic must be a CONTENT TOPIC only — never an image prompt, camera direction, or caption draft

AI-FIRST RULES:
- Generate dynamic, unique campaign directions
- Do NOT use generic templates like "Brand Awareness Week" or "Engagement Week"
- Each week should have a specific, creative strategic angle
- Topics should be specific enough that a content team can brief from them
- CTAs should be concrete actions, not generic "Learn more"

Return JSON only:
{{
  "weeks": [
    {{
      "week_number": 1,
      "theme": "specific campaign title",
      "funnel_goal": "awareness|engagement|conversion|retention",
      "item_plan": {{
        "title": "campaign list title",
        "campaign_type": "specific campaign type",
        "theme": "detailed campaign strategy paragraph",
        "call_to_action": "specific, actionable CTA",
        "audience": "specific audience segment",
        "post_prompts": [
          {{"type": "social", "topic": "specific content topic", "platforms": {json.dumps(platforms)}, "status": "draft"}}
        ]
      }}
    }}
  ]
}}""".strip()

    return prompt


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _concise_overlay(topic, brand_name):
    """Generate concise overlay text for image."""
    text = re.sub(r'\s+', ' ', str(topic or '')).strip()
    text = re.sub(r'^\s*' + re.escape(str(brand_name or '')) + r'\s*[:\-]\s*', '', text, flags=re.I)
    # Remove generic marketing labels
    text = re.sub(
        r'\b(?:campaign\s+week\s+\d+|week\s+\d+|practical\s+post\s+\d+|social\s+post\s+idea\s+\d+)\b',
        '', text, flags=re.I,
    ).strip(' :-')
    generic = {'awareness', 'engagement', 'conversion', 'retention', 'brand awareness'}
    if text.lower() in generic:
        text = ''
    if not text:
        return 'See The Difference'
    words = text.split()
    if len(words) > 8:
        text = ' '.join(words[:8])
    return text[:80]


def build_topic_generation_prompt(context, social_count=5, blog_count=0):
    """Build prompt for first-week topic planning."""
    brand_name = context.get('brand_name', 'the brand')
    services = context.get('services', [])
    audience = context.get('audience_text', '')
    language = context.get('language', 'English')
    visual_style = context.get('visual_style', {})

    prompt = f"""Create a first-week content topic plan for {brand_name}.

Business and brand context:
- Business: {brand_name}
- Services: {', '.join(services[:6]) or 'see brand profile'}
- Audience: {audience or 'brand target customers'}
- Brand tone: {context.get('tone', '') or 'professional'}
- Visual style: {visual_style.get('name', '') or 'Brand aligned'}

RULES:
- Generate exactly {social_count} social media post topics.
- Generate exactly {blog_count} blog topics.
- Topics must be specific to this business, audience, and services.
- Follow the selected content language for all visible topic text: {language}.
- Each topic should feel unique and strategic (pain point, proof, education, story, etc.).
- Do not write captions or image prompts; only topic titles.

Return JSON only in this shape:
{{
  "social_topics": [
    {{"title": "topic title", "angle": "pain_point|education|proof|story|offer|objection|trust"}}
  ],
  "blog_topics": [
    {{"title": "blog topic title", "angle": "education|proof|guide|comparison"}}
  ]
}}""".strip()
    return prompt


def build_campaign_regen_prompt(context, current_item_plan, instruction):
    """Build prompt for instruction-based campaign regeneration."""
    brand_name = context.get('brand_name', 'the brand')
    language = context.get('language', 'English')

    prompt = f"""Regenerate this campaign plan for {brand_name} using the user's instruction.

Current campaign plan:
{compact_json(current_item_plan)}

User instruction (apply ONLY requested changes):
{instruction}

RULES:
- Return ONLY an updated item_plan JSON object.
- Improve title, campaign_type, theme, call_to_action, and post_prompts as requested.
- Preserve existing images and references unless asked to change them.
- Keep the same narrative arc unless asked to rewrite the strategy.
- post_prompts[].topic must be a CONTENT TOPIC only.
- Write visible text in: {language}.

Return JSON only."""
    return prompt


def build_blog_generation_prompt(context, topic='', blog_plan_item=None):
    """Build a production-grade blog generation prompt."""
    brand_name = context.get('brand_name', 'the brand')
    services = context.get('services', [])
    audience = context.get('audience_text', '')
    language = context.get('language', 'English')
    tone = context.get('tone', '')
    visual_style = context.get('visual_style', {})
    campaign_theme = context.get('campaign_theme', '')
    campaign_cta = context.get('campaign_cta', '')
    keywords = context.get('keywords', [])

    # Use blog plan item if provided (from campaign planner)
    plan_context = ''
    if blog_plan_item and isinstance(blog_plan_item, dict):
        plan_context = f"""
APPROVED BLOG PLAN CONTEXT:
- Title Idea: {blog_plan_item.get('title', '')}
- Outline: {', '.join(blog_plan_item.get('outline', []))}
- Sections: {json.dumps(blog_plan_item.get('sections', []))}
"""

    prompt = f"""Write a premium, publishable blog article for {brand_name}.

BRAND INTELLIGENCE:
- Business: {brand_name}
- Services: {', '.join(services[:6]) or 'see brand profile'}
- Audience: {audience or 'brand target customers'}
- Brand Tone: {tone or 'professional and authoritative'}
- Language: {language}
- Campaign Theme: {campaign_theme or 'brand authority'}
- Campaign CTA: {campaign_cta or 'brand-appropriate action'}
- SEO Keywords: {', '.join(keywords[:5]) or 'relevant industry terms'}
{plan_context}

TOPIC: {topic or (blog_plan_item.get('title') if blog_plan_item else 'Expert Industry Insight')}

REQUIREMENTS:
- Write in a natural, engaging, and authoritative voice.
- Ensure the content is SEO-optimized but remains highly readable.
- Structure with clear headings and paragraphs.
- Make it specific to this business—avoid generic filler.
- Differentiate from competitors by highlighting brand-unique value.
- Include a clear, compelling Call to Action at the end.
- Write visible text ONLY in: {language}.

VISUAL DIRECTION (for accompanying images):
- Visual Style: {visual_style.get('name', '') or 'Brand aligned'}
- Colors: {', '.join(context.get('colors', [])[:4])}
- Note: If no logo is available, focus on brand colors and visual style.

Return JSON only in this structure:
{{
  "title": "SEO-optimized blog title",
  "meta_title": "concise meta title",
  "meta_description": "compelling meta description",
  "slug": "url-friendly-slug",
  "intro": "engaging introduction paragraph",
  "sections": [
    {{
      "heading": "section heading",
      "content": "detailed section content"
    }}
  ],
  "faq": [
    {{"question": "relevant question", "answer": "helpful answer"}}
  ],
  "cta": "final call to action text",
  "keywords": ["key1", "key2"],
  "featured_image_prompt": "premium image generation prompt for the cover",
  "inline_image_prompt": "supporting image generation prompt for the article body",
  "social_snippets": {{
    "facebook": "engaging teaser",
    "instagram": "visual-first teaser",
    "linkedin": "professional teaser",
    "x": "punchy teaser"
  }}
}}""".strip()

    return prompt
