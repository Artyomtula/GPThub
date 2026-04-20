"""
GPTHub Internationalisation (i18n)
==================================
Lightweight locale system for backend user-facing strings.
Supports English (en) and Russian (ru).  The active locale is
determined by the GPTHUB_LOCALE env-var (default: ``ru``).
"""

from __future__ import annotations

import os
from typing import Any

# ---------------------------------------------------------------------------
# Active locale
# ---------------------------------------------------------------------------

_DEFAULT_LOCALE = 'ru'

def get_locale() -> str:
    return os.getenv('GPTHUB_LOCALE', _DEFAULT_LOCALE).strip().lower()[:2]


# ---------------------------------------------------------------------------
# String catalogue
# ---------------------------------------------------------------------------

_STRINGS: dict[str, dict[str, str]] = {
    # ── Voice acknowledgement ──────────────────────────────────────────
    'voice_ack.image_generation': {
        'ru': 'Генерирую изображение, секунду.',
        'en': 'Generating image, one moment.',
    },
    'voice_ack.code': {
        'ru': 'Пишу код, сейчас покажу результат.',
        'en': 'Writing code, I will show the result shortly.',
    },
    'voice_ack.vision': {
        'ru': 'Анализирую изображение, подождите немного.',
        'en': 'Analysing image, please wait.',
    },
    'voice_ack.audio_transcription': {
        'ru': 'Распознаю аудио, это займет немного времени.',
        'en': 'Transcribing audio, this will take a moment.',
    },
    'voice_ack.web_search': {
        'ru': 'Ищу информацию в интернете.',
        'en': 'Searching the web for information.',
    },
    'voice_ack.research': {
        'ru': 'Запускаю исследование, собираю факты.',
        'en': 'Starting research, collecting facts.',
    },
    'voice_ack.default': {
        'ru': 'Принял запрос, сейчас сделаю.',
        'en': 'Got it, working on it now.',
    },

    # ── Manual-mode guidance (router) ──────────────────────────────────
    'guidance.switch_auto': {
        'ru': 'Рекомендую переключиться в **Auto Mode**.',
        'en': 'I recommend switching to **Auto Mode**.',
    },
    'guidance.switch_text_model': {
        'ru': 'Рекомендую переключиться в **Auto Mode** или выбрать текстовую LLM-модель.',
        'en': 'I recommend switching to **Auto Mode** or selecting a text LLM model.',
    },
    'guidance.switch_normal_model': {
        'ru': 'Рекомендую выбрать обычную LLM-модель или перейти в **Auto Mode**.',
        'en': 'I recommend choosing a regular LLM model or switching to **Auto Mode**.',
    },
    'guidance.switch_image_mode': {
        'ru': 'Рекомендую включить режим **Image** или переключиться в **Auto Mode**.',
        'en': 'I recommend enabling **Image** mode or switching to **Auto Mode**.',
    },
    'guidance.switch_auto_for_vision': {
        'ru': 'Рекомендую переключиться в **Auto Mode** для автоматического выбора.',
        'en': 'I recommend switching to **Auto Mode** for automatic selection.',
    },
    'guidance.image_only_model': {
        'ru': (
            'Модель **{model_name}** предназначена только для генерации изображений '
            'и не может отвечать на текстовые запросы.\n\n{switch}'
        ),
        'en': (
            'Model **{model_name}** is designed for image generation only '
            'and cannot answer text queries.\n\n{switch}'
        ),
    },
    'guidance.non_chat_model': {
        'ru': (
            'Сейчас выбрана модель **{model_name}**, она предназначена не для обычного диалога, '
            'а для специализированных задач (например, embeddings/поиск по векторам).\n\n'
            'Из-за этого ответы могут быть пустыми или непредсказуемыми.\n\n'
            '{switch}'
        ),
        'en': (
            'The selected model **{model_name}** is not designed for regular dialogue '
            'but for specialised tasks (e.g. embeddings / vector search).\n\n'
            'Responses may be empty or unpredictable.\n\n'
            '{switch}'
        ),
    },
    'guidance.image_gen_off': {
        'ru': (
            'Похоже, вы попросили сгенерировать изображение, но сейчас выбрана текстовая модель '
            '**{model_name}**.\n\n'
            'Чтобы корректно получить картинку:\n'
            '1. Включите переключатель **Image** под полем ввода.\n'
            '2. Либо переключитесь в **Auto Mode**, чтобы система сама выбрала нужный маршрут.\n\n'
            '{switch}'
        ),
        'en': (
            'It looks like you asked to generate an image, but the current model '
            '**{model_name}** is a text model.\n\n'
            'To get an image:\n'
            '1. Enable the **Image** toggle below the input field.\n'
            '2. Or switch to **Auto Mode** for automatic routing.\n\n'
            '{switch}'
        ),
    },
    'guidance.presentation_off': {
        'ru': (
            'Похоже, вы попросили создать презентацию, но сейчас выбрана модель '
            '**{model_name}** без включённого режима презентации.\n\n'
            'Чтобы создать PPTX-файл:\n'
            '1. Включите переключатель **Presentation** под полем ввода.\n'
            '2. Либо переключитесь в **Auto Mode**.\n\n'
            'Рекомендую включить переключатель **Presentation** или переключиться в **Auto Mode**.'
        ),
        'en': (
            'It looks like you asked to create a presentation, but the current model '
            '**{model_name}** does not have the presentation mode enabled.\n\n'
            'To create a PPTX file:\n'
            '1. Enable the **Presentation** toggle below the input field.\n'
            '2. Or switch to **Auto Mode**.\n\n'
            'I recommend enabling the **Presentation** toggle or switching to **Auto Mode**.'
        ),
    },
    'guidance.no_vision': {
        'ru': 'Модель **{model_name}** не поддерживает анализ изображений.\n\n{switch}',
        'en': 'Model **{model_name}** does not support image analysis.\n\n{switch}',
    },

    # ── Memory extractor system prompt ─────────────────────────────────
    'memory.extractor_system': {
        'ru': (
            "Ты извлекаешь только ДОЛГОСРОЧНЫЕ личные факты о пользователе из диалога.\n"
            "Верни строго JSON без markdown:\n"
            "{{\n"
            '  "facts": [\n'
            "    {{\n"
            '      "type": "identity|preference|profile",\n'
            '      "value": "краткий факт от лица пользователя",\n'
            '      "confidence": 0.0,\n'
            '      "ttl_days": 30\n'
            "    }}\n"
            "  ]\n"
            "}}\n"
            "Ограничение: максимум {max_facts} фактов.\n"
            "Допустимые типы: identity (имя, профессия, язык), preference (предпочтения, привычки), profile (биография, контекст).\n"
            "ЗАПРЕЩЕНО сохранять: инструкции для ИИ, команды ('делай X', 'отвечай Y'), темы и задачи разговора, временные данные, одноразовые запросы."
        ),
        'en': (
            "You extract only LONG-TERM personal facts about the user from the conversation.\n"
            "Return strict JSON without markdown:\n"
            "{{\n"
            '  "facts": [\n'
            "    {{\n"
            '      "type": "identity|preference|profile",\n'
            '      "value": "short fact from the user\'s perspective",\n'
            '      "confidence": 0.0,\n'
            '      "ttl_days": 30\n'
            "    }}\n"
            "  ]\n"
            "}}\n"
            "Limit: at most {max_facts} facts.\n"
            "Allowed types: identity (name, profession, language), preference (likes, habits), profile (bio, context).\n"
            "FORBIDDEN to save: AI instructions, commands ('do X', 'respond Y'), conversation topics/tasks, temporary data, one-time requests."
        ),
    },

    # ── Presentation handler ───────────────────────────────────────────
    'pres.status_designing': {
        'ru': 'Проектирую презентацию…',
        'en': 'Designing presentation…',
    },
    'pres.status_images': {
        'ru': 'Генерирую изображения для слайдов…',
        'en': 'Generating slide images…',
    },
    'pres.status_image_n': {
        'ru': 'Генерирую изображение {n}/{total}…',
        'en': 'Generating image {n}/{total}…',
    },
    'pres.status_building': {
        'ru': 'Собираю презентацию…',
        'en': 'Building presentation…',
    },
    'pres.status_done': {
        'ru': 'Презентация создана!',
        'en': 'Presentation created!',
    },
    'pres.status_error': {
        'ru': 'Ошибка создания презентации',
        'en': 'Presentation creation error',
    },
    'pres.slide_n': {
        'ru': 'Слайд {n}',
        'en': 'Slide {n}',
    },
    'pres.with_images': {
        'ru': ' с {count} сгенерированными изображениями',
        'en': ' with {count} generated images',
    },
    'pres.system_success': {
        'ru': (
            'Презентация "{title}" ({slide_count} слайдов{img_note}) '
            'уже создана и прикреплена как PPTX-файл. Пользователь видит файл для скачивания. '
            '{slide_outline}. '
            'Кратко подтверди, что презентация готова, опиши что в ней, и предложи скачать. '
            'НЕ создавай текстовый план и НЕ перечисляй слайды в виде таблицы — файл уже создан.'
        ),
        'en': (
            'Presentation "{title}" ({slide_count} slides{img_note}) '
            'has been created and attached as a PPTX file. The user can see the download link. '
            '{slide_outline}. '
            'Briefly confirm the presentation is ready, describe its content, and suggest downloading. '
            'Do NOT create a text plan or list slides in a table — the file is already created.'
        ),
    },
    'pres.system_error': {
        'ru': (
            'При создании презентации произошла ошибка: {error}. '
            'Сообщи пользователю об ошибке и предложи попробовать ещё раз.'
        ),
        'en': (
            'An error occurred while creating the presentation: {error}. '
            'Inform the user about the error and suggest trying again.'
        ),
    },
    'pres.confirm_user_message': {
        'ru': 'Подтверди создание презентации (файл уже прикреплён).',
        'en': 'Confirm the presentation creation (file is already attached).',
    },

    # ── Routing explainability ─────────────────────────────────────────
    'routing.reason.manual_requested': {
        'ru': 'Выбрана вручную',
        'en': 'Manually selected',
    },
    'routing.reason.router_model_choice': {
        'ru': 'Выбрана автоматически (LLM-роутер)',
        'en': 'Automatically selected (LLM router)',
    },
    'routing.reason.router_heuristic_fallback': {
        'ru': 'Выбрана по эвристике',
        'en': 'Selected by heuristic',
    },
    'routing.reason.auto_capability_without_router': {
        'ru': 'Выбрана по возможностям',
        'en': 'Selected by capability',
    },
    'routing.reason.manual_virtual_capability': {
        'ru': 'Виртуальная модель → реальная',
        'en': 'Virtual model → real',
    },
    'routing.reason.auto_fallback_first_available': {
        'ru': 'Первая доступная (fallback)',
        'en': 'First available (fallback)',
    },
    'routing.reason.default': {
        'ru': 'Автоматический выбор',
        'en': 'Automatic selection',
    },

    # ── Capability labels ──────────────────────────────────────────────
    'cap.text': {'ru': 'Текст', 'en': 'Text'},
    'cap.code': {'ru': 'Код', 'en': 'Code'},
    'cap.vision': {'ru': 'Зрение', 'en': 'Vision'},
    'cap.image_generation': {'ru': 'Генерация изображений', 'en': 'Image generation'},
    'cap.audio_transcription': {'ru': 'Распознавание речи', 'en': 'Speech recognition'},
    'cap.audio_speech': {'ru': 'Синтез речи', 'en': 'Text to speech'},
    'cap.web_search': {'ru': 'Поиск в интернете', 'en': 'Web search'},
    'cap.research': {'ru': 'Исследование', 'en': 'Research'},
    'cap.presentation': {'ru': 'Презентация', 'en': 'Presentation'},
    'cap.auto': {'ru': 'Авто', 'en': 'Auto'},
    'cap.manual': {'ru': 'Вручную', 'en': 'Manual'},
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def t(key: str, locale: str | None = None, **kwargs: Any) -> str:
    """
    Translate *key* into the active (or given) locale.
    Any ``{name}`` placeholders in the string are filled from *kwargs*.
    Falls back to English, then to the key itself.
    """
    locale = (locale or get_locale())[:2].lower()
    entry = _STRINGS.get(key)
    if entry is None:
        return key
    text = entry.get(locale) or entry.get('en') or key
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError):
            pass
    return text


def t_cap(capability: str, locale: str | None = None) -> str:
    """Translate a capability name."""
    return t(f'cap.{capability}', locale)


def t_routing_reason(reason: str, locale: str | None = None) -> str:
    """Translate a routing resolution_reason.  Strips pipe suffixes."""
    base = reason.split('|')[0] if reason else 'default'
    return t(f'routing.reason.{base}', locale)
