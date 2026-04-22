"""Layer 6: WSL, Docker, Kubernetes, databases, cloud CLIs (Phase 2B)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from core.catalog_install import install_catalog_layer
from core.pwsh_util import ensure_wsl_default_distro, ensure_wsl_prereq
from core.winget_util import ensure_winget_package, which

if TYPE_CHECKING:
    from rich.console import Console

    from core.install_context import InstallContext
    from core.manifest import Manifest


def _wants_docker(ctx: InstallContext) -> bool:
    return ctx.profile_selected("web-fullstack") or ctx.profile_selected("ai-ml")


def _wants_kubernetes_cli(ctx: InstallContext) -> bool:
    return any(ctx.profile_selected(p) for p in ("web-fullstack", "ai-ml", "systems"))


def run_devops(ctx: InstallContext, manifest: Manifest, console: Console) -> None:
    console.print("[bold]Layer 6 — DevOps & containers[/bold]")

    ensure_wsl_prereq(ctx, manifest, console)
    if ctx.wsl_default_distro:
        ensure_wsl_default_distro(ctx, manifest, console, ctx.wsl_default_distro)

    if not _wants_docker(ctx):
        manifest.record_tool(
            tool="docker-desktop",
            layer="devops",
            status="skipped",
            install_method="profile-gate",
            notes="Select ai-ml or web-fullstack for Docker Desktop.",
        )
        console.print("  [skipped] Docker Desktop — profile not selected")
    else:
        ensure_winget_package(
            ctx,
            manifest,
            console,
            tool="docker-desktop",
            layer="devops",
            winget_id="Docker.DockerDesktop",
            detect=lambda: which("docker.exe") is not None,
        )

    if _wants_kubernetes_cli(ctx):
        ensure_winget_package(
            ctx,
            manifest,
            console,
            tool="kubectl",
            layer="devops",
            winget_id="Kubernetes.kubectl",
            detect=lambda: which("kubectl.exe") is not None,
        )
        ensure_winget_package(
            ctx,
            manifest,
            console,
            tool="helm",
            layer="devops",
            winget_id="Helm.Helm",
            detect=lambda: which("helm.exe") is not None,
        )
    else:
        for t in ("kubectl", "helm"):
            manifest.record_tool(
                tool=t,
                layer="devops",
                status="skipped",
                install_method="profile-gate",
                notes="Select web-fullstack, ai-ml, or systems for Kubernetes CLIs.",
            )
        console.print("  [skipped] kubectl / helm — profile not selected")

    install_catalog_layer(ctx, manifest, console, "devops")
