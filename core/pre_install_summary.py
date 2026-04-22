"""CLI pre-install summary after Layer 0 (Phase 2, PROJECT.md pre-install screen).

Also exposes plain-text formatting for the Phase 3 Flet GUI (``format_pre_install_summary_text``).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from rich.panel import Panel
from rich.table import Table

if TYPE_CHECKING:
    from rich.console import Console

    from core.install_context import InstallContext


# Scripted / non-catalog steps (preflight, infra wingets not in catalog, scoop, rustup, extensions, etc.).
_OFF_CATALOG_STEP_BUDGET: int = 34


def _absentmind_equivalent(profiles: list[str]) -> bool:
    from core.install_context import default_profiles_from_absentmind

    return sorted(profiles) == sorted(default_profiles_from_absentmind())


def _estimate_steps(ctx: InstallContext) -> int:
    from core.install_catalog import count_winget_actions

    return (
        count_winget_actions(ctx.profiles, catalog_excludes=ctx.catalog_exclude_tools)
        + _OFF_CATALOG_STEP_BUDGET
    )


def _min_free_volume_gb(profile: dict[str, Any]) -> float | None:
    storage = profile.get("storage")
    if not isinstance(storage, dict):
        return None
    vols = storage.get("volumes")
    if not isinstance(vols, list):
        return None
    best: float | None = None
    for v in vols:
        if not isinstance(v, dict):
            continue
        fb = v.get("free_bytes")
        if fb is None:
            continue
        try:
            gb = int(fb) / (1024**3)
        except (TypeError, ValueError):
            continue
        if best is None or gb < best:
            best = gb
    return best


def _latency_hint_ms(profile: dict[str, Any]) -> str:
    net = profile.get("network")
    if not isinstance(net, dict):
        return "unknown"
    ms = net.get("probe_latency_ms")
    if ms is None:
        return "unknown"
    try:
        v = float(ms)
    except (TypeError, ValueError):
        return "unknown"
    if v < 80:
        return "fast"
    if v < 300:
        return "moderate"
    return "slow"


def _time_bracket(profile: dict[str, Any], steps: int) -> str:
    lat = _latency_hint_ms(profile)
    if lat == "fast":
        lo, hi = 12, 28
    elif lat == "moderate":
        lo, hi = 20, 45
    elif lat == "slow":
        lo, hi = 35, 90
    else:
        lo, hi = 18, 50
    bump = max(0, (steps - 40) // 8) * 3
    return f"~{lo + bump}-{hi + bump} min (heuristic; network class: {lat})"


def _winutil_config_hint(
    repo_root: Path,
    *,
    run_sanitation: bool,
    sanitation_preset: str = "minimal",
) -> str | None:
    """Warn when sanitation is on but the selected WinUtil JSON is missing or invalid."""
    if not run_sanitation:
        return None
    from core.install_context import winutil_config_path_for_preset

    cfg = winutil_config_path_for_preset(repo_root, sanitation_preset)
    try:
        rel = cfg.relative_to(repo_root)
    except ValueError:
        rel = cfg
    try:
        raw = cfg.read_text(encoding="utf-8")
    except OSError:
        return f"WinUtil: config file missing ({rel}). Sanitation may fail."
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return f"WinUtil: config is not valid JSON — fix {rel}."
    if isinstance(data, dict) and len(data) == 0:
        return (
            f"WinUtil: config is empty {{}} — add WPFTweaks IDs to {rel} "
            "(see Chris Titus WinUtil automation docs)."
        )
    if isinstance(data, dict):
        wpf = data.get("WPFTweaks")
        if wpf is None:
            return (
                "WinUtil: config has no WPFTweaks array — exports must list tweak IDs "
                "(export from WinUtil or use the repo preset)."
            )
        if isinstance(wpf, list) and len(wpf) == 0:
            return "WinUtil: WPFTweaks array is empty — sanitation would apply no tweaks."
    return None


def pre_install_summary_title(ctx: InstallContext) -> str:
    """Panel / section title for the summary block."""
    if _absentmind_equivalent(ctx.profiles):
        return "Pre-install summary (Absentmind-style full stack)"
    return "Pre-install summary"


def pre_install_summary_lines(ctx: InstallContext) -> list[str]:
    """Body lines shared by Rich CLI panel and Phase 3 GUI text."""
    steps = _estimate_steps(ctx)
    prof = ctx.profiles
    absent = _absentmind_equivalent(prof)

    if absent:
        body_lines = [
            "You selected the full curated profile set (all stacks).",
            f"Estimated steps: catalog winget rows + off-catalog budget ~{steps} (see install_catalog.py).",
            _time_bracket(ctx.system_profile, steps),
        ]
    else:
        body_lines = [
            f"Profiles: {', '.join(prof)}",
            f"Estimated steps: ~{steps} (winget catalog + fixed budget for scoop, extensions, etc.)",
            _time_bracket(ctx.system_profile, steps),
        ]

    mfree = _min_free_volume_gb(ctx.system_profile)
    if mfree is not None:
        body_lines.append(f"Smallest sampled volume free space: {mfree:.1f} GB")

    body_lines.append(f"Windows sanitation (CTT WinUtil): {'YES' if ctx.run_sanitation else 'no'}")
    if ctx.run_sanitation:
        sp = getattr(ctx, "sanitation_preset", "minimal") or "minimal"
        cfg_name = (
            "am-devkit-winutil-standard.json"
            if str(sp).lower() == "standard"
            else "am-devkit-winutil.json"
        )
        body_lines.append(f"WinUtil preset: {sp} ({cfg_name})")
    body_lines.append(f"WSL DISM + default distro: {'yes' if ctx.enable_wsl else 'no'}" + (f" ({ctx.wsl_default_distro})" if ctx.wsl_default_distro else ""))
    body_lines.append(f"Dry run: {'yes' if ctx.dry_run else 'no'}")
    if ctx.catalog_exclude_tools:
        tools = sorted(ctx.catalog_exclude_tools)
        preview = ", ".join(tools[:14])
        if len(tools) > 14:
            preview += ", …"
        body_lines.append(f"Catalog exclusions ({len(tools)}): {preview}")

    hint = _winutil_config_hint(
        ctx.repo_root,
        run_sanitation=ctx.run_sanitation,
        sanitation_preset=getattr(ctx, "sanitation_preset", "minimal"),
    )
    if hint:
        body_lines.append(hint)

    warns = ctx.system_profile.get("warnings") if isinstance(ctx.system_profile.get("warnings"), list) else []
    if warns:
        body_lines.append("")
        body_lines.append("Layer 0 warnings (first 5):")
        for w in warns[:5]:
            body_lines.append(f"  - {w}")

    if not ctx.system_profile.get("schema_version"):
        body_lines.append("")
        body_lines.append(
            "No Layer 0 scan loaded — use “Run system scan” in the GUI or "
            "python core/system_scan.py --output system-profile.json for time/disk heuristics."
        )

    return body_lines


def format_pre_install_summary_text(ctx: InstallContext) -> str:
    """Plain-text summary for embedding in Flet or logs (no Rich)."""
    title = pre_install_summary_title(ctx)
    lines = pre_install_summary_lines(ctx)
    return title + "\n\n" + "\n".join(lines)


def show_pre_install_summary(ctx: InstallContext, console: Console) -> None:
    """Print summary; optionally require confirmation (non-dry-run, TTY)."""
    if ctx.skip_summary:
        return

    title = pre_install_summary_title(ctx)
    body_lines = pre_install_summary_lines(ctx)

    table = Table(show_header=False, box=None, padding=(0, 1))
    for line in body_lines:
        table.add_row(line)

    console.print(Panel(table, title=title, border_style="cyan"))

    if ctx.dry_run or ctx.assume_yes:
        return

    if not sys.stdin.isatty():
        console.print("[dim]Non-interactive stdin: proceeding without confirmation (use --yes or --skip-summary).[/dim]")
        return

    ans = console.input("[bold]Proceed with install?[/bold] [y/N] ").strip().lower()
    if ans not in ("y", "yes"):
        console.print("[yellow]Aborted before sanitation / installs (no changes after Layer 0 on disk except manifest flush so far).[/yellow]")
        raise SystemExit(2)
