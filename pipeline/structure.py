"""
pipeline/structure.py — NETRA-DR Phase 2: Retinal Structure Analysis

This module grows over three tasks:
  TASK-006  run_vessel_segmentation()   — vessel U-Net mask + overlay
  TASK-007  run_lesion_segmentation()   — HE/EX/SE masks + overlay
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


# ---------------------------------------------------------------------------
# TASK-007: Lesion Segmentation — Internal helper
# ---------------------------------------------------------------------------

def _draw_lesion_overlay(
    preprocessed_image: np.ndarray,
    he_mask: np.ndarray,
    ex_mask: np.ndarray,
    se_mask: np.ndarray,
    alpha: float = 0.45,
) -> np.ndarray:
    """
    Composite three lesion masks onto the source image as distinctly-coloured
    semi-transparent overlays.

    Colour assignments (BGR):
        HE (Haemorrhages)      — red   (0,   0,   255)
        EX (Hard Exudates)     — yellow(0,   200, 255)
        SE (Soft Exudates/CWS) — blue  (255, 100, 0  )

    Pixels that belong to more than one mask class are drawn in the colour of
    the last class applied (SE > EX > HE, since later writes overwrite), which
    is acceptable at hackathon-prototype fidelity.

    Args:
        preprocessed_image: HWC float32 or uint8 source image (RGB or float [0,1]).
        he_mask:  HW uint8 binary mask (0 / 255) for haemorrhages.
        ex_mask:  HW uint8 binary mask (0 / 255) for hard exudates.
        se_mask:  HW uint8 binary mask (0 / 255) for soft exudates / cotton-wool spots.
        alpha:    Blend factor for masked pixels (0 = invisible, 1 = solid colour).

    Returns:
        HWC uint8 BGR image with lesion overlay applied.
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

    # BGR colours — deliberately distinct so all three classes are visually separable
    _LESION_COLORS = {
        "HE": (0,   0,   255),   # red
        "EX": (0,   200, 255),   # yellow
        "SE": (255, 100, 0),     # blue-orange
    }

    for mask, color in (
        (he_mask, _LESION_COLORS["HE"]),
        (ex_mask, _LESION_COLORS["EX"]),
        (se_mask, _LESION_COLORS["SE"]),
    ):
        mask_bool = mask > 0
        overlay[mask_bool] = color

    result = cv2.addWeighted(base_bgr, 1.0 - alpha, overlay, alpha, 0)
    return result


# ---------------------------------------------------------------------------
# TASK-007: Lesion Segmentation — Public API
# ---------------------------------------------------------------------------

