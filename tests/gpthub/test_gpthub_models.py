import os
import sys
import importlib.util
import pytest
from unittest.mock import patch

# Import gpthub_models directly to avoid pulling in open_webui.__init__
# which requires heavy dependencies (typer, uvicorn, etc.).
_MODELS_PATH = os.path.join(
    os.path.dirname(__file__), os.pardir, os.pardir, "backend", "open_webui", "utils", "gpthub_models.py"
)
_spec = importlib.util.spec_from_file_location("gpthub_models", os.path.abspath(_MODELS_PATH))
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

VIRTUAL_MODEL_PREFIX = _mod.VIRTUAL_MODEL_PREFIX
VIRTUAL_MODEL_SPECS = _mod.VIRTUAL_MODEL_SPECS
CAPABILITY_ORDER = _mod.CAPABILITY_ORDER
VirtualModelSpec = _mod.VirtualModelSpec
env_bool = _mod.env_bool
env_int = _mod.env_int
env_float = _mod.env_float
extract_json_object = _mod.extract_json_object
virtual_models_enabled = _mod.virtual_models_enabled
is_virtual_model_id = _mod.is_virtual_model_id
is_virtual_model = _mod.is_virtual_model
get_virtual_capability = _mod.get_virtual_capability
build_virtual_models = _mod.build_virtual_models
prepend_virtual_models = _mod.prepend_virtual_models
infer_model_capabilities = _mod.infer_model_capabilities
build_capability_graph = _mod.build_capability_graph
infer_request_capability = _mod.infer_request_capability


# ---------------------------------------------------------------------------
# env_bool / env_int / env_float
# ---------------------------------------------------------------------------

class TestEnvBool:
    def test_default_true(self):
        with patch.dict(os.environ, {}, clear=True):
            assert env_bool("MISSING_VAR", True) is True

    def test_default_false(self):
        with patch.dict(os.environ, {}, clear=True):
            assert env_bool("MISSING_VAR", False) is False

    @pytest.mark.parametrize("val", ["1", "true", "True", "TRUE", "yes", "YES", "on", " ON "])
    def test_truthy(self, val):
        with patch.dict(os.environ, {"TEST_VAR": val}):
            assert env_bool("TEST_VAR", False) is True

    @pytest.mark.parametrize("val", ["0", "false", "no", "off", "random", ""])
    def test_falsy(self, val):
        with patch.dict(os.environ, {"TEST_VAR": val}):
            assert env_bool("TEST_VAR", True) is False


class TestEnvInt:
    def test_default(self):
        assert env_int("MISSING_VAR", 42) == 42

    def test_valid(self):
        with patch.dict(os.environ, {"TEST_VAR": "100"}):
            assert env_int("TEST_VAR", 0) == 100

    def test_invalid_falls_back(self):
        with patch.dict(os.environ, {"TEST_VAR": "not_a_number"}):
            assert env_int("TEST_VAR", 7) == 7


class TestEnvFloat:
    def test_default(self):
        assert env_float("MISSING_VAR", 3.14) == 3.14

    def test_valid(self):
        with patch.dict(os.environ, {"TEST_VAR": "2.5"}):
            assert env_float("TEST_VAR", 0.0) == 2.5

    def test_invalid_falls_back(self):
        with patch.dict(os.environ, {"TEST_VAR": "abc"}):
            assert env_float("TEST_VAR", 1.0) == 1.0


# ---------------------------------------------------------------------------
# extract_json_object
# ---------------------------------------------------------------------------

class TestExtractJsonObject:
    def test_clean_json(self):
        assert extract_json_object('{"key": "value"}') == {"key": "value"}

    def test_json_with_surrounding_noise(self):
        text = 'Here is the result: {"a": 1} -- done'
        assert extract_json_object(text) == {"a": 1}

    def test_empty_string(self):
        assert extract_json_object("") is None

    def test_none_like(self):
        assert extract_json_object("   ") is None

    def test_no_json(self):
        assert extract_json_object("just plain text") is None

    def test_array_not_object(self):
        assert extract_json_object("[1, 2, 3]") is None

    def test_nested_object(self):
        text = '{"outer": {"inner": true}}'
        result = extract_json_object(text)
        assert result == {"outer": {"inner": True}}

    def test_multiple_objects_returns_none_for_invalid_span(self):
        text = '{"a": 1} some text {"b": 2}'
        # The span from first '{' to last '}' is not valid JSON
        assert extract_json_object(text) is None

    def test_broken_json(self):
        assert extract_json_object('{"key": }') is None


# ---------------------------------------------------------------------------
# Virtual model identity
# ---------------------------------------------------------------------------

class TestVirtualModelId:
    def test_prefix(self):
        assert is_virtual_model_id("gpthub:auto") is True
        assert is_virtual_model_id("gpthub:code") is True

    def test_non_virtual(self):
        assert is_virtual_model_id("gpt-4o") is False
        assert is_virtual_model_id("") is False
        assert is_virtual_model_id(None) is False


class TestIsVirtualModel:
    def test_by_meta_flag(self):
        model = {"id": "custom", "info": {"meta": {"gpthub_virtual": True}}}
        assert is_virtual_model(model) is True

    def test_by_id_prefix(self):
        model = {"id": "gpthub:vision"}
        assert is_virtual_model(model) is True

    def test_non_virtual(self):
        model = {"id": "gpt-4o", "info": {"meta": {}}}
        assert is_virtual_model(model) is False

    def test_none(self):
        assert is_virtual_model(None) is False

    def test_not_dict(self):
        assert is_virtual_model("string") is False


