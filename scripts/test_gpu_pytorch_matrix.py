#!/usr/bin/env python3
"""
GPU + PyTorch path selection test matrix - 50 hardware scenarios.

Mocks nvidia-smi and Win32_VideoController so no real hardware is required.
Exercises the actual detect_gpu_for_pytorch() logic from scripts/gpu_detect.py
across 50 representative GPU/driver configurations.

Useful for:
  - Verifying PyTorch wheel selection logic is correct after gpu_detect.py changes
  - Generating a review log for LLM or human audit
  - Regression testing new CUDA wheel table entries

Run:
    python scripts/test_gpu_pytorch_matrix.py              # plain text (default)
    python scripts/test_gpu_pytorch_matrix.py --markdown   # Markdown table for LLM review
    python scripts/test_gpu_pytorch_matrix.py --json       # JSON array for tooling

Exit code: 0 if all expected paths match actual; 1 if any mismatches.
"""

from __future__ import annotations

import argparse
import json
import sys
from contextlib import ExitStack
from dataclasses import dataclass, field
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts.gpu_detect import VideoAdapter, detect_gpu_for_pytorch  # noqa: E402


# ---------------------------------------------------------------------------
# Scenario definitions
# ---------------------------------------------------------------------------

@dataclass
class Scenario:
    """One simulated GPU environment."""
    name: str
    # What Win32_VideoController / WMI reports (vendor key, see _make_adapters).
    wmi_vendor: str
    # What nvidia-smi reports. None = nvidia-smi absent/failed.
    cuda_version: tuple[int, int] | None
    # True = mock returns a discrete GPU adapter; False = iGPU or software adapter.
    # For wmi_vendor="nvidia" + use_discrete=False, WMI shows only an Intel iGPU
    # (Optimus), but nvidia-smi may still succeed independently.
    use_discrete: bool
    # Expected torch_path_kind: "nvidia_cuda" | "amd_directml" | "cpu"
    expected_path: str
    # Simulate nvidia-smi on PATH but returning a non-zero error code.
    broken_smi: bool = False
    # Free-text notes for the log / LLM review.
    notes: str = ""


