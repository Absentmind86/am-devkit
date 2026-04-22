"""Layer 2: Git, terminals, package managers, SSH, Tailscale, modern CLI (Phase 2)."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from core.pwsh_util import ensure_openssh_client, ensure_scoop, ensure_scoop_cli_bundle
from core.winget_util import ensure_winget_package, which

if TYPE_CHECKING:
    from rich.console import Console

    from core.install_context import InstallContext
    from core.manifest import Manifest


def _git_lfs_available() -> bool:
    try:
        proc = subprocess.run(
            ["git", "lfs", "version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15.0,
        )
        return proc.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _ssh_client_available() -> bool:
    return which("ssh.exe") is not None


def run_infrastructure(ctx: InstallContext, manifest: Manifest, console: Console) -> None:
    console.print("[bold]Layer 2 — Core infrastructure[/bold]")

    ensure_winget_package(
        ctx,
        manifest,
        console,
        tool="git",
        layer="infrastructure",
        winget_id="Git.Git",
        detect=lambda: which("git.exe") is not None,
    )
    ensure_winget_package(
        ctx,
        manifest,
        console,
        tool="git-lfs",
        layer="infrastructure",
        winget_id="GitHub.GitLFS",
        detect=_git_lfs_available,
    )
    ensure_winget_package(
        ctx,
        manifest,
        console,
        tool="github-cli",
        layer="infrastructure",
        winget_id="GitHub.cli",
        detect=lambda: which("gh.exe") is not None,
    )
    ensure_winget_package(
        ctx,
        manifest,
        console,
        tool="windows-terminal",
        layer="infrastructure",
        winget_id="Microsoft.WindowsTerminal",
        detect=lambda: which("wt.exe") is not None,
    )
    ensure_winget_package(
        ctx,
        manifest,
        console,
        tool="powershell-7",
        layer="infrastructure",
        winget_id="Microsoft.PowerShell",
        detect=lambda: which("pwsh.exe") is not None,
    )

    if _ssh_client_available():
        manifest.record_tool(
            tool="openssh-client",
            layer="infrastructure",
            status="skipped",
            install_method="WindowsOptionalFeature",
            notes="ssh.exe already available.",
        )
        console.print("  [skipped] openssh-client — already available")
    else:
        ensure_openssh_client(ctx, manifest, console)

    ensure_scoop(ctx, manifest, console)
    ensure_scoop_cli_bundle(ctx, manifest, console)

    ensure_winget_package(
        ctx,
        manifest,
        console,
        tool="oh-my-posh",
        layer="infrastructure",
        winget_id="JanDeDobbeleer.OhMyPosh",
        detect=lambda: which("oh-my-posh.exe") is not None,
    )
    ensure_winget_package(
        ctx,
        manifest,
        console,
        tool="tailscale",
        layer="infrastructure",
        winget_id="Tailscale.Tailscale",
        detect=lambda: which("tailscale.exe") is not None,
    )
