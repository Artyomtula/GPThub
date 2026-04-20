import os
import importlib.util
import pytest
from unittest.mock import patch

# Import gpthub_router directly to avoid the heavy open_webui.__init__ chain.
_ROUTER_PATH = os.path.join(
    os.path.dirname(__file__), os.pardir, os.pardir, 'backend', 'open_webui', 'utils', 'gpthub_router.py'
)

# gpthub_router imports from gpthub_models and gpthub_i18n, so ensure they are importable.
_MODELS_PATH = os.path.join(
    os.path.dirname(__file__), os.pardir, os.pardir, 'backend', 'open_webui', 'utils', 'gpthub_models.py'
)
_mspec = importlib.util.spec_from_file_location('open_webui.utils.gpthub_models', os.path.abspath(_MODELS_PATH))
_mmod = importlib.util.module_from_spec(_mspec)
import sys

sys.modules['open_webui.utils.gpthub_models'] = _mmod
_mspec.loader.exec_module(_mmod)

_I18N_PATH = os.path.join(
    os.path.dirname(__file__), os.pardir, os.pardir, 'backend', 'open_webui', 'utils', 'gpthub_i18n.py'
)
_ispec = importlib.util.spec_from_file_location('open_webui.utils.gpthub_i18n', os.path.abspath(_I18N_PATH))
_imod = importlib.util.module_from_spec(_ispec)
sys.modules['open_webui.utils.gpthub_i18n'] = _imod
_ispec.loader.exec_module(_imod)

_rspec = importlib.util.spec_from_file_location('gpthub_router', os.path.abspath(_ROUTER_PATH))
_rmod = importlib.util.module_from_spec(_rspec)
_rspec.loader.exec_module(_rmod)

extract_last_user_prompt = _rmod.extract_last_user_prompt
parse_model_selection = _rmod.parse_model_selection
select_router_model_id = _rmod.select_router_model_id
extract_router_json = _rmod.extract_router_json
extract_router_output_text = _rmod.extract_router_output_text
pick_first_available_model_for_capability = _rmod.pick_first_available_model_for_capability
pick_preferred_model_for_capability = _rmod.pick_preferred_model_for_capability
is_deep_research_model = _rmod.is_deep_research_model
is_non_chat_model = _rmod.is_non_chat_model
build_voice_ack_text = _rmod.build_voice_ack_text
build_manual_mode_guidance_response = _rmod.build_manual_mode_guidance_response


# ---------------------------------------------------------------------------
# extract_last_user_prompt
# ---------------------------------------------------------------------------


class TestExtractLastUserPrompt:
    def test_simple_string(self):
        form = {'messages': [{'role': 'user', 'content': 'Hello'}]}
        assert extract_last_user_prompt(form) == 'Hello'

    def test_multiple_messages_takes_last_user(self):
        form = {
            'messages': [
                {'role': 'user', 'content': 'First'},
                {'role': 'assistant', 'content': 'Response'},
                {'role': 'user', 'content': 'Second'},
            ]
        }
        assert extract_last_user_prompt(form) == 'Second'

    def test_multipart_content(self):
        form = {
            'messages': [
                {
                    'role': 'user',
                    'content': [
                        {'type': 'text', 'text': 'Describe this'},
                        {'type': 'image_url', 'image_url': {'url': 'data:...'}},
                    ],
                }
            ]
        }
        result = extract_last_user_prompt(form)
        assert 'Describe this' in result
        assert '[user_attached_images=1]' in result

    def test_empty_messages(self):
        assert extract_last_user_prompt({'messages': []}) == ''

    def test_no_messages_key(self):
        assert extract_last_user_prompt({}) == ''

    def test_only_assistant_messages(self):
        form = {'messages': [{'role': 'assistant', 'content': 'Hi'}]}
        assert extract_last_user_prompt(form) == ''

    def test_images_only(self):
        form = {
            'messages': [
                {
                    'role': 'user',
                    'content': [{'type': 'image_url', 'image_url': {'url': 'data:...'}}],
                }
            ]
        }
        result = extract_last_user_prompt(form)
        assert 'user_attached_images=1' in result


# ---------------------------------------------------------------------------
# parse_model_selection
# ---------------------------------------------------------------------------


