import os
import sys
import importlib.util
import time
import pytest

# Load gpthub_models first (dependency of gpthub_memory).
_MODELS_PATH = os.path.join(
    os.path.dirname(__file__), os.pardir, os.pardir, "backend", "open_webui", "utils", "gpthub_models.py"
)
_mspec = importlib.util.spec_from_file_location("open_webui.utils.gpthub_models", os.path.abspath(_MODELS_PATH))
_mmod = importlib.util.module_from_spec(_mspec)
sys.modules["open_webui.utils.gpthub_models"] = _mmod
_mspec.loader.exec_module(_mmod)

# Load gpthub_i18n (dependency of gpthub_router).
_I18N_PATH = os.path.join(
    os.path.dirname(__file__), os.pardir, os.pardir, "backend", "open_webui", "utils", "gpthub_i18n.py"
)
_ispec = importlib.util.spec_from_file_location("open_webui.utils.gpthub_i18n", os.path.abspath(_I18N_PATH))
_imod = importlib.util.module_from_spec(_ispec)
sys.modules["open_webui.utils.gpthub_i18n"] = _imod
_ispec.loader.exec_module(_imod)

# Load gpthub_router (dependency of gpthub_memory).
_ROUTER_PATH = os.path.join(
    os.path.dirname(__file__), os.pardir, os.pardir, "backend", "open_webui", "utils", "gpthub_router.py"
)
_rspec = importlib.util.spec_from_file_location("open_webui.utils.gpthub_router", os.path.abspath(_ROUTER_PATH))
_rmod = importlib.util.module_from_spec(_rspec)
sys.modules["open_webui.utils.gpthub_router"] = _rmod
_rspec.loader.exec_module(_rmod)

# Load gpthub_memory.
_MEMORY_PATH = os.path.join(
    os.path.dirname(__file__), os.pardir, os.pardir, "backend", "open_webui", "utils", "gpthub_memory.py"
)
_memspec = importlib.util.spec_from_file_location("gpthub_memory", os.path.abspath(_MEMORY_PATH))
_memmod = importlib.util.module_from_spec(_memspec)
_memspec.loader.exec_module(_memmod)

normalize_memory_content = _memmod.normalize_memory_content
extract_assistant_content_from_response = _memmod.extract_assistant_content_from_response
parse_memory_record = _memmod.parse_memory_record
is_memory_record_active = _memmod.is_memory_record_active
build_memory_record = _memmod.build_memory_record
memory_extractor_system_prompt = _memmod.memory_extractor_system_prompt
memory_enabled_for_user = _memmod.memory_enabled_for_user


# ---------------------------------------------------------------------------
# normalize_memory_content
# ---------------------------------------------------------------------------

class TestNormalizeMemoryContent:
    def test_strips_whitespace(self):
        assert normalize_memory_content("  hello  world  ") == "hello world"

    def test_collapses_newlines(self):
        assert normalize_memory_content("line1\n\nline2\t\ttab") == "line1 line2 tab"

    def test_truncates_to_280(self):
        long_text = "a" * 500
        assert len(normalize_memory_content(long_text)) == 280

    def test_empty(self):
        assert normalize_memory_content("") == ""

    def test_none_safe(self):
        assert normalize_memory_content(None) == ""


# ---------------------------------------------------------------------------
# extract_assistant_content_from_response
# ---------------------------------------------------------------------------

class TestExtractAssistantContent:
    def test_openai_format(self):
        response = {"choices": [{"message": {"content": "Hello user"}}]}
        assert extract_assistant_content_from_response(response) == "Hello user"

    def test_empty_choices(self):
        assert extract_assistant_content_from_response({"choices": []}) == ""

    def test_no_choices(self):
        assert extract_assistant_content_from_response({}) == ""

    def test_non_string_content(self):
        response = {"choices": [{"message": {"content": 42}}]}
        assert extract_assistant_content_from_response(response) == ""


# ---------------------------------------------------------------------------
# parse_memory_record
# ---------------------------------------------------------------------------

