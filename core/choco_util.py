"""Chocolatey-based installs — Windows fallback when winget fails."""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rich.console import Console

    from core.install_context import InstallContext
    from core.manifest import Manifest


def choco_available() -> bool:
    return shutil.which("choco.exe") is not None or shutil.which("choco") is not None


def run_choco_install(
    choco_id: str,
    *,
    dry_run: bool,
    timeout_s: float = 3600.0,
) -> tuple[int, str, str]:
    if dry_run:
        return 0, "", ""
    argv = ["choco", "install", choco_id, "-y", "--no-progress"]
    try:
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


def ensure_choco_package(
    ctx: InstallContext,
    manifest: Manifest,
    console: Console,
    *,
    tool: str,
    layer: str,
    choco_id: str,
    detect: Callable[[], bool],
    version_hint: str | None = None,
) -> bool:
    """Install choco_id via Chocolatey; returns True if installed/already-present."""
    if detect():
        manifest.record_tool(
            tool=tool, layer=layer, status="skipped",
            install_method="choco", version=version_hint,
            notes="Already present on PATH or detector.",
        )
        console.print(f"  [skipped] {tool} — already installed")
        return True

    if ctx.dry_run:
        manifest.record_tool(
            tool=tool, layer=layer, status="planned",
            install_method="choco", version=version_hint,
            notes=f"Would run: choco install {choco_id} -y",
        )
        console.print(f"  [planned] {tool} — dry-run (choco fallback)")
        return True

    if not choco_available():
        manifest.record_tool(
            tool=tool, layer=layer, status="failed",
            install_method="choco",
            notes="choco not found on PATH.",
        )
        console.print(f"  [failed] {tool} — chocolatey not available")
        return False

    console.print(f"  [installing] {tool} via choco (fallback)…")
    code, out, err = run_choco_install(choco_id, dry_run=False)
    combined = (out + "\n" + err).strip()

    if code == 0 or "already installed" in combined.lower():
        manifest.record_tool(
            tool=tool, layer=layer, status="installed",
            install_method="choco", version=version_hint,
            notes=combined[-2000:] if combined else None,
        )
        console.print(f"  [done] {tool} (via choco)")
        return True

    manifest.record_tool(
        tool=tool, layer=layer, status="failed",
        install_method="choco",
        notes=f"exit {code}: {combined[-2000:]}",
    )
    console.print(f"  [failed] {tool} via choco (exit {code})")
    return False
