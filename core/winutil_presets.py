"""CTT WinUtil preset registry.

Fetches the available presets from the upstream preset.json at runtime so
AM-DevKit automatically reflects any new presets CTT ships.  Falls back to
hardcoded Minimal / Standard when the network is unavailable.

Adding a polished description for a new preset only requires adding an entry
to CURATED_DESCRIPTIONS — unknown presets get a generic fallback automatically.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

PRESET_URL = (
    "https://raw.githubusercontent.com/ChrisTitusTech/winutil/main/config/preset.json"
)

# Edit this dict to control what users see for known presets.
# Unknown/future presets automatically get _FALLBACK_DESCRIPTION.
CURATED_DESCRIPTIONS: dict[str, str] = {
    "Minimal": (
        "Light privacy cleanup — removes Microsoft's suggested app ads, disables "
        "unnecessary background services, and turns off basic telemetry. "
        "Safe for most users and fully reversible via System Restore."
    ),
    "Standard": (
        "Full privacy and performance tuning — everything in Minimal, plus: disables "
        "Activity History, GameDVR, location tracking, disk telemetry, and "
        "PowerShell 7 telemetry; clears temp files; and adds End Task to the taskbar. "
        "Recommended for most power users."
    ),
}

_FALLBACK_DESCRIPTION = "Additional preset from CTT WinUtil."


@dataclass
class PresetInfo:
    key: str
    description: str
    tweaks: list[str] = field(default_factory=list)

    @property
    def tweak_count(self) -> int:
        return len(self.tweaks)


def fetch_presets(timeout: float = 6.0) -> list[PresetInfo]:
    """Fetch the live preset list from upstream.  Raises on network failure."""
    import json
    import urllib.request

    with urllib.request.urlopen(PRESET_URL, timeout=timeout) as resp:
        data: dict[str, Any] = json.loads(resp.read().decode())

    result: list[PresetInfo] = []
    for key, tweaks in data.items():
        result.append(PresetInfo(
            key=key,
            description=CURATED_DESCRIPTIONS.get(key, _FALLBACK_DESCRIPTION),
            tweaks=tweaks if isinstance(tweaks, list) else [],
        ))

    # Stable ordering: curated presets first (in declared order), then alpha
    _order = list(CURATED_DESCRIPTIONS.keys())
    result.sort(key=lambda p: (
        _order.index(p.key) if p.key in _order else len(_order),
        p.key,
    ))
    return result


def fallback_presets() -> list[PresetInfo]:
    """Return Minimal + Standard offline when the network is unavailable."""
    return [
        PresetInfo(key="Minimal", description=CURATED_DESCRIPTIONS["Minimal"]),
        PresetInfo(key="Standard", description=CURATED_DESCRIPTIONS["Standard"]),
    ]


def get_tweaks_for_preset(preset_key: str, timeout: float = 6.0) -> list[str]:
    """Return the WPFTweaks list for *preset_key* (case-insensitive), or [] on failure."""
    try:
        presets = fetch_presets(timeout=timeout)
        key_lower = preset_key.strip().lower()
        for p in presets:
            if p.key.lower() == key_lower:
                return p.tweaks
    except Exception:
        pass
    return []
