"""
GPTHub Auto-Mode Router
=======================
Extracts and centralises all model-routing logic that was previously inlined
in main.py.  Functions are pure where possible, with IO/LLM calls receiving
injected dependencies.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any, Optional
from urllib.parse import urlencode
from uuid import uuid4

from open_webui.utils.gpthub_i18n import t, t_cap, t_routing_reason
from open_webui.utils.gpthub_models import (
    build_capability_graph,
    env_bool,
    env_float,
    env_int,
    extract_json_object,
    get_virtual_capability,
    infer_model_capabilities,
    infer_request_capability,
    is_virtual_model,
    is_virtual_model_id,
)

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Prompt extraction helpers
# ---------------------------------------------------------------------------


def extract_last_user_prompt(form_data: dict) -> str:
    messages = form_data.get('messages')
    if not isinstance(messages, list):
        return ''

    for message in reversed(messages):
        if not isinstance(message, dict) or message.get('role') != 'user':
            continue

        content = message.get('content')
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts: list[str] = []
            image_count = 0
            for part in content:
                if not isinstance(part, dict):
                    continue
                if part.get('type') in {'text', 'input_text'} and isinstance(part.get('text'), str):
                    parts.append(part.get('text', ''))
                if part.get('type') == 'image_url':
                    image_count += 1

            text = ' '.join(parts).strip()
            if image_count > 0:
                if text:
                    return f'{text} [user_attached_images={image_count}]'
                return f'user_attached_images={image_count}'
            return text

    return ''


def parse_model_selection(form_data: dict) -> tuple[str, list[str]]:
    """Parse auto/manual mode and model IDs from the client payload."""
    selection = form_data.get('selection', {})
    mode = None
    model_ids: list[str] = []

    if isinstance(selection, dict):
        selection_mode = selection.get('mode')
        if selection_mode in {'auto', 'manual'}:
            mode = selection_mode

        selection_model_ids = selection.get('model_ids')
        if isinstance(selection_model_ids, list):
            model_ids = [
                model_id
                for model_id in selection_model_ids
                if isinstance(model_id, str) and model_id.strip()
            ]

    legacy_mode = form_data.get('model_selection_mode')
    if mode is None and legacy_mode in {'auto', 'manual'}:
        mode = legacy_mode

    requested_model = form_data.get('model')
    if isinstance(requested_model, str) and requested_model.strip():
        model_ids = [requested_model, *[mid for mid in model_ids if mid != requested_model]]

    return (mode or 'manual'), model_ids


# ---------------------------------------------------------------------------
# Router model selection
# ---------------------------------------------------------------------------

_PREFERRED_ROUTER_PATTERNS: tuple[str, ...] = (
    'mws-gpt-alpha',
    'qwen3-coder',
    'qwen2.5-72b',
    'deepseek',
    'gpt-oss',
    'llama',
)


def select_router_model_id(
    available_models: dict,
    accessible_model_ids: list[str],
) -> str | None:
    configured = os.getenv('GPTHUB_ROUTER_MODEL_ID', '').strip()
    if configured and configured in accessible_model_ids:
        model = available_models.get(configured)
        if model and not is_virtual_model(model):
            return configured

    for pattern in _PREFERRED_ROUTER_PATTERNS:
        for model_id in accessible_model_ids:
            if pattern in model_id.lower():
                model = available_models.get(model_id)
                if model and not is_virtual_model(model):
                    return model_id

    return accessible_model_ids[0] if accessible_model_ids else None


# ---------------------------------------------------------------------------
# Router LLM output parsing
# ---------------------------------------------------------------------------


def extract_router_json(text: str) -> dict[str, Any] | None:
    if not isinstance(text, str) or not text.strip():
        return None

    stripped = text.strip()
    candidates = [stripped]

    fenced_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', stripped, flags=re.DOTALL)
    if fenced_match:
        candidates.insert(0, fenced_match.group(1))

    brace_start = stripped.find('{')
    brace_end = stripped.rfind('}')
    if brace_start >= 0 and brace_end > brace_start:
        candidates.insert(0, stripped[brace_start: brace_end + 1])

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            continue

    return None


def extract_router_output_text(response: Any) -> str:
    if not isinstance(response, dict):
        return ''

    choices = response.get('choices')
    if isinstance(choices, list) and choices:
        first_choice = choices[0] if isinstance(choices[0], dict) else {}
        message = first_choice.get('message', {}) if isinstance(first_choice, dict) else {}
        content = message.get('content') if isinstance(message, dict) else None
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            texts: list[str] = []
            for part in content:
                if isinstance(part, dict) and isinstance(part.get('text'), str):
                    texts.append(part['text'])
            return '\n'.join(texts)

    output = response.get('output')
    if isinstance(output, list):
        texts: list[str] = []
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get('content')
            if isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and isinstance(part.get('text'), str):
                        texts.append(part['text'])
        if texts:
            return '\n'.join(texts)

    return ''


# ---------------------------------------------------------------------------
# Capability-based model picking
# ---------------------------------------------------------------------------

_CAPABILITY_FALLBACKS: dict[str, list[str]] = {
    'auto': ['text', 'code', 'vision', 'image_generation'],
    'code': ['code', 'text'],
    'vision': ['vision', 'text'],
    'image_generation': ['image_generation'],
    'audio_transcription': ['audio_transcription', 'text'],
    'audio_speech': ['audio_speech', 'text'],
    'web_search': ['text', 'code', 'vision'],
    'research': ['text', 'code', 'vision'],
}


def pick_first_available_model_for_capability(
    capability_graph: dict[str, list[str]],
    capability: str,
) -> str | None:
    fallbacks = _CAPABILITY_FALLBACKS.get(capability, [capability, 'text', 'code', 'vision'])
    for candidate_capability in fallbacks:
        model_ids = capability_graph.get(candidate_capability, [])
        if model_ids:
            return model_ids[0]
    return None


def is_deep_research_model(model: dict | None) -> bool:
    if not model:
        return False

    text = f"{(model.get('id') or '').lower()} {(model.get('name') or '').lower()}"
    tags = model.get('tags') or []
    tag_text = ' '.join(
        [str(tag.get('name', '')).lower() for tag in tags if isinstance(tag, dict)]
    )
    text = f'{text} {tag_text}'

    return any(
        marker in text
        for marker in ['deepseek', 'reason', 'r1', 'o1', 'o3', 'analysis', 'think', 'research']
    )


def pick_preferred_model_for_capability(
    capability_graph: dict[str, list[str]],
    capability: str,
    available_models: dict[str, dict],
    prefer_deep_research: bool = False,
) -> str | None:
    base_pick = pick_first_available_model_for_capability(capability_graph, capability)
    if not prefer_deep_research:
        return base_pick

    # Vision has a broader search scope if deep research is preferred.
    if capability == 'vision':
        fallbacks = ['vision', 'image_generation', 'text']
    else:
        fallbacks = _CAPABILITY_FALLBACKS.get(capability, [capability, 'text', 'code', 'vision'])

    for candidate_capability in fallbacks:
        model_ids = capability_graph.get(candidate_capability, [])
        if not model_ids:
            continue

        deep_candidates = [mid for mid in model_ids if is_deep_research_model(available_models.get(mid))]
        if deep_candidates:
            return deep_candidates[0]

        if base_pick is None:
            base_pick = model_ids[0]

    return base_pick


# ---------------------------------------------------------------------------
# Non-chat model detection
# ---------------------------------------------------------------------------


_NON_CHAT_MARKERS: tuple[str, ...] = (
    'embedding', 'embeddings', 'embed', 'bge-', '/bge', 'e5-',
    'rerank', 'reranker', 'colbert', 'jina-emb', 'text-embedding',
    'whisper', 'asr', 'transcrib',
)


def is_non_chat_model(model: dict | None) -> bool:
    if not model:
        return False

    text = f"{(model.get('id') or '').lower()} {(model.get('name') or '').lower()}"
    tags = model.get('tags') or []
    tag_text = ' '.join(
        [str(tag.get('name', '')).lower() for tag in tags if isinstance(tag, dict)]
    )
    text = f'{text} {tag_text}'
    return any(marker in text for marker in _NON_CHAT_MARKERS)


# ---------------------------------------------------------------------------
# Voice acknowledgement text
# ---------------------------------------------------------------------------


_VOICE_ACK_KEYS: dict[str, str] = {
    'image_generation': 'voice_ack.image_generation',
    'code': 'voice_ack.code',
    'vision': 'voice_ack.vision',
    'audio_transcription': 'voice_ack.audio_transcription',
    'web_search': 'voice_ack.web_search',
    'research': 'voice_ack.research',
}


def build_voice_ack_text(capability: str | None) -> str:
    key = _VOICE_ACK_KEYS.get(capability or '', 'voice_ack.default')
    return t(key)


# ---------------------------------------------------------------------------
# Manual-mode guidance response builder
# ---------------------------------------------------------------------------


def _make_guidance_completion(model_id: str, content: str) -> dict:
    return {
        'id': f'chatcmpl-gpthub-guidance-{uuid4()}',
        'object': 'chat.completion',
        'created': int(time.time()),
        'model': model_id,
        'choices': [
            {
                'index': 0,
                'message': {'role': 'assistant', 'content': content},
                'finish_reason': 'stop',
            }
        ],
    }


def _recommend_switch_line(
    model_id: str,
    model_name: str,
    fallback: str = '',
) -> str:
    if not fallback:
        fallback = t('guidance.switch_auto')
    if model_name and model_id:
        switch_href = f"gpthub://select-model?{urlencode({'model': model_id})}"
        return f'[{model_name}]({switch_href})'
    return fallback


def _get_recommended_model(
    capability_graph: dict,
    capability: str,
    available_models: dict,
) -> tuple[str, str]:
    candidates = capability_graph.get(capability) or capability_graph.get('text') or []
    mid = candidates[0] if candidates else ''
    model = available_models.get(mid) if mid else None
    mname = (model.get('name') or mid) if model else mid
    return mid, mname


def build_manual_mode_guidance_response(
    form_data: dict,
    selection_effective: dict,
    available_models: dict[str, dict],
) -> dict | None:
    if selection_effective.get('mode') != 'manual':
        return None

    resolved_model_id = selection_effective.get('resolved_model_id')
    if not isinstance(resolved_model_id, str) or not resolved_model_id:
        return None

    selected_model = available_models.get(resolved_model_id)
    if not selected_model or is_virtual_model(selected_model):
        return None

    features = form_data.get('features') or {}
    prompt = extract_last_user_prompt(form_data)
    requested_capability = infer_request_capability(prompt)
    selected_caps = infer_model_capabilities(selected_model)
    selected_model_name = selected_model.get('name') or resolved_model_id
    capability_graph = selection_effective.get('capability_graph') or {}

    # Image-only model used for a non-image text request.
    _image_only_caps = selected_caps - {'text'}
    if _image_only_caps == {'image_generation'} and requested_capability != 'image_generation':
        mid, mname = _get_recommended_model(capability_graph, 'text', available_models)
        switch = _recommend_switch_line(mid, mname, t('guidance.switch_text_model'))
        content = t('guidance.image_only_model', model_name=selected_model_name, switch=switch)
        return _make_guidance_completion(resolved_model_id, content)

    # Non-chat model (embedding / ASR / reranker)
    if is_non_chat_model(selected_model):
        target = 'text' if requested_capability in {'web_search', 'research'} else requested_capability
        mid, mname = _get_recommended_model(capability_graph, target, available_models)
        switch = _recommend_switch_line(mid, mname, t('guidance.switch_normal_model'))
        content = t('guidance.non_chat_model', model_name=selected_model_name, switch=switch)
        return _make_guidance_completion(resolved_model_id, content)

    # Image generation requested but feature is off and model can't do it natively.
    if requested_capability == 'image_generation' and not features.get('image_generation'):
        if 'image_generation' in selected_caps:
            return None
        mid = ''
        image_candidates = capability_graph.get('image_generation') or []
        if image_candidates:
            mid = image_candidates[0]
        else:
            configured = os.getenv('IMAGE_GENERATION_MODEL', '')
            if configured in available_models:
                mid = configured
        model = available_models.get(mid) if mid else None
        mname = (model.get('name') or mid) if model else mid
        switch = _recommend_switch_line(mid, mname, t('guidance.switch_image_mode'))
        content = t('guidance.image_gen_off', model_name=selected_model_name, switch=switch)
        return _make_guidance_completion(resolved_model_id, content)

    # Presentation capability mismatch
    if requested_capability == 'presentation' and not features.get('presentation'):
        content = t('guidance.presentation_off', model_name=selected_model_name)
        return _make_guidance_completion(resolved_model_id, content)

    # Vision capability mismatch
    if requested_capability == 'vision' and 'vision' not in selected_caps:
        mid, mname = _get_recommended_model(capability_graph, 'vision', available_models)
        switch = _recommend_switch_line(mid, mname, t('guidance.switch_auto_for_vision'))
        content = t('guidance.no_vision', model_name=selected_model_name, switch=switch)
        return _make_guidance_completion(resolved_model_id, content)

    return None


# ---------------------------------------------------------------------------
# Core: resolve effective model selection
# ---------------------------------------------------------------------------


async def resolve_effective_model_selection(
    request,
    form_data: dict,
    mode: str,
    requested_model_ids: list[str],
    available_models: dict,
    user=None,
    *,
    check_model_access_fn=None,
    bypass_model_access_control: bool = False,
    bypass_admin_access_control: bool = False,
    chat_completion_handler_fn=None,
) -> dict:
    """
    Central routing logic.  Previously `_resolve_effective_model_selection` in main.py.

    *check_model_access_fn* and *chat_completion_handler_fn* are injected to
    avoid circular imports with main.py.
    """

    def is_accessible(model_id: str) -> bool:
        model = available_models.get(model_id)
        if not model:
            return False
        if is_virtual_model(model):
            return True
        if not bypass_model_access_control and user and (
            user.role != 'admin' or not bypass_admin_access_control
        ):
            try:
                if check_model_access_fn:
                    check_model_access_fn(user, model)
            except Exception:
                return False
        return True

    available_model_ids = [mid for mid in available_models if is_accessible(mid)]
    routable_model_ids = [
        mid for mid, model in available_models.items()
        if not is_virtual_model(model) and not is_non_chat_model(model) and is_accessible(mid)
    ]
    chat_compatible_model_ids = [
        mid for mid in available_model_ids
        if (model := available_models.get(mid)) and not is_virtual_model(model) and not is_non_chat_model(model)
    ]
    capability_graph = build_capability_graph(available_models, routable_model_ids)
    last_user_prompt = extract_last_user_prompt(form_data)
    features = form_data.get('features') or {}
    prefer_deep_research = bool(features.get('deep_research') or features.get('research'))

    resolved_model_id = None
    resolution_reason = 'manual_missing'
    display_model_id = None
    resolved_capability = None
    router_model_id = None

    # Detect virtual model in request
    requested_virtual_model_id = None
    requested_virtual_capability = None
    for requested_model_id in requested_model_ids:
        model = available_models.get(requested_model_id)
        if model and is_virtual_model(model):
            requested_virtual_model_id = requested_model_id
            requested_virtual_capability = get_virtual_capability(model, requested_model_id)
            break
        if requested_virtual_capability is None and is_virtual_model_id(requested_model_id):
            legacy_capability = get_virtual_capability(None, requested_model_id)
            if legacy_capability:
                requested_virtual_model_id = requested_model_id
                requested_virtual_capability = legacy_capability
                break

    # Manual mode: explicit real model always wins.
    if mode == 'manual':
        for requested_model_id in requested_model_ids:
            candidate = available_models.get(requested_model_id)
            if not candidate or is_virtual_model(candidate):
                continue
            if is_accessible(requested_model_id):
                resolved_model_id = requested_model_id
                display_model_id = requested_model_id
                resolved_capability = 'manual'
                resolution_reason = 'manual_requested'
                break

    requested_capability = requested_virtual_capability or ('auto' if mode == 'auto' else None)
    should_route_with_model = requested_capability == 'auto' and env_bool('GPTHUB_ROUTER_ENABLED', True)

    if resolved_model_id is None and requested_capability:
        if should_route_with_model:
            router_model_id = select_router_model_id(available_models, routable_model_ids)

            if router_model_id and chat_completion_handler_fn:
                max_candidates = env_int('GPTHUB_ROUTER_MAX_CANDIDATES', 16)
                model_catalogue = []
                for mid in routable_model_ids[:max_candidates]:
                    if mid == router_model_id:
                        continue
                    model = available_models.get(mid, {})
                    caps = sorted(infer_model_capabilities(model))
                    model_catalogue.append({'id': mid, 'name': model.get('name') or mid, 'capabilities': caps})

                router_input = {'user_request': last_user_prompt, 'available_models': model_catalogue}
                router_system = (
                    'You are a model router. Given a user request and a list of available models, '
                    'choose the single best model to handle that request. '
                    "Consider each model's capabilities carefully. "
                    'IMPORTANT: Only select an image_generation model when the user explicitly asks '
                    'to create, generate, draw, or render an image/picture. '
                    'Do NOT select an image_generation model for text, writing, analysis, or '
                    'any request that merely mentions images or paintings as a topic. '
                    'When the request contains [user_attached_images=N], the user has attached '
                    'images for analysis — select a vision-capable model, NOT an image_generation model. '
                    'You MUST return ONLY a JSON object with two fields: '
                    '"model_id" (exact id string from the list) and "reason" (one sentence). '
                    'Example: {"model_id": "gpt-4o", "reason": "Best for text tasks."}'
                )
                if prefer_deep_research:
                    router_system += (
                        ' Prefer models that are stronger at long-form reasoning, '
                        'multi-step analysis and research synthesis.'
                    )

                try:
                    router_response = await chat_completion_handler_fn(
                        request,
                        {
                            'model': router_model_id,
                            'messages': [
                                {'role': 'system', 'content': router_system},
                                {'role': 'user', 'content': json.dumps(router_input, ensure_ascii=False)},
                            ],
                            'stream': False,
                            'temperature': env_float('GPTHUB_ROUTER_TEMPERATURE', 0.0),
                            'max_tokens': env_int('GPTHUB_ROUTER_MAX_TOKENS', 180),
                        },
                        user,
                        bypass_filter=True,
                        bypass_system_prompt=True,
                    )
                    router_text = extract_router_output_text(router_response)
                    router_json = extract_router_json(router_text)
                    if router_json:
                        candidate_model_id = router_json.get('model_id')
                        if (
                            isinstance(candidate_model_id, str)
                            and candidate_model_id in routable_model_ids
                            and not is_virtual_model_id(candidate_model_id)
                        ):
                            resolved_model_id = candidate_model_id
                            resolved_capability = infer_request_capability(last_user_prompt)
                            resolution_reason = 'router_model_choice'
                except Exception as e:
                    log.warning('router LLM call failed: %s: %s', e.__class__.__name__, e)

            if resolved_model_id is None:
                resolved_capability = infer_request_capability(last_user_prompt)
                resolved_model_id = pick_preferred_model_for_capability(
                    capability_graph, resolved_capability, available_models,
                    prefer_deep_research=prefer_deep_research,
                )
                resolution_reason = 'router_heuristic_fallback'
        else:
            resolved_capability = requested_capability
            if requested_capability == 'vision':
                inferred = infer_request_capability(last_user_prompt)
                if inferred == 'image_generation':
                    resolved_capability = 'image_generation'

            resolved_model_id = pick_preferred_model_for_capability(
                capability_graph, resolved_capability, available_models,
                prefer_deep_research=prefer_deep_research,
            )
            resolution_reason = (
                'manual_virtual_capability' if mode == 'manual'
                else 'auto_capability_without_router'
            )

        if requested_virtual_model_id and resolved_model_id:
            display_model_id = requested_virtual_model_id

    # Auto fallbacks
    if resolved_model_id is None and mode == 'auto':
        for pool, label in [
            (routable_model_ids, 'auto_fallback_first_available'),
            (chat_compatible_model_ids, 'auto_fallback_first_chat_compatible'),
            (available_model_ids, 'auto_fallback_first_available_any'),
        ]:
            if pool:
                resolved_model_id = pool[0]
                resolved_capability = resolved_capability or 'text'
                resolution_reason = label
                break

    # Reroute image_generation / presentation to text model for the follow-up LLM call.
    for cap_override in ('image_generation', 'presentation'):
        if resolved_capability == cap_override:
            text_model_id = pick_preferred_model_for_capability(
                capability_graph, 'text', available_models,
                prefer_deep_research=prefer_deep_research,
            )
            if text_model_id:
                resolved_model_id = text_model_id
                resolution_reason = f'{resolution_reason}|text_override_for_followup'

    if display_model_id is None and resolved_model_id:
        display_model_id = resolved_model_id

    # Build human-readable explainability metadata
    resolved_model = available_models.get(resolved_model_id) if resolved_model_id else None
    resolved_model_name = (resolved_model.get('name') or resolved_model_id) if resolved_model else resolved_model_id
    routing_explanation = {
        'reason_key': resolution_reason,
        'reason_label': t_routing_reason(resolution_reason),
        'resolved_model_name': resolved_model_name or '',
        'resolved_capability_label': t_cap(resolved_capability) if resolved_capability else '',
        'router_model_id': router_model_id,
    }

    log.info(
        'routing resolved: mode=%s model=%s capability=%s reason=%s',
        mode, resolved_model_id, resolved_capability, resolution_reason,
    )

    return {
        'mode': mode,
        'requested_model_ids': requested_model_ids,
        'resolved_model_id': resolved_model_id,
        'display_model_id': display_model_id,
        'effective_model_ids': [resolved_model_id] if resolved_model_id else [],
        'resolved_capability': resolved_capability,
        'requested_virtual_model_id': requested_virtual_model_id,
        'router_model_id': router_model_id,
        'resolution_reason': resolution_reason,
        'capability_graph': capability_graph,
        'routing_explanation': routing_explanation,
    }