SCENARIOS: list[Scenario] = [
    # ── NVIDIA current generation ──────────────────────────────────────────
    Scenario("NVIDIA RTX 4090, CUDA 12.8",
             "nvidia", (12, 8), True, "nvidia_cuda"),
    Scenario("NVIDIA RTX 4080, CUDA 12.6",
             "nvidia", (12, 6), True, "nvidia_cuda"),
    Scenario("NVIDIA RTX 4070, CUDA 12.4",
             "nvidia", (12, 4), True, "nvidia_cuda"),
    Scenario("NVIDIA RTX 4060, CUDA 12.1",
             "nvidia", (12, 1), True, "nvidia_cuda"),
    # ── NVIDIA previous generation ─────────────────────────────────────────
    Scenario("NVIDIA RTX 3090, CUDA 11.8",
             "nvidia", (11, 8), True, "nvidia_cuda"),
    Scenario("NVIDIA RTX 3080, CUDA 12.0",
             "nvidia", (12, 0), True, "nvidia_cuda",
             notes="12.0 is below cu121 but above cu118; expect cu118 (compat)"),
    Scenario("NVIDIA RTX 3070, CUDA 11.7",
             "nvidia", (11, 7), True, "cpu",
             notes="11.7 < cu118 minimum (11.8); expect CPU fallback"),
    Scenario("NVIDIA RTX 3060, CUDA 11.4",
             "nvidia", (11, 4), True, "cpu"),
    # ── NVIDIA older / consumer ────────────────────────────────────────────
    Scenario("NVIDIA GTX 1080 Ti, CUDA 11.1",
             "nvidia", (11, 1), True, "cpu"),
    Scenario("NVIDIA GTX 1060, CUDA 10.1 (ancient)",
             "nvidia", (10, 1), True, "cpu"),
    # ── NVIDIA edge cases ─────────────────────────────────────────────────
    Scenario("NVIDIA laptop, discrete primary in WMI",
             "nvidia", (12, 6), True, "nvidia_cuda"),
    Scenario("NVIDIA Optimus: WMI shows Intel iGPU, nvidia-smi still works",
             "intel",  (12, 4), False, "nvidia_cuda",
             notes="smi dominates over WMI vendor for CUDA path selection"),
    Scenario("NVIDIA present in WMI, nvidia-smi absent from PATH",
             "nvidia",  None,  True, "cpu",
             notes="WMI detects NVIDIA but smi not available; warns + CPU"),
    Scenario("NVIDIA Quadro, CUDA 11.8",
             "nvidia", (11, 8), True, "nvidia_cuda"),
    Scenario("NVIDIA CUDA 12.9, above current cap (cu128)",
             "nvidia", (12, 9), True, "nvidia_cuda",
             notes="capped to cu128 with warning; newer than tracked stable"),
    Scenario("NVIDIA CUDA 9.2, below all tracked wheel lines",
             "nvidia",  (9, 2), True, "cpu"),
    Scenario("NVIDIA, nvidia-smi on PATH but returns driver error",
             "nvidia",  None,  True, "cpu",
             broken_smi=True,
             notes="smi exit non-0/non-127; two warnings expected"),
    # ── NVIDIA datacenter ─────────────────────────────────────────────────
    Scenario("NVIDIA H100 (Hopper), CUDA 12.8",
             "nvidia", (12, 8), True, "nvidia_cuda"),
    Scenario("NVIDIA Tesla V100, CUDA 11.8",
             "nvidia", (11, 8), True, "nvidia_cuda"),
    Scenario("NVIDIA Titan X Pascal, CUDA 11.4",
             "nvidia", (11, 4), True, "cpu"),
    # ── NVIDIA passthrough VM ─────────────────────────────────────────────
    Scenario("NVIDIA passthrough in Proxmox VM, CUDA 12.6",
             "nvidia", (12, 6), True, "nvidia_cuda"),
    # ── AMD discrete ──────────────────────────────────────────────────────
    Scenario("AMD RX 7900 XTX (RDNA3)",
             "amd", None, True, "amd_directml"),
    Scenario("AMD RX 6800 XT (RDNA2)",
             "amd", None, True, "amd_directml"),
    Scenario("AMD RX 5700 XT (RDNA1)",
             "amd", None, True, "amd_directml"),
    Scenario("AMD RX 580 (Polaris)",
             "amd", None, True, "amd_directml"),
    Scenario("AMD Vega 64",
             "amd", None, True, "amd_directml"),
    Scenario("AMD Instinct MI300X (datacenter)",
             "amd", None, True, "amd_directml"),
    Scenario("AMD RX 7600S laptop (discrete)",
             "amd", None, True, "amd_directml"),
    Scenario("AMD passthrough in Hyper-V VM",
             "amd", None, True, "amd_directml"),
    Scenario("AMD R9 390X (old GCN)",
             "amd", None, True, "amd_directml"),
    # ── AMD integrated ────────────────────────────────────────────────────
    Scenario("AMD Ryzen iGPU only (Radeon 780M, VEN_1002)",
             "amd", None, False, "amd_directml",
             notes="Ryzen iGPU has VEN_1002; dominant_discrete_vendor returns amd; DirectML installs"),
    # ── Intel discrete ────────────────────────────────────────────────────
    Scenario("Intel Arc A770 (discrete, VEN_8086)",
             "intel", None, True, "cpu",
             notes="Intel GPU: no DirectML path in gpu_detect; CPU fallback with warning"),
    # ── Intel integrated ──────────────────────────────────────────────────
    Scenario("Intel UHD 770 (integrated only)",
             "intel", None, False, "cpu"),
    Scenario("Intel Iris Xe (laptop integrated)",
             "intel", None, False, "cpu"),
    Scenario("Intel HD 4000 (very old integrated)",
             "intel", None, False, "cpu"),
    # ── Intel passthrough ─────────────────────────────────────────────────
    Scenario("Intel passthrough in KVM",
             "intel", None, True, "cpu"),
    # ── Mixed GPU configs ─────────────────────────────────────────────────
    Scenario("NVIDIA + Intel laptop, NVIDIA primary in WMI",
             "nvidia", (12, 6), True, "nvidia_cuda"),
    Scenario("AMD + Intel laptop, AMD discrete primary in WMI",
             "amd", None, True, "amd_directml"),
    # ── VM / software renderers ───────────────────────────────────────────
    Scenario("Microsoft Basic Display Adapter (Hyper-V guest, ROOT\\BasicDisplay)",
             "microsoft", None, False, "cpu"),
    Scenario("Microsoft Basic Display Adapter (VMware guest)",
             "microsoft", None, False, "cpu"),
    Scenario("Microsoft Basic Display Adapter (VirtualBox guest)",
             "microsoft", None, False, "cpu"),
    Scenario("VMware SVGA 3D (VEN_15AD)",
             "vmware", None, False, "cpu"),
    Scenario("VirtualBox Graphics Adapter (VEN_80EE)",
             "virtualbox", None, False, "cpu"),
    Scenario("Hyper-V Video Adapter (VEN_1414 = microsoft)",
             "hyperv", None, False, "cpu",
             notes="VEN_1414 maps to 'microsoft' vendor; falls to intel|microsoft CPU branch"),
    # ── Headless / no GPU ─────────────────────────────────────────────────
    Scenario("No GPU detected (headless server, empty adapter list)",
             "unknown", None, False, "cpu"),
    # ── CUDA cap boundary ─────────────────────────────────────────────────
    Scenario("NVIDIA CUDA 12.8 (exactly at cap, no capping warning)",
             "nvidia", (12, 8), True, "nvidia_cuda"),
    Scenario("NVIDIA CUDA 13.0 (above cap, capped to cu128 with warning)",
             "nvidia", (13, 0), True, "nvidia_cuda"),
    # ── Multi-GPU rigs ────────────────────────────────────────────────────
    Scenario("NVIDIA + AMD dual-GPU (NVIDIA dominant, NVIDIA in WMI mock)",
             "nvidia", (12, 6), True, "nvidia_cuda"),
    Scenario("NVIDIA RTX 4060 Laptop + Intel iGPU (NVIDIA in WMI mock)",
             "nvidia", (12, 6), True, "nvidia_cuda"),
    Scenario("AMD discrete + Radeon iGPU (AMD dominant in WMI mock)",
             "amd", None, True, "amd_directml"),
    # ── AMD + Intel laptop ────────────────────────────────────────────────
    Scenario("AMD + Intel laptop (AMD discrete + Intel iGPU, AMD primary)",
             "amd", None, True, "amd_directml"),
]

