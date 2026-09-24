"""
pipeline/grading.py — NETRA-DR Phase 3: DR Grading Model Integration

Loads the diabetic retinopathy grading model (ResNet-50, or backup EfficientNet-B0)
via the model contract, runs ONNX inference on the preprocessed fundus image,
and returns the ICDR 0–4 class probabilities along with the predicted severity class.

Contract schema required for models/grading/metadata.json (type: classifier):
    model_name, model_version, input_size, channels, normalization, model_file,
    framework, training_dataset, preprocessing, eval_metrics,
    class_labels, output_format, threshold

In accordance with NETRA-DR rules:
- No hardcoded image size, normalization parameters, or class lists.
- Fails with a clear "model artifact missing" error when the ONNX file or metadata is missing.
- Returns raw (uncalibrated) probabilities — calibration (temperature scaling) is handled
  in TASK-011.
- Exposes backbone / model metadata so whether ResNet-50 or EfficientNet-B0 ran is visible.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np

from pipeline.contract import (
    ModelArtifactNotFoundError,
    ModelContractError,
    load_contract,
    resolve_model_path,
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _run_onnx_inference(model_path: str, input_array: np.ndarray) -> np.ndarray:
    """
    Run ONNX inference and return the raw output array (probabilities or logits).

    Args:
        model_path:  Path to the .onnx model file.
        input_array: NCHW float32 numpy array (1, C, H, W).

    Returns:
        1-D float32 numpy array of class scores for the single input.

    Raises:
        RuntimeError: If onnxruntime is not installed or inference fails.
    """
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


def _prepare_grading_input(
    image: Union[np.ndarray, str, Path],
    contract: Dict[str, Any],
) -> np.ndarray:
    """
    Resize and normalize an input image specifically for the grading model,
    using the model contract's input_size and normalization specification.

    Args:
        image:    Preprocessed fundus image as HWC numpy array (float32 [0,1] or uint8 [0,255]),
                  or path to image file.
        contract: Validated contract dictionary for the classifier model.

    Returns:
        NCHW float32 numpy array (1, C, H, W) ready for ONNX inference.

    Raises:
        ValueError: If image format/shape is invalid or contract input_size is malformed.
        FileNotFoundError: If image file path is given but does not exist.
    """
    import cv2
    from PIL import Image

    if isinstance(image, (str, Path)):
        img_path = Path(image)
        if not img_path.is_file():
            raise FileNotFoundError(f"Input image not found: {img_path}")
        try:
            with Image.open(img_path) as pil_img:
                rgb_img = pil_img.convert("RGB")
                raw_arr = np.array(rgb_img, dtype=np.uint8)
        except Exception as exc:
            raise ValueError(
                f"Corrupted or unsupported image file: {img_path}. Details: {exc}"
            ) from exc
    elif isinstance(image, np.ndarray):
        if image.ndim != 3 or image.shape[2] != 3:
            raise ValueError(
                f"preprocessed_image must be a 3D HWC array with 3 channels, "
                f"got shape {image.shape}."
            )
        if image.dtype == np.float32 or image.dtype == np.float64:
            raw_arr = (np.clip(image, 0.0, 1.0) * 255.0).astype(np.uint8)
        elif image.dtype == np.uint8:
            raw_arr = image.copy()
        else:
            raw_arr = np.clip(image, 0, 255).astype(np.uint8)
    else:
        raise ValueError(
            f"Expected preprocessed_image as np.ndarray, str, or Path, got {type(image).__name__}."
        )

    # Validate and extract input_size from contract [H, W]
    input_size: List[int] = contract["input_size"]
    if not isinstance(input_size, (list, tuple)) or len(input_size) != 2:
        raise ValueError(
            f"Contract input_size must be [H, W] (2 elements), got {input_size}"
        )
    target_h, target_w = int(input_size[0]), int(input_size[1])

    resized = cv2.resize(raw_arr, (target_w, target_h), interpolation=cv2.INTER_LINEAR)

    # Normalize per contract spec
    norm_spec = contract.get("normalization", {})
    if isinstance(norm_spec, dict):
        norm_mean = norm_spec.get("mean", [0.0, 0.0, 0.0])
        norm_std = norm_spec.get("std", [1.0, 1.0, 1.0])
    else:
        norm_mean = [0.0, 0.0, 0.0]
        norm_std = [1.0, 1.0, 1.0]

    img_float = resized.astype(np.float32) / 255.0
    mean = np.array(norm_mean, dtype=np.float32).reshape(1, 1, 3)
    std = np.array(norm_std, dtype=np.float32).reshape(1, 1, 3)
    img_float = (img_float - mean) / std

    # HWC -> NCHW (1, C, H, W)
    img_nchw = np.transpose(img_float, (2, 0, 1))[np.newaxis, ...]
    return img_nchw.astype(np.float32)


def _softmax(logits: np.ndarray) -> np.ndarray:
    """Numerically stable softmax for 1D logits."""
    shifted = logits - np.max(logits)
    exp = np.exp(shifted)
    return exp / np.sum(exp)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_grading(
    preprocessed_image: Union[np.ndarray, str, Path],
    model_dir: Union[str, Path] = "models/grading",
) -> Dict[str, Any]:
    """
    Phase 3 DR grading inference function.

    Loads the classifier contract, resolves the ONNX grading model,
    runs inference, and returns raw class probabilities and the predicted severity class.

    Args:
        preprocessed_image: HWC float32 or uint8 numpy array, or path to image.
        model_dir:          Directory containing the grading model ONNX + metadata.json.
                            Defaults to 'models/grading' (project-relative).

    Returns:
        dict with keys:
            severity_class (int)        — Predicted ICDR class (0–4), argmax of probabilities
            probabilities  (List[float])— Raw (uncalibrated) probabilities for classes 0–4
            model_name     (str)        — Name of the backbone model executed (e.g. ResNet-50 / EfficientNet-B0)
            model_version  (str)        — Version from contract metadata
            class_labels   (List[str])  — Class labels list from contract (e.g. ['0', '1', '2', '3', '4'])
            metadata       (Dict[str, Any]) — Additional model provenance metadata

    Raises:
        FileNotFoundError:          If metadata.json is missing in model_dir.
        ModelContractError:         If metadata.json is incomplete or invalid.
        ModelArtifactNotFoundError: If the ONNX model artifact cannot be found.
        ValueError:                 If preprocessed_image or contract format is invalid.
    """
    model_dir = Path(model_dir)

    # ---- 1. Load and validate contract (classifier schema) ----
    try:
        contract = load_contract(model_dir, "classifier")
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            f"model artifact missing — Phase 3 cannot run: "
            f"metadata.json not found in '{model_dir}'. "
            f"(Original error: {exc})"
        ) from exc

    # ---- 2. Resolve ONNX model path ----
    try:
        model_path = resolve_model_path(model_dir, contract)
    except ModelArtifactNotFoundError as exc:
        raise ModelArtifactNotFoundError(
            f"model artifact missing — Phase 3 cannot run: "
            f"ONNX model file '{contract.get('model_file')}' not found in '{model_dir}'. "
            f"Deliver the MATLAB-exported ONNX artifact to complete Phase 3. "
            f"(Original error: {exc})"
        ) from exc

    # ---- 3. Prepare model input ----
    model_input = _prepare_grading_input(preprocessed_image, contract)

    # ---- 4. Run ONNX inference ----
    raw_scores = _run_onnx_inference(model_path, model_input)

    # ---- 5. Probabilities computation (raw, uncalibrated) ----
    output_format = str(contract.get("output_format", "softmax")).lower()
    if output_format == "softmax" and np.isclose(float(np.sum(raw_scores)), 1.0, atol=1e-2) and np.all(raw_scores >= 0):
        # Already normalized probabilities from model
        probabilities = raw_scores / np.sum(raw_scores)
    else:
        # Raw logits -> apply softmax
        probabilities = _softmax(raw_scores)

    class_labels: List[str] = contract.get("class_labels", ["0", "1", "2", "3", "4"])
    if len(probabilities) != len(class_labels):
        raise ValueError(
            f"Grading model output dimension ({len(probabilities)}) does not match "
            f"contract class_labels length ({len(class_labels)})."
        )

    severity_class = int(np.argmax(probabilities))

    model_name = str(contract.get("model_name", "unknown"))
    model_version = str(contract.get("model_version", "unknown"))

    return {
        "severity_class": severity_class,
        "probabilities": [float(p) for p in probabilities],
        "model_name": model_name,
        "model_version": model_version,
        "class_labels": [str(lbl) for lbl in class_labels],
        "metadata": {
            "backbone": model_name,
            "model_version": model_version,
            "framework": str(contract.get("framework", "onnx")),
            "training_dataset": str(contract.get("training_dataset", "")),
            "output_format": output_format,
        },
    }


def apply_calibration(
    probabilities: Union[List[float], np.ndarray],
    temperature: Optional[float] = None,
    config_path: Union[str, Path] = "configs/calibration.json",
) -> Dict[str, Any]:
    """
    Apply temperature scaling to raw grading probabilities, producing calibrated confidence.

    Temperature scaling transforms logits z_i = log(p_i) -> z_i / T before re-applying softmax.
    - If temperature == 1.0 (or default unfitted config), calibrated probabilities equal raw probabilities (no-op).
    - If temperature > 1.0, the probability distribution is softened/flattened (max probability decreases).
    - If temperature < 1.0, the probability distribution is sharpened (max probability increases).

    Args:
        probabilities: 1D array or list of raw probabilities (e.g. 5 ICDR classes) from run_grading().
        temperature:   Optional scalar temperature T > 0. If None, loaded from config_path.
        config_path:   Path to calibration.json. Defaults to 'configs/calibration.json'.

    Returns:
        dict with keys:
            calibrated_probabilities (List[float]) — Temperature-scaled class probabilities (summing to 1.0)
            confidence               (float)       — Maximum calibrated probability (primary confidence score)
            temperature              (float)       — Temperature value applied
            fitted                   (bool)        — Whether the temperature value came from a fitted calibration procedure

    Raises:
        ValueError: If probabilities array is invalid, empty, or negative, or if temperature <= 0.
    """
    # 1. Validate probabilities
    probs = np.asarray(probabilities, dtype=np.float64)
    if probs.ndim != 1 or len(probs) == 0:
        raise ValueError("probabilities must be a non-empty 1D array or list.")
    if np.any(probs < 0.0):
        raise ValueError(f"All probabilities must be non-negative, got {probabilities}.")
    
    prob_sum = float(np.sum(probs))
    if prob_sum <= 0.0:
        raise ValueError("Sum of probabilities must be strictly positive.")
    
    # Normalize input probabilities to sum to 1
    norm_probs = probs / prob_sum

    # 2. Determine temperature and fitted status
    if temperature is None:
        cfg_file = Path(config_path)
        if cfg_file.is_file():
            with open(cfg_file, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            temp_val = float(cfg.get("temperature", 1.0))
            is_fitted = bool(cfg.get("fitted", False))
        else:
            temp_val = 1.0
            is_fitted = False
    else:
        temp_val = float(temperature)
        cfg_file = Path(config_path)
        if cfg_file.is_file():
            try:
                with open(cfg_file, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                if float(cfg.get("temperature", 1.0)) == temp_val:
                    is_fitted = bool(cfg.get("fitted", False))
                else:
                    is_fitted = (temp_val != 1.0)
            except Exception:
                is_fitted = (temp_val != 1.0)
        else:
            is_fitted = (temp_val != 1.0)

    if temp_val <= 0.0:
        raise ValueError(f"Temperature must be strictly positive (> 0), got {temp_val}.")

    # 3. Apply temperature scaling
    if np.isclose(temp_val, 1.0):
        calibrated = norm_probs.astype(np.float32)
    else:
        # Safe log of probabilities with epsilon protection
        eps = 1e-12
        clipped_probs = np.clip(norm_probs, eps, 1.0)
        logits = np.log(clipped_probs)
        scaled_logits = logits / temp_val
        calibrated = _softmax(scaled_logits).astype(np.float32)

    confidence = float(np.max(calibrated))

    return {
        "calibrated_probabilities": [float(p) for p in calibrated],
        "confidence": confidence,
        "temperature": float(temp_val),
        "fitted": is_fitted,
    }
