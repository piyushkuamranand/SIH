"""
pipeline/report.py — NETRA-DR Phase 4: Final Report Assembly

Single entry point for the website: runs all four pipeline phases in order and
returns one structured result dict.  The web layer (TASK-017) calls only
``run_full_pipeline(image_path)`` — it never orchestrates individual phase
modules directly.

Output contract
---------------
{
    "phase1": {
        "quality_label": str,
        "quality_score": float,
        "preprocessed_image": np.ndarray   # float32 HWC
    },
    "phase2": {
        "vessel_mask":     np.ndarray | None,
        "vessel_overlay":  np.ndarray | None,
        "lesion_overlay":  np.ndarray | None,
        "he_mask":         np.ndarray | None,
        "ex_mask":         np.ndarray | None,
        "se_mask":         np.ndarray | None,
        "he_presence":     bool,
        "ex_area":         float,
        "ma_count":        int,
        "ma_overlay":      np.ndarray | None
    },
    "phase3": {
        "severity_class":            int,
        "probabilities":             list[float],
        "calibrated_probabilities":  list[float],
        "confidence":                float,
        "referable_decision":        str,
        "grade_alone_decision":      str,
        "fitted":                    bool,
        "fusion_status":             str,
        "reason":                    str
    },
    "phase4": {
        "heatmap_overlay": np.ndarray,
        "heatmap_raw":     np.ndarray,
        "label":           str           # always "model attention"
    },
    "stopped_at_phase1": bool,
    "error": str | None,                 # populated only if a phase raised an error
    "timings": {                         # seconds, measured with time.perf_counter() —
        "quality_gate": float,           # never estimated. A stage that did not run
        "vessel_segmentation": float,    # (skipped or errored before starting) is simply
        "lesion_segmentation": float,    # absent from this dict, not zero.
        "ma_detection": float,
        "grading": float,
        "calibration": float,
        "decision_fusion": float,
        "gradcam": float,
        "total": float,
    }
}

Rules (per HANDOFF.md)
----------------------
- If Phase 1 quality_label is "Reject", set stopped_at_phase1=True and return
  the partial dict with None for phases 2-4 keys.  This is not an error.
- Each phase call is wrapped so that a failure produces a clear, phase-labelled
  error in the returned "error" key rather than an unhandled exception propagating
  to the caller.  The caller is free to surface the error string to the user.
- Never fabricate any result for a phase whose model artifact is missing.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional, Union

import numpy as np

# Top-level imports so tests can patch "pipeline.report.<name>"
from pipeline.quality import run_quality_gate
from pipeline.structure import (
    run_vessel_segmentation,
    run_lesion_segmentation,
    run_ma_detection,
)
from pipeline.grading import run_grading, apply_calibration
from pipeline.decision import run_decision_fusion
from pipeline.explain import run_gradcam

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _empty_phase2() -> Dict[str, Any]:
    """Return a Phase 2 dict with all values set to None / zero."""
    return {
        "vessel_mask": None,
        "vessel_overlay": None,
        "lesion_overlay": None,
        "he_mask": None,
        "ex_mask": None,
        "se_mask": None,
        "he_presence": False,
        "ex_area": 0.0,
        "ma_count": 0,
        "ma_overlay": None,
    }


def _empty_phase3() -> Dict[str, Any]:
    return {
        "severity_class": None,
        "probabilities": None,
        "calibrated_probabilities": None,
        "confidence": None,
        "referable_decision": None,
        "grade_alone_decision": None,
        "fitted": None,
        "fusion_status": None,
        "reason": None,
        "model_name": None,
        "model_version": None,
        "calibration_temperature": None,
        "calibration_fitted": None,
    }


def _empty_phase4() -> Dict[str, Any]:
    return {
        "heatmap_overlay": None,
        "heatmap_raw": None,
        "label": "model attention",
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_full_pipeline(
    image_path: Union[str, Path],
    quality_model_dir: Union[str, Path] = "models/quality",
    vessel_model_dir: Union[str, Path] = "models/vessel_seg",
    lesion_model_dir: Union[str, Path] = "models/lesion_seg",
    ma_model_dir: Union[str, Path] = "models/ma_detector",
    grading_model_dir: Union[str, Path] = "models/grading",
    preprocessing_config: Union[str, Path] = "configs/preprocessing.json",
    calibration_config: Union[str, Path] = "configs/calibration.json",
    decision_config: Union[str, Path] = "configs/decision_rule.json",
    decision_model_dir: Union[str, Path] = "models/decision_fusion",
) -> Dict[str, Any]:
    """
    Run all four NETRA-DR pipeline phases in sequence and return a single
    structured result dict for the website to render.

    Phase 1 — Quality Gate
        Assesses image quality; Reject images stop here.
    Phase 2 — Retinal Structure Analysis
        Vessel segmentation, HE/EX/SE lesion segmentation, MA detection.
    Phase 3 — DR Grading & Referral Decision
        ICDR grading, temperature calibration, quality-aware decision fusion.
    Phase 4 — Explainability
        Grad-CAM model-attention heatmap overlay.

    Args:
        image_path:          Path to the raw fundus image (jpg/png).
        quality_model_dir:   Directory for the IQA model artifact + metadata.
        vessel_model_dir:    Directory for the vessel U-Net artifact + metadata.
        lesion_model_dir:    Directory for the lesion segmentation model.
        ma_model_dir:        Directory for the MA detector model.
        grading_model_dir:   Directory for the DR grading model.
        preprocessing_config: Path to configs/preprocessing.json.
        calibration_config:  Path to configs/calibration.json.
        decision_config:     Path to configs/decision_rule.json.
        decision_model_dir:  Directory for the decision fusion model (optional).

    Returns:
        Structured dict with keys:
            phase1            (dict)  — Quality gate outputs
            phase2            (dict)  — Structure analysis outputs (None values if stopped)
            phase3            (dict)  — Grading + decision outputs (None values if stopped)
            phase4            (dict)  — Explainability output (None values if stopped)
            stopped_at_phase1 (bool)  — True only when quality_label == "Reject"
            error             (str|None) — Phase-labelled error message if a phase failed

    Raises:
        FileNotFoundError: If image_path does not exist (before any phase runs).
    """
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(
            f"Input image not found: '{image_path}'. "
            "Supply a valid path to a fundus image."
        )

    pipeline_start = time.perf_counter()
    timings: Dict[str, float] = {}  # seconds, measured — never estimated. Missing key = stage did not run.

    result: Dict[str, Any] = {
        "phase1": None,
        "phase2": None,
        "phase3": None,
        "phase4": None,
        "stopped_at_phase1": False,
        "error": None,
        "timings": timings,
    }

    # -----------------------------------------------------------------------
    # PHASE 1 — Quality Gate
    # -----------------------------------------------------------------------
    try:
        _t0 = time.perf_counter()
        phase1_out = run_quality_gate(
            image_path=image_path,
            model_dir=quality_model_dir,
            preprocessing_config=preprocessing_config,
        )
        timings["quality_gate"] = time.perf_counter() - _t0
        result["phase1"] = phase1_out
    except Exception as exc:
        error_msg = f"Phase 1 error: {type(exc).__name__}: {exc}"
        logger.error(error_msg)
        result["error"] = error_msg
        result["phase1"] = {
            "quality_label": None,
            "quality_score": None,
            "preprocessed_image": None,
        }
        # If Phase 1 cannot run at all, stop and surface the error.
        result["stopped_at_phase1"] = True
        result["phase2"] = _empty_phase2()
        result["phase3"] = _empty_phase3()
        result["phase4"] = _empty_phase4()
        timings["total"] = time.perf_counter() - pipeline_start
        return result

    # Check Reject gate — Reject images never proceed to Phase 2 onwards.
    quality_label: str = str(phase1_out.get("quality_label", ""))
    if quality_label.strip().lower() == "reject":
        result["stopped_at_phase1"] = True
        result["phase2"] = _empty_phase2()
        result["phase3"] = _empty_phase3()
        result["phase4"] = _empty_phase4()
        timings["total"] = time.perf_counter() - pipeline_start
        return result

    preprocessed_image: Optional[np.ndarray] = phase1_out.get("preprocessed_image")

    # -----------------------------------------------------------------------
    # PHASE 2 — Retinal Structure Analysis
    # -----------------------------------------------------------------------
    phase2: Dict[str, Any] = _empty_phase2()
    phase2_errors: list = []

    # 2a — Vessel segmentation
    try:
        _t0 = time.perf_counter()
        vessel_out = run_vessel_segmentation(
            preprocessed_image=preprocessed_image,
            model_dir=vessel_model_dir,
        )
        timings["vessel_segmentation"] = time.perf_counter() - _t0
        phase2["vessel_mask"] = vessel_out.get("vessel_mask")
        phase2["vessel_overlay"] = vessel_out.get("vessel_overlay")
    except Exception as exc:
        msg = f"Phase 2 vessel segmentation error: {type(exc).__name__}: {exc}"
        logger.warning(msg)
        phase2_errors.append(msg)

    # 2b — Lesion segmentation (HE/EX/SE)
    try:
        _t0 = time.perf_counter()
        lesion_out = run_lesion_segmentation(
            preprocessed_image=preprocessed_image,
            model_dir=lesion_model_dir,
        )
        timings["lesion_segmentation"] = time.perf_counter() - _t0
        phase2["lesion_overlay"] = lesion_out.get("lesion_overlay")
        phase2["he_mask"] = lesion_out.get("he_mask")
        phase2["ex_mask"] = lesion_out.get("ex_mask")
        phase2["se_mask"] = lesion_out.get("se_mask")
        phase2["he_presence"] = bool(lesion_out.get("he_presence", False))
        phase2["ex_area"] = float(lesion_out.get("ex_area", 0.0))
    except Exception as exc:
        msg = f"Phase 2 lesion segmentation error: {type(exc).__name__}: {exc}"
        logger.warning(msg)
        phase2_errors.append(msg)

    # 2c — MA detection
    try:
        _t0 = time.perf_counter()
        ma_out = run_ma_detection(
            preprocessed_image=preprocessed_image,
            model_dir=ma_model_dir,
        )
        timings["ma_detection"] = time.perf_counter() - _t0
        phase2["ma_count"] = int(ma_out.get("ma_count", 0))
        phase2["ma_overlay"] = ma_out.get("ma_overlay")
    except Exception as exc:
        msg = f"Phase 2 MA detection error: {type(exc).__name__}: {exc}"
        logger.warning(msg)
        phase2_errors.append(msg)

    result["phase2"] = phase2
    if phase2_errors:
        existing_err = result["error"] or ""
        result["error"] = (existing_err + "; ".join(phase2_errors)).lstrip("; ")

    # -----------------------------------------------------------------------
    # PHASE 3 — DR Grading & Referral Decision
    # -----------------------------------------------------------------------
    phase3 = _empty_phase3()

    try:
        _t0 = time.perf_counter()
        grading_out = run_grading(
            preprocessed_image=preprocessed_image,
            model_dir=grading_model_dir,
        )
        timings["grading"] = time.perf_counter() - _t0
        severity_class: int = grading_out["severity_class"]
        raw_probs = grading_out["probabilities"]

        _t0 = time.perf_counter()
        cal_out = apply_calibration(
            probabilities=raw_probs,
            config_path=calibration_config,
        )
        timings["calibration"] = time.perf_counter() - _t0

        _t0 = time.perf_counter()
        decision_out = run_decision_fusion(
            calibrated_probabilities=cal_out["calibrated_probabilities"],
            ma_count=phase2.get("ma_count", 0),
            he_presence=phase2.get("he_presence", False),
            ex_area=phase2.get("ex_area", 0.0),
            quality_label=quality_label,
            config_path=decision_config,
            model_dir=decision_model_dir,
        )
        timings["decision_fusion"] = time.perf_counter() - _t0

        phase3 = {
            "severity_class": severity_class,
            "probabilities": raw_probs,
            "calibrated_probabilities": cal_out["calibrated_probabilities"],
            "confidence": cal_out["confidence"],
            "referable_decision": decision_out["referable_decision"],
            "grade_alone_decision": decision_out["grade_alone_decision"],
            "fitted": decision_out["fitted"],
            "fusion_status": decision_out["fusion_status"],
            "reason": decision_out["reason"],
            "model_name": grading_out.get("model_name"),
            "model_version": grading_out.get("model_version"),
            "calibration_temperature": cal_out.get("temperature"),
            "calibration_fitted": cal_out.get("fitted"),
        }

    except Exception as exc:
        msg = f"Phase 3 error: {type(exc).__name__}: {exc}"
        logger.error(msg)
        existing_err = result["error"] or ""
        result["error"] = (existing_err + "; " + msg).lstrip("; ")

    result["phase3"] = phase3

    # -----------------------------------------------------------------------
    # PHASE 4 — Explainability (Grad-CAM)
    # -----------------------------------------------------------------------
    phase4 = _empty_phase4()
    sc = phase3.get("severity_class")

    if sc is not None:
        try:
            _t0 = time.perf_counter()
            gradcam_out = run_gradcam(
                preprocessed_image=preprocessed_image,
                severity_class=int(sc),
                model_dir=grading_model_dir,
            )
            timings["gradcam"] = time.perf_counter() - _t0
            phase4 = {
                "heatmap_overlay": gradcam_out["heatmap_overlay"],
                "heatmap_raw": gradcam_out["heatmap_raw"],
                # Mandatory: always "model attention" — never "evidence" or "proof"
                "label": gradcam_out["label"],
            }
        except Exception as exc:
            msg = f"Phase 4 explainability error: {type(exc).__name__}: {exc}"
            logger.error(msg)
            existing_err = result["error"] or ""
            result["error"] = (existing_err + "; " + msg).lstrip("; ")
    else:
        logger.info(
            "Phase 4 skipped: no severity_class available from Phase 3 "
            "(model artifact likely missing)."
        )

    result["phase4"] = phase4
    timings["total"] = time.perf_counter() - pipeline_start
    return result
