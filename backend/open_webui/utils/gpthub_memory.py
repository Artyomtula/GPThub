"""
GPTHub Long-Term Memory
=======================
Extracts and stores personal facts about the user from conversations.
All persistence operations (DB, vector store, LLM calls) are injected via
function parameters to avoid circular imports with main.py.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any

from open_webui.utils.gpthub_i18n import t
from open_webui.utils.gpthub_models import extract_json_object
from open_webui.utils.gpthub_router import extract_last_user_prompt, is_non_chat_model

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def normalize_memory_content(text: str) -> str:
    cleaned = re.sub(r'\s+', ' ', (text or '')).strip()
    return cleaned[:280]


def extract_assistant_content_from_response(response: dict) -> str:
    try:
        choices = response.get('choices') or []
        if not choices:
            return ''
        message = choices[0].get('message') or {}
        content = message.get('content')
        return content if isinstance(content, str) else ''
    except Exception:
        return ''


def parse_memory_record(content: str) -> dict | None:
    record = extract_json_object(content)
    if not record:
        return None
    if record.get('schema') != 'gpthub_memory_v1':
        return None
    if not isinstance(record.get('value'), str):
        return None
    return record


def is_memory_record_active(record: dict, now_ts: int | None = None) -> bool:
    now_ts = now_ts or int(time.time())
    if record.get('status') == 'inactive':
        return False
    expires_at = record.get('expires_at')
    if isinstance(expires_at, int) and expires_at > 0 and now_ts > expires_at:
        return False
    return True


def build_memory_record(
    fact_type: str,
    value: str,
    confidence: float,
    ttl_days: int,
) -> dict:
    now_ts = int(time.time())
    expires_at = now_ts + max(ttl_days, 1) * 86400 if ttl_days > 0 else None
    return {
        'schema': 'gpthub_memory_v1',
        'type': fact_type,
        'value': normalize_memory_content(value),
        'confidence': round(float(confidence), 3),
        'status': 'active',
        'source': 'llm_extractor',
        'created_at': now_ts,
        'updated_at': now_ts,
        'last_seen': now_ts,
        'ttl_days': int(ttl_days),
        'expires_at': expires_at,
    }


def memory_extractor_system_prompt(max_facts: int) -> str:
    return t('memory.extractor_system', max_facts=max_facts)


# ---------------------------------------------------------------------------
# Memory-enabled check
# ---------------------------------------------------------------------------


def memory_enabled_for_user(
    enable_memories: bool,
    features: dict | None,
    user_id: str,
    user_permissions: dict,
    *,
    has_permission_fn=None,
) -> bool:
    if not enable_memories:
        return False
    if isinstance(features, dict) and features.get('memory') is False:
        return False
    try:
        if has_permission_fn:
            return has_permission_fn(user_id, 'features.memories', user_permissions)
        return False
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Pick extractor model
# ---------------------------------------------------------------------------


def pick_memory_extractor_model(
    selection_effective: dict,
    available_models: dict[str, dict],
    fallback_model_id: str,
    *,
    is_virtual_model_fn=None,
) -> str:
    from open_webui.utils.gpthub_models import is_virtual_model as _is_virtual

    _is_virtual_fn = is_virtual_model_fn or _is_virtual

    configured = os.getenv('MEMORY_EXTRACTION_MODEL', '').strip()
    if configured and configured in available_models and not is_non_chat_model(available_models.get(configured)):
        return configured

    capability_graph = selection_effective.get('capability_graph') or {}
    for capability in ['text', 'code', 'vision']:
        for model_id in capability_graph.get(capability, []):
            model = available_models.get(model_id)
            if model and not _is_virtual_fn(model) and not is_non_chat_model(model):
                return model_id

    model = available_models.get(fallback_model_id)
    if model and not _is_virtual_fn(model) and not is_non_chat_model(model):
        return fallback_model_id

    for model_id, model in available_models.items():
        if not _is_virtual_fn(model) and not is_non_chat_model(model):
            return model_id

    return fallback_model_id


# ---------------------------------------------------------------------------
# LLM-based extraction
# ---------------------------------------------------------------------------


async def extract_long_term_memory_candidates_llm(
    request,
    user,
    user_prompt: str,
    assistant_content: str,
    selection_effective: dict,
    fallback_model_id: str,
    *,
    chat_completion_handler_fn=None,
) -> list[dict]:
    if not user_prompt:
        return []

    max_facts = max(1, int(os.getenv('MEMORY_EXTRACTION_MAX_FACTS', '4')))
    extractor_model_id = pick_memory_extractor_model(selection_effective, request.app.state.MODELS, fallback_model_id)

    extraction_payload = {
        'model': extractor_model_id,
        'stream': False,
        'messages': [
            {'role': 'system', 'content': memory_extractor_system_prompt(max_facts)},
            {
                'role': 'user',
                'content': (f'User message:\n{user_prompt}\n\nAssistant reply:\n{assistant_content or "(empty)"}\n'),
            },
        ],
        'params': {'temperature': 0},
        'features': {'memory': False, 'web_search': False, 'image_generation': False, 'code_interpreter': False},
    }

    try:
        if not chat_completion_handler_fn:
            return []
        extraction_response = await chat_completion_handler_fn(
            request,
            extraction_payload,
            user,
            bypass_filter=True,
            bypass_system_prompt=True,
        )
    except Exception as e:
        log.warning(f'memory extractor call failed: {e.__class__.__name__}: {e}')
        return []

    if not isinstance(extraction_response, dict):
        return []

    content = extract_assistant_content_from_response(extraction_response)
    parsed = extract_json_object(content) or {}
    facts = parsed.get('facts') if isinstance(parsed, dict) else None
    if not isinstance(facts, list):
        return []

    min_conf = float(os.getenv('MEMORY_EXTRACTION_MIN_CONFIDENCE', '0.72'))
    normalized_facts: list[dict] = []
    for fact in facts[:max_facts]:
        if not isinstance(fact, dict):
            continue
        fact_type = str(fact.get('type') or '').strip().lower()
        value = normalize_memory_content(str(fact.get('value') or ''))
        if not fact_type or not value:
            continue
        try:
            confidence = float(fact.get('confidence', 0.0))
        except Exception:
            confidence = 0.0
        if confidence < min_conf:
            continue
        try:
            ttl_days = int(fact.get('ttl_days', 180))
        except Exception:
            ttl_days = 180
        ttl_days = max(7, min(ttl_days, 3650))
        normalized_facts.append(
            {
                'type': fact_type,
                'value': value,
                'confidence': confidence,
                'ttl_days': ttl_days,
            }
        )

    return normalized_facts


# ---------------------------------------------------------------------------
# Store memories (DB + vector)
# ---------------------------------------------------------------------------

_SINGLETON_TYPES = frozenset(
    {
        'identity',
        'profile',
        'timezone',
        'city',
        'role',
        'project',
        'goal',
        'constraint',
        'preference',
    }
)


async def store_long_term_memories(
    request,
    user,
    candidates: list[dict],
    *,
    memories_model=None,
    vector_db_client=None,
) -> int:
    if not candidates:
        return 0
    if not memories_model:
        return 0

    existing = memories_model.get_memories_by_user_id(user.id) or []
    now_ts = int(time.time())
    existing_records: list[tuple[Any, dict]] = []
    for memory in existing:
        record = parse_memory_record(memory.content or '')
        if not record:
            continue
        existing_records.append((memory, record))

    inserted_count = 0

    for candidate in candidates:
        fact_type = str(candidate.get('type') or '').strip().lower()
        value = normalize_memory_content(str(candidate.get('value') or ''))
        confidence = float(candidate.get('confidence') or 0.0)
        ttl_days = int(candidate.get('ttl_days') or 180)

        if not fact_type or not value:
            continue

        # 1) Update exact active match (same type + same normalized value)
        exact_match = None
        for mem, record in existing_records:
            if not is_memory_record_active(record, now_ts):
                continue
            if str(record.get('type', '')).lower() != fact_type:
                continue
            if normalize_memory_content(str(record.get('value', ''))).lower() == value.lower():
                exact_match = (mem, record)
                break

        if exact_match:
            mem, record = exact_match
            record['last_seen'] = now_ts
            record['updated_at'] = now_ts
            record['confidence'] = max(float(record.get('confidence') or 0.0), confidence)
            record['ttl_days'] = max(int(record.get('ttl_days') or ttl_days), ttl_days)
            if record.get('ttl_days', 0) > 0:
                record['expires_at'] = now_ts + int(record['ttl_days']) * 86400

            updated = memories_model.update_memory_by_id_and_user_id(
                mem.id, user.id, json.dumps(record, ensure_ascii=False)
            )
            if updated and vector_db_client:
                try:
                    vector = await request.app.state.EMBEDDING_FUNCTION(record.get('value', ''), user=user)
                    vector_db_client.upsert(
                        collection_name=f'user-memory-{user.id}',
                        items=[
                            {
                                'id': mem.id,
                                'text': record.get('value', ''),
                                'vector': vector,
                                'metadata': {'created_at': updated.created_at, 'updated_at': updated.updated_at},
                            }
                        ],
                    )
                except Exception as e:
                    log.warning(f'long-term memory embedding update failed: {e.__class__.__name__}: {e}')
            continue

        # 2) Deactivate conflicting singleton fact of same type
        if fact_type in _SINGLETON_TYPES:
            for mem, record in existing_records:
                if not is_memory_record_active(record, now_ts):
                    continue
                if str(record.get('type', '')).lower() != fact_type:
                    continue
                if normalize_memory_content(str(record.get('value', ''))).lower() == value.lower():
                    continue

                record['status'] = 'inactive'
                record['updated_at'] = now_ts
                memories_model.update_memory_by_id_and_user_id(mem.id, user.id, json.dumps(record, ensure_ascii=False))
                if vector_db_client:
                    try:
                        vector_db_client.delete(collection_name=f'user-memory-{user.id}', ids=[mem.id])
                    except Exception as e:
                        log.warning(f'vector DB delete failed for memory {mem.id}: {e.__class__.__name__}: {e}')

        # 3) Insert new active fact
        new_record = build_memory_record(fact_type, value, confidence, ttl_days)
        memory = memories_model.insert_new_memory(user.id, json.dumps(new_record, ensure_ascii=False))
        if not memory:
            continue

        try:
            vector = await request.app.state.EMBEDDING_FUNCTION(new_record['value'], user=user)
            if vector_db_client:
                vector_db_client.upsert(
                    collection_name=f'user-memory-{user.id}',
                    items=[
                        {
                            'id': memory.id,
                            'text': new_record['value'],
                            'vector': vector,
                            'metadata': {'created_at': memory.created_at, 'updated_at': memory.updated_at},
                        }
                    ],
                )
            inserted_count += 1
            existing_records.append((memory, new_record))
        except Exception as e:
            memories_model.delete_memory_by_id_and_user_id(memory.id, user.id)
            log.warning(f'long-term memory embedding failed: {e.__class__.__name__}: {e}')

    return inserted_count


# ---------------------------------------------------------------------------
# Orchestrator: extract + store in one call
# ---------------------------------------------------------------------------


async def run_long_term_memory_write(
    request,
    user,
    metadata: dict,
    form_data: dict,
    model_id_for_fallback: str,
    assistant_content: str = '',
    *,
    chat_completion_handler_fn=None,
    memories_model=None,
    vector_db_client=None,
    event_emitter_fn=None,
) -> int:
    user_prompt = (metadata.get('user_prompt') or extract_last_user_prompt(form_data) or '').strip()
    if not user_prompt:
        return 0

    memory_candidates = await extract_long_term_memory_candidates_llm(
        request,
        user,
        user_prompt,
        assistant_content,
        metadata.get('selection_effective') or {},
        metadata.get('selected_model_id') or form_data.get('model') or model_id_for_fallback,
        chat_completion_handler_fn=chat_completion_handler_fn,
    )
    inserted = await store_long_term_memories(
        request,
        user,
        memory_candidates,
        memories_model=memories_model,
        vector_db_client=vector_db_client,
    )
    if inserted > 0:
        log.info(f'long-term memory updated: inserted={inserted}, user_id={user.id}')
        if event_emitter_fn:
            event_emitter = event_emitter_fn(metadata)
            if event_emitter:
                await event_emitter(
                    {
                        'type': 'chat:memory:updated',
                        'data': {'inserted': inserted},
                    }
                )
    return inserted