class TestParseModelSelection:
    def test_auto_mode(self):
        form = {'selection': {'mode': 'auto', 'model_ids': ['gpthub:auto']}}
        mode, ids = parse_model_selection(form)
        assert mode == 'auto'
        assert ids == ['gpthub:auto']

    def test_manual_mode(self):
        form = {'selection': {'mode': 'manual', 'model_ids': ['gpt-4o']}}
        mode, ids = parse_model_selection(form)
        assert mode == 'manual'
        assert ids == ['gpt-4o']

    def test_legacy_mode_fallback(self):
        form = {'model_selection_mode': 'auto'}
        mode, ids = parse_model_selection(form)
        assert mode == 'auto'

    def test_model_field_prepended(self):
        form = {'model': 'gpt-4o', 'selection': {'mode': 'manual', 'model_ids': ['llama-3']}}
        mode, ids = parse_model_selection(form)
        assert ids[0] == 'gpt-4o'
        assert 'llama-3' in ids

    def test_default_manual(self):
        mode, ids = parse_model_selection({})
        assert mode == 'manual'
        assert ids == []

    def test_filters_empty_strings(self):
        form = {'selection': {'mode': 'manual', 'model_ids': ['', 'gpt-4o', '  ']}}
        _, ids = parse_model_selection(form)
        assert '' not in ids
        assert '  ' not in ids


# ---------------------------------------------------------------------------
# select_router_model_id
# ---------------------------------------------------------------------------


class TestSelectRouterModelId:
    def test_configured_env(self):
        models = {'my-router': {'id': 'my-router', 'name': 'Router'}}
        with patch.dict(os.environ, {'GPTHUB_ROUTER_MODEL_ID': 'my-router'}):
            result = select_router_model_id(models, ['my-router'])
            assert result == 'my-router'

    def test_pattern_matching(self):
        models = {
            'some-model': {'id': 'some-model', 'name': 'Some Model'},
            'deepseek-v3': {'id': 'deepseek-v3', 'name': 'DeepSeek V3'},
        }
        result = select_router_model_id(models, ['some-model', 'deepseek-v3'])
        assert result == 'deepseek-v3'

    def test_fallback_to_first(self):
        models = {'plain-model': {'id': 'plain-model', 'name': 'Plain'}}
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop('GPTHUB_ROUTER_MODEL_ID', None)
            result = select_router_model_id(models, ['plain-model'])
            assert result == 'plain-model'

    def test_skips_virtual_models(self):
        models = {
            'gpthub:auto': {'id': 'gpthub:auto', 'info': {'meta': {'gpthub_virtual': True}}},
            'real-model': {'id': 'real-model', 'name': 'Real'},
        }
        with patch.dict(os.environ, {'GPTHUB_ROUTER_MODEL_ID': 'gpthub:auto'}):
            # Configured model is virtual so it's skipped; no pattern matches,
            # so falls back to first in list. Put real-model first.
            result = select_router_model_id(models, ['real-model', 'gpthub:auto'])
            assert result == 'real-model'

    def test_empty_list(self):
        assert select_router_model_id({}, []) is None


# ---------------------------------------------------------------------------
# extract_router_json
# ---------------------------------------------------------------------------


class TestExtractRouterJson:
    def test_plain_json(self):
        result = extract_router_json('{"model_id": "gpt-4o", "reason": "best"}')
        assert result == {'model_id': 'gpt-4o', 'reason': 'best'}

    def test_fenced_json(self):
        text = 'Here is my choice:\n```json\n{"model_id": "llama", "reason": "good"}\n```'
        result = extract_router_json(text)
        assert result['model_id'] == 'llama'

    def test_noise_around_json(self):
        text = 'I think the best model is {"model_id": "x", "reason": "y"} for this task.'
        result = extract_router_json(text)
        assert result['model_id'] == 'x'

    def test_empty(self):
        assert extract_router_json('') is None
        assert extract_router_json(None) is None

    def test_no_json(self):
        assert extract_router_json('just text') is None


# ---------------------------------------------------------------------------
# extract_router_output_text
# ---------------------------------------------------------------------------


class TestExtractRouterOutputText:
    def test_openai_format(self):
        response = {'choices': [{'message': {'content': 'Hello'}}]}
        assert extract_router_output_text(response) == 'Hello'

    def test_output_format(self):
        response = {'output': [{'content': [{'text': 'Part1'}, {'text': 'Part2'}]}]}
        assert 'Part1' in extract_router_output_text(response)
        assert 'Part2' in extract_router_output_text(response)

    def test_empty_response(self):
        assert extract_router_output_text({}) == ''
        assert extract_router_output_text(None) == ''

    def test_multipart_message(self):
        response = {'choices': [{'message': {'content': [{'text': 'a'}, {'text': 'b'}]}}]}
        result = extract_router_output_text(response)
        assert 'a' in result and 'b' in result


# ---------------------------------------------------------------------------
# pick_first_available_model_for_capability
# ---------------------------------------------------------------------------


class TestPickFirstAvailableModel:
    def test_direct_match(self):
        graph = {'code': ['coder-1', 'coder-2'], 'text': ['gpt-4o']}
        assert pick_first_available_model_for_capability(graph, 'code') == 'coder-1'

    def test_fallback(self):
        graph = {'text': ['gpt-4o']}
        assert pick_first_available_model_for_capability(graph, 'code') == 'gpt-4o'

    def test_no_match(self):
        assert pick_first_available_model_for_capability({}, 'code') is None


# ---------------------------------------------------------------------------
# is_deep_research_model
# ---------------------------------------------------------------------------