assert len(SCENARIOS) == 51, f"Expected 51 scenarios, got {len(SCENARIOS)}"


# ---------------------------------------------------------------------------
# Mock helpers - return types match actual gpu_detect.py API exactly
# ---------------------------------------------------------------------------

_VENDOR_ADAPTER: dict[tuple[str, bool], tuple[str, str]] = {
    # (wmi_vendor, use_discrete): (adapter_name, pnp_device_id)
    ("nvidia",      True):  ("NVIDIA GeForce RTX 4090",        "PCI\\VEN_10DE&DEV_2684"),
    ("nvidia",      False): ("Intel UHD Graphics",              "PCI\\VEN_8086&DEV_A780"),  # Optimus
    ("amd",         True):  ("AMD Radeon RX 7900 XTX",          "PCI\\VEN_1002&DEV_744C"),
    ("amd",         False): ("AMD Radeon Graphics",             "PCI\\VEN_1002&DEV_15BF"),  # Ryzen iGPU
    ("intel",       True):  ("Intel Arc A770",                  "PCI\\VEN_8086&DEV_56A0"),
    ("intel",       False): ("Intel UHD Graphics 770",          "PCI\\VEN_8086&DEV_A780"),
    ("microsoft",   False): ("Microsoft Basic Display Adapter", "ROOT\\BasicDisplay\\0000"),
    ("vmware",      False): ("VMware SVGA 3D",                  "PCI\\VEN_15AD&DEV_0405"),
    ("virtualbox",  False): ("VirtualBox Graphics Adapter",     "PCI\\VEN_80EE&DEV_BEEF"),
    ("hyperv",      False): ("Microsoft Hyper-V Video",         "PCI\\VEN_1414&DEV_5353"),
}


