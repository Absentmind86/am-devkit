"""Winget-based installs with existence checks (Phase 2)."""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rich.console import Console

    from core.install_context import InstallContext
    from core.manifest import Manifest


def which(exe: str) -> Path | None:
    found = shutil.which(exe)
    return Path(found) if found else None


def winget_available() -> bool:
    return which("winget.exe") is not None


def run_winget_install(
    winget_id: str,
    *,
    dry_run: bool,
    timeout_s: float = 3600.0,
    show_output: bool = True,
) -> tuple[int, str, str]:
    if dry_run:
        return 0, "", ""
    argv = [
        "winget.exe",
        "install",
        "--id",
        winget_id,
        "-e",
        "--accept-package-agreements",
        "--accept-source-agreements",
        "--disable-interactivity",
    ]
    try:
        if show_output:
            # Stream output in real-time (no capture)
            proc = subprocess.run(
                argv,
                capture_output=False,
                text=True,
                timeout=timeout_s,
            )
            return proc.returncode, "", ""
        else:
            # Capture for logging
            proc = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_s,
            )
            return proc.returncode, proc.stdout or "", proc.stderr or ""
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, "", f"{type(exc).__name__}: {exc}"


def ensure_winget_package(
    ctx: InstallContext,
    manifest: Manifest,
    console: Console,
    *,
    tool: str,
    layer: str,
    winget_id: str,
    detect: Callable[[], bool],
    version_hint: str | None = None,
) -> None:
    """If *detect* is false, install *winget_id* unless dry-run."""
    if detect():
        manifest.record_tool(
            tool=tool,
            layer=layer,
            status="skipped",
            install_method="winget",
            version=version_hint,
            notes="Already present on PATH or detector.",
            winget_id=winget_id,
        )
        console.print(f"  [skipped] {tool} — already installed")
        return

    if ctx.dry_run:
        manifest.record_tool(
            tool=tool,
            layer=layer,
            status="planned",
            install_method="winget",
            version=version_hint,
            notes=f"Would run: winget install --id {winget_id}",
            winget_id=winget_id,
        )
        console.print(f"  [planned] {tool} — dry-run")
        return

    if not winget_available():
        manifest.record_tool(
            tool=tool,
            layer=layer,
            status="failed",
            install_method="winget",
            notes="winget.exe not found on PATH.",
            winget_id=winget_id,
        )
        console.print(f"  [failed] {tool} — winget not available")
        return

    console.print(f"  [installing] {tool} via winget (streaming output below)…")
    code, out, err = run_winget_install(winget_id, dry_run=False, show_output=True)
    combined = (out + "\n" + err).strip()
    if code == 0:
        manifest.record_tool(
            tool=tool,
            layer=layer,
            status="installed",
            install_method="winget",
            version=version_hint,
            notes=combined[-2000:] if combined else None,
            winget_id=winget_id,
        )
        console.print(f"  [done] {tool}")
        return

    manifest.record_tool(
        tool=tool,
        layer=layer,
        status="failed",
        install_method="winget",
        notes=f"exit {code}: {combined[-2000:]}",
        winget_id=winget_id,
    )
    console.print(f"  [failed] {tool} (exit {code})")
