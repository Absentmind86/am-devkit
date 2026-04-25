"""Layer 1: Native Windows sanitization via scripts/sanitize.ps1.

Applies a curated set of privacy and performance registry/service tweaks
from a bundled PowerShell script. No external downloads. No GUI.

Presets (defined in config/sanitize-*.json for display, implemented in sanitize.ps1):
  Minimal  — telemetry, consumer features, service cleanup, WPBT disable
  Standard — Minimal + activity history, Game DVR, location, temp cleanup,
             DISM component cleanup, End Task on taskbar, PS7 telemetry opt-out
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rich.console import Console

    from core.install_context import InstallContext
    from core.manifest import Manifest


def run_sanitize(ctx: InstallContext, manifest: Manifest, console: Console) -> None:
    """Invoke native sanitization script (opt-in: ``ctx.run_sanitation``)."""
    from core.pwsh_util import run_powershell

    console.print("[bold]Layer 1 — Windows sanitization[/bold]")
    preset_name = (getattr(ctx, "sanitation_preset", "Minimal") or "Minimal").strip() or "Minimal"

    if not ctx.run_sanitation:
        manifest.record_tool(
            tool="am-sanitize",
            layer="sanitize",
            status="skipped",
            install_method="native-ps1",
            notes="Sanitation not requested (pass --run-sanitation to enable).",
        )
        console.print("  [skipped] sanitization — use --run-sanitation to enable")
        return

    manifest_path = ctx.repo_root / "devkit-manifest.json"
    if manifest_path.is_file():
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            for entry in data.get("tools", []):
                if entry.get("tool") == "am-sanitize" and entry.get("status") == "installed":
                    prev = entry.get("notes", "")
                    console.print(f"  [skipped] sanitization already applied in a prior run ({prev})")
                    manifest.record_tool(
                        tool="am-sanitize",
                        layer="sanitize",
                        status="skipped",
                        install_method="native-ps1",
                        notes=f"Already applied in a prior run. {prev}".strip(),
                    )
                    return
        except Exception:
            pass

    if ctx.dry_run:
        manifest.record_tool(
            tool="am-sanitize",
            layer="sanitize",
            status="planned",
            install_method="native-ps1",
            notes=f"Would run scripts/sanitize.ps1 -Preset {preset_name}.",
        )
        console.print(f"  [planned] sanitization — dry-run (preset: {preset_name})")
        return

    script: Path = ctx.repo_root / "scripts" / "sanitize.ps1"
    if not script.is_file():
        manifest.record_tool(
            tool="am-sanitize",
            layer="sanitize",
            status="failed",
            install_method="native-ps1",
            notes=f"sanitize.ps1 not found at {script}",
        )
        console.print(f"  [failed] sanitize.ps1 not found: {script}")
        return

    console.print(
        f"  [installing] Windows sanitization (preset: {preset_name}) — "
        "streaming output below, takes 1-5 minutes …"
    )
    safe_path = str(script).replace("'", "''")
    ps = f"& '{safe_path}' -Preset '{preset_name}'"
    code, _out, _err = run_powershell(ps, timeout_s=1200.0, stream=True)

    if code == 0:
        manifest.record_tool(
            tool="am-sanitize",
            layer="sanitize",
            status="installed",
            install_method="native-ps1",
            notes=f"preset={preset_name}; output streamed to terminal.",
        )
        console.print("  [done] Windows sanitization")
        return

    manifest.record_tool(
        tool="am-sanitize",
        layer="sanitize",
        status="failed",
        install_method="native-ps1",
        notes=f"exit {code}; preset={preset_name} (output streamed to terminal)",
    )
    console.print(f"  [failed] sanitization (exit {code}) — check terminal output above")
