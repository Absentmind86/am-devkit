"""Layer 5: GPU detection, PyTorch, Ollama, optional ML pip bundle (Phase 2)."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from typing import TYPE_CHECKING

from core.platform_util import is_macos, is_windows
from core.winget_util import ensure_winget_package, which

if TYPE_CHECKING:
    from rich.console import Console

    from core.install_context import InstallContext
    from core.manifest import Manifest


from core import ensure_repo_on_sys_path


def _ensure_ollama_linux(ctx: InstallContext, manifest: Manifest, console: Console) -> None:
    """Install Ollama on Linux via the official curl installer (no apt package)."""
    if shutil.which("ollama") is not None:
        manifest.record_tool(tool="ollama", layer="ml_stack", status="skipped",
                             install_method="curl-installer",
                             notes="ollama already on PATH.")
        console.print("  [skipped] ollama — already installed")
        return
    if ctx.dry_run:
        manifest.record_tool(tool="ollama", layer="ml_stack", status="planned",
                             install_method="curl-installer",
                             notes="Would run: curl -fsSL https://ollama.com/install.sh | sh")
        console.print("  [planned] ollama — dry-run")
        return
    console.print("  [installing] ollama via curl installer…")
    try:
        proc = subprocess.run(
            ["bash", "-c", "curl -fsSL https://ollama.com/install.sh | sh"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300.0,
        )
        combined = (proc.stdout + "\n" + proc.stderr).strip()
        if proc.returncode == 0:
            manifest.record_tool(tool="ollama", layer="ml_stack", status="installed",
                                 install_method="curl-installer",
                                 notes=combined[-2000:] if combined else None)
            console.print("  [done] ollama")
        else:
            manifest.record_tool(tool="ollama", layer="ml_stack", status="failed",
                                 install_method="curl-installer",
                                 notes=f"exit {proc.returncode}: {combined[-2000:]}")
            console.print(f"  [failed] ollama (exit {proc.returncode})")
    except (OSError, subprocess.TimeoutExpired) as exc:
        manifest.record_tool(tool="ollama", layer="ml_stack", status="failed",
                             install_method="curl-installer", notes=str(exc))
        console.print(f"  [failed] ollama — {exc}")


def _pip_ml_base(ctx: InstallContext, manifest: Manifest, console: Console) -> None:
    """Lightweight scientific stack (CPU-friendly); separate from torch wheels."""
    tool = "pip-ml-base"
    pkgs = "numpy pandas matplotlib scikit-learn jupyter ipython"
    if not ctx.install_ml_base:
        manifest.record_tool(
            tool=tool,
            layer="ml_stack",
            status="skipped",
            install_method="pip",
            notes="Pass --install-ml-base to pip install numpy pandas matplotlib scikit-learn jupyter ipython.",
        )
        console.print(f"  [skipped] {tool} — use --install-ml-base")
        return
    if ctx.dry_run:
        manifest.record_tool(
            tool=tool,
            layer="ml_stack",
            status="planned",
            install_method="pip",
            notes=f"Would: {sys.executable} -m pip install {pkgs}",
        )
        console.print(f"  [planned] {tool} — dry-run")
        return

    import subprocess

    _pkg_list = pkgs.split()
    _show = subprocess.run(
        [sys.executable, "-m", "pip", "show", *_pkg_list],
        capture_output=True, text=True, timeout=60.0,
    )
    _found = sum(1 for line in _show.stdout.splitlines() if line.startswith("Name:"))
    if _found == len(_pkg_list):
        manifest.record_tool(tool=tool, layer="ml_stack", status="skipped", install_method="pip",
                             notes="All packages already installed.")
        console.print(f"  [skipped] {tool} — already installed")
        return

    argv = [sys.executable, "-m", "pip", "install", "--upgrade", "--quiet", *_pkg_list]
    console.print(f"  [installing] {tool} via pip (streaming output below)…")
    proc = subprocess.run(argv, capture_output=False, text=True, timeout=3600.0)
    if proc.returncode == 0:
        manifest.record_tool(tool=tool, layer="ml_stack", status="installed", install_method="pip")
        console.print(f"  [done] {tool}")
    else:
        manifest.record_tool(
            tool=tool,
            layer="ml_stack",
            status="failed",
            install_method="pip",
            notes=f"exit {proc.returncode}: see terminal output above",
        )
        console.print(f"  [failed] {tool} (exit {proc.returncode})")


def run_ml_stack(ctx: InstallContext, manifest: Manifest, console: Console) -> None:
    console.print("[bold]Layer 5 — AI / ML stack[/bold]")
    if not ctx.profile_selected("ai-ml"):
        manifest.record_tool(
            tool="gpu-detect",
            layer="ml_stack",
            status="skipped",
            install_method="profile-gate",
            notes="ai-ml profile not selected.",
        )
        console.print("  [skipped] GPU / PyTorch — ai-ml not selected")
        return

    ensure_repo_on_sys_path()
    from scripts.gpu_detect import detect_gpu_for_pytorch

    report = detect_gpu_for_pytorch()
    manifest.record_tool(
        tool="gpu-detect",
        layer="ml_stack",
        status="installed",
        install_method="internal",
        notes=json.dumps(report.to_json_dict(), indent=2)[:4000],
    )
    console.print(f"  [done] GPU detect — torch index: {report.pytorch_index_url}")

    # Ollama is in WINGET_CATALOG (ml_stack layer) so the GUI can exclude it.
    if "ollama" in ctx.catalog_exclude_tools:
        manifest.record_tool(
            tool="ollama",
            layer="ml_stack",
            status="skipped",
            install_method="user-exclude",
            notes="Excluded via --exclude-catalog-tool ollama.",
        )
        console.print("  [skipped] ollama — user excluded")
    elif is_windows():
        ensure_winget_package(
            ctx,
            manifest,
            console,
            tool="ollama",
            layer="ml_stack",
            winget_id="Ollama.Ollama",
            detect=lambda: bool(which("ollama.exe") or shutil.which("ollama")),
        )
    elif is_macos():
        from core.brew_util import ensure_brew_package
        ensure_brew_package(
            ctx, manifest, console,
            tool="ollama", layer="ml_stack",
            pkg_id="ollama", is_cask=True,
            detect=lambda: shutil.which("ollama") is not None,
        )
    else:
        _ensure_ollama_linux(ctx, manifest, console)

    _pip_ml_base(ctx, manifest, console)

    _is_directml = report.torch_path_kind == "amd_directml"

    if ctx.install_ml_wheels and not ctx.dry_run:
        import subprocess

        if _is_directml:
            _torch_pkg = "torch-directml"
            argv = [sys.executable, "-m", "pip", "install", "--upgrade", "--quiet", _torch_pkg]
            label = "PyTorch + DirectML (AMD GPU)"
        else:
            _torch_pkg = "torch"
            argv = [
                sys.executable, "-m", "pip", "install", "--upgrade", "--quiet",
                "torch", "torchvision", "torchaudio",
                "--index-url", report.pytorch_index_url,
            ]
            label = "PyTorch wheels"

        _torch_show = subprocess.run(
            [sys.executable, "-m", "pip", "show", _torch_pkg],
            capture_output=True, text=True, timeout=60.0,
        )
        if _torch_show.returncode == 0 and any(
            ln.startswith("Name:") for ln in _torch_show.stdout.splitlines()
        ):
            manifest.record_tool(tool="pytorch-pip", layer="ml_stack", status="skipped",
                                 install_method="pip", notes=f"{_torch_pkg} already installed.")
            console.print(f"  [skipped] {label} — already installed")
        else:
            console.print(f"  [installing] {label} via pip (streaming output below)…")
            proc = subprocess.run(argv, capture_output=False, text=True, timeout=3600.0)
            if proc.returncode == 0:
                manifest.record_tool(
                    tool="pytorch-pip",
                    layer="ml_stack",
                    status="installed",
                    install_method="pip",
                )
                console.print(f"  [done] {label}")
            else:
                manifest.record_tool(
                    tool="pytorch-pip",
                    layer="ml_stack",
                    status="failed",
                    install_method="pip",
                    notes=f"exit {proc.returncode}: see terminal output above",
                )
                console.print(f"  [failed] {label} (exit {proc.returncode})")
    elif ctx.install_ml_wheels and ctx.dry_run:
        dry_note = (
            "Would pip install torch-directml (AMD DirectX 12 GPU)"
            if _is_directml
            else f"Would pip install torch from {report.pytorch_index_url}"
        )
        manifest.record_tool(
            tool="pytorch-pip",
            layer="ml_stack",
            status="planned",
            install_method="pip",
            notes=dry_note,
        )
        console.print("  [planned] PyTorch pip — dry-run")
    else:
        skip_note = (
            "Pass --install-ml-wheels to run pip install torch-directml (AMD GPU detected)."
            if _is_directml
            else "Pass --install-ml-wheels to run pip install torch."
        )
        manifest.record_tool(
            tool="pytorch-pip",
            layer="ml_stack",
            status="skipped",
            install_method="pip",
            notes=skip_note,
        )
        console.print("  [skipped] PyTorch pip — use --install-ml-wheels to install")
