"""Linux package manager installs — apt / dnf / pacman / zypper (mirrors winget_util.py pattern)."""
from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rich.console import Console

    from core.install_context import InstallContext
    from core.manifest import Manifest

_SUPPORTED_MANAGERS = ("apt", "apt-get", "dnf", "pacman", "zypper")

# Bash one-liners that add a third-party apt repo + run apt-get update.
# Only applied when the package manager is apt/apt-get; other managers
# attempt the install directly (package may exist in default repos).
_APT_REPO_SETUP: dict[str, str] = {
    "gh": (
        "sudo mkdir -p /etc/apt/keyrings && "
        "wget -qO- https://cli.github.com/packages/githubcli-archive-keyring.gpg "
        "| sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg > /dev/null && "
        "sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg && "
        'echo "deb [arch=$(dpkg --print-architecture) '
        "signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] "
        'https://cli.github.com/packages stable main" '
        "| sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null && "
        "sudo apt-get update -q"
    ),
    "microsoft": (
        "wget -q https://packages.microsoft.com/config/ubuntu/"
        "$(lsb_release -rs)/packages-microsoft-prod.deb -O /tmp/ms-prod.deb && "
        "sudo dpkg -i /tmp/ms-prod.deb && rm -f /tmp/ms-prod.deb && "
        "sudo apt-get update -q"
    ),
    "vscode": (
        "wget -qO- https://packages.microsoft.com/keys/microsoft.asc "
        "| gpg --dearmor > /tmp/packages.microsoft.gpg && "
        "sudo install -D -o root -g root -m 644 "
        "/tmp/packages.microsoft.gpg /etc/apt/keyrings/packages.microsoft.gpg && "
        'echo "deb [arch=amd64,arm64,armhf '
        "signed-by=/etc/apt/keyrings/packages.microsoft.gpg] "
        'https://packages.microsoft.com/repos/code stable main" '
        "| sudo tee /etc/apt/sources.list.d/vscode.list > /dev/null && "
        "rm -f /tmp/packages.microsoft.gpg && sudo apt-get update -q"
    ),
    "azure-cli": (
        "curl -sLS https://packages.microsoft.com/keys/microsoft.asc "
        "| gpg --dearmor | sudo tee /etc/apt/keyrings/microsoft.gpg > /dev/null && "
        "sudo chmod go+r /etc/apt/keyrings/microsoft.gpg && "
        "AZ_DIST=$(lsb_release -cs) && "
        'echo "deb [arch=$(dpkg --print-architecture) '
        "signed-by=/etc/apt/keyrings/microsoft.gpg] "
        "https://packages.microsoft.com/repos/azure-cli/ ${AZ_DIST} main\" "
        "| sudo tee /etc/apt/sources.list.d/azure-cli.list > /dev/null && "
        "sudo apt-get update -q"
    ),
    "kubernetes": (
        "sudo mkdir -p /etc/apt/keyrings && "
        "curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.30/deb/Release.key "
        "| gpg --dearmor -o /tmp/kubernetes-archive-keyring.gpg && "
        "sudo install -o root -g root -m 644 "
        "/tmp/kubernetes-archive-keyring.gpg /etc/apt/keyrings/ && "
        'echo "deb [signed-by=/etc/apt/keyrings/kubernetes-archive-keyring.gpg] '
        "https://pkgs.k8s.io/core:/stable:/v1.30/deb/ /\" "
        "| sudo tee /etc/apt/sources.list.d/kubernetes.list > /dev/null && "
        "sudo apt-get update -q"
    ),
    "helm": (
        "curl -fsSL https://baltocdn.com/helm/signing.asc "
        "| gpg --dearmor | sudo tee /usr/share/keyrings/helm.gpg > /dev/null && "
        "sudo apt-get install -y apt-transport-https && "
        'echo "deb [arch=$(dpkg --print-architecture) '
        "signed-by=/usr/share/keyrings/helm.gpg] "
        'https://baltocdn.com/helm/stable/debian/ all main" '
        "| sudo tee /etc/apt/sources.list.d/helm-stable-debian.list > /dev/null && "
        "sudo apt-get update -q"
    ),
    "tailscale": (
        "curl -fsSL https://tailscale.com/install.sh | sh"
    ),
    "google-cloud": (
        "curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg "
        "| sudo gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg && "
        'echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] '
        'https://packages.cloud.google.com/apt cloud-sdk main" '
        "| sudo tee /etc/apt/sources.list.d/google-cloud-sdk.list > /dev/null && "
        "sudo apt-get update -q"
    ),
    "adoptium": (
        "sudo mkdir -p /etc/apt/keyrings && "
        "wget -qO - https://packages.adoptium.net/artifactory/api/gpg/key/public "
        "| gpg --dearmor | sudo tee /etc/apt/keyrings/adoptium.gpg > /dev/null && "
        'echo "deb [signed-by=/etc/apt/keyrings/adoptium.gpg] '
        "https://packages.adoptium.net/artifactory/deb "
        "$(awk -F= '/^VERSION_CODENAME/{print$2}' /etc/os-release) main\" "
        "| sudo tee /etc/apt/sources.list.d/adoptium.list > /dev/null && "
        "sudo apt-get update -q"
    ),
    "unity": (
        "sudo mkdir -p /etc/apt/keyrings && "
        "wget -qO - https://hub.unity3d.com/linux/keys/public "
        "| gpg --dearmor | sudo tee /etc/apt/keyrings/Unity_Technologies_ApS.gpg > /dev/null && "
        'echo "deb [signed-by=/etc/apt/keyrings/Unity_Technologies_ApS.gpg] '
        "https://hub.unity3d.com/linux/repos/deb stable main\" "
        "| sudo tee /etc/apt/sources.list.d/unityhub.list > /dev/null && "
        "sudo apt-get update -q"
    ),
    "ngrok": (
        "curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc "
        "| sudo tee /etc/apt/trusted.gpg.d/ngrok.asc > /dev/null && "
        'echo "deb https://ngrok-agent.s3.amazonaws.com buster main" '
        "| sudo tee /etc/apt/sources.list.d/ngrok.list > /dev/null && "
        "sudo apt-get update -q"
    ),
}


