"""Unit tests for core/winutil_presets.py — preset parsing and fallback logic."""

from __future__ import annotations

from core.winutil_presets import (
    CURATED_DESCRIPTIONS,
    PresetInfo,
    _parse_preset_json,
    fallback_presets,
)

# ---------------------------------------------------------------------------
# _parse_preset_json
# ---------------------------------------------------------------------------

class TestParsePresetJson:
    def test_parses_known_presets(self):
        data = {
            "Minimal": ["WPFTweak1", "WPFTweak2"],
            "Standard": ["WPFTweak1", "WPFTweak2", "WPFTweak3"],
        }
        presets = _parse_preset_json(data)
        assert len(presets) == 2
        keys = [p.key for p in presets]
        assert "Minimal" in keys
        assert "Standard" in keys

    def test_known_presets_ordered_first(self):
        data = {
            "Standard": ["T1"],
            "Custom": ["T2"],
            "Minimal": ["T3"],
        }
        presets = _parse_preset_json(data)
        assert presets[0].key == "Minimal"
        assert presets[1].key == "Standard"
        assert presets[2].key == "Custom"

    def test_curated_description_applied(self):
        data = {"Minimal": ["T1"]}
        presets = _parse_preset_json(data)
        assert presets[0].description == CURATED_DESCRIPTIONS["Minimal"]

    def test_unknown_preset_gets_fallback_description(self):
        data = {"ExoticPreset": ["T1", "T2"]}
        presets = _parse_preset_json(data)
        assert presets[0].description != ""
        assert presets[0].key == "ExoticPreset"

    def test_tweak_count(self):
        data = {"Minimal": ["A", "B", "C"]}
        presets = _parse_preset_json(data)
        assert presets[0].tweak_count == 3

    def test_non_list_tweaks_become_empty(self):
        data = {"Minimal": "not-a-list"}
        presets = _parse_preset_json(data)
        assert presets[0].tweaks == []

    def test_empty_dict(self):
        presets = _parse_preset_json({})
        assert presets == []


# ---------------------------------------------------------------------------
# PresetInfo
# ---------------------------------------------------------------------------

class TestPresetInfo:
    def test_tweak_count_property(self):
        p = PresetInfo(key="Test", description="desc", tweaks=["A", "B"])
        assert p.tweak_count == 2

    def test_tweak_count_empty(self):
        p = PresetInfo(key="Test", description="desc")
        assert p.tweak_count == 0


# ---------------------------------------------------------------------------
# fallback_presets
# ---------------------------------------------------------------------------

class TestFallbackPresets:
    def test_returns_minimal_and_standard(self):
        presets = fallback_presets()
        keys = [p.key for p in presets]
        assert "Minimal" in keys
        assert "Standard" in keys

    def test_descriptions_nonempty(self):
        for p in fallback_presets():
            assert p.description

    def test_returns_preset_info_instances(self):
        for p in fallback_presets():
            assert isinstance(p, PresetInfo)
