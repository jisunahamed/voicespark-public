"""
generation_orchestrator.py — Centralized AI Generation Entry Point

Single entry point for ALL AI generation/regeneration flows.
Standardizes: context loading, Gemini execution, retry handling,
state transitions, quality validation, logging, error normalization.

All flows route through orchestrate_generation().
"""

import logging
import time
import uuid

from django.utils import timezone

from utils.chatbot import gemini_text, gemini_error_payload, GeminiError

from .context_builder import (
    build_generation_context,
    create_context_snapshot,
    merge_snapshot_with_current,
    validate_generation_quality,
    validate_and_sanitize_json,
    validate_caption_output,
    sanitize_caption,
    safe_transition_job,
    generate_correlation_id,
    generate_idempotency_key,
    structured_log,
    PROMPT_VERSION,
    PIPELINE_VERSION,
)
from .prompt_builder import (
    build_advanced_image_prompt,
    build_advanced_caption_prompt,
    build_caption_edit_prompt,
    build_image_edit_prompt,
    build_image_regen_prompt,
    build_campaign_prompt,
    build_topic_generation_prompt,
    build_campaign_regen_prompt,
    build_blog_generation_prompt,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SOFT_TIMEOUT_SECONDS = 30
HARD_TIMEOUT_SECONDS = 55
MAX_RETRIES = 2

PRIORITY_HIGH = 'high'
PRIORITY_MEDIUM = 'medium'
PRIORITY_LOW = 'low'

FLOW_PRIORITIES = {
    'create_post': PRIORITY_HIGH,
    'regenerate_image': PRIORITY_HIGH,
    'regenerate_caption': PRIORITY_HIGH,
    'edit_post': PRIORITY_HIGH,
    'create_blog': PRIORITY_HIGH,
    'campaign_generation': PRIORITY_HIGH,
    'topic_generation': PRIORITY_MEDIUM,
    'caption_variant': PRIORITY_MEDIUM,
    'background_enrichment': PRIORITY_LOW,
}


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

def orchestrate_generation(
    flow,
    user,
    workspace,
    payload=None,
    correlation_id=None,
    priority=None,
    topic='',
    target_platform='multi-platform',
    campaign_context=None,
    existing_post=None,
    user_instruction='',
    content_type='social',
    aspect_ratio='1:1',
    previous_caption='',
    context_snapshot=None,
    reference_image_url=None,
):
    """Centralized entry point for all AI generation flows.

    Returns dict with: status, caption, image_prompt, platform_captions,
    correlation_id, quality, lineage, error.
    """
    started = time.monotonic()
    correlation_id = correlation_id or generate_correlation_id(flow, workspace)
    priority = priority or FLOW_PRIORITIES.get(flow, PRIORITY_MEDIUM)

    result = {
        'status': 'failed',
        'correlation_id': correlation_id,
        'flow': flow,
        'prompt_version': PROMPT_VERSION,
        'pipeline_version': PIPELINE_VERSION,
        'error': None,
        'caption': '',
        'image_prompt': '',
        'platform_captions': {},
        'quality': {},
        'duration_ms': 0,
        'retry_count': 0,
    }

    try:
        # 1. Build context (workspace-isolated)
        context = build_generation_context(
            user=user,
            workspace=workspace,
            topic=topic,
            campaign_context=campaign_context,
            existing_post=existing_post,
            user_instruction=user_instruction,
            target_platform=target_platform,
            content_type=content_type,
            correlation_id=correlation_id,
            reference_image_url=reference_image_url,
        )

        # Merge with snapshot for regeneration consistency
        if context_snapshot and isinstance(context_snapshot, dict):
            context = merge_snapshot_with_current(context_snapshot, context)

        # 2. Execute flow
        if flow == 'create_post':
            result = _execute_create_post(context, result, aspect_ratio)
        elif flow == 'regenerate_caption':
            result = _execute_caption_regen(context, result, previous_caption)
        elif flow == 'regenerate_image':
            result = _execute_image_regen(context, result, aspect_ratio, previous_caption)
        elif flow == 'edit_post':
            result = _execute_edit(context, result, aspect_ratio, previous_caption)
        elif flow == 'caption_variant':
            result = _execute_caption_variant(context, result, previous_caption)
        elif flow == 'campaign_generation':
            result = _execute_campaign_generation(context, result, payload)
        elif flow == 'campaign_regen':
            result = _execute_campaign_regen(context, result, payload, user_instruction)
        elif flow == 'topic_generation':
            result = _execute_topic_generation(context, result, payload)
        elif flow == 'create_blog':
            result = _execute_blog_generation(context, result, payload)
        else:
            result['error'] = f'Unsupported flow: {flow}'

        # 3. Quality validation (non-blocking diagnostic)
        if result['status'] == 'completed':
            result['quality'] = validate_generation_quality(
                context, result, flow,
            )
            # Create snapshot for future regeneration
            result['context_snapshot'] = create_context_snapshot(context)

    except GeminiError as exc:
        result['error'] = str(exc)
        result['error_type'] = exc.error_type
        result['retryable'] = exc.retryable
    except Exception as exc:
        logger.exception('orchestrate_generation failed flow=%s corr=%s', flow, correlation_id)
        payload_err = gemini_error_payload(exc)
        result['error'] = payload_err['message']
        result['error_type'] = payload_err.get('error_type', 'unknown')
        result['retryable'] = payload_err.get('retryable', True)

    # 4. Observability
    result['duration_ms'] = int((time.monotonic() - started) * 1000)
    structured_log(
        logger,
        'generation_complete',
        correlation_id=correlation_id,
        flow=flow,
        status=result['status'],
        duration_ms=result['duration_ms'],
        retry_count=result.get('retry_count', 0),
        prompt_version=PROMPT_VERSION,
        pipeline_version=PIPELINE_VERSION,
        priority=priority,
        error=result.get('error', ''),
    )

    return result


# ---------------------------------------------------------------------------
# Flow executors
# ---------------------------------------------------------------------------

def _execute_create_post(context, result, aspect_ratio):
    """Generate caption + image prompt for a new post."""
    topic = context.get('topic', '')
    platform = context.get('target_platform', 'multi-platform')

    # Generate caption
    caption = _generate_caption_with_retry(context, topic, platform)
    result['caption'] = caption

    # Generate platform-specific captions if smart captions enabled
    if context.get('smart_captions', True):
        result['platform_captions'] = _generate_platform_captions(
            context, topic, caption,
        )

    # Generate image prompt
    image_prompt = build_advanced_image_prompt(
        context, topic, platform, aspect_ratio,
    )
    result['image_prompt'] = image_prompt
    result['status'] = 'completed'
    return result


def _execute_caption_regen(context, result, previous_caption):
    """Regenerate caption for a specific platform."""
    platform = context.get('target_platform', 'multi-platform')
    topic = context.get('topic', '')
    instruction = context.get('user_instruction', '')

    if instruction:
        prompt = build_caption_edit_prompt(
            context, platform, previous_caption, instruction,
        )
    else:
        prompt = build_advanced_caption_prompt(context, topic, platform)

    caption_text = _call_gemini_caption(prompt, platform)
    result['caption'] = caption_text
    result['status'] = 'completed'
    return result


def _execute_image_regen(context, result, aspect_ratio, previous_caption=''):
    """Context-preserving image and caption regeneration."""
    topic = context.get('topic', '')
    platform = context.get('target_platform', 'multi-platform')

    # Regenerate caption
    caption = _generate_caption_with_retry(context, topic, platform)
    result['caption'] = caption

    # Regenerate image prompt
    image_prompt = build_image_regen_prompt(
        context, topic, platform, aspect_ratio,
    )
    result['image_prompt'] = image_prompt
    result['status'] = 'completed'
    return result


def _execute_edit(context, result, aspect_ratio, previous_caption):
    """Delta-focused edit: change only what's requested."""
    instruction = context.get('user_instruction', '')
    platform = context.get('target_platform', 'multi-platform')

    # Determine what to change
    change_caption = _instruction_targets_caption(instruction)
    change_image = _instruction_targets_image(instruction)

    if change_caption:
        prompt = build_caption_edit_prompt(
            context, platform, previous_caption, instruction,
        )
        caption_text = _call_gemini_caption(prompt, platform)
        result['caption'] = caption_text

    if change_image:
        image_prompt = build_image_edit_prompt(
            context, instruction,
        )
        result['image_prompt'] = image_prompt

    result['change_caption'] = change_caption
    result['change_image'] = change_image
    result['status'] = 'completed'
    return result


def _execute_caption_variant(context, result, previous_caption):
    """Generate a fresh caption variant for one platform."""
    platform = context.get('target_platform', 'instagram')
    topic = context.get('topic', '')

    prompt = build_advanced_caption_prompt(context, topic, platform)
    caption_text = _call_gemini_caption(prompt, platform)
    result['caption'] = caption_text
    result['status'] = 'completed'
    return result


# ---------------------------------------------------------------------------
# Gemini call helpers with retry
# ---------------------------------------------------------------------------

def _generate_caption_with_retry(context, topic, platform, max_retries=MAX_RETRIES):
    """Generate a caption with bounded retry."""
    prompt = build_advanced_caption_prompt(context, topic, platform)
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            caption_text = _call_gemini_caption(prompt, platform)
            if validate_caption_output(caption_text):
                return sanitize_caption(caption_text)
        except Exception as exc:
            last_error = exc
            if attempt < max_retries:
                time.sleep(1 * (attempt + 1))
                continue
            break

    if last_error:
        raise last_error
    raise RuntimeError('Caption generation returned empty output after retries.')


def _call_gemini_caption(prompt, platform):
    """Single Gemini call for caption generation. Validates output."""
    import json as json_module

    raw = (gemini_text(
        prompt,
        system_prompt=(
            f'You are a senior social media copywriter specializing in {platform}. '
            'Return ONLY valid JSON with keys: caption, cta, hashtags, tone, reasoning. '
            'No markdown, no explanation outside the JSON.'
        ),
    ) or '').strip()

    # Try to parse as structured JSON
    is_valid, parsed = validate_and_sanitize_json(raw, required_fields=['caption'])
    if is_valid and parsed.get('caption'):
        return sanitize_caption(parsed['caption'])

    # Fallback: treat as plain text caption
    caption = sanitize_caption(raw)
    if validate_caption_output(caption):
        return caption

    raise RuntimeError(f'Gemini returned invalid {platform} caption.')


def _generate_platform_captions(context, topic, base_caption):
    """Generate platform-specific captions. Each platform gets its own call."""
    platforms = ('instagram', 'facebook', 'linkedin', 'twitter')
    captions = {}

    for platform in platforms:
        try:
            prompt = build_advanced_caption_prompt(context, topic, platform)
            caption = _call_gemini_caption(prompt, platform)
            captions[platform] = caption
        except Exception as exc:
            logger.warning(
                'Platform caption failed platform=%s corr=%s error=%s',
                platform, context.get('correlation_id', ''), exc,
            )
            # Fallback to base caption for this platform
            captions[platform] = base_caption

    return captions


# ---------------------------------------------------------------------------
# Instruction analysis
# ---------------------------------------------------------------------------

CAPTION_KEYWORDS = {
    'caption', 'text', 'copy', 'cta', 'hashtag', 'wording',
    'write', 'rewrite', 'shorten', 'lengthen', 'tone', 'emoji',
}

IMAGE_KEYWORDS = {
    'image', 'photo', 'picture', 'background', 'color', 'darker',
    'lighter', 'brighter', 'product', 'logo', 'style', 'composition',
    'layout', 'remove', 'add', 'replace', 'filter', 'generate',
}


def _execute_campaign_generation(context, result, payload):
    """Generate a 4-week marketing campaign plan."""
    plan = payload.get('plan') if isinstance(payload, dict) else None
    prompt = build_campaign_prompt(context, plan)

    raw = gemini_text(
        prompt,
        system_prompt="You are a senior marketing strategist. Return ONLY valid JSON.",
    )
    is_valid, parsed = validate_and_sanitize_json(raw, required_fields=['weeks'])

    if is_valid:
        result['campaign_plan'] = parsed
        result['status'] = 'completed'
    else:
        raise RuntimeError('Gemini failed to generate a valid campaign plan JSON.')

    return result


def _execute_campaign_regen(context, result, payload, instruction):
    """Instruction-based campaign regeneration."""
    current_item_plan = payload.get('item_plan') if isinstance(payload, dict) else {}
    prompt = build_campaign_regen_prompt(context, current_item_plan, instruction)

    raw = gemini_text(
        prompt,
        system_prompt="Update the campaign plan. Return ONLY the item_plan JSON.",
    )
    is_valid, parsed = validate_and_sanitize_json(raw)

    if is_valid:
        result['item_plan'] = parsed
        result['status'] = 'completed'
    else:
        raise RuntimeError('Gemini failed to regenerate campaign plan JSON.')

    return result


def _execute_topic_generation(context, result, payload):
    """Generate first-week topics."""
    social_count = payload.get('social_count', 5) if isinstance(payload, dict) else 5
    blog_count = payload.get('blog_count', 0) if isinstance(payload, dict) else 0

    prompt = build_topic_generation_prompt(context, social_count, blog_count)
    raw = gemini_text(
        prompt,
        system_prompt="Generate content topics. Return ONLY JSON.",
    )
    is_valid, parsed = validate_and_sanitize_json(raw, required_fields=['social_topics'])

    if is_valid:
        result['topics'] = parsed
        result['status'] = 'completed'
    else:
        raise RuntimeError('Gemini failed to generate topics JSON.')

    return result


def _execute_blog_generation(context, result, payload):
    """Generate full structured blog content."""
    topic = payload.get('topic', '')
    blog_plan_item = payload.get('blog_plan_item')

    prompt = build_blog_generation_prompt(context, topic, blog_plan_item)
    raw = gemini_text(
        prompt,
        system_prompt="You are a senior content strategist and SEO expert. Return ONLY valid JSON.",
    )
    is_valid, parsed = validate_and_sanitize_json(raw, required_fields=['title', 'sections'])

    if is_valid:
        result['blog_content'] = parsed
        result['status'] = 'completed'
    else:
        raise RuntimeError('Gemini failed to generate valid blog JSON.')

    return result


def _instruction_targets_caption(instruction):
    if not instruction:
        return False
    words = set(instruction.lower().split())
    return bool(words & CAPTION_KEYWORDS)


def _instruction_targets_image(instruction):
    if not instruction:
        return True  # default to image change
    words = set(instruction.lower().split())
    return bool(words & IMAGE_KEYWORDS) or not _instruction_targets_caption(instruction)
