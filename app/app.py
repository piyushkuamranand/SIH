"""
app/app.py — NETRA-DR Prototype Integration: Phase 1 EyeQ Quality Assessment

Routes:
  GET  /            → Upload interface with quick-test demo triggers
  POST /            → Evaluates fundus image through Phase 1 EyeQ quality assessment
  POST /api/quality → JSON API for automated/programmatic quality assessment
  GET  /api/status  → Health and model readiness status

Flow:
  USER UPLOADS FUNDUS IMAGE
          ↓
  INPUT VALIDATION
          ↓
  PHASE 1 — EYEQ QUALITY ASSESSMENT
          ↓
  QUALITY RESULT
          ↓
  GOOD / BORDERLINE / REJECT
          ↓
  Appropriate prototype action & guidance
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
from pathlib import Path
from typing import Any, Dict, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from flask import Flask, jsonify, render_template, request
from PIL import Image as PILImage
import numpy as np

from pipeline.startup_check import run_startup_check
from pipeline.quality import run_quality_gate
from pipeline.quality_service import check_eyeq_availability, get_quality_service

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


def _allowed(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def _ndarray_to_data_uri(image: np.ndarray) -> str:
    """Convert an HWC uint8 RGB numpy array to a base64-encoded PNG data URI."""
    if image is None:
        return ""
    if np.issubdtype(image.dtype, np.floating):
        image = (np.clip(image, 0.0, 1.0) * 255.0).astype(np.uint8)
    pil = PILImage.fromarray(image, mode="RGB")
    buf = io.BytesIO()
    pil.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


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
                "Manual ophthalmologist review is recommended to confirm automated findings."
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


def _prepare_display(result: dict) -> dict:
    """Prepare Phase 1 pipeline output for template rendering."""
    display: Dict[str, Any] = {
        "stopped_at_phase1": result.get("stopped_at_phase1", False),
        "error": result.get("error"),
        "startup_report": _STARTUP_REPORT,
    }

    p1 = result.get("phase1") or {}
    q_label = p1.get("quality_label")
    q_score = p1.get("quality_score")
    probs = p1.get("probabilities") or {}
    eyeq_details = p1.get("eyeq_details") or {}

    recommendation = _get_recommendation(q_label)

    display["phase1"] = {
        "quality_label": q_label,
        "quality_score": f"{q_score:.1%}" if q_score is not None else None,
        "confidence_float": q_score,
        "probabilities": {
            "good": round(probs.get("good", 0.0) * 100, 1),
            "borderline": round(probs.get("borderline", probs.get("uncertain", 0.0)) * 100, 1),
            "reject": round(probs.get("reject", probs.get("bad", 0.0)) * 100, 1),
        },
        "raw_probabilities": probs,
        "preprocessed_image": _ndarray_to_data_uri(p1.get("preprocessed_image")),
        "recommendation": recommendation,
        "inference_time_ms": eyeq_details.get("inference_time_ms"),
        "model_name": "EyeQ EfficientNet-B4 Ensemble (8 Seeds)",
        "input_resolution": "520 × 520 px",
        "normalization": "Non-zero pixel mean/std normalization",
    }

    p2 = result.get("phase2") or {}
    display["phase2"] = {
        "vessel_overlay": _ndarray_to_data_uri(p2.get("vessel_overlay")),
        "lesion_overlay": _ndarray_to_data_uri(p2.get("lesion_overlay")),
        "ma_overlay": _ndarray_to_data_uri(p2.get("ma_overlay")),
        "ma_count": p2.get("ma_count", 0),
        "he_presence": p2.get("he_presence", False),
        "ex_area": f"{p2['ex_area']:.4f}" if p2.get("ex_area") is not None else "N/A",
    }

    p3 = result.get("phase3") or {}
    sc = p3.get("severity_class")
    display["phase3"] = {
        "severity_class": sc,
        "severity_label": None,
        "probabilities": p3.get("probabilities"),
        "calibrated_probabilities": p3.get("calibrated_probabilities"),
        "confidence": None,
        "referable_decision": p3.get("referable_decision"),
        "grade_alone_decision": p3.get("grade_alone_decision"),
        "fusion_status": p3.get("fusion_status"),
        "fitted": p3.get("fitted"),
        "reason": p3.get("reason"),
    }

    p4 = result.get("phase4") or {}
    display["phase4"] = {
        "label": p4.get("label", "model attention"),
        "heatmap_overlay": _ndarray_to_data_uri(p4.get("heatmap_overlay")),
    }

    return display


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return render_template(
            "index.html",
            display=None,
            startup_report=_STARTUP_REPORT,
        )

    # POST handling
    demo_choice = request.form.get("demo_image")
    file = request.files.get("image")

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

        # Run Phase 1 quality assessment gate
        gate_res = run_quality_gate(temp_path)
        q_label = str(gate_res.get("quality_label", "")).strip().upper()
        is_reject = (q_label == "REJECT")

        result = {
            "phase1": gate_res,
            "stopped_at_phase1": is_reject,
            "error": None,
        }
        display = _prepare_display(result)

        # Read original image for display
        with open(temp_path, "rb") as f:
            ext_mime = "jpeg" if suffix in (".jpg", ".jpeg") else "png"
            orig_b64 = base64.b64encode(f.read()).decode("ascii")
            display["original_image"] = f"data:image/{ext_mime};base64,{orig_b64}"

        return render_template("index.html", display=display, startup_report=_STARTUP_REPORT)

    except Exception as exc:
        logger.exception("Error evaluating fundus image")
        return render_template(
            "index.html",
            display=None,
            upload_error=f"Quality Assessment Error: {type(exc).__name__}: {exc}",
            startup_report=_STARTUP_REPORT,
        )
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                pass


# ---------------------------------------------------------------------------
# Programmatic JSON API Endpoints
# ---------------------------------------------------------------------------

@app.route("/api/quality", methods=["POST"])
def api_quality():
    """
    POST /api/quality
    Programmatic endpoint for Phase 1 EyeQ quality assessment.
    Accepts multipart/form-data with 'image' file, or JSON with 'image_path'.
    """
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

        try:
            with PILImage.open(target_path) as im:
                im.verify()
        except Exception as exc:
            return jsonify({"status": "error", "error": f"Corrupted or invalid image: {exc}"}), 400

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
            "model_info": {
                "name": "EyeQ-EfficientNetB4",
                "ensemble_size": 8,
                "input_size": [520, 520],
                "decision_policy": "argmax",
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
    # If torch is not in host environment, auto-reexec with EyeQ virtualenv
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

    # Pre-warm EyeQ model into memory at startup so user requests are fast
    logger.info("Pre-warming EyeQ Quality Assessment Model...")
    try:
        _svc = get_quality_service()
        logger.info("EyeQ ensemble pre-warmed successfully (%d models in memory).", _svc.ensemble_size)
    except Exception as _init_err:
        logger.warning("EyeQ pre-warming deferred: %s", _init_err)

    print("\n" + "=" * 65)
    print("  NETRA-DR Phase 1 Prototype Server")
    print("  EyeQ Quality Assessment Active")
    print("  Visit: http://127.0.0.1:5000")
    print("=" * 65 + "\n")
    app.run(host="127.0.0.1", port=5000, debug=False)
