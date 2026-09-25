"""
pipeline/startup_check.py — NETRA-DR TASK-019: Model Readiness Startup Check

Verifies every expected model directory has both a valid metadata.json
and the ONNX model artifact referenced by it, before the server starts
accepting requests.

Usage (called automatically from app/app.py):
    from pipeline.startup_check import run_startup_check
    report = run_startup_check(verbose=True)

Behaviour:
- Checks all five model directories.
- For each: attempts load_contract() then resolve_model_path().
- Reports per-model status: ready | missing metadata | missing artifact.
- If any model is missing, the server STILL starts (to support partial demos
  during development), but the website will show clear "unavailable" sections
  for the affected phases — never silently skip or fabricate.
- Prints a summary table to stdout when verbose=True.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List

from pipeline.contract import (
    ModelArtifactNotFoundError,
    ModelContractError,
    load_contract,
    resolve_model_path,
)

logger = logging.getLogger(__name__)

# Model directory → (model_type, human-readable phase label)
_MODEL_REGISTRY: List[tuple] = [
    ("models/quality",       "classifier",   "Phase 1 — Quality Gate (IQA)"),
    ("models/vessel_seg",    "segmentation", "Phase 2 — Vessel Segmentation"),
    ("models/lesion_seg",    "segmentation", "Phase 2 — Lesion Segmentation (HE/EX/SE)"),
    ("models/ma_detector",   "ma_detector",  "Phase 2 — MA Detector"),
    ("models/grading",       "classifier",   "Phase 3/4 — DR Grading + Grad-CAM"),
]


def run_startup_check(verbose: bool = True) -> Dict[str, Any]:
    """
    Check all model directories for readiness.

    Args:
        verbose: If True, print a summary table to stdout.

    Returns:
        dict with keys:
            all_ready     (bool)       — True if every model is ready
            missing_count (int)        — Number of missing models
            items         (list[dict]) — Per-model status dicts:
                name    (str)  — Human-readable label
                ready   (bool) — True if artifact + metadata both present
                message (str)  — Status detail
    """
    items: List[Dict[str, Any]] = []
    missing_count = 0

    for model_dir_str, model_type, label in _MODEL_REGISTRY:
        model_dir = Path(model_dir_str)
        item: Dict[str, Any] = {"name": label, "ready": False, "message": ""}

        # 1. Check metadata.json
        try:
            contract = load_contract(model_dir, model_type)
        except FileNotFoundError:
            item["message"] = (
                f"metadata.json not found in '{model_dir}' - ONNX not yet exported from MATLAB."
            )
            items.append(item)
            missing_count += 1
            continue
        except ModelContractError as exc:
            item["message"] = f"metadata.json invalid: {exc}"
            items.append(item)
            missing_count += 1
            continue
        except Exception as exc:
            item["message"] = f"Unexpected error reading contract: {exc}"
            items.append(item)
            missing_count += 1
            continue

        # 2. Check model artifact
        try:
            model_path = resolve_model_path(model_dir, contract)
            item["ready"] = True
            item["message"] = (
                f"Ready — {contract.get('model_name', 'unknown')} v{contract.get('model_version', '?')} "
                f"({model_path})"
            )
        except ModelArtifactNotFoundError as exc:
            item["message"] = (
                f"metadata.json found but ONNX artifact missing: {exc}. "
                "Deliver the MATLAB-exported ONNX file."
            )
            missing_count += 1
        except Exception as exc:
            item["message"] = f"Unexpected error resolving artifact: {exc}"
            missing_count += 1

        items.append(item)

    report: Dict[str, Any] = {
        "all_ready": missing_count == 0,
        "missing_count": missing_count,
        "items": items,
    }

    if verbose:
        _print_startup_report(report)

    return report


def _print_startup_report(report: Dict[str, Any]) -> None:
    """Print a human-readable startup report to stdout (ASCII-safe for Windows cp1252)."""
    sep = "=" * 70
    print("\n" + sep)
    print("  NETRA-DR - Model Readiness Check")
    print(sep)
    for item in report["items"]:
        status = "[OK]  " if item["ready"] else "[MISS]"
        print(f"  {status}  {item['name']}")
        print(f"          {item['message']}")
        print()
    if report["all_ready"]:
        print("  [OK]  All models ready. NETRA-DR is fully operational.")
    else:
        print(
            f"  [WARN] {report['missing_count']} model(s) missing. "
            "Affected phases will show 'unavailable' in the web UI.\n"
            "         See models/ directories and deliver MATLAB ONNX exports."
        )
    print(sep + "\n")
