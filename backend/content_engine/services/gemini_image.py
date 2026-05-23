import base64
import concurrent.futures
import logging
import mimetypes
import os
import re
import time
import uuid
from io import BytesIO

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
import requests
from PIL import Image, ImageDraw, ImageFont
from utils.chatbot import GeminiError, classify_gemini_error

logger = logging.getLogger(__name__)


def configured_image_models():
    candidates = [
        os.getenv('GEMINI_IMAGE_MODEL', '').strip(),
        'gemini-3.1-flash-image-preview',
        'gemini-3-pro-image-preview',
    ]
    return [model for model in dict.fromkeys(candidates) if model]


IMAGE_MODELS = configured_image_models()

GEMINI_IMAGE_TIMEOUT_SECONDS = max(12, min(int(os.getenv('GEMINI_IMAGE_TIMEOUT_SECONDS', '45') or 45), 55))

STYLE_DIRECTIVES = {
    'ultra_realistic': 'Ultra realistic commercial photography. Real humans, real places, authentic surfaces, natural skin texture, believable lighting, lens depth, no illustration.',
    'ultra-realistic': 'Ultra realistic commercial photography. Real humans, real places, authentic surfaces, natural skin texture, believable lighting, lens depth, no illustration.',
    'infographic': 'Modern infographic design. Clean visual hierarchy, diagrams, icons, data blocks, minimal readable labels only when useful, brand color system.',
    'cartoon_animated': 'Polished cartoon or animated illustration. Expressive characters, clean vector-like forms, brand colors, friendly storytelling, no photorealism.',
    'cartoon-animation': 'Polished cartoon or animated illustration. Expressive characters, clean vector-like forms, brand colors, friendly storytelling, no photorealism.',
    'product_studio': 'Premium product studio image. Sharp hero subject, clean background, controlled reflections, soft shadows, high-end lighting.',
    'product-studio': 'Premium product studio image. Sharp hero subject, clean background, controlled reflections, soft shadows, high-end lighting.',
    'editorial_lifestyle': 'Editorial lifestyle photography. Real people in contextual scenes, candid but composed, cinematic natural light, brand-specific moment.',
    'editorial-lifestyle': 'Editorial lifestyle photography. Real people in contextual scenes, candid but composed, cinematic natural light, brand-specific moment.',
}

STYLE_ID_ALIASES = {
    'ultra-realistic': 'ultra_realistic',
    'cartoon-animation': 'cartoon_animated',
    'product-studio': 'product_studio',
    'editorial-lifestyle': 'editorial_lifestyle',
}


def normalize_style_id(value):
    raw = str(value or '').strip().lower()
    return STYLE_ID_ALIASES.get(raw) or raw.replace('-', '_')


def business_name_from_profile(profile):
    if not profile:
        return 'the brand'
    # This helper is used by both content_engine.BusinessProfile and
    # auth_user.UserProfile generation paths. Keep it defensive so regenerate
    # flows never fail because they received the wrong but still useful profile
    # object.
    raw_profile_data = getattr(profile, 'profile', None)
    profile_data = raw_profile_data if isinstance(raw_profile_data, dict) else {}
    for key in ('name', 'business_name', 'brand_name', 'title'):
        value = str(profile_data.get(key) or '').strip()
        if value:
            return value
    brand_voice = getattr(profile, 'brand_voice', None)
    if isinstance(brand_voice, dict):
        for key in ('business_name', 'brand_name', 'name'):
            value = str(brand_voice.get(key) or '').strip()
            if value:
                return value
        style = brand_voice.get('brand_style') if isinstance(brand_voice.get('brand_style'), dict) else {}
        value = str(style.get('brand_name') or style.get('name') or '').strip()
        if value:
            return value
    markdown = getattr(profile, 'editable_markdown', '') or getattr(profile, 'markdown', '') or ''
    for pattern in (
        r"^#\s+(.+?)(?:'s Business Profile| Business Profile)?\s*$",
        r"^(.+?)(?:'s Business Profile| Business Profile)\s*$",
    ):
        match = re.search(pattern, markdown, flags=re.MULTILINE)
        if match:
            value = match.group(1).strip()
            if value:
                return value
    website_url = getattr(profile, 'website_url', '') or ''
    if website_url:
        host = re.sub(r'^https?://', '', website_url).split('/')[0]
        return host.replace('www.', '').split('.')[0].replace('-', ' ').title()
    workspace = getattr(profile, 'workspace', None)
    workspace_name = str(getattr(workspace, 'name', '') or '').strip()
    if workspace_name:
        return workspace_name
    return 'the brand'