class TestParseMemoryRecord:
    def test_valid_record(self):
        content = '{"schema": "gpthub_memory_v1", "type": "identity", "value": "John"}'
        record = parse_memory_record(content)
        assert record is not None
        assert record["value"] == "John"

    def test_wrong_schema(self):
        content = '{"schema": "other_v1", "type": "identity", "value": "John"}'
        assert parse_memory_record(content) is None

    def test_missing_value(self):
        content = '{"schema": "gpthub_memory_v1", "type": "identity"}'
        assert parse_memory_record(content) is None

    def test_not_json(self):
        assert parse_memory_record("just text") is None

    def test_empty(self):
        assert parse_memory_record("") is None


# ---------------------------------------------------------------------------
# is_memory_record_active
# ---------------------------------------------------------------------------

class TestIsMemoryRecordActive:
    def test_active_record(self):
        record = {"status": "active"}
        assert is_memory_record_active(record) is True

    def test_inactive_status(self):
        record = {"status": "inactive"}
        assert is_memory_record_active(record) is False

    def test_expired(self):
        record = {"status": "active", "expires_at": int(time.time()) - 100}
        assert is_memory_record_active(record) is False

    def test_not_expired(self):
        record = {"status": "active", "expires_at": int(time.time()) + 86400}
        assert is_memory_record_active(record) is True

    def test_no_expiry(self):
        record = {"status": "active"}
        assert is_memory_record_active(record) is True

    def test_zero_expires_at(self):
        record = {"status": "active", "expires_at": 0}
        assert is_memory_record_active(record) is True


# ---------------------------------------------------------------------------
# build_memory_record
# ---------------------------------------------------------------------------

class TestBuildMemoryRecord:
    def test_basic_record(self):
        record = build_memory_record("identity", "John Doe", 0.95, 180)
        assert record["schema"] == "gpthub_memory_v1"
        assert record["type"] == "identity"
        assert record["value"] == "John Doe"
        assert record["confidence"] == 0.95
        assert record["status"] == "active"
        assert record["source"] == "llm_extractor"
        assert record["ttl_days"] == 180
        assert record["expires_at"] is not None
        assert record["expires_at"] > record["created_at"]

    def test_zero_ttl_no_expiry(self):
        record = build_memory_record("pref", "dark mode", 0.8, 0)
        # ttl_days=0 → condition ttl_days > 0 is False → expires_at = None
        assert record["expires_at"] is None

    def test_normalizes_value(self):
        record = build_memory_record("identity", "  lots   of   spaces  ", 0.9, 30)
        assert record["value"] == "lots of spaces"

    def test_confidence_rounding(self):
        record = build_memory_record("pref", "test", 0.12345, 30)
        assert record["confidence"] == 0.123


# ---------------------------------------------------------------------------
# memory_extractor_system_prompt
# ---------------------------------------------------------------------------

class TestMemoryExtractorSystemPrompt:
    def test_contains_max_facts(self):
        prompt = memory_extractor_system_prompt(5)
        assert "5" in prompt

    def test_contains_json_structure(self):
        prompt = memory_extractor_system_prompt(3)
        assert "facts" in prompt
        assert "type" in prompt


# ---------------------------------------------------------------------------
# memory_enabled_for_user
# ---------------------------------------------------------------------------

class TestMemoryEnabledForUser:
    def test_disabled_globally(self):
        assert memory_enabled_for_user(False, {}, "user1", {}) is False

    def test_disabled_by_feature_flag(self):
        assert memory_enabled_for_user(True, {"memory": False}, "user1", {}) is False

    def test_enabled_with_permission(self):
        def has_permission(user_id, perm, perms):
            return True

        result = memory_enabled_for_user(
            True, {}, "user1", {},
            has_permission_fn=has_permission,
        )
        assert result is True

    def test_no_permission_fn(self):
        assert memory_enabled_for_user(True, {}, "user1", {}) is False

    def test_permission_denied(self):
        def has_permission(user_id, perm, perms):
            return False

        result = memory_enabled_for_user(
            True, {}, "user1", {},
            has_permission_fn=has_permission,
        )
        assert result is False

    def test_permission_fn_throws(self):
        def has_permission(user_id, perm, perms):
            raise RuntimeError("boom")

        result = memory_enabled_for_user(
            True, {}, "user1", {},
            has_permission_fn=has_permission,
        )
        assert result is False