class TestIsDeepResearchModel:
    def test_deepseek(self):
        assert is_deep_research_model({'id': 'deepseek-r1', 'name': 'DeepSeek R1'}) is True

    def test_o1(self):
        assert is_deep_research_model({'id': 'o1-preview', 'name': 'O1'}) is True

    def test_regular_model(self):
        assert is_deep_research_model({'id': 'gpt-4o-mini', 'name': 'GPT-4o Mini'}) is False

    def test_none(self):
        assert is_deep_research_model(None) is False


# ---------------------------------------------------------------------------
# is_non_chat_model
# ---------------------------------------------------------------------------


class TestIsNonChatModel:
    def test_embedding(self):
        assert is_non_chat_model({'id': 'text-embedding-ada-002', 'name': 'Embedding'}) is True

    def test_whisper(self):
        assert is_non_chat_model({'id': 'whisper-1', 'name': 'Whisper'}) is True

    def test_reranker(self):
        assert is_non_chat_model({'id': 'bge-reranker-v2', 'name': 'BGE Reranker'}) is True

    def test_regular_model(self):
        assert is_non_chat_model({'id': 'gpt-4o', 'name': 'GPT-4o'}) is False

    def test_none(self):
        assert is_non_chat_model(None) is False


# ---------------------------------------------------------------------------
# build_voice_ack_text
# ---------------------------------------------------------------------------


class TestBuildVoiceAckText:
    def test_known_capability(self):
        assert 'изображение' in build_voice_ack_text('image_generation').lower()

    def test_unknown_capability(self):
        result = build_voice_ack_text('unknown')
        assert 'Принял' in result

    def test_none(self):
        result = build_voice_ack_text(None)
        assert 'Принял' in result


# ---------------------------------------------------------------------------
# build_manual_mode_guidance_response
# ---------------------------------------------------------------------------


class TestBuildManualModeGuidance:
    def _make_selection(self, model_id, mode='manual', graph=None):
        return {
            'mode': mode,
            'resolved_model_id': model_id,
            'capability_graph': graph or {'text': ['gpt-4o']},
        }

    def test_returns_none_for_auto_mode(self):
        sel = self._make_selection('gpt-4o', mode='auto')
        result = build_manual_mode_guidance_response({}, sel, {})
        assert result is None

    def test_returns_none_for_virtual_model(self):
        models = {'gpthub:auto': {'id': 'gpthub:auto', 'info': {'meta': {'gpthub_virtual': True}}}}
        sel = self._make_selection('gpthub:auto')
        result = build_manual_mode_guidance_response({}, sel, models)
        assert result is None

    def test_non_chat_model_warning(self):
        models = {
            'text-embedding-ada': {'id': 'text-embedding-ada', 'name': 'Ada Embedding'},
            'gpt-4o': {'id': 'gpt-4o', 'name': 'GPT-4o'},
        }
        form = {'messages': [{'role': 'user', 'content': 'hello'}]}
        sel = self._make_selection('text-embedding-ada', graph={'text': ['gpt-4o']})
        result = build_manual_mode_guidance_response(form, sel, models)
        assert result is not None
        assert (
            'embedding' in result['choices'][0]['message']['content'].lower()
            or 'специализированных' in result['choices'][0]['message']['content']
        )

    def test_image_only_model_for_text(self):
        models = {
            'flux-1': {'id': 'flux-1', 'name': 'Flux', 'info': {'meta': {'capabilities': {'image_generation': True}}}},
            'gpt-4o': {'id': 'gpt-4o', 'name': 'GPT-4o'},
        }
        form = {'messages': [{'role': 'user', 'content': 'расскажи о погоде'}]}
        sel = self._make_selection('flux-1', graph={'text': ['gpt-4o'], 'image_generation': ['flux-1']})
        result = build_manual_mode_guidance_response(form, sel, models)
        assert result is not None
        assert 'генерации изображений' in result['choices'][0]['message']['content']

    def test_no_guidance_needed(self):
        models = {'gpt-4o': {'id': 'gpt-4o', 'name': 'GPT-4o'}}
        form = {'messages': [{'role': 'user', 'content': 'hello'}]}
        sel = self._make_selection('gpt-4o', graph={'text': ['gpt-4o']})
        result = build_manual_mode_guidance_response(form, sel, models)
        assert result is None

    def test_pick_preferred_with_deep_research(self):
        graph = {
            'text': ['gpt-4o', 'deepseek-r1'],
            'code': ['gpt-4o'],
        }
        models = {
            'gpt-4o': {'id': 'gpt-4o', 'name': 'GPT-4o'},
            'deepseek-r1': {'id': 'deepseek-r1', 'name': 'DeepSeek R1'},
        }
        result = pick_preferred_model_for_capability(graph, 'text', models, prefer_deep_research=True)
        assert result == 'deepseek-r1'
