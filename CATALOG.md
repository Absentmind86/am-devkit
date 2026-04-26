# AM-DevKit — Full Install Catalog

Everything this devkit can install, organized by profile and layer.
Use this as a reference when deciding which profiles to select.

For install instructions see [README.md](README.md).
For the full changelog see [CHANGELOG.md](CHANGELOG.md).

---

## Profiles

| Profile | Flag | What it's for |
|---|---|---|
| `ai-ml` | `--profile ai-ml` | Machine learning, local LLMs, GPU/PyTorch stack |
| `extras` | `--profile extras` | Optional personal productivity apps |
| `game-dev` | `--profile game-dev` | Unity, Godot, game tooling |
| `hardware-robotics` | `--profile hardware-robotics` | Arduino, embedded, serial, network analysis |
| `systems` | `--profile systems` | Low-level systems, networking, DevOps, cloud |
| `web-fullstack` | `--profile web-fullstack` | Web development, databases, cloud CLIs, containers |

Profiles can be combined. `--absentmind` selects all core profiles (everything except Extras).

---

## Core — Installed with Every Profile

### Bootstrap (runs before everything else)

| Tool | How | Description |
|---|---|---|
| Git | winget | Version control |
| Git LFS | winget | Large file storage extension for Git |
| OpenSSH Client | Windows feature | SSH client (`ssh.exe`) |
| Scoop | irm installer | User-scope Windows package manager |
| Python 3.12 | winget | Python runtime (required by the installer itself) |

### Infrastructure

| Tool | How | Description |
|---|---|---|
| GitHub CLI (`gh`) | winget | Create PRs, manage issues, clone repos from the terminal |
| Windows Terminal | winget | Modern tabbed terminal with profiles |
| PowerShell 7 | winget | Cross-platform PowerShell (runs alongside Windows PS 5.1) |
| Oh My Posh | winget | Prompt theme engine for any shell |
| Tailscale | winget | Mesh VPN — connect machines across networks |
| `bat` | scoop | `cat` with syntax highlighting |
| `ripgrep` (`rg`) | scoop | Fast regex file search |
| `fd` | scoop | User-friendly `find` alternative |
| `fzf` | scoop | Fuzzy finder — pipe anything into interactive search |
| `jq` | scoop | JSON processor and query tool |
| `lazygit` | scoop | Terminal UI for Git |
| `delta` | scoop | Side-by-side Git diff viewer |

### Editors

| Tool | How | Description |
|---|---|---|
| VS Code | winget | Visual Studio Code |
| Cursor | winget | AI-enhanced fork of VS Code |
| JetBrains Toolbox | winget | Launcher for all JetBrains IDEs |

**VS Code and Cursor extensions (20, installed into both):**

| Extension | Description |
|---|---|
| GitLens | Git blame, history, and code authorship inline |
| Prettier | Opinionated code formatter |
| ESLint | JavaScript/TypeScript linting |
| Error Lens | Inline error and warning display |
| Path Intellisense | Filename autocompletion |
| Python | Python language support |
| Pylance | Fast Python type checking |
| Ruff | Extremely fast Python linter |
| Jupyter | Jupyter notebook support |
| Auto Rename Tag | Automatically rename paired HTML/XML tags |
| CSS Peek | Jump to CSS definitions from HTML |
| REST Client | Send HTTP requests directly from `.http` files |
| Docker | Docker container management in the sidebar |
| Remote - SSH | Edit files on remote machines over SSH |
| Remote - WSL | Full VS Code experience inside WSL |
| Material Icon Theme | File icon theme |
| Material Theme | Color theme |
| CodeSnap | Beautiful code screenshots |
| TODO Highlight | Highlight TODO/FIXME comments |
| Continue | Local and cloud AI coding assistant |

### Utilities (installed with all profiles)

| Tool | How | Description |
|---|---|---|
| 7-Zip | winget | Archive utility (zip, 7z, tar, rar, …) |
| Notepad++ | winget | Lightweight advanced text editor |
| Everything | winget | Instant file search across all drives |
| DevToys | winget | Offline developer utilities (JSON, Base64, diff, UUID, …) |
| WinMerge | winget | File and folder diff / merge tool |

---

## Profile: `ai-ml`