def linux_manager_available(manager: str) -> bool:
    return shutil.which(manager) is not None


def _is_apt(manager: str) -> bool:
    return manager in ("apt", "apt-get")


def setup_linux_repo(
    repo_key: str,
    manager: str,
    *,
    dry_run: bool,
    timeout_s: float = 120.0,
) -> tuple[int, str, str]:
    """Run the apt repo-setup script for *repo_key* if on an apt-based system."""
    if not _is_apt(manager):
        return 0, "", ""  # non-apt: skip repo setup, attempt install directly

    script = _APT_REPO_SETUP.get(repo_key)
    if not script:
        return 0, "", f"No repo setup defined for key {repo_key!r} — skipping"

    if dry_run:
        return 0, "", ""

    try:
        proc = subprocess.run(
            ["bash", "-c", script],
            capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout_s,
        )
        return proc.returncode, proc.stdout or "", proc.stderr or ""
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, "", f"{type(exc).__name__}: {exc}"


def _build_install_argv(manager: str, pkg_id: str) -> list[str]:
    if manager in ("apt", "apt-get"):
        return ["sudo", manager, "install", "-y", pkg_id]
    if manager == "dnf":
        return ["sudo", "dnf", "install", "-y", pkg_id]
    if manager == "pacman":
        return ["sudo", "pacman", "-Sy", "--noconfirm", pkg_id]
    if manager == "zypper":
        return ["sudo", "zypper", "--non-interactive", "install", pkg_id]
    raise ValueError(f"Unsupported package manager: {manager!r}")


def run_linux_install(
    manager: str,
    pkg_id: str,
    *,
    dry_run: bool,
    timeout_s: float = 3600.0,
) -> tuple[int, str, str]:
    if dry_run:
        return 0, "", ""
    argv = _build_install_argv(manager, pkg_id)
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


def ensure_linux_package(
    ctx: InstallContext,
    manifest: Manifest,
    console: Console,
    *,
    tool: str,
    layer: str,
    pkg_id: str,
    manager: str,
    detect: Callable[[], bool],
    repo_key: str | None = None,
    version_hint: str | None = None,
) -> bool:
    """Install pkg_id via the given Linux package manager unless already present.

    If *repo_key* is set and the manager is apt/apt-get, the corresponding
    third-party repository is configured before the install is attempted.
    Returns True if the tool ended up installed or was already present.
    """
    if detect():
        manifest.record_tool(
            tool=tool, layer=layer, status="skipped",
            install_method=manager, version=version_hint,
            notes="Already present on PATH or detector.",
        )
        console.print(f"  [skipped] {tool} — already installed")
        return True

    if ctx.dry_run:
        argv_str = " ".join(_build_install_argv(manager, pkg_id))
        manifest.record_tool(
            tool=tool, layer=layer, status="planned",
            install_method=manager, version=version_hint,
            notes=f"Would run: {argv_str}",
        )
        console.print(f"  [planned] {tool} — dry-run")
        return True

    if not linux_manager_available(manager):
        manifest.record_tool(
            tool=tool, layer=layer, status="failed",
            install_method=manager,
            notes=f"{manager} not found on PATH.",
        )
        console.print(f"  [failed] {tool} — {manager} not available")
        return False

    if repo_key:
        console.print(f"  [repo-setup] {repo_key} apt repository…")
        r_code, _, r_err = setup_linux_repo(repo_key, manager, dry_run=False)
        if r_code != 0:
            console.print(f"  [warn] repo setup for {repo_key} exited {r_code} — continuing anyway")
            if r_err:
                console.print(f"         {r_err.strip()[-300:]}")

    console.print(f"  [installing] {tool} via {manager}…")
    code, out, err = run_linux_install(manager, pkg_id, dry_run=False)
    combined = (out + "\n" + err).strip()

    if code == 0:
        manifest.record_tool(
            tool=tool, layer=layer, status="installed",
            install_method=manager, version=version_hint,
            notes=combined[-2000:] if combined else None,
        )
        console.print(f"  [done] {tool}")
        return True

    manifest.record_tool(
        tool=tool, layer=layer, status="failed",
        install_method=manager,
        notes=f"exit {code}: {combined[-2000:]}",
    )
    console.print(f"  [failed] {tool} (exit {code})")
    return False
