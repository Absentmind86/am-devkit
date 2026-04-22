# Third-party notices and licensing

Absentmind's DevKit **AM-DevKit** (`LICENSE` at repo root) is licensed under the **MIT License**. Copyright notices for this project appear in `LICENSE`.

This document satisfies common expectations for attribution, describes **bundled versus runtime** dependencies, and states limitations of liability for third-party tools AM-DevKit **invokes but does not ship**.

---

## Disclaimer

AM-DevKit is **not** affiliated with Microsoft, Chris Titus Tech / CT Tech Group LLC, Chris Titus Tech contributors, Flutter/Flet/Appveyor Systems Inc., or any application publisher installed via Winget or other installers. Names and trademarks belong to their owners.

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

## Windows sanitization — Chris Titus Tech WinUtil

When `--run-sanitation` / the GUI sanitation option is enabled, `core/sanitize.py` runs PowerShell that **downloads and executes** the utility hosted at **`https://christitus.com/win`** (Invoke-RestMethod / `irm`), passing one of the repo’s WinUtil JSON presets as `-Config` and `-Run` (`am-devkit-winutil.json` for `--sanitation-preset minimal`, `am-devkit-winutil-standard.json` for `standard`; tweak IDs align with Chris Titus Tech [`preset.json`](https://github.com/ChrisTitusTech/winutil/blob/main/config/preset.json) Minimal / Standard lists).

- **WinUtil** upstream is maintained at [ChrisTitusTech/winutil](https://github.com/ChrisTitusTech/winutil).
- Its license is **MIT** (“Copyright (c) 2022 CT Tech Group LLC”). Full text:  
  https://github.com/ChrisTitusTech/winutil/blob/main/LICENSE  

AM-DevKit **does not embed** WinUtil source in this repository. Execution pulls the live script **over the network**; behavior may change when upstream updates. The JSON preset in `config/am-devkit-winutil.json` uses **`WPFTweaks`** tweak identifiers aligned with WinUtil’s automation format; tweak definitions are authored by the WinUtil project.

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
| WinUtil script | No (download at runtime) | MIT (CT Tech Group LLC) |
| Winget packages | No | Per-package + Microsoft |
| PowerShell bootstrap | Yes (MIT project) | Same as repo |

Update this file when adding **direct** Python dependencies to `requirements.txt` or materially changing integration with external tools.