def run_lesion_segmentation(
    preprocessed_image: np.ndarray,
    model_dir: Union[str, Path] = "models/lesion_seg",
) -> Dict[str, Any]:
    """
    Phase 2 — lesion segmentation (HE / EX / SE).

    Loads the HE/EX/SE multi-channel segmentation ONNX model via the model
    contract, runs inference on the preprocessed image, and returns three
    separate binary masks plus derived scalar features used downstream by
    Phase 3's decision fusion.

    Lesion reporting follows the project specification strictly:
      - HE, EX, and SE are returned as separate binary masks (never merged).
      - ``he_presence`` is a boolean: True if any HE pixel exceeds the noise
        threshold defined in the contract (field ``he_presence_threshold``,
        default 50 positive pixels if absent).
      - ``ex_area`` is the normalised fraction of image area covered by the EX
        mask (positive pixels / total pixels, float in [0, 1]).
      - No lesion subtypes (flame / dot-blot / deep) are invented or reported.

    The label order (which channel of the model output maps to HE, EX, SE) is
    read from ``contract["mask_labels"]`` — it is never assumed in code.

    Steps:
      1. Load and validate the segmentation contract from metadata.json.
      2. Resolve the ONNX artifact path (raises ModelArtifactNotFoundError if absent).
      3. Prepare NCHW input from the preprocessed image using contract input_size
         and normalization — the contract is authoritative, not a hardcoded value.
      4. Run ONNX inference.  The model is expected to output a tensor of shape
         (1, N_classes, H, W) where N_classes == len(mask_labels).
      5. For each label in mask_labels, threshold the corresponding output channel
         into a binary mask and resize to the preprocessed image's spatial dims.
      6. Compute ``he_presence`` and ``ex_area`` from the HE / EX masks.
      7. Composite the three masks into a single coloured display overlay.

    Args:
        preprocessed_image: HWC float32 numpy array from
                            pipeline.preprocessing.preprocess(). Values should
                            be in [0, 1] or the contract's normalised range.
        model_dir:          Directory containing lesion_seg.onnx + metadata.json.
                            Defaults to 'models/lesion_seg' (project-relative).

    Returns:
        dict with keys:
            he_mask        (np.ndarray, uint8, HW)  — binary mask, 0 or 255
            ex_mask        (np.ndarray, uint8, HW)  — binary mask, 0 or 255
            se_mask        (np.ndarray, uint8, HW)  — binary mask, 0 or 255
            he_presence    (bool)                   — True if HE pixels exceed threshold
            ex_area        (float)                  — EX coverage fraction [0, 1]
            lesion_overlay (np.ndarray, uint8, HWC) — BGR image with mask overlay

    Raises:
        FileNotFoundError:          If metadata.json is missing from model_dir.
        ModelContractError:         If metadata.json is invalid or incomplete.
        ModelArtifactNotFoundError: If the ONNX model file is not yet present.
        ValueError:                 If preprocessed_image has an unexpected shape,
                                    or if mask_labels is missing required lesion types.
    """
    model_dir = Path(model_dir)

    # ---- 1. Load and validate contract ----
    try:
        contract = load_contract(model_dir, "segmentation")
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            f"model artifact missing — Phase 2 lesion segmentation cannot run: "
            f"metadata.json not found in '{model_dir}'. "
            f"(Original error: {exc})"
        ) from exc

    # ---- 2. Resolve ONNX model path — fail loudly if absent ----
    try:
        model_path = resolve_model_path(model_dir, contract)
    except ModelArtifactNotFoundError as exc:
        raise ModelArtifactNotFoundError(
            f"model artifact missing — Phase 2 lesion segmentation cannot run: "
            f"ONNX model file '{contract.get('model_file')}' not found in '{model_dir}'. "
            f"Deliver the MATLAB-exported ONNX artifact to complete Phase 2. "
            f"(Original error: {exc})"
        ) from exc

    if preprocessed_image.ndim != 3:
        raise ValueError(
            f"preprocessed_image must be a 3-D HWC array, got shape {preprocessed_image.shape}"
        )

    original_hw = (preprocessed_image.shape[0], preprocessed_image.shape[1])

    # ---- 3. Read mask_labels from contract — never assume the order ----
    mask_labels: List[str] = contract["mask_labels"]
    # Normalise to upper-case for case-insensitive matching
    mask_labels_upper = [lbl.upper() for lbl in mask_labels]

    # We need HE, EX, SE channels.  Check that all three are present.
    for required in ("HE", "EX", "SE"):
        if required not in mask_labels_upper:
            raise ValueError(
                f"Contract mask_labels {mask_labels} does not contain required "
                f"lesion label '{required}'. Check models/lesion_seg/metadata.json."
            )

    idx_he = mask_labels_upper.index("HE")
    idx_ex = mask_labels_upper.index("EX")
    idx_se = mask_labels_upper.index("SE")

    # ---- 4. Prepare model input ----
    model_input = _prepare_segmentation_input(preprocessed_image, contract)

    # ---- 5. ONNX inference ----
    raw_output = _run_onnx_inference(model_path, model_input)
    # Expected output shape: (1, N_classes, H, W)
    if raw_output.ndim == 4:
        # Shape: (1, N_classes, H, W)
        raw_output = raw_output[0]  # -> (N_classes, H, W)
    elif raw_output.ndim == 3 and raw_output.shape[0] == len(mask_labels):
        pass  # already (N_classes, H, W)
    else:
        raise ValueError(
            f"Unexpected lesion model output shape {raw_output.shape}; "
            f"expected (1, {len(mask_labels)}, H, W) or ({len(mask_labels)}, H, W). "
            "Check metadata.json output_format."
        )

    # ---- Per-channel threshold for each lesion class ----
    # Use a single threshold field if present; the contract doesn't currently
    # define per-class thresholds, so we fall back to 0.5 (probability midpoint).
    threshold: float = float(contract.get("threshold", 0.5))

    def _channel_to_mask(channel_idx: int) -> np.ndarray:
        """Extract one channel, threshold it, and resize to original image dims."""
        channel = raw_output[channel_idx]              # (H, W)
        channel_4d = channel[np.newaxis, np.newaxis]   # (1, 1, H, W)
        return _threshold_to_binary_mask(channel_4d, threshold, original_hw)

    he_mask = _channel_to_mask(idx_he)
    ex_mask = _channel_to_mask(idx_ex)
    se_mask = _channel_to_mask(idx_se)

    # ---- 6. Compute scalar features ----
    # he_presence: True if the number of positive HE pixels exceeds a noise
    # threshold.  Read from contract field 'he_presence_threshold' (int, pixel
    # count).  Default: 50 pixels.  This avoids magic numbers in code.
    he_noise_threshold: int = int(contract.get("he_presence_threshold", 50))
    he_presence: bool = bool(int(np.sum(he_mask > 0)) >= he_noise_threshold)

    # ex_area: normalised fraction of image pixels covered by EX mask [0, 1].
    # Documented choice: pixel fraction rather than raw count, so the value is
    # scale-invariant and directly comparable across different input resolutions.
    total_pixels: int = original_hw[0] * original_hw[1]
    ex_area: float = float(np.sum(ex_mask > 0)) / float(total_pixels)

    # ---- 7. Composite overlay ----
    lesion_overlay = _draw_lesion_overlay(
        preprocessed_image, he_mask, ex_mask, se_mask
    )

    return {
        "he_mask":       he_mask,
        "ex_mask":       ex_mask,
        "se_mask":       se_mask,
        "he_presence":   he_presence,
        "ex_area":       ex_area,
        "lesion_overlay": lesion_overlay,
    }
