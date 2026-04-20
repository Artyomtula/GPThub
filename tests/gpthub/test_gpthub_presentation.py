import os
import sys
import importlib.util
import io
import json
import pytest

# ---------------------------------------------------------------------------
# Direct-load gpthub_i18n (dependency)
# ---------------------------------------------------------------------------

_I18N_PATH = os.path.join(
    os.path.dirname(__file__), os.pardir, os.pardir, 'backend', 'open_webui', 'utils', 'gpthub_i18n.py'
)
_i18n_spec = importlib.util.spec_from_file_location('open_webui.utils.gpthub_i18n', os.path.abspath(_I18N_PATH))
_i18n_mod = importlib.util.module_from_spec(_i18n_spec)
sys.modules['open_webui.utils.gpthub_i18n'] = _i18n_mod
_i18n_spec.loader.exec_module(_i18n_mod)

# ---------------------------------------------------------------------------
# Direct-load gpthub_presentation (subject under test)
# We only test the *pure* functions — no async handlers.
# ---------------------------------------------------------------------------

# Stub fastapi.Request so the import doesn't fail
import types

_fastapi = types.ModuleType('fastapi')


class _FakeRequest:
    pass


_fastapi.Request = _FakeRequest
sys.modules.setdefault('fastapi', _fastapi)

_PRES_PATH = os.path.join(
    os.path.dirname(__file__), os.pardir, os.pardir, 'backend', 'open_webui', 'utils', 'gpthub_presentation.py'
)
_pspec = importlib.util.spec_from_file_location('gpthub_presentation', os.path.abspath(_PRES_PATH))
_pmod = importlib.util.module_from_spec(_pspec)
_pspec.loader.exec_module(_pmod)

PPTX_THEMES = _pmod.PPTX_THEMES
PPTX_THEME_KEYWORDS = _pmod.PPTX_THEME_KEYWORDS
detect_pptx_theme = _pmod.detect_pptx_theme
PPTX_LAYOUTS = _pmod.PPTX_LAYOUTS
VALID_LAYOUTS = _pmod.VALID_LAYOUTS

# build_pptx needs python-pptx & lxml; check availability
try:
    import pptx
    import lxml

    HAS_PPTX = True
except ImportError:
    HAS_PPTX = False


# ---------------------------------------------------------------------------
# PPTX_THEMES
# ---------------------------------------------------------------------------


class TestPptxThemes:
    def test_has_all_themes(self):
        assert 'corporate' in PPTX_THEMES
        assert 'dark' in PPTX_THEMES
        assert 'minimal' in PPTX_THEMES

    def test_theme_keys(self):
        for name, theme in PPTX_THEMES.items():
            assert 'bg' in theme, f"Theme '{name}' missing 'bg'"
            assert 'title_fg' in theme, f"Theme '{name}' missing 'title_fg'"
            assert 'body_fg' in theme, f"Theme '{name}' missing 'body_fg'"
            assert 'html_bg' in theme, f"Theme '{name}' missing 'html_bg'"

    def test_bg_is_rgb_tuple(self):
        for name, theme in PPTX_THEMES.items():
            bg = theme['bg']
            assert isinstance(bg, tuple) and len(bg) == 3, f"Theme '{name}' bg not RGB tuple"
            assert all(0 <= c <= 255 for c in bg), f"Theme '{name}' bg values out of range"


# ---------------------------------------------------------------------------
# detect_pptx_theme
# ---------------------------------------------------------------------------


class TestDetectPptxTheme:
    def test_corporate_keywords(self):
        assert detect_pptx_theme('Make a corporate presentation') == 'corporate'
        assert detect_pptx_theme('бизнес отчёт') == 'corporate'

    def test_dark_keywords(self):
        assert detect_pptx_theme('dark mode presentation') == 'dark'
        assert detect_pptx_theme('темная тема') == 'dark'

    def test_minimal_keywords(self):
        assert detect_pptx_theme('minimal clean design') == 'minimal'
        assert detect_pptx_theme('светлый дизайн') == 'minimal'

    def test_default_corporate(self):
        assert detect_pptx_theme('random text with no theme hints') == 'corporate'

    def test_empty_string(self):
        assert detect_pptx_theme('') == 'corporate'


