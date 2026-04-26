"""Install catalog rows with profile gates, manifest skips, and cross-platform dispatch."""

from __future__ import annotations

from typing import TYPE_CHECKING

from core.install_catalog import CatalogEntry, catalog_entries_for_layer, get_detector
from core.platform_util import is_macos, is_windows, primary_pkg_manager
from core.winget_util import ensure_winget_package

if TYPE_CHECKING:
    from rich.console import Console

    from core.install_context import InstallContext
    from core.manifest import Manifest


def _get_pkg_id(entry: CatalogEntry) -> str | None:
    """Return the package ID for the current OS, or None if unsupported."""
    if is_windows():
        return entry.win_id
    if is_macos():
        return entry.macos_id
    return entry.linux_id


def _install_entry(
    ctx: InstallContext,
    manifest: Manifest,
    console: Console,
    entry: CatalogEntry,
    layer: str,
) -> None:
    pkg_id = _get_pkg_id(entry)
    detect = get_detector(entry)

    # On Linux, pkg_id=None (no apt package) is not terminal if snap_id is set.
    # For Windows and macOS, None means genuinely unavailable.
    if pkg_id is None and (is_windows() or is_macos()):
        manifest.record_tool(
            tool=entry.tool,
            layer=layer,
            status="skipped",
            install_method="platform",
            notes=f"Not available on this platform ({primary_pkg_manager()}).",
        )
        console.print(f"  [skipped] {entry.tool} — not available on this platform")
        return

    if is_windows():
        ok = ensure_winget_package(
            ctx, manifest, console,
            tool=entry.tool, layer=layer,
            winget_id=pkg_id,  # type: ignore[arg-type]  # never None here
            detect=detect,
        )
        if not ok and entry.choco_id:
            from core.choco_util import ensure_choco_package
            console.print(f"  [fallback] {entry.tool} — winget failed, trying choco…")
            ensure_choco_package(
                ctx, manifest, console,
                tool=entry.tool, layer=layer,
                choco_id=entry.choco_id,
                detect=detect,
            )
    elif is_macos():
        from core.brew_util import ensure_brew_package
        ensure_brew_package(
            ctx, manifest, console,
            tool=entry.tool, layer=layer,
            pkg_id=pkg_id,  # type: ignore[arg-type]  # never None here
            is_cask=entry.macos_cask,
            detect=detect,
            brew_tap=entry.brew_tap,
        )
    else:
        # Linux
        if pkg_id is None:
            # No apt package: try snap, or record as unavailable
            if entry.snap_id:
                from core.snap_util import ensure_snap_package
                ensure_snap_package(
                    ctx, manifest, console,
                    tool=entry.tool, layer=layer,
                    snap_id=entry.snap_id,
                    classic=entry.snap_classic,
                    detect=detect,
                )
            else:
                manifest.record_tool(
                    tool=entry.tool, layer=layer, status="skipped",
                    install_method="platform",
                    notes="Not available on Linux (no apt package or snap ID).",
                )
                console.print(f"  [skipped] {entry.tool} — not available on Linux")
            return
        from core.linux_util import ensure_linux_package
        ok = ensure_linux_package(
            ctx, manifest, console,
            tool=entry.tool, layer=layer,
            pkg_id=pkg_id,
            manager=primary_pkg_manager(),
            detect=detect,
            repo_key=entry.linux_repo,
        )
        if not ok and entry.snap_id:
            from core.snap_util import ensure_snap_package
            console.print(f"  [fallback] {entry.tool} — apt failed, trying snap…")
            ensure_snap_package(
                ctx, manifest, console,
                tool=entry.tool, layer=layer,
                snap_id=entry.snap_id,
                classic=entry.snap_classic,
                detect=detect,
            )


def install_catalog_layer(
    ctx: InstallContext,
    manifest: Manifest,
    console: Console,
    layer: str,
    *,
    skip_tools: frozenset[str] | None = None,
) -> None:
    """Apply all CatalogEntry rows for *layer*."""
    selected = set(ctx.profiles)
    for entry in catalog_entries_for_layer(layer):
        if skip_tools and entry.tool in skip_tools:
            continue
        if entry.tool in ctx.catalog_exclude_tools:
            manifest.record_tool(
                tool=entry.tool,
                layer=layer,
                status="skipped",
                install_method="user-exclude",
                notes="Excluded via Custom Mode / --exclude-catalog-tool.",
            )
            console.print(f"  [skipped] {entry.tool} — user exclude")
            continue
        if not entry.applies_to(selected):
            req = ", ".join(sorted(entry.profiles)) if entry.profiles else ""
            manifest.record_tool(
                tool=entry.tool,
                layer=layer,
                status="skipped",
                install_method="profile-gate",
                notes=f"Requires one of these profiles: {req}",
            )
            console.print(f"  [skipped] {entry.tool} — profile gate")
            continue
        _install_entry(ctx, manifest, console, entry, layer)
