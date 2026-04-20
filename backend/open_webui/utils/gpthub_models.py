import json
import os
import re
import time
from dataclasses import dataclass
from typing import Any


VIRTUAL_MODEL_PREFIX = 'gpthub:'


@dataclass(frozen=True)
class VirtualModelSpec:
    id: str
    name: str
    capability: str
    description: str
    tags: tuple[str, ...]


VIRTUAL_MODEL_SPECS: tuple[VirtualModelSpec, ...] = (
    VirtualModelSpec(
        id='gpthub:auto',
        name='Auto Router',
        capability='auto',
        description='Automatically picks the best model for your request — just type and go.',
        tags=('GPTHub', 'Virtual', 'Auto'),
    ),
)


CAPABILITY_ORDER: tuple[str, ...] = (
    'text',
    'code',
    'vision',
    'image_generation',
    'audio_transcription',
    'audio_speech',
    'web_search',
    'research',
    'presentation',
)


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


# Keep backward-compat alias used inside this file.
_env_bool = env_bool


def env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default


def env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except Exception:
        return default


def extract_json_object(text: str) -> dict | None:
    """Try to parse a JSON object from *text*, tolerating surrounding noise."""
    if not text:
        return None
    text = text.strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    start = text.find('{')
    end = text.rfind('}')
    if start == -1 or end == -1 or end <= start:
        return None
    candidate = text[start: end + 1]
    try:
        parsed = json.loads(candidate)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


def virtual_models_enabled() -> bool:
    return _env_bool('GPTHUB_ENABLE_VIRTUAL_MODELS', True)


def is_virtual_model_id(model_id: str | None) -> bool:
    return isinstance(model_id, str) and model_id.startswith(VIRTUAL_MODEL_PREFIX)


def is_virtual_model(model: dict[str, Any] | None) -> bool:
    if not isinstance(model, dict):
        return False

    meta = model.get('info', {}).get('meta', {}) if isinstance(model.get('info'), dict) else {}
    if meta.get('gpthub_virtual') is True:
        return True

    return is_virtual_model_id(model.get('id'))


def get_virtual_capability(model: dict[str, Any] | None, model_id: str | None = None) -> str | None:
    if not is_virtual_model(model) and not is_virtual_model_id(model_id):
        return None

    if isinstance(model, dict):
        meta = model.get('info', {}).get('meta', {}) if isinstance(model.get('info'), dict) else {}
        capability = meta.get('gpthub_virtual_capability')
        if isinstance(capability, str) and capability:
            return capability

    if isinstance(model_id, str):
        # Backward compatibility: legacy virtual assistant ids
        if model_id == 'gpthub:code':
            return 'code'
        if model_id == 'gpthub:vision':
            return 'vision'
        if model_id == 'gpthub:web':
            return 'web_search'
        if model_id == 'gpthub:image':
            return 'image_generation'
        if model_id == 'gpthub:research':
            return 'research'

        for spec in VIRTUAL_MODEL_SPECS:
            if spec.id == model_id:
                return spec.capability

    return None


def build_virtual_models() -> list[dict[str, Any]]:
    now = int(time.time())
    models: list[dict[str, Any]] = []
    for spec in VIRTUAL_MODEL_SPECS:
        models.append(
            {
                'id': spec.id,
                'name': spec.name,
                'object': 'model',
                'created': now,
                'owned_by': 'openai',
                'connection_type': 'external',
                'tags': [{'name': tag} for tag in spec.tags],
                'info': {
                    'meta': {
                        'gpthub_virtual': True,
                        'gpthub_virtual_capability': spec.capability,
                        'description': spec.description,
                        'capabilities': _virtual_capabilities(spec.capability),
                    }
                },
            }
        )
    return models


