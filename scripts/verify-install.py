#!/usr/bin/env python3
"""Post-install verification: check every manifest tool against the actual system state.

Uses the same detector logic as the installer for catalog tools.
Non-catalog tools (scoop, pip, rustup, pyenv, etc.) have explicit detectors here.
"""

from __future__ import annotations

import importlib.metadata
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))

from core.install_catalog import WINGET_CATALOG, get_detector  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _which(exe: str) -> bool:
    return shutil.which(exe) is not None


def _file(*paths: str | Path) -> bool:
    return any(Path(p).is_file() for p in paths)


def _dir(*paths: str | Path) -> bool:
    return any(Path(p).is_dir() for p in paths)


def _pip_pkg(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except Exception:
        return None


def _run(cmd: list[str], timeout: int = 5) -> int:
    try:
        return subprocess.run(cmd, capture_output=True, timeout=timeout).returncode
    except Exception:
        return -1


# ---------------------------------------------------------------------------
# Non-catalog tool detectors
# Keyed by the tool name written to devkit-manifest.json
# ---------------------------------------------------------------------------

_LOC  = Path(os.environ.get("LOCALAPPDATA", ""))
_PF   = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
_HOME = Path(os.environ.get("USERPROFILE", ""))


def _detect_non_catalog(tool: str) -> bool | None:
    """Return True/False for known non-catalog tools, None if unknown."""

    # ── bootstrap / infrastructure ────────────────────────────────────────
    if tool == "scoop":
        return _which("scoop") or _file(_HOME / "scoop" / "shims" / "scoop.ps1")

    if tool == "scoop-cli-bundle":
        # All seven tools must be present
        return all(_which(t) for t in ("bat", "rg", "fd", "fzf", "jq", "lazygit", "delta"))

    if tool == "openssh-client":
        return _which("ssh.exe") or _which("ssh")

    if tool == "pyenv-win":
        return (
            _which("pyenv")
            or _file(_HOME / ".pyenv" / "pyenv-win" / "bin" / "pyenv.bat")
        )

    if tool == "rustup-stable":
        return _which("rustup") or _which("cargo")

    # ── editors / extensions ──────────────────────────────────────────────
    if tool in ("vscode-extensions", "cursor-extensions"):
        ext_dir = _LOC / "Programs" / "Microsoft VS Code" / "resources" / "app" / "extensions"
        cursor_ext = _LOC / "Programs" / "cursor" / "resources" / "app" / "extensions"
        vscode_user_ext = _HOME / ".vscode" / "extensions"
        cursor_user_ext = _HOME / ".cursor" / "extensions"
        return _dir(ext_dir, cursor_ext, vscode_user_ext, cursor_user_ext)

    # ── ML stack ─────────────────────────────────────────────────────────
    if tool == "gpu-detect":
        return True  # internal step, always runs

    if tool in ("pytorch-pip", "pytorch-cuda", "pytorch-directml"):
        try:
            import torch  # noqa: F401
            return True
        except ImportError:
            return False

    if tool == "pip-ml-base":
        return all(
            _pip_pkg(p) is not None
            for p in ("numpy", "pandas", "matplotlib", "scikit-learn", "jupyter")
        )

    # ── sanitization ─────────────────────────────────────────────────────
    if tool == "am-sanitize":
        return _file(_REPO_ROOT / "scripts" / "sanitize.ps1")

    # ── WSL ──────────────────────────────────────────────────────────────
    if tool == "wsl-prereq":
        return _which("wsl") or _which("wsl.exe")

    if tool == "wsl-default-distro":
        rc = _run(["wsl.exe", "--list", "--quiet"], timeout=8)
        return rc == 0

    # ── meta / always-true bookkeeping entries ────────────────────────────
    if tool in (
        "install-start", "system-scan", "system-restore-point",
        "dotfiles-seed", "path-auditor", "html-report",
        "restore-bundle", "launchpad", "sandbox-templates",
        "obsidian-vault",
    ):
        return None  # skip — bookkeeping, not verifiable presence checks

    return None  # unknown tool


# ---------------------------------------------------------------------------
# Catalog detector wrapper
# ---------------------------------------------------------------------------

_CATALOG_BY_TOOL = {e.tool: e for e in WINGET_CATALOG}


def _detect(tool: str) -> bool | None:
    """Return True=found, False=missing, None=skip (unverifiable)."""
    non_cat = _detect_non_catalog(tool)
    if non_cat is not None:
        return non_cat
    if tool in _CATALOG_BY_TOOL:
        try:
            return get_detector(_CATALOG_BY_TOOL[tool])()
        except Exception:
            return False
    return None  # manifest tool not known to verifier — skip


# ---------------------------------------------------------------------------
# Manifest loader
# ---------------------------------------------------------------------------

def _load_manifest() -> dict[str, Any] | None:
    p = _REPO_ROOT / "devkit-manifest.json"
    if not p.is_file():
        return None
    try:
        with open(p) as f:
            return json.load(f)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# PyTorch deep check
# ---------------------------------------------------------------------------

def _pytorch_info() -> dict[str, Any]:
    try:
        import torch
        info: dict[str, Any] = {"installed": True, "version": torch.__version__}
        info["cuda_available"] = torch.cuda.is_available()
        if info["cuda_available"]:
            info["cuda_version"] = torch.version.cuda
            info["device_count"] = torch.cuda.device_count()
            info["device_name"] = torch.cuda.get_device_name(0)
        return info
    except ImportError:
        return {"installed": False}
    except Exception as exc:
        return {"installed": True, "error": str(exc)}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def verify_install() -> None:
    print("=" * 90)
    print("AM-DevKit Install Verification")
    print("=" * 90)

    manifest = _load_manifest()
    if not manifest:
        print("\nNo manifest found — run the installer first (even --dry-run writes a manifest).\n")
        return

    print(f"\nManifest generated : {manifest.get('generated_at', 'unknown')}")
    print(f"DevKit version     : {manifest.get('devkit_version', 'unknown')}\n")

    # Collect tools the manifest considers installed/planned
    expected: dict[str, dict] = {}
    for entry in manifest.get("tools", []):
        name   = entry.get("tool", "")
        status = entry.get("status", "")
        if name and status in ("installed", "planned"):
            expected[name] = {
                "status": status,
                "layer":  entry.get("layer", "?"),
                "method": entry.get("install_method", "?"),
            }

    print(f"Manifest: {len(expected)} tools marked installed/planned\n")
    print("TOOL VERIFICATION")
    print("-" * 90)

    found, missing, skipped = [], [], []

    for tool in sorted(expected):
        result = _detect(tool)
        if result is None:
            skipped.append(tool)
            continue
        layer = expected[tool]["layer"]
        if result:
            found.append(tool)
            print(f"  [+] {tool:40s} ({layer})")
        else:
            missing.append(tool)
            print(f"  [-] {tool:40s} ({layer})  MISSING")

    verifiable = len(found) + len(missing)
    print(f"\nResult: {len(found)}/{verifiable} verified present  "
          f"({len(skipped)} bookkeeping entries skipped)")

    # ── ML stack deep check ───────────────────────────────────────────────
    print("\n" + "=" * 90)
    print("ML STACK")
    print("-" * 90)

    pt = _pytorch_info()
    if pt["installed"]:
        print(f"PyTorch  v{pt.get('version', '?')}")
        if "error" in pt:
            print(f"  error: {pt['error']}")
        elif pt.get("cuda_available"):
            print(f"  CUDA {pt.get('cuda_version')}  |  "
                  f"{pt.get('device_count')} device(s)  |  {pt.get('device_name')}")
        else:
            print("  CUDA not available (CPU-only or DirectML build)")
    else:
        print("PyTorch  NOT installed")

    print("\nML pip packages:")
    ml_pkgs = {
        "numpy": "numpy",
        "pandas": "pandas",
        "matplotlib": "matplotlib",
        "scikit-learn": "scikit-learn",
        "jupyter_core": "jupyter",
        "IPython": "IPython",
    }
    for import_name, display in ml_pkgs.items():
        ver = _pip_pkg(import_name)
        tag = f"v{ver}" if ver else "NOT installed"
        icon = "[+]" if ver else "[-]"
        print(f"  {icon} {display:15s}  {tag}")

    # ── Sanitization ──────────────────────────────────────────────────────
    print("\n" + "=" * 90)
    print("SANITIZATION")
    print("-" * 90)
    san_entry = next(
        (e for e in manifest.get("tools", []) if e.get("tool") == "am-sanitize"),
        None,
    )
    if san_entry:
        print(f"  Status  : {san_entry.get('status', '?')}")
        print(f"  Notes   : {san_entry.get('notes', '—')}")
        print(f"  Script  : {'present' if _file(_REPO_ROOT / 'scripts' / 'sanitize.ps1') else 'MISSING'}")
    else:
        print("  Sanitization was not run (am-sanitize not in manifest)")

    # ── Summary ───────────────────────────────────────────────────────────
    print("\n" + "=" * 90)
    print("SUMMARY")
    print("=" * 90)

    if missing:
        print(f"\nMISSING ({len(missing)}):")
        for t in missing:
            layer = expected[t]["layer"]
            print(f"  - {t}  (layer: {layer})")
        print("\nRe-run the installer — idempotent steps will skip already-present tools.")
    else:
        print("\nAll verifiable tools confirmed present.")

    status_counts: dict[str, int] = {}
    for entry in manifest.get("tools", []):
        s = entry.get("status", "unknown")
        status_counts[s] = status_counts.get(s, 0) + 1
    print("\nManifest status breakdown:")
    for s in ("installed", "planned", "skipped", "failed"):
        if status_counts.get(s):
            print(f"  {s:12s}: {status_counts[s]}")
    print()


if __name__ == "__main__":
    verify_install()
