"""
NETRA-DR: Phase 1 — IQA (Image Quality Assessment) Gate.

Loads the quality-gate classifier via the model contract, runs inference on
the raw fundus image (supporting both PyTorch EyeQ ensemble and ONNX backends),
and returns the quality decision together with the preprocessed
image produced by pipeline.preprocessing.preprocess().

Contract schema required for models/quality/metadata.json (type: classifier):
    model_name, model_version, input_size, channels, normalization, model_file,
    framework, training_dataset, preprocessing, eval_metrics,
    class_labels, output_format, threshold

Raises a clear "model artifact missing" error when the model artifact is not yet
present — it never fabricates a result.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Union

import numpy as np

from pipeline.contract import (
    ModelArtifactNotFoundError,
    ModelContractError,
    load_contract,
    resolve_model_path,
)
from pipeline.preprocessing import preprocess

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers for ONNX inference (backwards compatibility & fallback)
# ---------------------------------------------------------------------------

def _prepare_model_input(
    image_path: Union[str, Path],
    contract: Dict[str, Any],
) -> np.ndarray:
    """
    Resize and normalize the raw image specifically for the quality model,
    using the model contract's own input_size and normalization spec.
    """
    import cv2
    from PIL import Image

    path = Path(image_path)
    if not path.is_file():
        raise FileNotFoundError(f"Input image not found: {path}")

    try:
        with Image.open(path) as pil_img:
            rgb_img = pil_img.convert("RGB")
            raw_arr = np.array(rgb_img, dtype=np.uint8)
    except Exception as exc:
        raise ValueError(
            f"Corrupted, invalid, or unsupported image file: {path}. Details: {exc}"
        ) from exc

    input_size: List[int] = contract["input_size"]
    if len(input_size) != 2:
        raise ValueError(
            f"Contract input_size must be [H, W] (2 elements), got {input_size}"
        )
    target_h, target_w = int(input_size[0]), int(input_size[1])
    resized = cv2.resize(raw_arr, (target_w, target_h), interpolation=cv2.INTER_LINEAR)

    norm_spec = contract["normalization"]
    if isinstance(norm_spec, dict):
        norm_mean = norm_spec.get("mean", [0.0, 0.0, 0.0])
        norm_std  = norm_spec.get("std",  [1.0, 1.0, 1.0])
    else:
        norm_mean = [0.0, 0.0, 0.0]
        norm_std  = [1.0, 1.0, 1.0]

    img_float = resized.astype(np.float32) / 255.0
    mean = np.array(norm_mean, dtype=np.float32).reshape(1, 1, 3)
    std  = np.array(norm_std,  dtype=np.float32).reshape(1, 1, 3)
    img_float = (img_float - mean) / std

    img_nchw = np.transpose(img_float, (2, 0, 1))[np.newaxis, ...]
    return img_nchw.astype(np.float32)


def _run_onnx_inference(
    model_path: str,
    input_array: np.ndarray,
) -> np.ndarray:
    """Run ONNX inference and return raw scores."""
    try:
        import onnxruntime as ort
    except ImportError as exc:
        raise RuntimeError(
            "onnxruntime is not installed. Add it to requirements.txt and run "
            "`pip install onnxruntime`."
        ) from exc

    session = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
    input_name = session.get_inputs()[0].name
    outputs = session.run(None, {input_name: input_array})
    raw = np.array(outputs[0], dtype=np.float32).flatten()
    return raw


def _softmax(logits: np.ndarray) -> np.ndarray:
    """Numerically stable softmax."""
    shifted = logits - logits.max()
    exp = np.exp(shifted)
    return exp / exp.sum()


# ---------------------------------------------------------------------------
# Rule-based IQA baseline (blueprint K.2 / DEC-01 mandatory baseline).
#
# Requires no trained model or labelled dataset: measures focus (Laplacian
# variance inside the detected field of view), illumination (mean level +
# clipped dark/bright pixel fractions), and field-of-view coverage, then
# applies documented threshold rules loaded from the model contract's
# `model_file` (models/quality/iqa_thresholds.json). Every measured value is
# reported in `reasons` so the decision is auditable — nothing is fabricated.
# ---------------------------------------------------------------------------

_FOCUS_CANONICAL_SIZE = (512, 512)  # focus/illumination measured in canonical space — scale-invariant


def _measure_quality_features(raw_rgb: np.ndarray, fov_bg_threshold: int) -> Dict[str, float]:
    """
    Compute deterministic focus / illumination / FOV features for one image.

    FOV area fraction is measured on the raw (native-resolution) frame, since it
    reflects camera framing/centring. Focus (Laplacian variance) and illumination
    are measured after resizing the cropped FOV to a fixed canonical resolution
    (matching pipeline/preprocessing.py's target_size) — raw Laplacian variance is
    resolution-dependent, so comparing it across images of different native sizes
    without this step would bias the reject decision toward smaller source images.
    """
    import cv2

    from pipeline.preprocessing import crop_fov

    gray_full = cv2.cvtColor(raw_rgb, cv2.COLOR_RGB2GRAY)
    fov_mask_full = gray_full > fov_bg_threshold
    total_px = int(gray_full.size)
    fov_px = int(np.count_nonzero(fov_mask_full))
    fov_area_fraction = float(fov_px) / float(total_px) if total_px > 0 else 0.0

    if fov_px == 0:
        # Entire frame below background threshold — cannot measure focus/illumination meaningfully.
        return {
            "fov_area_fraction": 0.0,
            "laplacian_variance": 0.0,
            "mean_intensity": 0.0,
            "dark_clipped_fraction": 1.0,
            "bright_clipped_fraction": 0.0,
        }

    try:
        cropped = crop_fov(raw_rgb, threshold=fov_bg_threshold, margin=0)
    except ValueError:
        cropped = raw_rgb

    canonical = cv2.resize(cropped, _FOCUS_CANONICAL_SIZE, interpolation=cv2.INTER_AREA)
    gray_c = cv2.cvtColor(canonical, cv2.COLOR_RGB2GRAY)
    fov_mask_c = gray_c > fov_bg_threshold
    fov_px_c = int(np.count_nonzero(fov_mask_c))

    if fov_px_c < 2:
        laplacian_variance = 0.0
        mean_intensity = 0.0
        dark_clipped_fraction = 1.0
        bright_clipped_fraction = 0.0
    else:
        fov_pixels_c = gray_c[fov_mask_c]
        laplacian = cv2.Laplacian(gray_c, cv2.CV_64F)
        laplacian_variance = float(np.var(laplacian[fov_mask_c]))
        mean_intensity = float(np.mean(fov_pixels_c))
        dark_clipped_fraction = float(np.count_nonzero(fov_pixels_c < 15)) / float(fov_px_c)
        bright_clipped_fraction = float(np.count_nonzero(fov_pixels_c > 245)) / float(fov_px_c)

    return {
        "fov_area_fraction": fov_area_fraction,
        "laplacian_variance": laplacian_variance,
        "mean_intensity": mean_intensity,
        "dark_clipped_fraction": dark_clipped_fraction,
        "bright_clipped_fraction": bright_clipped_fraction,
    }


def _rule_based_quality_decision(
    features: Dict[str, float],
    thresholds: Dict[str, Any],
) -> Dict[str, Any]:
    """Apply documented threshold rules to measured features. Returns label, score, reasons."""
    fov_cfg = thresholds.get("fov", {})
    focus_cfg = thresholds.get("focus", {})
    illum_cfg = thresholds.get("illumination", {})

    fov_frac = features["fov_area_fraction"]
    lap_var = features["laplacian_variance"]
    mean_i = features["mean_intensity"]
    dark_frac = features["dark_clipped_fraction"]
    bright_frac = features["bright_clipped_fraction"]

    reject_reasons: List[str] = []
    borderline_reasons: List[str] = []

    reject_fov = float(fov_cfg.get("reject_min_area_fraction", 0.28))
    borderline_fov = float(fov_cfg.get("borderline_min_area_fraction", 0.42))
    if fov_frac < reject_fov:
        reject_reasons.append(f"field of view too small ({fov_frac:.1%} of frame, need >= {reject_fov:.0%})")
    elif fov_frac < borderline_fov:
        borderline_reasons.append(f"field of view partially cropped ({fov_frac:.1%} of frame)")

    reject_focus = float(focus_cfg.get("reject_max_laplacian_variance", 25.0))
    borderline_focus = float(focus_cfg.get("borderline_max_laplacian_variance", 90.0))
    if lap_var < reject_focus:
        reject_reasons.append(f"severe blur (focus score {lap_var:.1f}, need >= {reject_focus:.0f})")
    elif lap_var < borderline_focus:
        borderline_reasons.append(f"reduced sharpness (focus score {lap_var:.1f})")

    reject_dark = float(illum_cfg.get("reject_max_dark_clipped_fraction", 0.35))
    reject_bright = float(illum_cfg.get("reject_max_bright_clipped_fraction", 0.20))
    borderline_dark = float(illum_cfg.get("borderline_max_dark_clipped_fraction", 0.15))
    borderline_bright = float(illum_cfg.get("borderline_max_bright_clipped_fraction", 0.08))
    if dark_frac > reject_dark:
        reject_reasons.append(f"severe underexposure ({dark_frac:.1%} of FOV near-black)")
    elif dark_frac > borderline_dark:
        borderline_reasons.append(f"partial underexposure ({dark_frac:.1%} of FOV near-black)")
    if bright_frac > reject_bright:
        reject_reasons.append(f"severe overexposure/glare ({bright_frac:.1%} of FOV near-white)")
    elif bright_frac > borderline_bright:
        borderline_reasons.append(f"partial overexposure/glare ({bright_frac:.1%} of FOV near-white)")

    ideal_lo, ideal_hi = illum_cfg.get("ideal_mean_range", [60, 200])
    slack = float(illum_cfg.get("borderline_mean_slack", 40))
    if mean_i < (float(ideal_lo) - slack) or mean_i > (float(ideal_hi) + slack):
        reject_reasons.append(f"illumination far outside expected range (mean intensity {mean_i:.0f})")
    elif mean_i < ideal_lo or mean_i > ideal_hi:
        borderline_reasons.append(f"illumination slightly outside ideal range (mean intensity {mean_i:.0f})")

    if reject_reasons:
        label = "REJECT"
        reasons = reject_reasons
    elif borderline_reasons:
        label = "BORDERLINE"
        reasons = borderline_reasons
    else:
        label = "GOOD"
        reasons = ["focus, illumination, and field of view all within expected range"]

    # Deterministic composite score in [0, 1]: how far the worst measured
    # criterion sits past its GOOD threshold (a heuristic severity index for
    # display, NOT a calibrated probability — every input value is reported
    # in `reasons` above so the score is always auditable).
    margins = [
        min(1.0, fov_frac / borderline_fov) if borderline_fov > 0 else 1.0,
        min(1.0, lap_var / borderline_focus) if borderline_focus > 0 else 1.0,
        1.0 - min(1.0, dark_frac / max(borderline_dark, 1e-6)),
        1.0 - min(1.0, bright_frac / max(borderline_bright, 1e-6)),
    ]
    composite = float(np.clip(np.mean(margins), 0.0, 1.0))

    if label == "GOOD":
        score = float(np.clip(0.55 + 0.45 * composite, 0.0, 1.0))
        probs = {"good": score, "borderline": (1.0 - score) * 0.7, "reject": (1.0 - score) * 0.3}
    elif label == "BORDERLINE":
        score = float(np.clip(0.45 + 0.20 * composite, 0.35, 0.75))
        probs = {"good": (1.0 - score) * 0.4, "borderline": score, "reject": (1.0 - score) * 0.6}
    else:
        score = float(np.clip(0.55 + 0.35 * (1.0 - composite), 0.35, 0.95))
        probs = {"good": (1.0 - score) * 0.15, "borderline": (1.0 - score) * 0.85, "reject": score}

    total = sum(probs.values())
    probs = {k: v / total for k, v in probs.items()}

    return {
        "quality_label": label,
        "quality_score": score,
        "probabilities": probs,
        "reasons": reasons,
        "measured": features,
    }


def _run_rule_based_quality_gate(image_path: Path, contract: Dict[str, Any], thresholds_path: str) -> Dict[str, Any]:
    """Rule-based IQA inference path — no model artifact, no torch/onnxruntime required."""
    from pipeline.preprocessing import load_image

    with open(thresholds_path, "r", encoding="utf-8") as f:
        thresholds = json.load(f)

    fov_bg_threshold = int(thresholds.get("fov", {}).get("background_intensity_threshold", 10))
    raw_rgb = load_image(image_path)
    features = _measure_quality_features(raw_rgb, fov_bg_threshold)
    decision = _rule_based_quality_decision(features, thresholds)
    return decision


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_quality_gate(
    image_path: Union[str, Path],
    model_dir: Union[str, Path] = "models/quality",
    preprocessing_config: Union[str, Path] = "configs/preprocessing.json",
) -> Dict[str, Any]:
    """
    Phase 1 entry point — assess the quality of a raw fundus image.

    Steps:
    1. Load and validate the quality model contract.
    2. Resolve the model path (raises ModelArtifactNotFoundError if absent).
    3. Run quality inference (using EyeQ PyTorch ensemble or ONNX engine per contract).
    4. Independently call preprocessing.preprocess() to produce the downstream image.

    Args:
        image_path:           Path to the raw fundus image (jpg / png).
        model_dir:            Directory containing quality model artifact + metadata.json.
                              Defaults to 'models/quality' (project-relative).
        preprocessing_config: Path to configs/preprocessing.json used for the downstream
                              preprocessed_image (independent of model input preparation).

    Returns:
        dict with keys:
            quality_label      (str)  — one of the contract's class_labels ("GOOD", "BORDERLINE", "REJECT")
            quality_score      (float)— confidence for the predicted class in [0, 1]
            preprocessed_image (np.ndarray) — float32 array from preprocessing.preprocess()
            probabilities      (dict, optional) — class probability breakdown

    Raises:
        FileNotFoundError:          If metadata.json is missing from model_dir or image not found.
        ModelContractError:         If metadata.json is invalid or incomplete.
        ModelArtifactNotFoundError: If the model file is not present.
        ValueError:                 If the image is corrupted or unreadable.
    """
    model_dir = Path(model_dir)

    # ---- 1. Load and validate contract ----
    try:
        contract = load_contract(model_dir, "classifier")
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            f"model artifact missing — Phase 1 cannot run: "
            f"metadata.json not found in '{model_dir}'. "
            f"(Original error: {exc})"
        ) from exc

    # ---- 2. Resolve model path — fail loudly if absent ----
    try:
        model_path = resolve_model_path(model_dir, contract)
    except ModelArtifactNotFoundError as exc:
        raise ModelArtifactNotFoundError(
            f"model artifact missing — Phase 1 cannot run: "
            f"model file '{contract.get('model_file')}' not found in '{model_dir}'. "
            f"(Original error: {exc})"
        ) from exc

    # Verify input image exists
    img_path = Path(image_path)
    if not img_path.is_file():
        raise FileNotFoundError(f"Input image not found: {img_path}")

    # ---- 3. Inference based on contract framework ----
    framework = str(contract.get("framework", "onnx")).lower()
    reasons: List[str] = []
    measured: Dict[str, float] = {}

    if framework == "rule_based":
        decision = _run_rule_based_quality_gate(img_path, contract, model_path)
        quality_label = decision["quality_label"]
        quality_score = float(decision["quality_score"])
        probabilities = decision["probabilities"]
        reasons = decision["reasons"]
        measured = decision["measured"]
    elif framework == "pytorch":
        from pipeline.quality_service import get_quality_service
        service = get_quality_service()
        pred = service.predict(img_path)
        quality_label = pred["netra_label"]
        quality_score = float(pred["confidence"])
        probabilities = pred.get("netra_probabilities")
    else:
        # ONNX inference path
        model_input = _prepare_model_input(img_path, contract)
        raw_scores = _run_onnx_inference(model_path, model_input)
        probs = _softmax(raw_scores)
        predicted_idx = int(np.argmax(probs))

        class_labels: List[str] = contract["class_labels"]
        if predicted_idx >= len(class_labels):
            raise ValueError(
                f"Model output index {predicted_idx} is out of range for "
                f"class_labels {class_labels} (length {len(class_labels)})."
            )

        quality_label = class_labels[predicted_idx]
        quality_score = float(probs[predicted_idx])
        probabilities = {
            class_labels[i].lower(): float(probs[i])
            for i in range(len(class_labels))
        }

    # ---- 4. Preprocessed image for downstream phases (TASK-003 path) ----
    preprocessed_image: np.ndarray = preprocess(img_path, config_path=preprocessing_config)

    return {
        "quality_label": quality_label,
        "quality_score": quality_score,
        "preprocessed_image": preprocessed_image,
        "probabilities": probabilities,
        "reasons": reasons,
        "measured": measured,
        "model_name": str(contract.get("model_name", "unknown")),
    }
