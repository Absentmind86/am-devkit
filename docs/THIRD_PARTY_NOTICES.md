# Third-party notices and licensing

Absentmind's DevKit **AM-DevKit** (`LICENSE` at repo root) is licensed under the **MIT License**. Copyright notices for this project appear in `LICENSE`.

This document satisfies common expectations for attribution, describes **bundled versus runtime** dependencies, and states limitations of liability for third-party tools AM-DevKit **invokes but does not ship**.

---

## Disclaimer

AM-DevKit is **not** affiliated with Microsoft, Flutter/Flet/Appveyor Systems Inc., or any application publisher installed via Winget or other installers. Names and trademarks belong to their owners.

Use third-party installers and OS tweaks **at your own risk**. Review each vendor’s license before use on production systems. AM-DevKit authors provide the orchestration scripts **without warranty**, as stated in `LICENSE`.

---

## Python packages (installed via pip from `requirements.txt`)

These libraries are **not** vendored inside this repository; users install them from PyPI. SPDX-style identifiers are given for clarity.

| Package | License | Notes |
|--------|---------|--------|
| **rich** | MIT | Terminal rendering — [Textualize/rich](https://github.com/Textualize/rich) |
| **flet** | Apache-2.0 | Phase 3 GUI — [flet-dev/flet](https://github.com/flet-dev/flet) |

Transitive dependencies (e.g. **httpx**, **pygments**) are governed by their respective PyPI declarations. Run `pip show <package>` or inspect your environment’s `site-packages` metadata for full texts.

Apache-2.0 obligations for **distribution** of binaries that embed Flet typically include retaining notices; if you ship a packaged app built with Flet, retain Flet’s `NOTICE`/license files per Flet’s packaging guidance.

---

## Windows sanitization

When `--run-sanitation` / the GUI sanitation option is enabled, `core/sanitize.py`
runs `scripts/sanitize.ps1` — a **bundled PowerShell script** that applies registry
and service tweaks directly. **No external download occurs.** No third-party tool is
invoked.

**Tweak selection attribution:** The specific registry keys, services, and settings
targeted by AM-DevKit’s sanitization presets were researched and selected by
referencing [ChrisTitusTech/winutil](https://github.com/ChrisTitusTech/winutil)
(MIT license, © Chris Titus Tech). The tweak set was verified current as of
**April 2026**. WinUtil’s `WPFTweaks`-prefixed identifiers are used in
`config/am-devkit-winutil*.json` for traceability back to the source.

AM-DevKit does **not** execute any WinUtil code at runtime. The PowerShell
implementation in `scripts/sanitize.ps1` was written independently and is
covered by AM-DevKit’s own MIT license. Users who want to verify parity or
check for upstream changes can compare against the WinUtil source at the link
above.

---

## Microsoft Windows Package Manager (winget)

Installations invoked via `winget` are subject to **Microsoft’s** terms for Winget and for each package’s publisher. AM-DevKit passes `--accept-package-agreements` / `--accept-source-agreements` where applicable so installs can proceed non-interactively. **You** remain responsible for complying with each installed product’s license (Visual Studio Code, Docker Desktop, Git, etc.).

---

## Scoop, Chocolatey, pip, pyenv-win, Rustup, VS Code extensions, etc.

Optional install paths may call **Scoop**, **Chocolatey**, **pip**, **rustup-init**, Visual Studio Code extension APIs, or similar. Each has its own license and terms; AM-DevKit orchestrates commands only and does not redistribute those programs.

---

## GPU / ML stacks (PyTorch, CUDA, Ollama, …)

When selected profiles request ML tooling, installers may pull wheels from NVIDIA/PyTorch/Ollama or others. Those components are **not** part of this repo; follow NVIDIA CUDA EULA, PyTorch BSD-style license, and respective vendor terms.

---

## Summary

| Component | Shipped in repo? | Typical license / terms |
|-----------|------------------|-------------------------|
| AM-DevKit scripts | Yes | MIT (`LICENSE`) |
| **rich**, **flet** (pip) | No (PyPI) | MIT / Apache-2.0 |
| sanitize.ps1 | Yes (bundled) | MIT (same as repo) |
| Winget packages | No | Per-package + Microsoft |
| PowerShell bootstrap | Yes (MIT project) | Same as repo |

Update this file when adding **direct** Python dependencies to `requirements.txt` or materially changing integration with external tools.
