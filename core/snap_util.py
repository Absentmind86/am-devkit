"""Snap-based installs for Linux — fallback when no apt package exists."""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rich.console import Console

    from core.install_context import InstallContext
    from core.manifest import Manifest


def snap_available() -> bool:
    return shutil.which("snap") is not None


def run_snap_install(
    snap_id: str,
    *,
    classic: bool = False,
    dry_run: bool,
    timeout_s: float = 3600.0,
) -> tuple[int, str, str]:
    if dry_run:
        return 0, "", ""
    argv = ["sudo", "snap", "install", snap_id]
    if classic:
        argv.append("--classic")
    try:
        proc = subprocess.run(
            argv,
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            timeout=timeout_s,
        )
        return proc.returncode, proc.stdout or "", proc.stderr or ""
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, "", f"{type(exc).__name__}: {exc}"


def ensure_snap_package(
    ctx: InstallContext,
    manifest: Manifest,
    console: Console,
    *,
    tool: str,
    layer: str,
    snap_id: str,
    classic: bool = False,
    detect: Callable[[], bool],
    version_hint: str | None = None,
) -> bool:
    """Install snap_id via snap unless already present. Returns True on success."""
    install_method = "snap"

    if detect():
        manifest.record_tool(
            tool=tool, layer=layer, status="skipped",
            install_method=install_method, version=version_hint,
            notes="Already present on PATH or detector.",
        )
        console.print(f"  [skipped] {tool} — already installed")
        return True

    if ctx.dry_run:
        flag = " --classic" if classic else ""
        manifest.record_tool(
            tool=tool, layer=layer, status="planned",
            install_method=install_method, version=version_hint,
            notes=f"Would run: sudo snap install {snap_id}{flag}",
        )
        console.print(f"  [planned] {tool} — dry-run (snap)")
        return True

    if not snap_available():
        manifest.record_tool(
            tool=tool, layer=layer, status="failed",
            install_method=install_method,
            notes="snap not found on PATH.",
        )
        console.print(f"  [failed] {tool} — snap not available")
        return False

    console.print(f"  [installing] {tool} via snap{'  --classic' if classic else ''}…")
    code, out, err = run_snap_install(snap_id, classic=classic, dry_run=False)
    combined = (out + "\n" + err).strip()

    if code == 0 or "already installed" in combined.lower():
        manifest.record_tool(
            tool=tool, layer=layer, status="installed",
            install_method=install_method, version=version_hint,
            notes=combined[-2000:] if combined else None,
        )
        console.print(f"  [done] {tool} (snap)")
        return True

    manifest.record_tool(
        tool=tool, layer=layer, status="failed",
        install_method=install_method,
        notes=f"exit {code}: {combined[-2000:]}",
    )
    console.print(f"  [failed] {tool} via snap (exit {code})")
    return False