# ---------------------------------------------------------------------------
# PPTX_LAYOUTS
# ---------------------------------------------------------------------------


class TestPptxLayouts:
    def test_valid_layouts_list(self):
        assert set(VALID_LAYOUTS) == set(PPTX_LAYOUTS.keys())

    def test_all_layouts_have_required_zones(self):
        for name, layout in PPTX_LAYOUTS.items():
            assert 'title' in layout, f"Layout '{name}' missing 'title'"
            assert 'body' in layout, f"Layout '{name}' missing 'body'"
            assert 'image' in layout, f"Layout '{name}' missing 'image'"

    def test_zones_are_4_tuples(self):
        for name, layout in PPTX_LAYOUTS.items():
            for zone_name, zone in layout.items():
                assert isinstance(zone, tuple) and len(zone) == 4, (
                    f"Layout '{name}' zone '{zone_name}' is not a 4-tuple"
                )
                assert all(isinstance(v, (int, float)) for v in zone), (
                    f"Layout '{name}' zone '{zone_name}' has non-numeric values"
                )


# ---------------------------------------------------------------------------
# build_pptx (requires python-pptx)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not HAS_PPTX, reason='python-pptx / lxml not installed')
class TestBuildPptx:
    def _sample_slides(self):
        return {
            'title': 'Test Presentation',
            'slides': [
                {'layout': 'hero', 'title': 'Title Slide', 'body': ['Welcome'], 'image_prompt': 'abstract background'},
                {'layout': 'split-right', 'title': 'Content', 'body': ['Point 1', 'Point 2'], 'image_prompt': ''},
            ],
        }

    def test_returns_bytes(self):
        build_pptx = _pmod.build_pptx
        result = build_pptx(self._sample_slides())
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_valid_pptx_magic(self):
        build_pptx = _pmod.build_pptx
        result = build_pptx(self._sample_slides())
        # PPTX files are ZIP format; check magic bytes
        assert result[:2] == b'PK'

    def test_all_themes(self):
        build_pptx = _pmod.build_pptx
        for theme_name in PPTX_THEMES:
            result = build_pptx(self._sample_slides(), theme=theme_name)
            assert isinstance(result, bytes) and len(result) > 0

    def test_unknown_layout_fallback(self):
        build_pptx = _pmod.build_pptx
        slides_data = {'slides': [{'layout': 'nonexistent', 'title': 'Test', 'body': ['Bullet']}]}
        result = build_pptx(slides_data)
        assert isinstance(result, bytes) and len(result) > 0

    def test_with_slide_images(self):
        build_pptx = _pmod.build_pptx
        # Create a minimal valid PNG (1x1 pixel)
        import struct
        import zlib

        def _minimal_png():
            sig = b'\x89PNG\r\n\x1a\n'
            ihdr_data = struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0)
            ihdr_crc = zlib.crc32(b'IHDR' + ihdr_data) & 0xFFFFFFFF
            ihdr = struct.pack('>I', 13) + b'IHDR' + ihdr_data + struct.pack('>I', ihdr_crc)
            raw = b'\x00' + b'\x00\x00\x00'  # filter + 1 RGB pixel
            idat_data = zlib.compress(raw)
            idat_crc = zlib.crc32(b'IDAT' + idat_data) & 0xFFFFFFFF
            idat = struct.pack('>I', len(idat_data)) + b'IDAT' + idat_data + struct.pack('>I', idat_crc)
            iend_crc = zlib.crc32(b'IEND') & 0xFFFFFFFF
            iend = struct.pack('>I', 0) + b'IEND' + struct.pack('>I', iend_crc)
            return sig + ihdr + idat + iend

        png_bytes = _minimal_png()
        slides_data = {
            'slides': [
                {'layout': 'split-right', 'title': 'With Image', 'body': ['Test']},
            ]
        }
        result = build_pptx(slides_data, slide_images={0: png_bytes})
        assert isinstance(result, bytes) and result[:2] == b'PK'

    def test_empty_slides(self):
        build_pptx = _pmod.build_pptx
        result = build_pptx({'slides': []})
        assert isinstance(result, bytes) and len(result) > 0
