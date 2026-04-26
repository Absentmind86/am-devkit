"""Layer 2: Core infrastructure — bootstrap tools + catalog-driven infra stack.

Bootstrap foundation (installed directly, NOT via catalog):
    Git, Git LFS   — required before anything else can clone or version-control
    Scoop          — required before any Scoop-based tool can be installed
    OpenSSH client — required early for key auth; enabled as a Windows feature

Everything else in Layer 2 (GitHub CLI, Windows Terminal, PowerShell 7,
Oh My Posh, Tailscale) is catalog-driven via install_catalog_layer so the
GUI can exclude individual tools with --exclude-catalog-tool.
"""

from __future__ import annotations

import shutil
import subprocess
from typing import TYPE_CHECKING

from core.catalog_install import install_catalog_layer
from core.platform_util import is_macos, is_windows, primary_pkg_manager
from core.winget_util import ensure_winget_package, which

if TYPE_CHECKING:
    from rich.console import Console

    from core.install_context import InstallContext
    from core.manifest import Manifest


def _git_lfs_available() -> bool:
    try:
        proc = subprocess.run(
            ["git", "lfs", "version"],
            capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=15.0,
        )
        return proc.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _ssh_available() -> bool:
    return shutil.which("ssh") is not None or shutil.which("ssh.exe") is not None


def _ensure_git_unix(ctx: InstallContext, manifest: Manifest, console: Console) -> None:
    """Install git on Linux/macOS if missing."""
    if shutil.which("git"):
        manifest.record_tool(tool="git", layer="infrastructure", status="skipped",
                             install_method="existing", notes="Already on PATH.")
        console.print("  [skipped] git — already installed")
        return
    if is_macos():
        from core.brew_util import ensure_brew_package
        ensure_brew_package(ctx, manifest, console, tool="git", layer="infrastructure",
                            pkg_id="git", detect=lambda: shutil.which("git") is not None)
    else:
        from core.linux_util import ensure_linux_package
        ensure_linux_package(ctx, manifest, console, tool="git", layer="infrastructure",
                             pkg_id="git", manager=primary_pkg_manager(),
                             detect=lambda: shutil.which("git") is not None)


def _ensure_git_lfs_unix(ctx: InstallContext, manifest: Manifest, console: Console) -> None:
    """Install git-lfs on Linux/macOS if missing."""
    if _git_lfs_available():
        manifest.record_tool(tool="git-lfs", layer="infrastructure", status="skipped",
                             install_method="existing", notes="Already on PATH.")
        console.print("  [skipped] git-lfs — already installed")
        return
    if is_macos():
        from core.brew_util import ensure_brew_package
        ensure_brew_package(ctx, manifest, console, tool="git-lfs", layer="infrastructure",
                            pkg_id="git-lfs", detect=_git_lfs_available)
    else:
        from core.linux_util import ensure_linux_package
        ensure_linux_package(ctx, manifest, console, tool="git-lfs", layer="infrastructure",
                             pkg_id="git-lfs", manager=primary_pkg_manager(),
                             detect=_git_lfs_available)


def run_infrastructure(ctx: InstallContext, manifest: Manifest, console: Console) -> None:
    console.print("[bold]Layer 2 — Core infrastructure[/bold]")

    # --- Bootstrap foundation (must run before catalog; no ordering flexibility) ---
    if is_windows():
        from core.pwsh_util import ensure_openssh_client, ensure_scoop, ensure_scoop_cli_bundle
        ensure_winget_package(
            ctx, manifest, console,
            tool="git", layer="infrastructure",
            winget_id="Git.Git",
            detect=lambda: which("git.exe") is not None,
        )
        ensure_winget_package(
            ctx, manifest, console,
            tool="git-lfs", layer="infrastructure",
            winget_id="GitHub.GitLFS",
            detect=_git_lfs_available,
        )
        if _ssh_available():
            manifest.record_tool(tool="openssh-client", layer="infrastructure", status="skipped",
                                 install_method="WindowsOptionalFeature", notes="ssh.exe already available.")
            console.print("  [skipped] openssh-client — already available")
        else:
            ensure_openssh_client(ctx, manifest, console)
        ensure_scoop(ctx, manifest, console)
        ensure_scoop_cli_bundle(ctx, manifest, console)
    else:
        _ensure_git_unix(ctx, manifest, console)
        _ensure_git_lfs_unix(ctx, manifest, console)
        if _ssh_available():
            manifest.record_tool(tool="openssh-client", layer="infrastructure", status="skipped",
                                 install_method="existing", notes="ssh already available.")
            console.print("  [skipped] openssh-client — already available")
        else:
            manifest.record_tool(tool="openssh-client", layer="infrastructure", status="skipped",
                                 install_method="existing",
                                 notes="ssh not found — install openssh-client manually.")
            console.print("  [skipped] openssh-client — not found; install manually")

    # --- Catalog-driven infra (excludable via --exclude-catalog-tool) ---
    install_catalog_layer(ctx, manifest, console, "infrastructure")