| Tool | How | Description |
|---|---|---|
| Ollama | winget | Run LLMs locally (Llama, Mistral, Gemma, Phi, …) |
| DBeaver Community | winget | Universal database client |
| Bruno | winget | Offline API client (Postman alternative) |
| Docker Desktop | winget | Container platform (required for many ML workflows) |
| kubectl | winget | Kubernetes CLI |
| Helm | winget | Kubernetes package manager |
| PostgreSQL 17 | winget | Relational database |
| Redis | winget | In-memory data store / cache |
| mkcert | winget | Generate trusted local HTTPS certificates |
| ngrok | winget | Expose local servers to the internet |
| AWS CLI | winget | Amazon Web Services command-line tools |
| Google Cloud SDK | winget | Google Cloud command-line tools |
| Azure CLI | winget | Microsoft Azure command-line tools |
| Podman Desktop | winget | Daemonless container engine (Docker alternative) |
| Go | winget | Go programming language |

**Opt-in pip packages (pass `--install-ml-base`):**

| Package | Description |
|---|---|
| numpy | Numerical computing |
| pandas | Data analysis and manipulation |
| matplotlib | Plotting and visualization |
| scikit-learn | Machine learning algorithms |
| jupyter | Notebook environment |
| ipython | Enhanced interactive Python shell |

**Opt-in PyTorch (pass `--install-ml-wheels`):**

| Variant | When | Packages |
|---|---|---|
| AMD GPU (DirectML) | AMD Radeon/RX GPU detected | `torch-directml` |
| NVIDIA GPU (CUDA) | NVIDIA GPU detected | `torch` `torchvision` `torchaudio` (CUDA index) |
| CPU-only | No discrete GPU | `torch` `torchvision` `torchaudio` (CPU index) |

---

## Profile: `web-fullstack`

| Tool | How | Description |
|---|---|---|
| NVM for Windows | winget | Node.js version manager |
| Go | winget | Go programming language |
| Temurin JDK 21 | winget | Eclipse Adoptium Java 21 LTS |
| .NET SDK 8 | winget | Microsoft .NET 8 SDK |
| DBeaver Community | winget | Universal database client |
| Bruno | winget | Offline API client (Postman alternative) |
| Docker Desktop | winget | Container platform |
| kubectl | winget | Kubernetes CLI |
| Helm | winget | Kubernetes package manager |
| PostgreSQL 17 | winget | Relational database |
| Redis | winget | In-memory data store / cache |
| mkcert | winget | Generate trusted local HTTPS certificates |
| ngrok | winget | Expose local servers to the internet |
| AWS CLI | winget | Amazon Web Services command-line tools |
| Google Cloud SDK | winget | Google Cloud command-line tools |
| Azure CLI | winget | Microsoft Azure command-line tools |
| Podman Desktop | winget | Daemonless container engine |

---

## Profile: `systems`

| Tool | How | Description |
|---|---|---|
| Go | winget | Go programming language |
| Temurin JDK 21 | winget | Eclipse Adoptium Java 21 LTS |
| .NET SDK 8 | winget | Microsoft .NET 8 SDK |
| CMake | winget | Cross-platform C/C++ build system |
| Ninja | winget | Fast build system (CMake backend) |
| Sysinternals Suite | winget | Deep Windows system utilities (Process Explorer, Autoruns, …) |
| Wireshark | winget | Network packet capture and analysis |
| Nmap | winget | Network scanner and security auditing |
| Docker Desktop | winget | Container platform |
| kubectl | winget | Kubernetes CLI |
| Helm | winget | Kubernetes package manager |
| AWS CLI | winget | Amazon Web Services command-line tools |
| Google Cloud SDK | winget | Google Cloud command-line tools |
| Azure CLI | winget | Microsoft Azure command-line tools |
| Podman Desktop | winget | Daemonless container engine |

---

## Profile: `game-dev`

| Tool | How | Description |
|---|---|---|
| Temurin JDK 21 | winget | Eclipse Adoptium Java 21 LTS |
| .NET SDK 8 | winget | Microsoft .NET 8 SDK |
| CMake | winget | Cross-platform C/C++ build system |
| Ninja | winget | Fast build system (CMake backend) |
| Unity Hub | winget | Unity Editor version manager and launcher |
| Godot Engine | winget | Open-source 2D/3D game engine |
| Wireshark | winget | Network packet capture and analysis |

---

## Profile: `hardware-robotics`

| Tool | How | Description |
|---|---|---|
| CMake | winget | Cross-platform C/C++ build system |
| Ninja | winget | Fast build system (CMake backend) |
| Sysinternals Suite | winget | Deep Windows system utilities |
| Wireshark | winget | Network packet capture and analysis |
| Nmap | winget | Network scanner and security auditing |
| Arduino IDE | winget | Arduino microcontroller development environment |
| PuTTY | winget | SSH and serial terminal client |

---

