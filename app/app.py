"""
app/app.py — NETRA-DR Prototype: End-to-End 4-Phase Diagnostic Pipeline

Phases:
  Phase 1 — EyeQ Fundus Quality Assessment Gate (Good / Borderline / Reject)
  Phase 2 — Retinal Structure Analysis (FR-UNet Vessels + HE/EX/SE/MA Lesions)
  Phase 3 — DR Severity Grading & Decision Fusion (ICDR 0-4 + Calibration + 5-Input Fusion)
  Phase 4 — Explainability & Consistency (Grad-CAM Model Attention vs Detected Evidence)

Routes:
  GET  /             → Main Interactive Screening Interface
  POST /             → Initial Image Upload / Demo Selector (runs Phase 1 & caches session)
  POST /api/quality  → Programmatic Phase 1 API
  POST /api/phase2   → Interactive Phase 2 Execution (gated on Phase 1 pass)
  POST /api/phase3   → Interactive Phase 3 Execution (gated on Phase 2 completion)
  POST /api/phase4   → Interactive Phase 4 Execution (gated on Phase 3 completion)
  POST /api/run_all  → Run all 4 phases end-to-end
  GET  /api/status   → Model readiness and system health
"""

from __future__ import annotations

import base64
import io
import json
import logging
import os
import shutil
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import cv2
import numpy as np
from flask import Flask, jsonify, render_template, request
from PIL import Image as PILImage

