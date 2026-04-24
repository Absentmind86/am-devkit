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

## SmartScreen / execution policy (per release)

Scripts are not code-signed in v0.8. Verify the two bootstrap flows behave as documented:

- [ ] **`irm | iex` path** — run `irm <raw-url>/fresh.ps1 | iex` on a clean VM (no prior zone tag). Confirm PowerShell runs the script without a SmartScreen block. *(Expected: no block — piped scripts have no Mark-of-the-Web tag.)*
- [ ] **Clone-then-run path** — `git clone` the repo via CLI, then `.\bootstrap\install.ps1 -Gui`. Confirm no execution policy error. *(Expected: no block — git does not attach a zone tag.)*
- [ ] **Browser download path** — download `fresh.ps1` directly from the GitHub UI (or via `Invoke-WebRequest` to a file), then try to run it. Confirm PowerShell refuses (zone-blocked). Then run `Unblock-File .\fresh.ps1` and confirm it runs. *(Expected: blocked before unblock, succeeds after.)*

If any of these fail unexpectedly, update the SmartScreen section in `README.md` before releasing.

## Sign-off

Record VM image build, Windows version, and commit SHA in the release issue or tag notes.