# ---------------------------------------------------------------------------
# get_virtual_capability
# ---------------------------------------------------------------------------

class TestGetVirtualCapability:
    def test_from_meta(self):
        model = {
            "id": "gpthub:custom",
            "info": {"meta": {"gpthub_virtual": True, "gpthub_virtual_capability": "code"}},
        }
        assert get_virtual_capability(model) == "code"

    def test_legacy_code(self):
        assert get_virtual_capability(None, "gpthub:code") == "code"

    def test_legacy_vision(self):
        assert get_virtual_capability(None, "gpthub:vision") == "vision"

    def test_legacy_web(self):
        assert get_virtual_capability(None, "gpthub:web") == "web_search"

    def test_legacy_image(self):
        assert get_virtual_capability(None, "gpthub:image") == "image_generation"

    def test_legacy_research(self):
        assert get_virtual_capability(None, "gpthub:research") == "research"

    def test_auto_from_spec(self):
        assert get_virtual_capability(None, "gpthub:auto") == "auto"

    def test_non_virtual_returns_none(self):
        assert get_virtual_capability({"id": "gpt-4o"}, "gpt-4o") is None


# ---------------------------------------------------------------------------
# build_virtual_models / prepend_virtual_models
# ---------------------------------------------------------------------------

class TestBuildVirtualModels:
    def test_returns_list(self):
        models = build_virtual_models()
        assert isinstance(models, list)
        assert len(models) == len(VIRTUAL_MODEL_SPECS)

    def test_model_structure(self):
        models = build_virtual_models()
        m = models[0]
        assert m["id"] == "gpthub:auto"
        assert m["info"]["meta"]["gpthub_virtual"] is True


class TestPrependVirtualModels:
    def test_prepends(self):
        real = [{"id": "gpt-4o"}]
        result = prepend_virtual_models(real)
        assert result[0]["id"].startswith("gpthub:")
        assert result[-1]["id"] == "gpt-4o"

    def test_no_duplicates(self):
        existing = build_virtual_models()
        result = prepend_virtual_models(existing)
        ids = [m["id"] for m in result]
        assert len(ids) == len(set(ids))

    def test_disabled(self):
        with patch.dict(os.environ, {"GPTHUB_ENABLE_VIRTUAL_MODELS": "false"}):
            real = [{"id": "gpt-4o"}]
            result = prepend_virtual_models(real)
            assert result is real


# ---------------------------------------------------------------------------
# infer_model_capabilities
# ---------------------------------------------------------------------------

class TestInferModelCapabilities:
    def test_code_by_name(self):
        model = {"id": "deepseek-coder-v2", "name": "DeepSeek Coder"}
        caps = infer_model_capabilities(model)
        assert "code" in caps

    def test_vision_by_meta(self):
        model = {"id": "gpt-4o", "name": "GPT-4o", "info": {"meta": {"capabilities": {"vision": True}}}}
        caps = infer_model_capabilities(model)
        assert "vision" in caps

    def test_default_is_text(self):
        model = {"id": "generic-model", "name": "Generic"}
        caps = infer_model_capabilities(model)
        assert "text" in caps

    def test_image_gen_implies_text(self):
        model = {"id": "dall-e-3", "name": "DALL-E 3"}
        caps = infer_model_capabilities(model)
        assert "image_generation" in caps
        assert "text" in caps


# ---------------------------------------------------------------------------
# build_capability_graph
# ---------------------------------------------------------------------------

class TestBuildCapabilityGraph:
    def test_builds_graph(self):
        models = {
            "coder-1": {"id": "coder-1", "name": "SuperCoder"},
            "gpt-4o": {"id": "gpt-4o", "name": "GPT-4o"},
        }
        graph = build_capability_graph(models, ["coder-1", "gpt-4o"])
        assert "code" in graph
        assert "coder-1" in graph["code"]

    def test_skips_virtual(self):
        models = {
            "gpthub:auto": {"id": "gpthub:auto", "info": {"meta": {"gpthub_virtual": True}}},
            "gpt-4o": {"id": "gpt-4o", "name": "GPT-4o"},
        }
        graph = build_capability_graph(models, ["gpthub:auto", "gpt-4o"])
        for cap, ids in graph.items():
            assert "gpthub:auto" not in ids

    def test_no_duplicates(self):
        models = {"m1": {"id": "m1", "name": "m1"}}
        graph = build_capability_graph(models, ["m1", "m1"])
        for ids in graph.values():
            assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# infer_request_capability
# ---------------------------------------------------------------------------

class TestInferRequestCapability:
    def test_image_generation_ru(self):
        assert infer_request_capability("нарисуй кота") == "image_generation"

    def test_image_generation_en(self):
        assert infer_request_capability("draw a cat") == "image_generation"

    def test_code(self):
        assert infer_request_capability("напиши код на python") == "code"

    def test_vision_ru(self):
        assert infer_request_capability("что на изображении?") == "vision"

    def test_presentation(self):
        assert infer_request_capability("создай презентацию на тему AI") == "presentation"

    def test_web_search(self):
        assert infer_request_capability("найди в интернете цену биткоина") == "web_search"

    def test_research(self):
        assert infer_request_capability("исследуй влияние AI на рынок труда") == "research"

    def test_default_is_text(self):
        assert infer_request_capability("привет, как дела?") == "text"

    def test_empty(self):
        assert infer_request_capability("") == "text"

    def test_attached_images_default_vision(self):
        assert infer_request_capability("описи это [user_attached_images=2]") == "vision"

    def test_attached_images_explicit_draw(self):
        assert infer_request_capability("нарисуй похожее [user_attached_images=1]") == "image_generation"