from pipeline.contract import ModelArtifactNotFoundError
from pipeline.decision import run_decision_fusion
from pipeline.explain import generate_heatmap_overlay, run_gradcam
from pipeline.grading import apply_calibration, run_grading
from pipeline.orchestrator import (
    NetraConfig,
    _check_consistency_flag,
    _run_calibration,
    _run_decision_fusion,
    _run_ensemble_grading,
    _run_explainability,
    _run_lesion_detection,
    _run_vessel_segmentation,
    run_netra_pipeline,
)
from pipeline.preprocessing import preprocess
from pipeline.quality import run_quality_gate
from pipeline.quality_service import check_eyeq_availability, get_quality_service
from pipeline.startup_check import run_startup_check
from pipeline.structure import (
    run_lesion_segmentation,
    run_ma_detection,
    run_vessel_segmentation,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024  # 32 MB upload limit

# Model readiness check
_STARTUP_REPORT = run_startup_check(verbose=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
DEMO_IMAGES = {
    "good": PROJECT_ROOT / "data" / "demo" / "good_sample.jpg",
    "reject": PROJECT_ROOT / "data" / "demo" / "reject_sample.jpg",
}

ICDR_CLASS_NAMES = {
    0: "Grade 0 — No Apparent Retinopathy",
    1: "Grade 1 — Mild Non-Proliferative DR",
    2: "Grade 2 — Moderate Non-Proliferative DR",
    3: "Grade 3 — Severe Non-Proliferative DR",
    4: "Grade 4 — Proliferative Diabetic Retinopathy",
}

# In-memory session store for multi-phase interactive execution
_SESSIONS: Dict[str, Dict[str, Any]] = {}


def _allowed(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def _ndarray_to_data_uri(image: np.ndarray) -> str:
    """Convert an HWC uint8 RGB numpy array to a base64-encoded PNG data URI."""
    if image is None:
        return ""
    if np.issubdtype(image.dtype, np.floating):
        image = (np.clip(image, 0.0, 1.0) * 255.0).astype(np.uint8)
    if image.ndim == 2:
        pil = PILImage.fromarray(image, mode="L")
    elif image.shape[2] == 3:
        pil = PILImage.fromarray(image, mode="RGB")
    else:
        pil = PILImage.fromarray(image[:, :, :3], mode="RGB")
    buf = io.BytesIO()
    pil.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def _draw_single_mask_overlay(
    image: np.ndarray,
    mask: np.ndarray,
    color_rgb: Tuple[int, int, int] = (255, 0, 0),
    alpha: float = 0.5,
) -> np.ndarray:
    """Draw a single binary mask over an RGB/float image with a custom color."""
    if image is None or mask is None:
        return None
    if image.dtype == np.float32 or image.dtype == np.float64:
        base = (np.clip(image, 0.0, 1.0) * 255.0).astype(np.uint8)
    else:
        base = image.astype(np.uint8).copy()

    if mask.shape[:2] != base.shape[:2]:
        mask_resized = cv2.resize(mask, (base.shape[1], base.shape[0]), interpolation=cv2.INTER_NEAREST)
    else:
        mask_resized = mask

    overlay = base.copy()
    overlay[mask_resized > 0] = color_rgb
    blended = cv2.addWeighted(base, 1.0 - alpha, overlay, alpha, 0)
    return blended


def _get_recommendation(quality_label: str) -> Dict[str, str]:
    lbl = (quality_label or "").upper()
    if lbl == "REJECT":
        return {
            "title": "Recapture Advised",
            "action": "HALT",
            "badge_class": "badge-reject",
            "summary": "Automated diagnostic pipeline halted. The image has poor quality (severe blur, underexposure, or obscuration).",
            "guidance": (
                "Please recapture the fundus photograph. Ensure adequate pupil dilation, "
                "correct focus on the retina, sufficient illumination without flash artifacts, "
                "and steady patient fixation."
            ),
        }
    elif lbl == "BORDERLINE":
        return {
            "title": "Borderline Quality — Caution Advised",
            "action": "PROCEED_WITH_CAUTION",
            "badge_class": "badge-borderline",
            "summary": "The image is usable but sub-optimal (e.g. non-uniform illumination or slight peripheral blur).",
            "guidance": (
                "Proceed with caution. Early microvascular lesions may exhibit reduced contrast. "
                "A stricter referral threshold (0.35) will be applied during Phase 3 decision fusion."
            ),
        }
    else:  # GOOD
        return {
            "title": "Quality Gate Passed",
            "action": "PROCEED",
            "badge_class": "badge-good",
            "summary": "High-quality retinal photograph suitable for automated diagnostic screening.",
            "guidance": (
                "All clarity, contrast, and field-of-view criteria are satisfied. "
                "Retinal vasculature and macula are clearly visible."
            ),
        }


def _format_phase2_dict(p2: dict, preprocessed_image: np.ndarray) -> dict:
    """Format Phase 2 outputs including separate labeled lesion overlays."""
    he_mask = p2.get("he_mask")
    ex_mask = p2.get("ex_mask")
    se_mask = p2.get("se_mask")
    vessel_mask = p2.get("vessel_mask")

    # Generate separate individual overlays (never merged)
    he_overlay = _draw_single_mask_overlay(preprocessed_image, he_mask, color_rgb=(255, 30, 30), alpha=0.55)
    ex_overlay = _draw_single_mask_overlay(preprocessed_image, ex_mask, color_rgb=(255, 220, 0), alpha=0.55)
    se_overlay = _draw_single_mask_overlay(preprocessed_image, se_mask, color_rgb=(0, 200, 255), alpha=0.55)
    vessel_overlay = p2.get("vessel_overlay")

    return {
        "status": p2.get("status", "ok"),
        "error": p2.get("error"),
        "evidence_label": "detected evidence",  # mandatory label
        # Vessel outputs
        "vessel_mask_uri": _ndarray_to_data_uri(vessel_mask),
        "vessel_overlay_uri": _ndarray_to_data_uri(vessel_overlay),
        "thin_vessel_sensitivity": f"{p2.get('thin_vessel_sensitivity', 0.0):.1%}" if p2.get("thin_vessel_sensitivity") is not None else "N/A",
        # Separate Lesion Overlays
        "he_overlay_uri": _ndarray_to_data_uri(he_overlay),
        "ex_overlay_uri": _ndarray_to_data_uri(ex_overlay),
        "se_overlay_uri": _ndarray_to_data_uri(se_overlay),
        "ma_overlay_uri": _ndarray_to_data_uri(p2.get("ma_overlay")),
        "composite_lesion_overlay_uri": _ndarray_to_data_uri(p2.get("lesion_overlay")),
        # Quantified Findings
        "ma_count": int(p2.get("ma_count", 0)),
        "ma_count_near_macula": int(p2.get("ma_count_near_macula", 0)),
        "he_presence": bool(p2.get("he_presence", False)),
        "he_area_fraction": f"{p2.get('he_area_fraction', 0.0):.4%}",
        "he_quadrant_counts": p2.get("he_quadrant_counts", {"TL": 0, "TR": 0, "BL": 0, "BR": 0}),
        "ex_area": f"{p2.get('ex_area', 0.0):.4%}",
        "ex_area_near_fovea": f"{p2.get('ex_area_near_fovea', 0.0):.4%}",
        "se_presence": bool(np.sum(se_mask > 0) > 0) if se_mask is not None else False,
    }


def _format_phase3_dict(p3_dec: dict, p3_grade: dict, p3_cal: dict) -> dict:
    """Format Phase 3 outputs for DR severity grading and decision fusion."""
    sc = p3_grade.get("severity_class", 0) if p3_grade else 0
    raw_p = p3_grade.get("probabilities", [0.0]*5) if p3_grade else [0.0]*5
    cal_p = p3_cal.get("calibrated_probabilities", raw_p) if p3_cal else raw_p
    conf = p3_cal.get("confidence", max(cal_p) if cal_p else 0.0) if p3_cal else max(cal_p)
    temp = p3_cal.get("temperature", 1.0) if p3_cal else 1.0

    ref_dec = p3_dec.get("referable_decision", "NO REFER")
    grade_alone = p3_dec.get("grade_alone_decision", "NO REFER")
    thresh = p3_dec.get("threshold_applied", 0.50)
    q_tier = p3_dec.get("quality_tier", "Good")
    reason = p3_dec.get("reason", "")
    fusion_status = p3_dec.get("fusion_status", "ok")

    return {
        "status": p3_dec.get("status", "ok"),
        "error": p3_dec.get("error"),
        "severity_class": sc,
        "severity_name": ICDR_CLASS_NAMES.get(sc, f"Grade {sc}"),
        "confidence": f"{conf:.1%}",
        "temperature": temp,
        "raw_probabilities": [round(p * 100, 1) for p in raw_p],
        "calibrated_probabilities": [round(p * 100, 1) for p in cal_p],
        "referable_decision": ref_dec,
        "grade_alone_decision": grade_alone,
        "threshold_applied": f"{thresh:.2f}",
        "quality_tier": q_tier,
        "reason": reason,
        "fusion_status": fusion_status,
        "referable_probability": f"{p3_dec.get('referable_probability', 0.0):.1%}",
        "feature_vector": p3_dec.get("fusion_feature_vector"),
    }


def _format_phase4_dict(p4: dict, p10: dict) -> dict:
    """Format Phase 4 Grad-CAM explainability and consistency check."""
    return {
        "status": p4.get("status", "ok"),
        "error": p4.get("error"),
        "label": "model attention",  # mandatory label
        "evidence_label": "detected evidence",  # mandatory label
        "heatmap_overlay_uri": _ndarray_to_data_uri(p4.get("heatmap_overlay")),
        "iou_vs_he": f"{p4.get('iou_vs_he'):.3f}" if p4.get("iou_vs_he") is not None else "N/A",
        "iou_vs_ex": f"{p4.get('iou_vs_ex'):.3f}" if p4.get("iou_vs_ex") is not None else "N/A",
        "priority_human_review": bool(p10.get("priority_human_review", False)),
        "consistency_flag_reason": p10.get("consistency_flag_reason", "Consistency check evaluated."),
        "threshold_used": p10.get("threshold_used", 0.10),
    }


# ---------------------------------------------------------------------------
# Core Views
# ---------------------------------------------------------------------------

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return render_template("index.html", display=None, startup_report=_STARTUP_REPORT)

    demo_choice = request.form.get("demo_image")
    file = request.files.get("image")
    run_mode = request.form.get("run_mode", "step")  # 'step' or 'full'

    temp_path: Optional[str] = None
    try:
        if demo_choice in DEMO_IMAGES and DEMO_IMAGES[demo_choice].is_file():
            source_path = DEMO_IMAGES[demo_choice]
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                shutil.copyfile(source_path, tmp.name)
                temp_path = tmp.name
                suffix = ".jpg"
        else:
            if file is None or file.filename == "":
                return render_template(
                    "index.html",
                    display=None,
                    upload_error="No image file was selected. Please choose a fundus image or click a demo sample.",
                    startup_report=_STARTUP_REPORT,
                )

            if not _allowed(file.filename):
                return render_template(
                    "index.html",
                    display=None,
                    upload_error="Unsupported file format. Please upload a JPG or PNG retinal fundus photograph.",
                    startup_report=_STARTUP_REPORT,
                )

            suffix = Path(file.filename).suffix.lower()
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                file.save(tmp.name)
                temp_path = tmp.name

            # Validate image integrity
            try:
                with PILImage.open(temp_path) as test_img:
                    test_img.verify()
                with PILImage.open(temp_path) as test_img:
                    w, h = test_img.size
                    if w < 50 or h < 50:
                        raise ValueError(f"Image resolution too small ({w}×{h}). Expected fundus photograph.")
            except Exception as val_exc:
                return render_template(
                    "index.html",
                    display=None,
                    upload_error=f"Invalid image file: {val_exc}",
                    startup_report=_STARTUP_REPORT,
                )

        # 1. Run Phase 1 Quality Gate
        gate_res = run_quality_gate(temp_path)
        q_label = str(gate_res.get("quality_label", "")).strip().upper()
        is_reject = (q_label == "REJECT")
        norm_q = "Reject" if is_reject else ("Borderline" if q_label == "BORDERLINE" else "Good")

        preprocessed_img = gate_res.get("preprocessed_image")
        if preprocessed_img is None:
            preprocessed_img = preprocess(temp_path)

        # Read original image data URI
        with open(temp_path, "rb") as f:
            ext_mime = "jpeg" if suffix in (".jpg", ".jpeg") else "png"
            orig_b64 = base64.b64encode(f.read()).decode("ascii")
            orig_uri = f"data:image/{ext_mime};base64,{orig_b64}"

        # Initialize Session
        analysis_id = str(uuid.uuid4())
        session_data: Dict[str, Any] = {
            "analysis_id": analysis_id,
            "original_image_uri": orig_uri,
            "preprocessed_image": preprocessed_img,
            "quality_tier": norm_q,
            "phase1": gate_res,
            "phase2": None,
            "phase3": None,
            "phase4": None,
        }

        # If user selected full pipeline run and quality passed
        if run_mode == "full" and not is_reject:
            logger.info("Executing full 4-phase pipeline for session %s...", analysis_id)
            pipe_res = run_netra_pipeline(preprocessed_img, norm_q)
            session_data["phase2"] = pipe_res.get("s2_lesion")
            session_data["phase2"]["vessel_mask"] = pipe_res.get("s1_vessel", {}).get("vessel_mask")
            session_data["phase2"]["vessel_overlay"] = pipe_res.get("s1_vessel", {}).get("vessel_overlay")
            session_data["phase2"]["thin_vessel_sensitivity"] = pipe_res.get("s1_vessel", {}).get("thin_vessel_sensitivity")
            
            session_data["phase3_decision"] = pipe_res.get("s5_decision")
            session_data["phase3_grading"] = pipe_res.get("s4_grading")
            session_data["phase3_calibration"] = pipe_res.get("s6_calibration")

            session_data["phase4_explain"] = pipe_res.get("s8_explain")
            session_data["phase4_consistency"] = pipe_res.get("s10_consistency")

        _SESSIONS[analysis_id] = session_data

        # Prepare Display
        q_score = gate_res.get("quality_score")
        probs = gate_res.get("probabilities") or {}
        eyeq_details = gate_res.get("eyeq_details") or {}
        recom = _get_recommendation(q_label)

        display: Dict[str, Any] = {
            "analysis_id": analysis_id,
            "stopped_at_phase1": is_reject,
            "original_image": orig_uri,
            "startup_report": _STARTUP_REPORT,
            "phase1": {
                "quality_label": q_label,
                "quality_score": f"{q_score:.1%}" if q_score is not None else None,
                "confidence_float": q_score,
                "probabilities": {
                    "good": round(probs.get("good", 0.0) * 100, 1),
                    "borderline": round(probs.get("borderline", probs.get("uncertain", 0.0)) * 100, 1),
                    "reject": round(probs.get("reject", probs.get("bad", 0.0)) * 100, 1),
                },
                "preprocessed_image": _ndarray_to_data_uri(preprocessed_img),
                "recommendation": recom,
                "inference_time_ms": eyeq_details.get("inference_time_ms"),
            },
            "phase2": None,
            "phase3": None,
            "phase4": None,
        }

        if session_data.get("phase2"):
            display["phase2"] = _format_phase2_dict(session_data["phase2"], preprocessed_img)

        if session_data.get("phase3_decision"):
            display["phase3"] = _format_phase3_dict(
                session_data["phase3_decision"],
                session_data["phase3_grading"],
                session_data["phase3_calibration"],
            )

        if session_data.get("phase4_explain"):
            display["phase4"] = _format_phase4_dict(
                session_data["phase4_explain"],
                session_data["phase4_consistency"],
            )

        return render_template("index.html", display=display, startup_report=_STARTUP_REPORT)

    except Exception as exc:
        logger.exception("Error evaluating fundus image")
        return render_template(
            "index.html",
            display=None,
            upload_error=f"Pipeline Error: {type(exc).__name__}: {exc}",
            startup_report=_STARTUP_REPORT,
        )
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                pass


# ---------------------------------------------------------------------------
# Interactive Phase API Endpoints
# ---------------------------------------------------------------------------

@app.route("/api/phase2", methods=["POST"])
def api_phase2():
    """
    POST /api/phase2
    Executes Phase 2 (Retinal Structure Analysis) on the PREPROCESSED image.
    Gated on Phase 1 quality pass (Good / Borderline).
    """
    try:
        data = request.get_json(silent=True) or request.form
        analysis_id = data.get("analysis_id")
        if not analysis_id or analysis_id not in _SESSIONS:
            return jsonify({"status": "error", "error": "Invalid or expired analysis session. Please upload/select an image first."}), 400

        sess = _SESSIONS[analysis_id]
        quality_tier = sess.get("quality_tier", "Reject")

        # Strict quality gating
        if quality_tier == "Reject":
            return jsonify({
                "status": "error",
                "error": "Gated by Phase 1 Quality Gate: Reject-quality image cannot proceed to Phase 2 retinal structure analysis.",
            }), 400

        preprocessed_img = sess.get("preprocessed_image")
        if preprocessed_img is None:
            return jsonify({"status": "error", "error": "Preprocessed image not found in session."}), 400

        config = NetraConfig()

        # Run S1 Vessel Segmentation
        vessel_res = _run_vessel_segmentation(preprocessed_img, config)
        if vessel_res.get("status") == "error":
            logger.error("Phase 2 Vessel Segmentation Error: %s", vessel_res.get("error"))

        # Run S2 Lesion Detection (HE, EX, SE, MA)
        lesion_res = _run_lesion_detection(preprocessed_img, config)
        if lesion_res.get("status") == "error":
            logger.error("Phase 2 Lesion Detection Error: %s", lesion_res.get("error"))

        # Merge Phase 2 outputs into session
        p2_combined = {
            **lesion_res,
            "vessel_mask": vessel_res.get("vessel_mask"),
            "vessel_overlay": vessel_res.get("vessel_overlay"),
            "thin_vessel_sensitivity": vessel_res.get("thin_vessel_sensitivity"),
        }
        sess["phase2"] = p2_combined

        formatted = _format_phase2_dict(p2_combined, preprocessed_img)
        return jsonify({"status": "success", "phase2": formatted}), 200

    except Exception as exc:
        logger.exception("Phase 2 API error")
        return jsonify({"status": "error", "error": f"{type(exc).__name__}: {exc}"}), 500


@app.route("/api/phase3", methods=["POST"])
def api_phase3():
    """
    POST /api/phase3
    Executes Phase 3 (DR Severity Grading & Decision Fusion).
    Gated on Phase 1 pass AND Phase 2 completion.
    """
    try:
        data = request.get_json(silent=True) or request.form
        analysis_id = data.get("analysis_id")
        if not analysis_id or analysis_id not in _SESSIONS:
            return jsonify({"status": "error", "error": "Invalid or expired analysis session."}), 400

        sess = _SESSIONS[analysis_id]
        quality_tier = sess.get("quality_tier", "Reject")

        if quality_tier == "Reject":
            return jsonify({"status": "error", "error": "Gated by Phase 1: Reject-quality image cannot proceed to Phase 3 grading."}), 400

        p2 = sess.get("phase2")
        if not p2:
            return jsonify({"status": "error", "error": "Phase 2 structure analysis must be completed before running Phase 3."}), 400

        preprocessed_img = sess.get("preprocessed_image")
        config = NetraConfig()

        # 1. S4/S7 DR Grading
        ens = _run_ensemble_grading(preprocessed_img, config)
        s4_grading = {
            "severity_class": int(np.argmax(ens["mean_probabilities"])),
            "probabilities": ens["mean_probabilities"],
            "model_name": ens.get("model_name", "drdetect EfficientNet-B0"),
            "model_version": ens.get("model_version", "best.ckpt"),
            "class_labels": ["0", "1", "2", "3", "4"],
        }
        sess["phase3_grading"] = s4_grading

        # 2. S6 Temperature Calibration
        cal = _run_calibration(s4_grading["probabilities"], config)
        sess["phase3_calibration"] = cal

        # 3. S5 Decision Fusion
        dec = _run_decision_fusion(
            calibrated_probabilities=cal["calibrated_probabilities"],
            s2_lesion=p2,
            quality_tier=quality_tier,
            config=config,
        )
        sess["phase3_decision"] = dec

        formatted = _format_phase3_dict(dec, s4_grading, cal)
        return jsonify({"status": "success", "phase3": formatted}), 200

    except Exception as exc:
        logger.exception("Phase 3 API error")
        return jsonify({"status": "error", "error": f"{type(exc).__name__}: {exc}"}), 500


@app.route("/api/phase4", methods=["POST"])
def api_phase4():
    """
    POST /api/phase4
    Executes Phase 4 (Grad-CAM Explainability & Consistency Check).
    Gated on Phase 1, Phase 2, and Phase 3 completion.
    """
    try:
        data = request.get_json(silent=True) or request.form
        analysis_id = data.get("analysis_id")
        if not analysis_id or analysis_id not in _SESSIONS:
            return jsonify({"status": "error", "error": "Invalid or expired analysis session."}), 400

        sess = _SESSIONS[analysis_id]
        quality_tier = sess.get("quality_tier", "Reject")
        if quality_tier == "Reject":
            return jsonify({"status": "error", "error": "Gated by Phase 1: Reject-quality image cannot proceed to Phase 4 explainability."}), 400

        p2 = sess.get("phase2")
        p3_grade = sess.get("phase3_grading")
        if not p2 or not p3_grade:
            return jsonify({"status": "error", "error": "Phases 2 and 3 must be completed before running Phase 4."}), 400

        preprocessed_img = sess.get("preprocessed_image")
        severity_class = p3_grade.get("severity_class", 0)
        config = NetraConfig()

        # 1. S8 Explainability
        s8_explain = _run_explainability(
            preprocessed_image=preprocessed_img,
            severity_class=int(severity_class),
            s2_lesion=p2,
            config=config,
        )
        sess["phase4_explain"] = s8_explain

        # 2. S10 Consistency Flag
        s10_cons = _check_consistency_flag(s8_explain, config)
        sess["phase4_consistency"] = s10_cons

        formatted = _format_phase4_dict(s8_explain, s10_cons)
        return jsonify({"status": "success", "phase4": formatted}), 200

    except Exception as exc:
        logger.exception("Phase 4 API error")
        return jsonify({"status": "error", "error": f"{type(exc).__name__}: {exc}"}), 500


@app.route("/api/run_all", methods=["POST"])
def api_run_all():
    """POST /api/run_all — Runs all 4 phases end-to-end for a given session."""
    try:
        data = request.get_json(silent=True) or request.form
        analysis_id = data.get("analysis_id")
        if not analysis_id or analysis_id not in _SESSIONS:
            return jsonify({"status": "error", "error": "Invalid or expired analysis session."}), 400

        sess = _SESSIONS[analysis_id]
        quality_tier = sess.get("quality_tier", "Reject")
        if quality_tier == "Reject":
            return jsonify({"status": "error", "error": "Reject-quality image halted at Phase 1."}), 400

        preprocessed_img = sess.get("preprocessed_image")
        pipe_res = run_netra_pipeline(preprocessed_img, quality_tier)

        sess["phase2"] = pipe_res.get("s2_lesion")
        sess["phase2"]["vessel_mask"] = pipe_res.get("s1_vessel", {}).get("vessel_mask")
        sess["phase2"]["vessel_overlay"] = pipe_res.get("s1_vessel", {}).get("vessel_overlay")
        sess["phase2"]["thin_vessel_sensitivity"] = pipe_res.get("s1_vessel", {}).get("thin_vessel_sensitivity")

        sess["phase3_decision"] = pipe_res.get("s5_decision")
        sess["phase3_grading"] = pipe_res.get("s4_grading")
        sess["phase3_calibration"] = pipe_res.get("s6_calibration")

        sess["phase4_explain"] = pipe_res.get("s8_explain")
        sess["phase4_consistency"] = pipe_res.get("s10_consistency")

        f_p2 = _format_phase2_dict(sess["phase2"], preprocessed_img)
        f_p3 = _format_phase3_dict(sess["phase3_decision"], sess["phase3_grading"], sess["phase3_calibration"])
        f_p4 = _format_phase4_dict(sess["phase4_explain"], sess["phase4_consistency"])

        return jsonify({
            "status": "success",
            "phase2": f_p2,
            "phase3": f_p3,
            "phase4": f_p4,
        }), 200

    except Exception as exc:
        logger.exception("Run All API error")
        return jsonify({"status": "error", "error": f"{type(exc).__name__}: {exc}"}), 500


@app.route("/api/quality", methods=["POST"])
def api_quality():
    """POST /api/quality — Phase 1 EyeQ quality assessment endpoint."""
    temp_path: Optional[str] = None
    try:
        if request.is_json:
            data = request.get_json() or {}
            img_path_str = data.get("image_path")
            if not img_path_str or not Path(img_path_str).is_file():
                return jsonify({"status": "error", "error": f"Image path not found: {img_path_str}"}), 400
            target_path = Path(img_path_str)
        else:
            file = request.files.get("image")
            if file is None or file.filename == "":
                return jsonify({"status": "error", "error": "No 'image' file provided in request."}), 400
            if not _allowed(file.filename):
                return jsonify({"status": "error", "error": "Invalid file type. Expected JPG or PNG."}), 400

            suffix = Path(file.filename).suffix.lower()
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                file.save(tmp.name)
                temp_path = tmp.name
                target_path = Path(temp_path)

        gate_res = run_quality_gate(str(target_path))
        label = gate_res["quality_label"]
        score = gate_res["quality_score"]
        probs = gate_res.get("probabilities", {})
        recom = _get_recommendation(label)

        response_payload = {
            "status": "success",
            "quality_label": label,
            "quality_score": round(score, 4),
            "confidence": round(score, 4),
            "action": recom["action"],
            "recommendation": recom["summary"],
            "guidance": recom["guidance"],
            "probabilities": {
                "good": round(probs.get("good", 0.0), 5),
                "borderline": round(probs.get("borderline", probs.get("uncertain", 0.0)), 5),
                "reject": round(probs.get("reject", probs.get("bad", 0.0)), 5),
            },
        }
        return jsonify(response_payload), 200

    except Exception as exc:
        logger.exception("API quality endpoint error")
        return jsonify({"status": "error", "error": f"{type(exc).__name__}: {exc}"}), 500
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                pass


@app.route("/api/status", methods=["GET"])
def api_status():
    """GET /api/status — Check server and model readiness."""
    eyeq_status = check_eyeq_availability()
    return jsonify({
        "status": "operational",
        "phase1_eyeq": eyeq_status,
        "startup_report": _STARTUP_REPORT,
    })


if __name__ == "__main__":
    try:
        import torch
    except ImportError:
        venv_py_win = PROJECT_ROOT / "external" / "EyeQ" / ".venv" / "Scripts" / "python.exe"
        venv_py_nix = PROJECT_ROOT / "external" / "EyeQ" / ".venv" / "bin" / "python"
        venv_target = venv_py_win if venv_py_win.is_file() else (venv_py_nix if venv_py_nix.is_file() else None)
        if venv_target and os.environ.get("NETRA_REEXEC") != "1":
            os.environ["NETRA_REEXEC"] = "1"
            import subprocess
            sys.exit(subprocess.call([str(venv_target), *sys.argv]))

    logger.info("Pre-warming EyeQ Quality Assessment Model...")
    try:
        _svc = get_quality_service()
        logger.info("EyeQ ensemble pre-warmed successfully (%d models in memory).", _svc.ensemble_size)
    except Exception as _init_err:
        logger.warning("EyeQ pre-warming deferred: %s", _init_err)

    print("\n" + "=" * 65)
    print("  NETRA-DR 4-Phase Diagnostic Pipeline Server")
    print("  All 4 Pipeline Stages Wired & Operational")
    print("  Visit: http://127.0.0.1:5000")
    print("=" * 65 + "\n")
    app.run(host="127.0.0.1", port=5000, debug=False)
