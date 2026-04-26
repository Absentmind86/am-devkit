"""Layer 3: VS Code, Cursor, extension pack (Phase 2)."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from core.catalog_install import install_catalog_layer
from core.platform_util import is_windows
from core.winget_util import ensure_winget_package, which

if TYPE_CHECKING:
    from rich.console import Console

    from core.install_context import InstallContext
    from core.manifest import Manifest


def _vscode_cli() -> Path | None:
    """Return the path to the VS Code CLI binary for the current platform."""
    if is_windows():
        local = Path(
            __import__("os").environ.get("LOCALAPPDATA", "")
        ) / "Programs" / "Microsoft VS Code" / "bin" / "code.cmd"
        if local.is_file():
            return local
        w = which("code.cmd") or which("code.exe")
        return Path(w) if w else None
    # macOS / Linux: code is on PATH after install
    found = shutil.which("code") or shutil.which("code-insiders")
    return Path(found) if found else None


def _cursor_cli() -> Path | None:
    """Return the path to the Cursor CLI binary for the current platform."""
    if is_windows():
        local = (
            Path(__import__("os").environ.get("LOCALAPPDATA", ""))
            / "Programs" / "cursor" / "resources" / "app" / "bin" / "cursor.cmd"
        )
        if local.is_file():
            return local
        w = which("cursor.cmd") or which("cursor.exe")
        return Path(w) if w else None
    found = shutil.which("cursor")
    return Path(found) if found else None


def _load_vscode_extension_ids(repo_root: Path) -> list[str]:
    path = repo_root / "config" / "vscode" / "extensions.json"
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    rec = data.get("recommendations")
    if not isinstance(rec, list):
        return []
    return [str(x).strip() for x in rec if isinstance(x, str) and str(x).strip()]


def _build_cli_argv(cli_cmd: Path, *args: str) -> list[str]:
    """Build the argv for a VS Code-compatible CLI call.

    On Windows the binary is a .cmd file and must be launched via cmd.exe.
    On other platforms it is a plain executable.
    """
    if is_windows():
        return ["cmd.exe", "/c", str(cli_cmd), *args]
    return [str(cli_cmd), *args]


def _list_installed_extensions(cli_cmd: Path) -> frozenset[str]:
    """Return the lowercase IDs of extensions already installed in this editor."""
    try:
        proc = subprocess.run(
            _build_cli_argv(cli_cmd, "--list-extensions"),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30.0,
        )
        if proc.returncode == 0:
            return frozenset(ln.strip().lower() for ln in proc.stdout.splitlines() if ln.strip())
    except (OSError, subprocess.TimeoutExpired):
        pass
    return frozenset()


def _install_extensions_via_cli(
    console: Console,
    cli_cmd: Path,
    extension_ids: list[str],
    label: str,
) -> tuple[int, list[str]]:
    """Install *extension_ids* via a VS Code-compatible CLI (code or cursor).

    Pre-checks which extensions are already installed and skips them to avoid
    unnecessary network downloads. Returns ``(ok_count, failed_list)``.
    """
    already_installed = _list_installed_extensions(cli_cmd)
    ok = 0
    failed: list[str] = []
    n = len(extension_ids)
    for i, ext in enumerate(extension_ids, 1):
        if ext.lower() in already_installed:
            console.print(f"    [{i}/{n}] {ext} — already installed")
            ok += 1
            continue
        console.print(f"    [{i}/{n}] {ext} …")
        argv = _build_cli_argv(cli_cmd, "--install-extension", ext)
        try:
            proc = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=600.0,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            failed.append(f"{ext}: {exc}")
            console.print(f"           failed: {exc}")
            continue
        if proc.returncode == 0:
            ok += 1
        else:
            tail = (proc.stderr or proc.stdout or "").strip()[-400:]
            failed.append(f"{ext}: exit {proc.returncode} {tail}")
            console.print(f"           failed (exit {proc.returncode})")
    return ok, failed


def _install_vscode_extensions(
    ctx: InstallContext,
    manifest: Manifest,
    console: Console,
    code_cmd: Path,
    extension_ids: list[str],
) -> None:
    if not extension_ids:
        manifest.record_tool(
            tool="vscode-extensions",
            layer="editors",
            status="skipped",
            install_method="code-cli",
            notes="No recommendations in config/vscode/extensions.json.",
        )
        console.print("  [skipped] vscode-extensions — empty list")
        return

    if ctx.dry_run:
        manifest.record_tool(
            tool="vscode-extensions",
            layer="editors",
            status="planned",
            install_method="code-cli",
            notes=f"Would install {len(extension_ids)} extensions.",
        )
        console.print(f"  [planned] vscode-extensions — {len(extension_ids)} ids (dry-run)")
        return

    n = len(extension_ids)
    console.print(f"  [installing] vscode-extensions — {n} extensions via code …")
    ok, failed = _install_extensions_via_cli(console, code_cmd, extension_ids, "vscode")

    notes = f"ok={ok} failed={len(failed)}"
    if failed:
        notes += "\n" + "\n".join(failed[:12])
    if ok == 0 and failed:
        status = "failed"
    elif failed:
        status = "installed"
        notes = "partial: " + notes
    else:
        status = "installed"
    manifest.record_tool(
        tool="vscode-extensions",
        layer="editors",
        status=status,
        install_method="code-cli",
        notes=notes[:4000],
    )
    label = "done" if ok == n else ("partial" if ok else "failed")
    console.print(f"  [{label}] vscode-extensions — {ok}/{n} ok")
    if failed:
        for line in failed[:5]:
            console.print(f"    [dim]{line[:160]}[/dim]")

    # Also install extensions for Cursor if available
    cursor = _cursor_cli()
    if cursor is not None and "cursor" not in ctx.catalog_exclude_tools:
        console.print(f"  [installing] cursor-extensions — {n} extensions via cursor …")
        c_ok, c_failed = _install_extensions_via_cli(console, cursor, extension_ids, "cursor")
        c_notes = f"ok={c_ok} failed={len(c_failed)}"
        if c_failed:
            c_notes += "\n" + "\n".join(c_failed[:12])
        if c_ok == 0 and c_failed:
            c_status = "failed"
        elif c_failed:
            c_status = "installed"
            c_notes = "partial: " + c_notes
        else:
            c_status = "installed"
        manifest.record_tool(
            tool="cursor-extensions",
            layer="editors",
            status=c_status,
            install_method="cursor-cli",
            notes=c_notes[:4000],
        )
        c_label = "done" if c_ok == n else ("partial" if c_ok else "failed")
        console.print(f"  [{c_label}] cursor-extensions — {c_ok}/{n} ok")
        if c_failed:
            for line in c_failed[:5]:
                console.print(f"    [dim]{line[:160]}[/dim]")


def run_editors(ctx: InstallContext, manifest: Manifest, console: Console) -> None:
    console.print("[bold]Layer 3 — Editors[/bold]")

    if is_windows():
        # Windows: install vscode/cursor directly via winget so code.cmd is available
        # immediately for the extension installer step below.
        if "vscode" in ctx.catalog_exclude_tools:
            manifest.record_tool(
                tool="vscode", layer="editors", status="skipped",
                install_method="user-exclude",
                notes="Excluded via --exclude-catalog-tool vscode.",
            )
            console.print("  [skipped] vscode — user excluded")
        else:
            ensure_winget_package(
                ctx, manifest, console,
                tool="vscode", layer="editors",
                winget_id="Microsoft.VisualStudioCode",
                detect=lambda: _vscode_cli() is not None,
            )

        if "cursor" in ctx.catalog_exclude_tools:
            manifest.record_tool(
                tool="cursor", layer="editors", status="skipped",
                install_method="user-exclude",
                notes="Excluded via --exclude-catalog-tool cursor.",
            )
            console.print("  [skipped] cursor — user excluded")
        else:
            ensure_winget_package(
                ctx, manifest, console,
                tool="cursor", layer="editors",
                winget_id="Anysphere.Cursor",
                detect=lambda: which("cursor.exe") is not None,
            )

        # Remaining editors (jetbrains-toolbox) — skip vscode/cursor already handled.
        install_catalog_layer(
            ctx, manifest, console, "editors",
            skip_tools=frozenset({"vscode", "cursor"}),
        )
    else:
        # macOS / Linux: catalog handles vscode (brew cask / apt + Microsoft repo)
        # and cursor (brew cask) alongside jetbrains-toolbox etc.
        install_catalog_layer(ctx, manifest, console, "editors")

    # VS Code extensions — platform-agnostic CLI invocation via _build_cli_argv.
    if "vscode" not in ctx.catalog_exclude_tools:
        ids = _load_vscode_extension_ids(ctx.repo_root)
        code = _vscode_cli()
        if code is None:
            manifest.record_tool(
                tool="vscode-extensions",
                layer="editors",
                status="skipped",
                install_method="code-cli",
                notes="VS Code CLI not found; install VS Code first.",
            )
            console.print("  [skipped] vscode-extensions — code CLI not found")
        else:
            _install_vscode_extensions(ctx, manifest, console, code, ids)