def normalize_reference_list(value):
    refs = []
    for item in value or []:
        if isinstance(item, str) and item.strip():
            refs.append(item.strip())
        elif isinstance(item, dict):
            candidate = item.get('url') or item.get('src') or item.get('image') or item.get('value') or item.get('hex') or item.get('color')
            if candidate:
                refs.append(str(candidate).strip())
    return refs


def first_reference_url(inspiration_images):
    for item in inspiration_images or []:
        if isinstance(item, str):
            candidate = item.strip()
            if candidate and not candidate.startswith('data:'):
                return candidate
        elif isinstance(item, dict):
            candidate = item.get('url') or item.get('src') or item.get('image') or item.get('value')
            if candidate:
                candidate = str(candidate).strip()
                if candidate and not candidate.startswith('data:'):
                    return candidate
    return None


def content_preferences_for_profile(profile):
    default = {
        'language': {'label': 'English'},
        'content_style': {},
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
        return {
            'language': {**default['language'], **language},
            'content_style': content_style,
        }
    except Exception:
        return default


def build_image_prompt(profile, brand, topic, platform='instagram', aspect_ratio='1:1', source_mode='text-to-image'):
    brand_name = business_name_from_profile(profile)
    business = profile.profile or {} if profile else {}
    preferences = content_preferences_for_profile(profile)
    language = (preferences.get('language') or {}).get('label') or 'English'
    preference_style = preferences.get('content_style') if isinstance(preferences.get('content_style'), dict) else {}
    font = (brand.font or {}).get('displayName') or (brand.font or {}).get('family') or 'selected brand font' if brand else 'selected brand font'
    style_data = brand.recommended_visual_style if brand and isinstance(brand.recommended_visual_style, dict) else {}
    if preference_style.get('id'):
        style_data = {**style_data, **preference_style}
    style_id = normalize_style_id(style_data.get('id', ''))
    style = style_data.get('name') or style_data.get('label') or ''
    style_prompt = style_data.get('prompt') or STYLE_DIRECTIVES.get(style_id) or style_data.get('description') or ''
    colors = ', '.join(normalize_reference_list(brand.colors)) if brand else ''
    logo_list = normalize_reference_list(brand.logos) if brand else []
    logos = ', '.join(logo_list) if logo_list else ''
    services = ', '.join((business.get('services') or [])[:6])
    audience = business.get('audience') or business.get('target_audience') or ''
    keywords = ', '.join((business.get('keywords') or [])[:10])
    profile_markdown = (profile.editable_markdown or '')[:3000] if profile else ''
    overlay_text = concise_overlay_text(topic.title, brand_name)
    competitor_context = ''
    if profile and profile.workspace_id:
        try:
            from content_engine.models import CompetitorAnalysis
            competitors = CompetitorAnalysis.objects.filter(
                user=profile.user,
                workspace=profile.workspace,
            ).order_by('-updated_at')[:5]
            competitor_context = '; '.join(
                f"{item.name}: features={', '.join((item.key_features or [])[:3])}; differentiators={', '.join((item.differentiators or [])[:3])}"
                for item in competitors
                if item.name
            )
        except Exception:
            competitor_context = ''
    return f"""
Create one premium, brand-aligned social media image for {brand_name}.

Brand context:
- Business: {brand_name}
- Business profile/documentation: {profile_markdown or 'Use the saved business profile.'}
- Services/offers: {services or 'use the strongest offer from the business profile'}
- Audience: {audience or 'the brand target customers'}
- Keywords: {keywords or 'brand-relevant marketing keywords'}
- Competitor/market context: {competitor_context or 'use the saved brand positioning to create a differentiated market-ready visual'}
- Brand colors: {colors or 'website-inspired palette'}
- Logo references: {logos or 'none supplied'}
- Brand voice/style notes: {(brand.tone or brand.image_style or '') if brand else ''}
- Brand typography: {font}
- Output language for any intentional image text: {language}
- Suggested image text overlay if visible text improves the concept: {overlay_text}

Content brief:
- Topic: {topic.title}
- Platform: {platform}
- Aspect ratio: {aspect_ratio}
- Source mode: {source_mode}

Mandatory content style:
- Selected style: {style or 'Brand aligned'}
- Style execution rules: {style_prompt or 'Use the saved brand visual identity.'}

Prompt engineering requirements:
- Make the image specific to this brand and this post, not generic stock content.
- Describe the main subject, environment, composition, lighting, color palette, camera/framing, mood, and visual hierarchy.
- Match the selected style exactly. Do not mix photorealism with cartoon unless the selected style allows it.
- Use brand colors naturally in props, lighting, background, UI accents, clothing, packaging, or abstract shapes.
- If visible text is used, keep it short, high-contrast, readable, and placed where it does not cover the product or face.
- TYPOGRAPHY: Use the selected brand font "{font}" for any visible text. If exact font rendering is unavailable, use a visually similar typeface. Do not use random fonts that conflict with the brand style.
- {'Include the brand logo in the image. Logo reference images are supplied as the 2nd/3rd attached images. Preserve them exactly with no redesign, no altered letters, no color changes, no warped shape, no fake substitute mark, and no cropped unreadable version.' if logos else 'No brand logo reference is supplied. Do NOT invent, draw, or include any fake logo. Only include the brand name as clean text if the prompt overlay requests it.'}
- The FIRST attached image is the IMMUTABLE PRODUCT REFERENCE. Treat it as the main subject. Keep the product type, cut/silhouette, material, pattern, color family, logo/label placement, and recognizable visual details perfectly consistent. Do not redesign the product.
- When both product and logo references are supplied, compose them together: product is the hero subject and the logo appears as an exact brand mark on packaging, corner lockup, signage, or UI where natural.
- Use the competitor/market context to show why this brand is different, but never mention competitor names in visible image text.
- No watermark, no random extra text, no fake logos, no clutter, no malformed hands/faces, no unrelated objects.

Return only the final image-generation prompt.
""".strip()


def concise_overlay_text(topic_title, brand_name):
    text = re.sub(r'\s+', ' ', str(topic_title or '')).strip()
    text = re.sub(r'^\s*' + re.escape(str(brand_name or '')) + r'\s*[:\-]\s*', '', text, flags=re.I)
    text = re.sub(
        r'\b(?:campaign\s+week\s+\d+|week\s+\d+|practical\s+post\s+\d+|social\s+post\s+idea\s+\d+|blog\s+idea\s+\d+|caption\s*(?:number)?\s*\d+|prompt\s+\d+)\b',
        '',
        text,
        flags=re.I,
    ).strip(' :-')
    generic = {'awareness', 'engagement', 'conversion', 'retention', 'brand awareness', 'marketing update'}
    if text.lower() in generic:
        text = ''
    if not text:
        return 'See The Difference'
    words = text.split()
    if len(words) > 8:
        text = ' '.join(words[:8])
    return text[:80]


def enhance_image_prompt(prompt):
    try:
        from utils.chatbot import gemini_text
        enhanced = gemini_text(
            'Turn this brief into a super prompt for image generation. Include subject, scene, composition, camera/framing, lighting, color, style, constraints, and negative rules.\n\n'
            f'{prompt}',
            system_prompt=(
                'You are an elite image prompt engineer for Gemini native image generation. '
                'Rewrite the user brief into a rich, precise, production-quality image prompt. '
                'Preserve all brand, style, color, platform, aspect-ratio, logo, reference-image, required text overlay, and typography rules. '
                'Return only the final prompt, no markdown and no explanation.'
            ),
        )
        enhanced = (enhanced or '').strip()
        return enhanced or prompt
    except Exception:
        return prompt


def reference_lock_rules(brand_name=None):
    label = brand_name or 'the brand'
    return (
        "\n\nCRITICAL PRODUCT & LOGO ANCHORING RULES:\n"
        "- The FIRST attached image is the IMMUTABLE PRODUCT REFERENCE. You MUST preserve its exact shape, silhouette, packaging, labels, and recognizable details. Do not redesign or hallucinate a similar product. It must be the EXACT product shown.\n"
        "- If additional images are attached, they are BRAND LOGOS. Apply them exactly as shown (no warped letters, no fake marks) on packaging, corner lockups, or natural surfaces.\n"
        f"- Generate for {label}, using these supplied images as mandatory visual evidence.\n"
        "- If you cannot perfectly preserve the product from the first image, do not generate an image."
    )


def generate_image(prompt, inspiration_images=None, brand_name=None, reference_mode='optional'):
    api_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
    if not api_key:
        raise GeminiError('invalid_response', 'GEMINI_API_KEY is not configured for image generation.', retryable=False)

    try:
        from google import genai
        from google.genai import types
    except Exception:
        raise GeminiError('invalid_response', 'google-genai SDK is unavailable for image generation.', retryable=False)

    try:
        client = genai.Client(api_key=api_key)
    except Exception as exc:
        error_type, retryable = classify_gemini_error(exc)
        raise GeminiError(error_type, str(exc), retryable=retryable) from exc
    last_error = None
    started = time.monotonic()
    diagnostics = {'requested': len(inspiration_images or []), 'failed_urls': []}
    image_parts = build_image_parts(inspiration_images or [], types, diagnostics=diagnostics)
    locked = str(reference_mode or '').lower() in ('required', 'locked', 'reference_required')
    if locked and not image_parts:
        logger.warning(
            "Gemini reference-locked image generation blocked because no references loaded refs=%s failed=%s",
            diagnostics.get('requested'),
            diagnostics.get('failed_urls'),
        )
        raise GeminiError(
            'invalid_response',
            'Reference image could not be loaded, so Voice Spark did not generate an unrelated image.',
            retryable=True,
        )
    final_prompt = f"{prompt}{reference_lock_rules(brand_name)}" if locked else prompt
    prompts = fallback_prompts(final_prompt, reference_locked=locked)
    # Gemini image generation docs use the image-only modality here. Some model
    # versions reject uppercase TEXT/IMAGE or silently return text-only output.
    image_config = types.GenerateContentConfig(response_modalities=['Image'])
    for model in IMAGE_MODELS:
        for candidate_prompt in prompts:
            try:
                attempt_started = time.monotonic()
                parts = [types.Part.from_text(text=candidate_prompt), *image_parts]
                response = run_with_timeout(
                    lambda: client.models.generate_content(
                        model=model,
                        contents=[types.Content(role='user', parts=parts)],
                        config=image_config,
                    ),
                    GEMINI_IMAGE_TIMEOUT_SECONDS,
                )
                image_url = extract_and_save_image(response)
                if image_url:
                    logger.info(
                        "Gemini image generated model=%s elapsed_ms=%s refs_requested=%s refs_loaded=%s reference_mode=%s",
                        model,
                        int((time.monotonic() - attempt_started) * 1000),
                        diagnostics.get('requested'),
                        len(image_parts),
                        reference_mode,
                    )
                    return image_url, model
            except TimeoutError as exc:
                last_error = exc
                time.sleep(1)
                continue
            except Exception as exc:
                last_error = exc
                time.sleep(1)
                continue
    if image_parts and not locked:
        for model in IMAGE_MODELS:
            for candidate_prompt in fallback_prompts(prompt, text_only=True):
                try:
                    response = run_with_timeout(
                        lambda: client.models.generate_content(
                            model=model,
                            contents=[types.Content(role='user', parts=[types.Part.from_text(text=candidate_prompt)])],
                            config=image_config,
                        ),
                        GEMINI_IMAGE_TIMEOUT_SECONDS,
                    )
                    image_url = extract_and_save_image(response)
                    if image_url:
                        return image_url, f'{model}:text-fallback'
                except TimeoutError as exc:
                    last_error = exc
                    time.sleep(1)
                    continue
                except Exception as exc:
                    last_error = exc
                    time.sleep(1)
                    continue
    error_type, retryable = classify_gemini_error(last_error)
    logger.warning(
        "Gemini image generation failed elapsed_ms=%s refs_requested=%s refs_loaded=%s reference_mode=%s error_type=%s error=%s failed_refs=%s",
        int((time.monotonic() - started) * 1000),
        diagnostics.get('requested'),
        len(image_parts),
        reference_mode,
        error_type,
        last_error,
        diagnostics.get('failed_urls'),
    )
    raise GeminiError(error_type, str(last_error) or 'Gemini image generation returned no image.', retryable=retryable) from last_error


def run_with_timeout(fn, timeout_seconds):
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = executor.submit(fn)
    try:
        return future.result(timeout=timeout_seconds)
    except concurrent.futures.TimeoutError as exc:
        future.cancel()
        raise TimeoutError(f'Gemini image generation timed out after {timeout_seconds}s') from exc
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


def fallback_brand_name(prompt):
    text = prompt or ''
    match = re.search(r'(?:for|Business:)\s+([^\n.]+)', text)
    if match:
        return match.group(1).strip()[:60]
    return 'Generated Brand'


def fallback_prompts(prompt, text_only=False, reference_locked=False):
    core = (prompt or '').strip()
    concise_context = core[:900]
    if text_only:
        return [
            (
                'Create one premium brand marketing image from this brief. '
                'Use text-to-image only, no source image dependency. One clear subject, clean composition, '
                'brand-relevant scene, premium lighting, include the requested short text overlay and brand logo treatment when described, no random text, no watermark. '
                f'Brief: {concise_context}'
            ),
            (
                'Hyper-realistic social media marketing image, one clear business-focused subject, '
                'clean background, natural premium light, short clean brand text overlay, no watermark. '
                f'Brand context: {concise_context}'
            ),
        ]
    if reference_locked:
        return [
            core,
            f'{core}\nSimplify only the background, lighting, and composition. The supplied reference product/logo identity remains mandatory and unchanged.',
        ]
    return [
        core,
        f'{core}\nFallback: simplify the scene, keep one clear subject, exact logo placement, and a minimal readable brand-safe text overlay.',
        f'Hyper-realistic brand marketing image, one clear subject, clean background, premium light, exact brand logo placement, short readable overlay text, no watermark. Context: {concise_context}',
    ]


def build_image_parts(inspiration_images, types, diagnostics=None):
    parts = []
    for item in (inspiration_images or [])[:4]:
        try:
            if isinstance(item, dict) and item.get('mime_type') and item.get('data'):
                parts.append(types.Part.from_bytes(data=base64.b64decode(item['data']), mime_type=item['mime_type']))
                continue
            if isinstance(item, str) and item.startswith('data:') and ';base64,' in item:
                header, raw = item.split(';base64,', 1)
                parts.append(types.Part.from_bytes(data=base64.b64decode(raw), mime_type=header.replace('data:', '') or 'image/png'))
                continue
            if isinstance(item, str) and item:
                response = requests.get(item, timeout=8)
                response.raise_for_status()
                mime_type = response.headers.get('Content-Type') or mimetypes.guess_type(item)[0] or 'image/png'
                parts.append(types.Part.from_bytes(data=response.content, mime_type=mime_type.split(';')[0]))
        except Exception as exc:
            if diagnostics is not None:
                diagnostics.setdefault('failed_urls', []).append({'url': str(item)[:500], 'error': str(exc)[:300]})
            continue
    return parts


def extract_and_save_image(response):
    parts = getattr(response, 'parts', None)
    if parts is None:
        candidates = getattr(response, 'candidates', None) or []
        if candidates:
            content = getattr(candidates[0], 'content', None)
            parts = getattr(content, 'parts', None)
    for part in parts or []:
        inline = getattr(part, 'inline_data', None) or getattr(part, 'inlineData', None)
        if inline and getattr(inline, 'data', None):
            return save_bytes(inline.data, getattr(inline, 'mime_type', None) or getattr(inline, 'mimeType', None) or 'image/png')
    return None


def save_image_from_url(url):
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        content_type = response.headers.get('Content-Type', '')
        ext = 'jpg' if 'jpeg' in content_type or 'jpg' in content_type else 'png'
        path = f'generated/{uuid.uuid4()}.{ext}'
        default_storage.save(path, ContentFile(response.content))
        return default_storage.url(path).split('?')[0]
    except Exception:
        return url


def save_bytes(data, mime_type):
    ext = 'jpg' if mime_type == 'image/jpeg' else 'png'
    path = f'generated/{uuid.uuid4()}.{ext}'
    default_storage.save(path, ContentFile(data))
    return default_storage.url(path).split('?')[0]


def placeholder_image(prompt, brand_name='Generated Brand'):
    label = (prompt or 'Generated image')[:72].replace('\n', ' ')
    image = Image.new('RGB', (1200, 1200), '#101827')
    draw = ImageDraw.Draw(image)
    for y in range(1200):
        mix = y / 1200
        r = int(16 + 72 * mix)
        g = int(24 + 30 * mix)
        b = int(39 + 120 * mix)
        draw.line((0, y, 1200, y), fill=(r, g, b))
    draw.ellipse((760, 80, 1200, 520), fill=(42, 55, 96), outline=None)
    draw.rounded_rectangle((120, 760, 1080, 980), radius=34, fill=(43, 58, 96), outline=None)
    try:
        title_font = ImageFont.truetype('DejaVuSans-Bold.ttf', 54)
        body_font = ImageFont.truetype('DejaVuSans.ttf', 30)
    except Exception:
        title_font = ImageFont.load_default()
        body_font = ImageFont.load_default()
    draw.text((160, 835), brand_name or 'Generated Brand', fill='#ffffff', font=title_font)
    draw.text((160, 915), label, fill='#e5e7eb', font=body_font)
    buffer = BytesIO()
    image.save(buffer, format='JPEG', quality=92)
    path = f'generated/{uuid.uuid4()}.jpg'
    default_storage.save(path, ContentFile(buffer.getvalue()))
    return default_storage.url(path).split('?')[0]
