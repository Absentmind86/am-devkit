"""Layer 6: WSL, Docker, Kubernetes, databases, cloud CLIs (Phase 2B).

Docker Desktop, kubectl, and Helm are now driven through WINGET_CATALOG
(install_catalog.py) so the GUI can exclude them via --exclude-catalog-tool.
The old _wants_docker / _wants_kubernetes_cli helpers are removed; profile
gating and user exclusions are handled by install_catalog_layer automatically.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from core.catalog_install import install_catalog_layer
from core.install_catalog import catalog_entries_for_layer
from core.pwsh_util import ensure_wsl_default_distro, ensure_wsl_prereq

if TYPE_CHECKING:
    from rich.console import Console

    from core.install_context import InstallContext
    from core.manifest import Manifest


_CONTAINER_TOOLS: frozenset[str] = frozenset({"docker-desktop", "podman-desktop"})


def run_devops(ctx: InstallContext, manifest: Manifest, console: Console) -> None:
    console.print("[bold]Layer 6 — DevOps & containers[/bold]")

    # Docker Desktop and Podman Desktop require WSL2 to function on Windows 11 Home.
    # Auto-enable the WSL prereq whenever either container tool will be installed,
    # without forcing the user to pass --enable-wsl.
    if not ctx.enable_wsl:
        selected = set(ctx.profiles)
        needs_wsl = any(
            e.tool in _CONTAINER_TOOLS
            and e.applies_to(selected)
            and e.tool not in ctx.catalog_exclude_tools
            for e in catalog_entries_for_layer("devops")
        )
        if needs_wsl:
            ctx.enable_wsl = True

    ensure_wsl_prereq(ctx, manifest, console)
    if ctx.wsl_default_distro:
        ensure_wsl_default_distro(ctx, manifest, console, ctx.wsl_default_distro)

    # Docker Desktop, kubectl, Helm, PostgreSQL, Redis, cloud CLIs, etc. are all
    # catalog-driven — profile gates and user excludes are applied automatically.
    install_catalog_layer(ctx, manifest, console, "devops")
