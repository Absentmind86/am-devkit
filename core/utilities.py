"""Layer 7: utilities + security/network tooling (Phase 2B — catalog + PROJECT.md)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from core.catalog_install import install_catalog_layer

if TYPE_CHECKING:
    from rich.console import Console

    from core.install_context import InstallContext
    from core.manifest import Manifest


def run_utilities(ctx: InstallContext, manifest: Manifest, console: Console) -> None:
    console.print("[bold]Layer 7 — Utilities[/bold]")
    install_catalog_layer(ctx, manifest, console, "utilities")
