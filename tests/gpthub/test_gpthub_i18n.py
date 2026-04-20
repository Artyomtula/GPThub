import os
import sys
import importlib.util
import pytest

# ---------------------------------------------------------------------------
# Direct-load gpthub_i18n to avoid heavy open_webui.__init__ chain
# ---------------------------------------------------------------------------

_I18N_PATH = os.path.join(
    os.path.dirname(__file__), os.pardir, os.pardir, 'backend', 'open_webui', 'utils', 'gpthub_i18n.py'
)
_spec = importlib.util.spec_from_file_location('gpthub_i18n', os.path.abspath(_I18N_PATH))
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

get_locale = _mod.get_locale
t = _mod.t
t_cap = _mod.t_cap
t_routing_reason = _mod.t_routing_reason


# ---------------------------------------------------------------------------
# get_locale
# ---------------------------------------------------------------------------


class TestGetLocale:
    def test_default_is_ru(self):
        os.environ.pop('GPTHUB_LOCALE', None)
        assert get_locale() == 'ru'

    def test_env_override(self):
        os.environ['GPTHUB_LOCALE'] = 'en'
        try:
            assert get_locale() == 'en'
        finally:
            os.environ.pop('GPTHUB_LOCALE', None)

    def test_trims_and_lowercases(self):
        os.environ['GPTHUB_LOCALE'] = '  EN  '
        try:
            assert get_locale() == 'en'
        finally:
            os.environ.pop('GPTHUB_LOCALE', None)


# ---------------------------------------------------------------------------
# t() — basic translation
# ---------------------------------------------------------------------------


class TestT:
    def test_known_key_ru(self):
        result = t('voice_ack.code', locale='ru')
        assert 'код' in result.lower() or 'Пишу' in result

    def test_known_key_en(self):
        result = t('voice_ack.code', locale='en')
        assert 'code' in result.lower()

    def test_unknown_key_returns_key(self):
        assert t('nonexistent.key') == 'nonexistent.key'

    def test_fallback_to_en(self):
        # Use a key that exists; request locale "xx" which doesn't exist
        result = t('voice_ack.default', locale='xx')
        # Should fall back to English
        assert 'Got it' in result or 'working' in result

    def test_format_kwargs(self):
        result = t('guidance.image_only_model', locale='en', model_name='TestModel', switch='click here')
        assert 'TestModel' in result
        assert 'click here' in result

    def test_format_missing_kwarg_safe(self):
        # Should not crash if a kwarg is missing — just returns string with placeholder
        result = t('guidance.image_only_model', locale='en')
        assert isinstance(result, str)

    def test_uses_env_locale(self):
        os.environ['GPTHUB_LOCALE'] = 'en'
        try:
            result = t('voice_ack.default')
            assert 'Got it' in result
        finally:
            os.environ.pop('GPTHUB_LOCALE', None)


# ---------------------------------------------------------------------------
# t_cap()
# ---------------------------------------------------------------------------


class TestTCap:
    def test_known_capability_ru(self):
        assert t_cap('text', locale='ru') == 'Текст'

    def test_known_capability_en(self):
        assert t_cap('text', locale='en') == 'Text'

    def test_unknown_capability(self):
        result = t_cap('unknown_cap', locale='en')
        assert result == 'cap.unknown_cap'  # key itself


# ---------------------------------------------------------------------------
# t_routing_reason()
# ---------------------------------------------------------------------------


class TestTRoutingReason:
    def test_manual_requested_ru(self):
        result = t_routing_reason('manual_requested', locale='ru')
        assert 'вручную' in result.lower()

    def test_manual_requested_en(self):
        result = t_routing_reason('manual_requested', locale='en')
        assert 'Manually' in result

    def test_router_model_choice(self):
        result = t_routing_reason('router_model_choice', locale='en')
        assert 'LLM' in result

    def test_pipe_suffix_stripped(self):
        result = t_routing_reason('router_model_choice|text_override_for_followup', locale='en')
        assert 'LLM' in result

    def test_unknown_reason(self):
        result = t_routing_reason('some_new_reason', locale='en')
        assert isinstance(result, str)

    def test_empty_reason(self):
        result = t_routing_reason('', locale='en')
        assert 'Automatic' in result  # default


# ---------------------------------------------------------------------------
# All string keys have both en and ru
# ---------------------------------------------------------------------------


class TestCatalogue:
    def test_all_keys_have_en_and_ru(self):
        for key, entry in _mod._STRINGS.items():
            assert 'en' in entry, f"Key '{key}' missing 'en' translation"
            assert 'ru' in entry, f"Key '{key}' missing 'ru' translation"
            assert isinstance(entry['en'], str) and len(entry['en']) > 0, f"Key '{key}' has empty 'en'"
            assert isinstance(entry['ru'], str) and len(entry['ru']) > 0, f"Key '{key}' has empty 'ru'"