def _make_adapters(wmi_vendor: str, use_discrete: bool) -> tuple[list[VideoAdapter], list[str]]:
    """Return (adapters, warnings) matching list_video_adapters_windows() signature."""
    if wmi_vendor == "unknown":
        return [], []
    key = (wmi_vendor, use_discrete)
    if key not in _VENDOR_ADAPTER:
        # Fallback for vendors that don't have a discrete variant defined
        key = (wmi_vendor, False)
    if key not in _VENDOR_ADAPTER:
        return [], [f"No mock adapter defined for vendor={wmi_vendor}"]
    name, pnp = _VENDOR_ADAPTER[key]
    return [VideoAdapter(name=name, driver_version="560.94", pnp_device_id=pnp)], []


def _make_smi(
    cuda_version: tuple[int, int] | None,
    broken: bool = False,
) -> tuple[int, str, str]:
    """Return (returncode, stdout, stderr) matching run_nvidia_smi() signature."""
    if broken:
        return 6, "", "NVML: Driver/library version mismatch"
    if cuda_version is None:
        return 127, "", "nvidia-smi not found on PATH"
    stdout = (
        "+-----------------------------------------------------------------------------+\n"
        f"| NVIDIA-SMI 560.94   Driver Version: 560.94   "
        f"CUDA Version: {cuda_version[0]}.{cuda_version[1]}   |\n"
        "+-----------------------------------------------------------------------------+\n"
    )
    return 0, stdout, ""


# ---------------------------------------------------------------------------
# Scenario runner
# ---------------------------------------------------------------------------

def run_scenario(s: Scenario) -> dict:
    """Run detect_gpu_for_pytorch() with all system calls mocked."""
    adapters_result = _make_adapters(s.wmi_vendor, s.use_discrete)
    smi_result = _make_smi(s.cuda_version, broken=s.broken_smi)

    patches = [
        patch("scripts.gpu_detect.platform.system", return_value="Windows"),
        patch("scripts.gpu_detect.list_video_adapters_windows", return_value=adapters_result),
        patch("scripts.gpu_detect.run_nvidia_smi", return_value=smi_result),
    ]
    if s.broken_smi:
        # Make _which("nvidia-smi") return a Path so the "non-zero exit" warning fires.
        patches.append(
            patch("scripts.gpu_detect._which", return_value=Path("/usr/local/bin/nvidia-smi"))
        )

    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        report = detect_gpu_for_pytorch()

    actual = report.torch_path_kind
    return {
        "actual_path":   actual,
        "expected_path": s.expected_path,
        "match":         actual == s.expected_path,
        "cuda_tag":      report.pytorch_cuda_wheel_tag,
        "driver_cuda":   (
            f"{report.nvidia_driver_cuda[0]}.{report.nvidia_driver_cuda[1]}"
            if report.nvidia_driver_cuda else None
        ),
        "discrete_vendor": report.discrete_vendor,
        "nvidia_smi_ok":   report.nvidia_smi_ok,
        "index_url":       report.pytorch_index_url,
        "warnings":        report.warnings,
        "human_summary":   report.human_summary,
        "scenario_notes":  s.notes,
    }


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------

