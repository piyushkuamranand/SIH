"""
app/app.py — NETRA-DR Prototype Web Server

Routes:
  GET  /            → Upload interface
  POST /            → Runs the full four-phase pipeline (pipeline.report.run_full_pipeline)
                       on the uploaded / demo fundus image and renders the results page
  POST /api/grade   → JSON API for automated/programmatic full-pipeline screening
  GET  /api/status  → Health and per-model readiness status

Flow:
  USER UPLOADS FUNDUS IMAGE
          ↓
  INPUT VALIDATION
          ↓
  PHASE 1 — Quality Gate  (Reject → halt, ask for recapture)
          ↓
  PHASE 2 — Retinal Structure Analysis (vessels, HE/EX/SE, MA)
          ↓
  PHASE 3 — DR Grading (ICDR 0–4) + Calibration + Decision Fusion
          ↓
  PHASE 4 — Explainability ("model attention" heatmap)
          ↓
  Single results page

Any phase whose model artifact is not yet delivered shows as "unavailable" in
the UI (pipeline.report.run_full_pipeline never fabricates a missing result) —
it does not crash the request.
"""

from __future__ import annotations

import base64
import io
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
from pipeline.report import run_full_pipeline

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024  # 32 MB upload limit

# Model readiness check (does not block startup — missing models show as
# "unavailable" per-phase in the UI, per docs/HANDOFF.md).
_STARTUP_REPORT = run_startup_check(verbose=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
DEMO_IMAGES = {
    "good": PROJECT_ROOT / "data" / "demo" / "good_sample.jpg",
    "reject": PROJECT_ROOT / "data" / "demo" / "reject_sample.jpg",
    "grade0": PROJECT_ROOT / "data" / "demo" / "aptos_grade0_0d0b8fc9ab5c.png",
    "grade2": PROJECT_ROOT / "data" / "demo" / "aptos_grade2_025a169a0bb0.png",
    "grade4": PROJECT_ROOT / "data" / "demo" / "aptos_grade4_875a2fc5fe23.png",
}

ICDR_LABELS = {
    0: "No DR",
    1: "Mild NPDR",
    2: "Moderate NPDR",
    3: "Severe NPDR",
    4: "Proliferative DR",
}


def _allowed(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def _ndarray_to_data_uri(image: Optional[np.ndarray]) -> str:
    """Convert an HWC uint8/float RGB numpy array to a base64-encoded PNG data URI."""
    if image is None:
        return ""
    if np.issubdtype(image.dtype, np.floating):
        image = (np.clip(image, 0.0, 1.0) * 255.0).astype(np.uint8)
    pil = PILImage.fromarray(image, mode="RGB")
    buf = io.BytesIO()
    pil.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def _get_recommendation(quality_label: Optional[str]) -> Dict[str, str]:
    lbl = (quality_label or "").upper()
    if lbl == "REJECT":
        return {
            "title": "Recapture Advised",
            "action": "HALT",
            "badge_class": "badge-reject",
            "summary": "Screening pipeline halted. The image has poor quality (severe blur, underexposure, or obscuration).",
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
    elif lbl == "GOOD":
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
    else:
        return {
            "title": "Quality Assessment Unavailable",
            "action": "UNKNOWN",
            "badge_class": "badge-borderline",
            "summary": "Quality could not be determined.",
            "guidance": "",
        }


def _prepare_display(result: dict) -> dict:
    """Prepare pipeline.report.run_full_pipeline() output for template rendering."""
    display: Dict[str, Any] = {
        "stopped_at_phase1": result.get("stopped_at_phase1", False),
        "error": result.get("error"),
        "startup_report": _STARTUP_REPORT,
    }

    # ---- Phase 1 ----
    p1 = result.get("phase1") or {}
    q_label = p1.get("quality_label")
    q_score = p1.get("quality_score")
    probs = p1.get("probabilities") or {}
    recommendation = _get_recommendation(q_label)

    display["phase1"] = {
        "available": q_label is not None,
        "quality_label": q_label,
        "quality_score": f"{q_score:.1%}" if q_score is not None else None,
        "confidence_float": q_score,
        "probabilities": {
            "good": round(probs.get("good", 0.0) * 100, 1),
            "borderline": round(probs.get("borderline", probs.get("uncertain", 0.0)) * 100, 1),
            "reject": round(probs.get("reject", probs.get("bad", 0.0)) * 100, 1),
        },
        "reasons": p1.get("reasons") or [],
        "measured": p1.get("measured") or {},
        "model_name": p1.get("model_name", "unknown"),
        "preprocessed_image": _ndarray_to_data_uri(p1.get("preprocessed_image")),
        "recommendation": recommendation,
    }

    # ---- Phase 2 (each lesion type gets its own card/image — never merged) ----
    p2 = result.get("phase2") or {}

    def _mask_to_display(mask):
        """Single-channel 0/255 mask -> viewable RGB data URI (white-on-black)."""
        if mask is None:
            return ""
        rgb = np.stack([mask, mask, mask], axis=-1).astype(np.uint8)
        return _ndarray_to_data_uri(rgb)

    display["phase2"] = {
        "vessel_overlay": _ndarray_to_data_uri(p2.get("vessel_overlay")),
        "vessel_available": p2.get("vessel_mask") is not None,
        "he_mask_img": _mask_to_display(p2.get("he_mask")),
        "ex_mask_img": _mask_to_display(p2.get("ex_mask")),
        "se_mask_img": _mask_to_display(p2.get("se_mask")),
        "lesion_overlay": _ndarray_to_data_uri(p2.get("lesion_overlay")),
        "lesion_available": p2.get("he_mask") is not None,
        "ma_overlay": _ndarray_to_data_uri(p2.get("ma_overlay")),
        "ma_available": p2.get("ma_overlay") is not None,
        "ma_count": p2.get("ma_count", 0),
        "he_presence": p2.get("he_presence", False),
        "he_pixel_count": int((p2.get("he_mask") > 0).sum()) if p2.get("he_mask") is not None else None,
        "ex_area": f"{p2['ex_area']:.4f}" if p2.get("ex_area") is not None else "N/A",
        "ex_pixel_count": int((p2.get("ex_mask") > 0).sum()) if p2.get("ex_mask") is not None else None,
        "se_pixel_count": int((p2.get("se_mask") > 0).sum()) if p2.get("se_mask") is not None else None,
        # Neovascularization is out of the trained scope for this build (FGADR-only per
        # the project spec, FGADR not downloaded) — always report unavailable, never fabricate.
        "nv_available": False,
    }

    # ---- Phase 3 ----
    p3 = result.get("phase3") or {}
    sc = p3.get("severity_class")
    cal_probs = p3.get("calibrated_probabilities")
    display["phase3"] = {
        "available": sc is not None,
        "severity_class": sc,
        "severity_label": ICDR_LABELS.get(sc) if sc is not None else None,
        "probabilities": p3.get("probabilities"),
        "probabilities_pct": (
            [round(float(p) * 100, 1) for p in p3["probabilities"]] if p3.get("probabilities") else None
        ),
        "calibrated_probabilities": cal_probs,
        "calibrated_probabilities_pct": (
            [round(float(p) * 100, 1) for p in cal_probs] if cal_probs else None
        ),
        "confidence": (f"{p3['confidence']:.1%}" if p3.get("confidence") is not None else None),
        "referable_decision": p3.get("referable_decision"),
        "grade_alone_decision": p3.get("grade_alone_decision"),
        "decisions_agree": (
            p3.get("referable_decision") == p3.get("grade_alone_decision")
            if p3.get("referable_decision") is not None else None
        ),
        "fusion_status": p3.get("fusion_status"),
        "fitted": p3.get("fitted"),
        "reason": p3.get("reason"),
        "model_name": p3.get("model_name"),
        "model_version": p3.get("model_version"),
        "calibration_temperature": p3.get("calibration_temperature"),
        "calibration_fitted": p3.get("calibration_fitted"),
    }

    # ---- Phase 4 ----
    p4 = result.get("phase4") or {}
    display["phase4"] = {
        "available": p4.get("heatmap_overlay") is not None,
        "label": p4.get("label", "model attention"),
        "heatmap_overlay": _ndarray_to_data_uri(p4.get("heatmap_overlay")),
        "cam_mode": p4.get("cam_mode"),
        "is_class_specific": p4.get("is_class_specific"),
    }

    # ---- Uncertainty (honest — single model per stage, no ensemble anywhere) ----
    display["uncertainty"] = {
        "ensemble_available": False,
        "status": "Single model per stage — no deterministic ensemble trained. "
                  "Confidence above is calibrated probability, not an ensemble-spread uncertainty estimate.",
    }

    # ---- Timings (measured, never estimated) ----
    timings = result.get("timings") or {}
    display["timings"] = {k: round(v * 1000, 1) for k, v in timings.items()}  # ms

    return display


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return render_template(
            "index.html",
            display=None,
            startup_report=_STARTUP_REPORT,
        )

    demo_choice = request.form.get("demo_image")
    file = request.files.get("image")

    temp_path: Optional[str] = None
    suffix = ".jpg"
    original_filename = "unknown"

    try:
        if demo_choice in DEMO_IMAGES and DEMO_IMAGES[demo_choice].is_file():
            source_path = DEMO_IMAGES[demo_choice]
            suffix = source_path.suffix.lower() or ".jpg"
            original_filename = source_path.name
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                shutil.copyfile(source_path, tmp.name)
                temp_path = tmp.name
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
            original_filename = file.filename
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                file.save(tmp.name)
                temp_path = tmp.name

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

        with PILImage.open(temp_path) as dims_img:
            original_width, original_height = dims_img.size

        # ---- Run the full four-phase pipeline ----
        result = run_full_pipeline(temp_path)
        display = _prepare_display(result)
        display["intake"] = {
            "filename": original_filename,
            "width": original_width,
            "height": original_height,
        }

        with open(temp_path, "rb") as f:
            ext_mime = "jpeg" if suffix in (".jpg", ".jpeg") else "png"
            orig_b64 = base64.b64encode(f.read()).decode("ascii")
            display["original_image"] = f"data:image/{ext_mime};base64,{orig_b64}"

        return render_template("index.html", display=display, startup_report=_STARTUP_REPORT)

    except Exception as exc:
        logger.exception("Error running pipeline")
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
# Programmatic JSON API endpoints
# ---------------------------------------------------------------------------

@app.route("/api/grade", methods=["POST"])
def api_grade():
    """
    POST /api/grade
    Programmatic endpoint running the full four-phase pipeline.
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

        result = run_full_pipeline(str(target_path))
        p1, p3, p4 = result.get("phase1") or {}, result.get("phase3") or {}, result.get("phase4") or {}

        response_payload = {
            "status": "success",
            "stopped_at_phase1": result.get("stopped_at_phase1", False),
            "error": result.get("error"),
            "quality": {
                "label": p1.get("quality_label"),
                "score": p1.get("quality_score"),
                "reasons": p1.get("reasons"),
            },
            "grading": {
                "severity_class": p3.get("severity_class"),
                "severity_label": ICDR_LABELS.get(p3.get("severity_class")),
                "calibrated_probabilities": p3.get("calibrated_probabilities"),
                "referable_decision": p3.get("referable_decision"),
                "grade_alone_decision": p3.get("grade_alone_decision"),
                "fitted": p3.get("fitted"),
            },
            "explainability": {
                "label": p4.get("label"),
            },
        }
        return jsonify(response_payload), 200

    except Exception as exc:
        logger.exception("API grade endpoint error")
        return jsonify({"status": "error", "error": f"{type(exc).__name__}: {exc}"}), 500
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                pass


@app.route("/api/status", methods=["GET"])
def api_status():
    """GET /api/status — Check server and per-model readiness."""
    return jsonify({
        "status": "operational",
        "startup_report": _STARTUP_REPORT,
    })


if __name__ == "__main__":
    print("\n" + "=" * 65)
    print("  NETRA-DR Prototype Server")
    print("  Full four-phase pipeline active")
    print("  Visit: http://127.0.0.1:5000")
    print("=" * 65 + "\n")
    app.run(host="127.0.0.1", port=5000, debug=False)
