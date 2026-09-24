"""
pipeline/structure.py — NETRA-DR Phase 2: Retinal Structure Analysis

This module grows over three tasks:
  TASK-006  run_vessel_segmentation()   — vessel U-Net mask + overlay
  TASK-007  run_lesion_segmentation()   — HE/EX/SE masks + overlay (added later)
  TASK-008  run_ma_detection()          — microaneurysm count + overlay (added later)

All functions load their model via pipeline.contract.load_contract() and
resolve the artifact path via pipeline.contract.resolve_model_path().
No image size, normalization value, mask label, or threshold is hardcoded
in this file; all such values are read from the model's metadata.json.

Missing-model behaviour: each function raises a clear, specific error
(ModelArtifactNotFoundError or FileNotFoundError) rather than fabricating
any result.  This is the contract working as intended, not a bug.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Union

import numpy as np

from pipeline.contract import (
    ModelArtifactNotFoundError,
    ModelContractError,
    load_contract,
    resolve_model_path,
)


# ---------------------------------------------------------------------------
# Internal helpers shared across structure functions
# ---------------------------------------------------------------------------

def _run_onnx_inference(model_path: str, input_array: np.ndarray) -> np.ndarray:
    """
    Run ONNX inference and return the raw output array.

    Args:
        model_path:  Path to the .onnx model file.
        input_array: NCHW float32 numpy array (1, C, H, W).

    Returns:
        numpy array — raw model output (shape depends on model type).

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
    return np.array(outputs[0], dtype=np.float32)


def _prepare_segmentation_input(
    preprocessed_image: np.ndarray,
    contract: Dict[str, Any],
) -> np.ndarray:
    """
    Resize and normalize a preprocessed image to the segmentation model's
    expected input shape, using values from the contract.

    Args:
        preprocessed_image: HWC float32 array from pipeline.preprocessing.preprocess().
        contract:           Validated contract dict for the segmentation model.

    Returns:
        NCHW float32 numpy array (1, C, H, W) ready for ONNX inference.

    Raises:
        ValueError: If input_size in contract is not a 2-element list or the
                    image has an unexpected number of channels.
    """
    import cv2

    input_size: List[int] = contract["input_size"]
    if len(input_size) != 2:
        raise ValueError(
            f"Contract input_size must be [H, W] (2 elements), got {input_size}"
        )
    target_h, target_w = int(input_size[0]), int(input_size[1])

    # If the image is already float in [0,1], convert back to uint8 for cv2.resize
    if preprocessed_image.dtype == np.float32:
        img_uint8 = (np.clip(preprocessed_image, 0.0, 1.0) * 255.0).astype(np.uint8)
    else:
        img_uint8 = preprocessed_image.astype(np.uint8)

    resized = cv2.resize(img_uint8, (target_w, target_h), interpolation=cv2.INTER_LINEAR)

    # Normalize per contract spec
    norm_spec = contract.get("normalization", {})
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

    # HWC -> NCHW
    img_nchw = np.transpose(img_float, (2, 0, 1))[np.newaxis, ...]
    return img_nchw.astype(np.float32)


def _threshold_to_binary_mask(
    raw_output: np.ndarray,
    threshold: float,
    original_hw: tuple,
) -> np.ndarray:
    """
    Threshold model output probabilities into a binary mask and resize
    back to the original image's spatial dimensions.

    Args:
        raw_output:  Float32 array; shape may be (1, 1, H, W) or (1, H, W) or (H, W).
        threshold:   Probability threshold above which a pixel is foreground.
        original_hw: (height, width) of the original preprocessed image.

    Returns:
        Binary uint8 mask of shape (original_H, original_W), values 0 or 255.
    """
    import cv2

    # Squeeze batch and channel dims to get (H, W)
    squeezed = raw_output.squeeze()
    if squeezed.ndim != 2:
        raise ValueError(
            f"After squeezing, segmentation output has shape {squeezed.shape}; "
            "expected 2-D (H, W). Check model output_format in metadata.json."
        )

    binary = (squeezed >= threshold).astype(np.uint8) * 255

    orig_h, orig_w = original_hw
    if binary.shape != (orig_h, orig_w):
        binary = cv2.resize(binary, (orig_w, orig_h), interpolation=cv2.INTER_NEAREST)

    return binary


