"""Layer 1: CTT WinUtil integration with AM config (Phase 2).

WinUtil is retrieved at runtime from ``https://christitus.com/win`` (not vendored here).
Upstream license: MIT, Chris Titus Tech / CT Tech Group LLC — see docs/THIRD_PARTY_NOTICES.md.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rich.console import Console

    from core.install_context import InstallContext
    from core.manifest import Manifest


def _resolve_config(ctx: InstallContext) -> tuple[Path, bool]:
    """Return ``(config_path, is_temp)`` for the selected preset.

    Tries to fetch the live tweaks list from the CTT preset.json and writes them
    to a temporary file so the config always reflects the upstream preset.  Falls
    back to the static local JSON files when the network is unavailable.
    """
    preset_key = getattr(ctx, "sanitation_preset", "Minimal") or "Minimal"

    # --- live path ---
    try:
        from core.winutil_presets import get_tweaks_for_preset
        tweaks = get_tweaks_for_preset(preset_key, timeout=6.0)
        if tweaks:
            tmp = Path(tempfile.mktemp(suffix=".json", prefix="am-devkit-winutil-"))
            tmp.write_text(json.dumps({"WPFTweaks": tweaks}), encoding="utf-8")
            return tmp, True
    except Exception:
        pass

    # --- local fallback ---
    from core.install_context import winutil_config_path_for_preset
    return winutil_config_path_for_preset(ctx.repo_root, preset_key), False


def run_sanitize(ctx: InstallContext, manifest: Manifest, console: Console) -> None:
    """Invoke Chris Titus WinUtil with our JSON preset (opt-in: ``ctx.run_sanitation``)."""
    console.print("[bold]Layer 1 — Windows sanitization[/bold]")
    preset_name = getattr(ctx, "sanitation_preset", "Minimal") or "Minimal"

    if not ctx.run_sanitation:
        manifest.record_tool(
            tool="ctt-winutil",
            layer="sanitize",
            status="skipped",
            install_method="winutil",
            notes="Sanitation not requested (pass --run-sanitation to enable).",
        )
        console.print("  [skipped] WinUtil — use --run-sanitation to enable (preset: none)")
        return

    if ctx.dry_run:
        manifest.record_tool(
            tool="ctt-winutil",
            layer="sanitize",
            status="planned",
            install_method="winutil",
            notes=f"Would invoke WinUtil with preset '{preset_name}'",
        )
        console.print(f"  [planned] WinUtil — dry-run (preset: {preset_name})")
        return

    config_path, is_temp = _resolve_config(ctx)
    source = "live" if is_temp else "local fallback"
    if not config_path.is_file():
        manifest.record_tool(
            tool="ctt-winutil",
            layer="sanitize",
            status="failed",
            install_method="winutil",
            notes=f"Config not found: {config_path}",
        )
        console.print(f"  [failed] WinUtil — config not found: {config_path}")
        return

    cfg = str(config_path).replace("'", "''")
    ps = (
        "$ErrorActionPreference = 'Stop'; "
        f"$config = '{cfg}'; "
        "iex \"& { $(irm 'https://christitus.com/win') } -Config $config -Run\""
    )
    console.print(
        f"  [installing] WinUtil (CTT) — preset: {preset_name} ({source}) — this may take several minutes …"
    )
    try:
        proc = subprocess.run(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=7200.0,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        manifest.record_tool(
            tool="ctt-winutil",
            layer="sanitize",
            status="failed",
            install_method="winutil",
            notes=f"{type(exc).__name__}: {exc}",
        )
        console.print(f"  [failed] WinUtil — {exc}")
        return
    finally:
        if is_temp:
            config_path.unlink(missing_ok=True)

    tail = ((proc.stdout or "") + "\n" + (proc.stderr or "")).strip()[-2000:]
    if proc.returncode == 0:
        manifest.record_tool(
            tool="ctt-winutil",
            layer="sanitize",
            status="installed",
            install_method="winutil",
            notes=tail or None,
        )
        console.print("  [done] WinUtil")
        return

    manifest.record_tool(
        tool="ctt-winutil",
        layer="sanitize",
        status="failed",
        install_method="winutil",
        notes=f"exit {proc.returncode}: {tail}",
    )
    console.print(f"  [failed] WinUtil (exit {proc.returncode})")
