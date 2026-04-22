# Release testing (Phase 4)

Use this checklist on **throwaway Windows VMs** before tagging a release. AM-DevKit changes system configuration, Winget state, and optionally CTT WinUtil tweaks — never use a production daily driver as the first validation target.

## Environment

- [ ] Fresh Windows 11 (or target SKU) VM, current patches, local admin
- [ ] Repo cloned to a short path (for example `C:\src\Absentminds-DevKit-Windows`) from [github.com/Absentmind86/Absentminds-DevKit-Windows](https://github.com/Absentmind86/Absentminds-DevKit-Windows)
- [ ] Python 3.11+ available (or run `bootstrap/install.ps1` per README)

## Smoke — non-destructive

From repo root:

- [ ] `python core/system_scan.py --output system-profile.json` completes and produces valid JSON
- [ ] `python scripts/gpu_detect.py` runs (note: VM may be CPU-only; expect CPU branch)
- [ ] `python -m core.installer --dry-run --profile systems --skip-summary` exits 0, writes manifest, HTML report, path fingerprint
- [ ] `python -m core.installer --dry-run --reuse-system-profile system-profile.json --profile systems --skip-summary` exits 0 when the JSON exists
- [ ] `python -m core.gui` opens; Summary updates after **Run system scan**; **Run installer (new console)** starts a second console without Python tracebacks

## Smoke — destructive (VM only)

- [ ] `python -m core.installer --profile systems --yes --skip-summary` (non-dry) completes without uncaught abort; review `post-install-report.html` PATH banner
- [ ] With `--profile extras` (and Obsidian not excluded): verify `Documents\AM-DevKit-Vault` and finalize manifest rows
- [ ] **Sanitation:** only after explicit approval, test `--run-sanitation` with `--sanitation-preset minimal` on a disposable VM; confirm WinUtil receives `config/am-devkit-winutil.json`

## Regression triggers

Re-run the non-destructive smoke set after any change to:

- `core/installer.py` layer order or `InstallContext` fields
- `core/install_catalog.py` / `core/catalog_install.py` tool ids
- `core/sanitize.py` or WinUtil JSON presets
- `bootstrap/install.ps1` handoff to Python

## Sign-off

Record VM image build, Windows version, and commit SHA in the release issue or tag notes.
