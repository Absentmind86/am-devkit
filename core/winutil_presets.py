"""AM-DevKit sanitization preset registry.

Defines the two built-in presets (Minimal and Standard) with curated
descriptions shown in the GUI and pre-install summary.  The tweaks
themselves are implemented in scripts/sanitize.ps1 — no external downloads.
"""

from __future__ import annotations

from dataclasses import dataclass, field

CURATED_DESCRIPTIONS: dict[str, str] = {
    "Minimal": (
        "Light privacy cleanup — removes Microsoft's suggested app ads, disables "
        "unnecessary background services, and turns off basic telemetry. "
        "Safe for most users and fully reversible via System Restore."
    ),
    "Standard": (
        "Full privacy and performance tuning — everything in Minimal, plus: disables "
        "Activity History, Game DVR, location tracking, disk telemetry, and "
        "PowerShell 7 telemetry; clears temp files; adds End Task to the taskbar; "
        "and runs DISM component cleanup. Recommended for most power users."
    ),
}


@dataclass
class PresetInfo:
    key: str
    description: str
    tweaks: list[str] = field(default_factory=list)

    @property
    def tweak_count(self) -> int:
        return len(self.tweaks)


def _parse_preset_json(data: dict) -> list[PresetInfo]:
    result: list[PresetInfo] = []
    for key, tweaks in data.items():
        result.append(PresetInfo(
            key=key,
            description=CURATED_DESCRIPTIONS.get(key, "Custom preset."),
            tweaks=tweaks if isinstance(tweaks, list) else [],
        ))
    _order = list(CURATED_DESCRIPTIONS.keys())
    result.sort(key=lambda p: (
        _order.index(p.key) if p.key in _order else len(_order),
        p.key,
    ))
    return result


def fallback_presets() -> list[PresetInfo]:
    """Return the two built-in presets for GUI rendering."""
    return [
        PresetInfo(key="Minimal", description=CURATED_DESCRIPTIONS["Minimal"]),
        PresetInfo(key="Standard", description=CURATED_DESCRIPTIONS["Standard"]),
    ]