## Profile: `extras` (opt-in personal apps)

Pass `--profile extras` to include these. Not selected by `--absentmind`.

| Tool | How | Description |
|---|---|---|
| Microsoft PowerToys | winget | Power-user utilities: FancyZones, PowerRename, Color Picker, Run, … |
| Obsidian | winget | Markdown knowledge base with graph view and backlinks |
| OBS Studio | winget | Screen recording and live streaming |
| ShareX | winget | Screenshot, screen recording, and file sharing |
| HWiNFO | winget | Detailed hardware sensors and system information |
| WizTree | winget | Visual disk space analyzer |
| VLC | winget | Universal media player |
| Bitwarden | winget | Open-source password manager |
| KeePassXC | winget | Offline password manager |
| Fork | winget | Git GUI client |
| AutoHotkey | winget | Windows automation and macro scripting |
| Discord | winget | Voice, video, and text chat |
| FFmpeg | winget | Command-line media encoding and conversion |

---

## Optional: WSL (Windows Subsystem for Linux)

Pass `--enable-wsl` to enable. Requires a reboot on first enable.

| Item | How | Description |
|---|---|---|
| WSL feature | DISM | Enables Microsoft-Windows-Subsystem-Linux + VirtualMachinePlatform |
| Linux distro | `wsl --install` | Default: none. Pass `--wsl-default-distro Ubuntu` (or any distro name) |

---

## Optional: Windows Sanitization

Pass `--run-sanitation` to apply. Choose `--sanitation-preset Minimal` or `Standard`.
All changes are reversible via `scripts/sanitize-restore.ps1`.

### Minimal preset (4 tweaks)

| Tweak | What it does |
|---|---|
| Disable Telemetry | Turns off advertising ID, tailored experiences, speech privacy, input personalization, feedback prompts, and Defender sample submission. Disables DiagTrack and dmwappushservice services. |
| Disable Consumer Features | Blocks Windows from installing suggested / sponsored apps via cloud content policy. |
| Service Cleanup | Sets SvcHost split threshold to match installed RAM. Sets MapsBroker to Manual, disables SharedAccess and CscService. |
| Disable WPBT | Prevents OEM firmware from injecting executables into Windows startup via the Wake Platform Binary Table. |

### Standard preset (Minimal + 9 more)

| Tweak | What it does |
|---|---|
| Disable Activity History | Turns off activity feed, user activity publishing and uploading via policy. |
| Disable Explorer Auto-Discovery | Clears the folder type cache (Bags/BagMRU) so Explorer stops switching folder templates unexpectedly. |
| Disable Game DVR | Disables background Game Bar capture and AppCapture. |
| Disable Location Services | Disables lfsvc service, sets location access to Deny, clears sensor permission. |
| Delete Temporary Files | Clears `%TEMP%` and `C:\Windows\Temp`. |
| DISM Component Cleanup | Runs `DISM /Cleanup-Image /StartComponentCleanup` to reclaim WinSxS disk space (takes 2–5 min). |
| Enable End Task on Taskbar | Adds "End Task" to the taskbar right-click context menu. |
| Create System Restore Point | Creates a restore point labelled "AM-DevKit sanitization checkpoint" before changes. |
| Disable PowerShell 7 Telemetry | Sets `POWERSHELL_TELEMETRY_OPTOUT=1` machine-wide. |

---

## Language Runtimes (all profiles)

| Tool | How | Notes |
|---|---|---|
| Python 3.12 | winget | Installed if not already present |
| pyenv-win | scoop | Python version manager |
| Rust (rustup stable) | rustup-init.exe | Skippable via `--skip-rust`. Installed when systems / game-dev / hardware-robotics / ai-ml profile is active. |
| uv | winget | Fast Python package/project manager (all profiles) |

---

## What Gets Generated (not installed, but created)

| Output | Location | Description |
|---|---|---|
| `devkit-manifest.json` | repo root | Full record of every tool: status, version, method, timestamp |
| `post-install-report.html` | repo root | Visual report with PATH audit, install summary, and launchpad links |
| `path-fingerprint.json` | repo root | SHA256 fingerprint of your PATH for conflict tracking |
| `scripts/restore-winget-from-manifest.ps1` | repo root | Generated script to reinstall everything on a new machine |
| `am-devkit-out/sandbox/` | repo root | Windows Sandbox and Dev Container config templates |
| `Documents/AM-DevKit-Vault/` | user home | Starter Obsidian vault (extras profile only) |
| Dotfiles seed | user home | `.gitconfig`, `.bashrc`, PowerShell profile — skipped if files already exist |