def _draw_vessel_overlay(
    preprocessed_image: np.ndarray,
    vessel_mask: np.ndarray,
    overlay_color: tuple = (0, 255, 0),
    alpha: float = 0.4,
) -> np.ndarray:
    """
    Draw the vessel mask as a semi-transparent coloured overlay on the image.

    The base image is converted to uint8 BGR for display.  Mask pixels are
    blended with ``overlay_color`` at opacity ``alpha``; non-mask pixels are
    unchanged.

    Args:
        preprocessed_image: HWC float32 or uint8 source image.
        vessel_mask:        HW binary mask (values 0 or 255).
        overlay_color:      BGR colour for the vessel overlay (default: green).
        alpha:              Blend factor for mask pixels (0 = invisible, 1 = solid).

    Returns:
        HWC uint8 BGR image with the vessel overlay applied.
    """
    import cv2

    # Convert source to uint8 BGR
    if preprocessed_image.dtype == np.float32:
        base_bgr = cv2.cvtColor(
            (np.clip(preprocessed_image, 0.0, 1.0) * 255.0).astype(np.uint8),
            cv2.COLOR_RGB2BGR,
        )
    else:
        base_bgr = cv2.cvtColor(preprocessed_image.astype(np.uint8), cv2.COLOR_RGB2BGR)

    overlay = base_bgr.copy()
    mask_bool = vessel_mask > 0

    # Fill mask region with overlay_color
    overlay[mask_bool] = overlay_color

    # Blend overlay with base
    result = cv2.addWeighted(base_bgr, 1.0 - alpha, overlay, alpha, 0)
    return result


# ---------------------------------------------------------------------------
# TASK-006: Vessel Segmentation — Public API
# ---------------------------------------------------------------------------

def run_vessel_segmentation(
    preprocessed_image: np.ndarray,
    model_dir: Union[str, Path] = "models/vessel_seg",
) -> Dict[str, Any]:
    """
    Phase 2 — vessel segmentation.

    Loads the vessel U-Net ONNX model via the model contract, runs inference
    on the preprocessed image, and returns a binary vessel mask together with
    a colour overlay suitable for display.

    Steps:
      1. Load and validate the segmentation contract from metadata.json.
      2. Resolve the ONNX artifact path (raises ModelArtifactNotFoundError if absent).
      3. Prepare NCHW input from the preprocessed image using contract input_size
         and normalization — the contract is authoritative, not a hardcoded value.
      4. Run ONNX inference and threshold the output into a binary mask using
         the contract's threshold field (default 0.5 if absent).
      5. Resize the mask back to the preprocessed image's spatial dimensions.
      6. Draw the mask as a coloured overlay on a copy of the image.

    Args:
        preprocessed_image: HWC float32 numpy array from pipeline.preprocessing.preprocess().
                            Values should be in [0, 1] or the contract's normalized range.
        model_dir:          Directory containing vessel_seg.onnx + metadata.json.
                            Defaults to 'models/vessel_seg' (project-relative).

    Returns:
        dict with keys:
            vessel_mask    (np.ndarray, uint8, HW)  — binary mask, 0 or 255
            vessel_overlay (np.ndarray, uint8, HWC) — BGR image with mask overlay

    Raises:
        FileNotFoundError:          If metadata.json is missing from model_dir.
        ModelContractError:         If metadata.json is invalid or incomplete.
        ModelArtifactNotFoundError: If the ONNX model file is not yet present.
        ValueError:                 If preprocessed_image has an unexpected shape.
    """
    model_dir = Path(model_dir)

    # ---- 1. Load and validate contract ----
    try:
        contract = load_contract(model_dir, "segmentation")
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            f"model artifact missing — Phase 2 vessel segmentation cannot run: "
            f"metadata.json not found in '{model_dir}'. "
            f"(Original error: {exc})"
        ) from exc

    # ---- 2. Resolve ONNX model path — fail loudly if absent ----
    try:
        model_path = resolve_model_path(model_dir, contract)
    except ModelArtifactNotFoundError as exc:
        raise ModelArtifactNotFoundError(
            f"model artifact missing — Phase 2 vessel segmentation cannot run: "
            f"ONNX model file '{contract.get('model_file')}' not found in '{model_dir}'. "
            f"Deliver the MATLAB-exported ONNX artifact to complete Phase 2. "
            f"(Original error: {exc})"
        ) from exc

    if preprocessed_image.ndim != 3:
        raise ValueError(
            f"preprocessed_image must be a 3-D HWC array, got shape {preprocessed_image.shape}"
        )

    original_hw = (preprocessed_image.shape[0], preprocessed_image.shape[1])

    # ---- 3. Prepare model input ----
    model_input = _prepare_segmentation_input(preprocessed_image, contract)

    # ---- 4. ONNX inference + threshold ----
    raw_output = _run_onnx_inference(model_path, model_input)

    # Threshold: prefer contract-provided value; fall back to 0.5 for probability outputs
    threshold: float = float(contract.get("threshold", 0.5))

    vessel_mask = _threshold_to_binary_mask(raw_output, threshold, original_hw)

    # ---- 5. Build colour overlay (green vessels on the image copy) ----
    vessel_overlay = _draw_vessel_overlay(preprocessed_image, vessel_mask)

    return {
        "vessel_mask": vessel_mask,
        "vessel_overlay": vessel_overlay,
    }