def prepend_virtual_models(models: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not virtual_models_enabled():
        return models

    existing_ids = {model.get('id') for model in models}
    virtuals = [model for model in build_virtual_models() if model['id'] not in existing_ids]
    if not virtuals:
        return models

    return [*virtuals, *models]


def infer_model_capabilities(model: dict[str, Any]) -> set[str]:
    capabilities: set[str] = set()
    meta_caps = (
        model.get('info', {}).get('meta', {}).get('capabilities', {})
        if isinstance(model.get('info'), dict)
        else {}
    )

    if isinstance(meta_caps, dict):
        for key, enabled in meta_caps.items():
            if enabled:
                capabilities.add(str(key))

    model_id = (model.get('id') or '').lower()
    model_name = (model.get('name') or '').lower()
    text = f'{model_id} {model_name}'

    if re.search(r'(coder|code|program|dev|deepseek-r1|qwen3-coder)', text):
        capabilities.add('code')
    if re.search(r'(vision|vl|image-understanding|multimodal)', text):
        capabilities.add('vision')
    if re.search(r'(image|flux|dall|sdxl|stable-diffusion)', text):
        capabilities.add('image_generation')
    if re.search(r'(whisper|asr|transcrib|speech-to-text|audio-stt)', text):
        capabilities.add('audio_transcription')
    if re.search(r'(tts|speech|kokoro|audio-tts)', text):
        capabilities.add('audio_speech')

    if 'image_generation' in capabilities:
        capabilities.add('text')
    if not capabilities:
        capabilities.add('text')

    return capabilities


def build_capability_graph(
    available_models: dict[str, dict[str, Any]],
    candidate_model_ids: list[str],
) -> dict[str, list[str]]:
    graph: dict[str, list[str]] = {capability: [] for capability in CAPABILITY_ORDER}
    graph.setdefault('auto', [])

    for model_id in candidate_model_ids:
        model = available_models.get(model_id)
        if not model:
            continue
        if is_virtual_model(model):
            continue

        inferred_caps = infer_model_capabilities(model)
        for capability in inferred_caps:
            graph.setdefault(capability, [])
            graph[capability].append(model_id)

    # Ensure deterministic order and no duplicates
    for capability, model_ids in graph.items():
        seen = set()
        deduped = []
        for model_id in model_ids:
            if model_id in seen:
                continue
            seen.add(model_id)
            deduped.append(model_id)
        graph[capability] = deduped

    return graph


def infer_request_capability(prompt: str) -> str:
    normalized = (prompt or '').lower()

    # Detect and strip image-attachment markers injected by _extract_last_user_prompt
    # to avoid false positives (the tag contains the word "image").
    has_attached_images = bool(re.search(r'\[user_attached_images=\d+\]', normalized))
    normalized = re.sub(r'\s*\[user_attached_images=\d+\]', '', normalized)

    # When the user attached images, default to vision (image analysis) unless
    # they explicitly ask to generate/draw a NEW image.
    if has_attached_images:
        if re.search(r'(нарис|сгенерируй\s+изображ|создай\s+изображ|сделай\s+изображ)', normalized):
            return 'image_generation'
        return 'vision'

    if re.search(r'(нарис|сгенерируй\s+изображ|создай\s+изображ|сделай\s+изображ|image|illustrat|draw|render|logo|poster)', normalized):
        return 'image_generation'
    if re.search(r'(что на изображ|что изображ|опиши.*фото|расскажи.*фото|проанализир.*фото|vision|analy[sz]e image|caption image|describe.*image|what.*photo)', normalized):
        return 'vision'
    if re.search(
        r'(создай.*презентац|сделай.*презентац|напиши.*презентац|презентац.*тему|'
        r'сгенерир.*презентац|слайды.*тем|сделай.*слайд|'
        r'create.*presentation|make.*presentation|generate.*presentation|build.*presentation|'
        r'create.*slides|make.*slides|write.*presentation|powerpoint|keynote|pptx)',
        normalized,
    ):
        return 'presentation'
    if re.search(r'(код|code|bug|debug|refactor|typescript|javascript|python|sql|regex|api)', normalized):
        return 'code'
    if re.search(r'(audio|speech|voice|transcrib|распознай|расшифруй|аудио|транскриб|запись)', normalized):
        return 'audio_transcription'
    if re.search(
        r'(исследуй|напиши.*отчёт|напиши.*доклад|deep.?research|research.*report|comprehensive.*analysis|'
        r'подготовь.*анализ|подробный.*анализ|detailed.*report)',
        normalized,
    ):
        return 'research'
    if re.search(
        r'(найди в интернет|поищи|найди информ|актуальн|последн.*новост|что сейчас|'
        r'search.*web|find.*online|latest.*news|current.*price|today.*weather)',
        normalized,
    ):
        return 'web_search'

    return 'text'


def _virtual_capabilities(capability: str) -> dict[str, bool]:
    defaults = {
        'vision': False,
        'file_upload': True,
        'file_context': True,
        'web_search': True,
        'image_generation': False,
        'code_interpreter': False,
        'usage': True,
    }

    if capability == 'auto':
        return {
            **defaults,
            'vision': True,
            'image_generation': True,
            'code_interpreter': True,
        }

    if capability == 'code':
        return {
            **defaults,
            'code_interpreter': True,
        }

    if capability == 'vision':
        return {
            **defaults,
            'vision': True,
            'image_generation': True,
        }

    if capability == 'image_generation':
        return {
            **defaults,
            'image_generation': True,
        }

    if capability == 'web_search':
        return {
            **defaults,
            'web_search': True,
        }

    if capability == 'research':
        return {
            **defaults,
            'web_search': True,  # research uses web_search under the hood
            'research': True,
        }

    return defaults
