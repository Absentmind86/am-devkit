"""Install pyenv for Windows via Scoop when not already on PATH."""

from __future__ import annotations

from typing import TYPE_CHECKING

from core.pwsh_util import run_powershell
from core.winget_util import which

if TYPE_CHECKING:
    from rich.console import Console

    from core.install_context import InstallContext
    from core.manifest import Manifest


def ensure_pyenv_scoop(ctx: InstallContext, manifest: Manifest, console: Console) -> None:
    """``pyenv`` userland install (Scoop). Falls back gracefully if Scoop is missing."""
    tool = "pyenv-win"
    if which("pyenv.exe") is not None:
        manifest.record_tool(
            tool=tool,
            layer="languages",
            status="skipped",
            install_method="scoop",
            notes="pyenv already on PATH.",
        )
        console.print(f"  [skipped] {tool} — already installed")
        return

    if ctx.dry_run:
        manifest.record_tool(
            tool=tool,
            layer="languages",
            status="planned",
            install_method="scoop",
            notes="Would: scoop install pyenv",
        )
        console.print(f"  [planned] {tool} — dry-run")
        return

    ps = r"""
$ErrorActionPreference = 'Stop'
if (-not (Get-Command scoop -ErrorAction SilentlyContinue)) { exit 2 }
scoop install pyenv
exit $LASTEXITCODE
"""
    console.print(f"  [installing] {tool} via scoop …")
    code, out, err = run_powershell(ps, timeout_s=600.0)
    tail = (out + "\n" + err).strip()[-2000:]
    if code == 0:
        manifest.record_tool(
            tool=tool,
            layer="languages",
            status="installed",
            install_method="scoop",
            notes=tail or None,
        )
        console.print(f"  [done] {tool}")
        return
    if code == 2:
        manifest.record_tool(
            tool=tool,
            layer="languages",
            status="skipped",
            install_method="scoop",
            notes="scoop not available.",
        )
        console.print(f"  [skipped] {tool} — scoop not on PATH")
        return
    manifest.record_tool(
        tool=tool,
        layer="languages",
        status="failed",
        install_method="scoop",
        notes=f"exit {code}: {tail}",
    )
    console.print(f"  [failed] {tool} (exit {code})")