def _shorten(warnings: list[str], max_chars: int = 80) -> str:
    if not warnings:
        return "-"
    first = warnings[0]
    truncated = first[:max_chars] + "..." if len(first) > max_chars else first
    suffix = f" (+{len(warnings)-1} more)" if len(warnings) > 1 else ""
    return truncated + suffix


def print_plain(rows: list[dict], scenarios: list[Scenario]) -> None:
    for i, (s, r) in enumerate(zip(scenarios, rows), 1):
        ok = "PASS" if r["match"] else "FAIL MISMATCH"
        print(f"\n[{i:02d}] {s.name}")
        print(f"     {ok}  path={r['actual_path']}  expected={r['expected_path']}")
        print(f"     vendor={r['discrete_vendor']}  cuda_tag={r['cuda_tag'] or '-'}  "
              f"driver_cuda={r['driver_cuda'] or '-'}  smi_ok={r['nvidia_smi_ok']}")
        print(f"     index={r['index_url']}")
        for w in r["warnings"]:
            print(f"     WARN  {w}")
        if s.notes:
            print(f"     note: {s.notes}")


def print_markdown(rows: list[dict], scenarios: list[Scenario]) -> None:
    cols = ["#", "Scenario", "Expected", "Actual", "Match", "CUDA Tag", "1st Warning"]
    print("| " + " | ".join(cols) + " |")
    print("| " + " | ".join(["---"] * len(cols)) + " |")
    for i, (s, r) in enumerate(zip(scenarios, rows), 1):
        row = [
            str(i),
            s.name,
            r["expected_path"],
            r["actual_path"],
            "PASS" if r["match"] else "**FAIL**",
            r["cuda_tag"] or "-",
            _shorten(r["warnings"]),
        ]
        print("| " + " | ".join(row) + " |")


def print_json(rows: list[dict], scenarios: list[Scenario]) -> None:
    out = []
    for i, (s, r) in enumerate(zip(scenarios, rows), 1):
        out.append({"n": i, "scenario": s.name, **r})
    json.dump(out, sys.stdout, indent=2)
    sys.stdout.write("\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--markdown", action="store_true", help="Output as Markdown table")
    parser.add_argument("--json",     action="store_true", help="Output as JSON array")
    args = parser.parse_args()

    rows: list[dict] = []
    errors: list[tuple[int, str, str]] = []

    for i, s in enumerate(SCENARIOS, 1):
        try:
            rows.append(run_scenario(s))
        except Exception as exc:
            rows.append({
                "actual_path": "ERROR", "expected_path": s.expected_path,
                "match": False, "cuda_tag": None, "driver_cuda": None,
                "discrete_vendor": s.wmi_vendor, "nvidia_smi_ok": False,
                "index_url": "", "warnings": [str(exc)],
                "human_summary": f"EXCEPTION: {exc}", "scenario_notes": s.notes,
            })
            errors.append((i, s.name, str(exc)))

    if args.json:
        print_json(rows, SCENARIOS)
    elif args.markdown:
        print_markdown(rows, SCENARIOS)
    else:
        print_plain(rows, SCENARIOS)

    mismatches = [(i + 1, SCENARIOS[i].name, r) for i, r in enumerate(rows) if not r["match"]]

    # Summary footer
    total = len(SCENARIOS)
    n_pass = sum(1 for r in rows if r["match"])
    n_fail = total - n_pass

    if not args.json:
        print(f"\n{'='*70}")
        print(f"Results: {n_pass}/{total} matched expected path  "
              f"({'PASS' if n_fail == 0 else f'FAIL - {n_fail} mismatch(es)'})")
        if mismatches:
            print("\nMismatches:")
            for n, name, r in mismatches:
                print(f"  [{n:02d}] {name}")
                print(f"       expected={r['expected_path']}  actual={r['actual_path']}")
        if errors:
            print("\nExceptions:")
            for n, name, err in errors:
                print(f"  [{n:02d}] {name}: {err}")

    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
