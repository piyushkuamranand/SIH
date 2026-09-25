"""
pipeline/structure.py — NETRA-DR Phase 2: Retinal Structure Analysis

This module grows over three tasks:
  TASK-006  run_vessel_segmentation()   — vessel U-Net mask + overlay
  TASK-007  run_lesion_segmentation()   — HE/EX/SE masks + overlay
  TASK-008  run_ma_detection()          — microaneurysm count + overlay

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


# ---------------------------------------------------------------------------
# TASK-008: MA Detection — Internal helpers
# ---------------------------------------------------------------------------

def _extract_candidates_tophat(
    preprocessed_image: "np.ndarray",
    disk_radius: int = 6,
    threshold_factor: float = 2.0,
) -> list:
    """
    Step A — classical candidate extraction using morphological top-hat transform.

    Applies a circular structuring element of ``disk_radius`` pixels to the green
    channel (index 1, most informative for MAs in fundus images), then thresholds
    the residual at ``mean + threshold_factor * std`` to produce candidate centre
    points.  This is the black-hat variant (closing minus original), which highlights
    dark blobs on a bright background — the typical MA appearance in fundus images.

    Args:
        preprocessed_image: HWC float32 or uint8 image (RGB or float [0,1]).
        disk_radius:        Radius of the circular structuring element (pixels).
                            Caller reads from contract[tophat_disk_radius].
        threshold_factor:   Threshold = mean + factor * std of the top-hat image.
                            Caller reads from contract[tophat_threshold_factor].

    Returns:
        List of (row, col) integer tuples for each MA candidate centre.
    """
    import cv2

    if preprocessed_image.dtype == np.float32:
        img_uint8 = (np.clip(preprocessed_image, 0.0, 1.0) * 255.0).astype(np.uint8)
    else:
        img_uint8 = preprocessed_image.astype(np.uint8)

    # Green channel (index 1 in RGB) has highest MA contrast
    green = img_uint8[:, :, 1]

    # Black-hat highlights dark blobs smaller than the structuring element
    kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (2 * disk_radius + 1, 2 * disk_radius + 1)
    )
    tophat_img = cv2.morphologyEx(green, cv2.MORPH_BLACKHAT, kernel)

    # Adaptive threshold: pixels above mean + factor * std
    mean_val = float(np.mean(tophat_img))
    std_val  = float(np.std(tophat_img))
    cutoff   = mean_val + threshold_factor * std_val
    binary   = (tophat_img.astype(np.float32) >= cutoff).astype(np.uint8) * 255

    # Label connected components; take centroids as candidate locations
    n_labels, _labels, _stats, centroids = cv2.connectedComponentsWithStats(
        binary, connectivity=8
    )

    candidates: list = []
    for label_idx in range(1, n_labels):  # skip background label 0
        cx = int(round(float(centroids[label_idx][0])))
        cy = int(round(float(centroids[label_idx][1])))
        candidates.append((cy, cx))  # (row, col)

    return candidates


def _extract_candidates_matched_filter(
    preprocessed_image: "np.ndarray",
    sigma: float = 1.0,
    threshold_factor: float = 2.0,
) -> list:
    """
    Step A — classical candidate extraction using a 2-D Gaussian matched filter.

    Convolves the green channel with a small 2-D Gaussian kernel (approximating
    the expected MA blob profile) and thresholds the response at
    ``mean + threshold_factor * std``.

    Args:
        preprocessed_image: HWC float32 or uint8 image (RGB or float [0,1]).
        sigma:              Gaussian sigma in pixels.
                            Caller reads from contract[matched_filter_sigma].
        threshold_factor:   Threshold = mean + factor * std of the filter response.
                            Caller reads from contract[matched_filter_threshold_factor].

    Returns:
        List of (row, col) integer tuples for each MA candidate centre.
    """
    import cv2

    if preprocessed_image.dtype == np.float32:
        green = preprocessed_image[:, :, 1]
    else:
        green = preprocessed_image[:, :, 1].astype(np.float32) / 255.0

    # Invert so dark blobs become bright peaks for the Gaussian filter
    inverted = 1.0 - green

    # Gaussian matched filter approximates correlation with a Gaussian MA template
    ksize = int(round(6 * sigma)) | 1  # ensure odd kernel size
    filtered = cv2.GaussianBlur(inverted, (ksize, ksize), sigmaX=sigma, sigmaY=sigma)

    mean_val = float(np.mean(filtered))
    std_val  = float(np.std(filtered))
    cutoff   = mean_val + threshold_factor * std_val
    binary   = (filtered >= cutoff).astype(np.uint8) * 255

    n_labels, _labels, _stats, centroids = cv2.connectedComponentsWithStats(
        binary, connectivity=8
    )

    candidates: list = []
    for label_idx in range(1, n_labels):
        cx = int(round(float(centroids[label_idx][0])))
        cy = int(round(float(centroids[label_idx][1])))
        candidates.append((cy, cx))  # (row, col)

    return candidates


def _prepare_patch_input(
    preprocessed_image: "np.ndarray",
    row: int,
    col: int,
    patch_size: int,
    contract: "Dict[str, Any]",
) -> "np.ndarray | None":
    """
    Extract and normalise a square patch around a candidate point for the CNN FP-reducer.

    Args:
        preprocessed_image: HWC float32 source image.
        row, col:           Candidate centre coordinates.
        patch_size:         Side length of the square patch in pixels.
        contract:           Validated MA-detector contract dict (provides normalization).

    Returns:
        NCHW float32 numpy array of shape (1, C, patch_size, patch_size) ready for ONNX,
        or None if the patch would extend outside the image boundary.
    """
    import cv2

    h, w = preprocessed_image.shape[:2]
    half  = patch_size // 2

    r0, r1 = row - half, row + half
    c0, c1 = col - half, col + half

    # Discard candidates too close to the image border
    if r0 < 0 or r1 > h or c0 < 0 or c1 > w:
        return None

    patch = preprocessed_image[r0:r1, c0:c1, :].copy()

    if patch.shape[0] != patch_size or patch.shape[1] != patch_size:
        if preprocessed_image.dtype == np.float32:
            patch_u8 = (np.clip(patch, 0.0, 1.0) * 255.0).astype(np.uint8)
        else:
            patch_u8 = patch.astype(np.uint8)
        patch_u8 = cv2.resize(
            patch_u8, (patch_size, patch_size), interpolation=cv2.INTER_LINEAR
        )
        patch = patch_u8.astype(np.float32) / 255.0
    elif preprocessed_image.dtype != np.float32:
        patch = patch.astype(np.float32) / 255.0

    # Apply contract normalization
    norm_spec = contract.get("normalization", {})
    if isinstance(norm_spec, dict):
        norm_mean = norm_spec.get("mean", [0.0, 0.0, 0.0])
        norm_std  = norm_spec.get("std",  [1.0, 1.0, 1.0])
    else:
        norm_mean = [0.0, 0.0, 0.0]
        norm_std  = [1.0, 1.0, 1.0]

    mean = np.array(norm_mean, dtype=np.float32).reshape(1, 1, 3)
    std  = np.array(norm_std,  dtype=np.float32).reshape(1, 1, 3)
    patch = (patch - mean) / std

    # HWC -> NCHW
    return np.transpose(patch, (2, 0, 1))[np.newaxis, ...].astype(np.float32)


def _draw_ma_overlay(
    preprocessed_image: "np.ndarray",
    ma_locations: list,
    dot_color: tuple = (0, 0, 255),
    dot_radius: int = 5,
) -> "np.ndarray":
    """
    Draw detected MA candidate locations as coloured dots on the image.

    Args:
        preprocessed_image: HWC float32 or uint8 source image (RGB or float [0,1]).
        ma_locations:       List of (row, col) tuples for each confirmed MA centre.
        dot_color:          BGR colour for the MA dots (default: red).
        dot_radius:         Radius of each drawn circle in pixels.

    Returns:
        HWC uint8 BGR image with MA locations marked.
    """
    import cv2

    if preprocessed_image.dtype == np.float32:
        base_bgr = cv2.cvtColor(
            (np.clip(preprocessed_image, 0.0, 1.0) * 255.0).astype(np.uint8),
            cv2.COLOR_RGB2BGR,
        )
    else:
        base_bgr = cv2.cvtColor(preprocessed_image.astype(np.uint8), cv2.COLOR_RGB2BGR)

    result = base_bgr.copy()
    for (row, col) in ma_locations:
        cv2.circle(
            result, center=(col, row), radius=dot_radius,
            color=dot_color, thickness=2, lineType=cv2.LINE_AA,
        )

    return result


# ---------------------------------------------------------------------------
# TASK-008: MA Detection — Public API
# ---------------------------------------------------------------------------

def run_ma_detection(
    preprocessed_image: np.ndarray,
    model_dir: Union[str, Path] = "models/ma_detector",
) -> Dict[str, Any]:
    """
    Phase 2 — microaneurysm (MA) detection (two-stage hybrid approach).

    Stage A — Classical candidate extraction:
        Implements the method named in contract["candidate_extraction_method"].
        Supported methods:
          "top_hat"        — morphological black-hat transform on the green channel.
          "matched_filter" — 2-D Gaussian correlation on the inverted green channel.
        The method is selected strictly from the contract — never silently overridden.

    Stage B — CNN false-positive reducer:
        For each candidate location, a square patch of size contract["patch_size"]
        (default 32) is extracted and run through the ONNX model given in
        contract["fp_reducer_model_file"].  Only candidates whose predicted class
        matches contract["ma_positive_class_index"] (default 1) are kept as true MAs.

    ma_count is the integer count of candidates surviving Stage B.
    ma_overlay marks each confirmed MA location on the image as a red circle.

    All parameters (patch size, disk radius, Gaussian sigma, threshold factors,
    positive class index) are read from the contract — no magic numbers are
    hardcoded in this function.

    Args:
        preprocessed_image: HWC float32 numpy array from
                            pipeline.preprocessing.preprocess(). Values should
                            be in [0, 1] or the contract normalised range.
        model_dir:          Directory containing the FP-reducer ONNX model and
                            metadata.json.  Defaults to models/ma_detector
                            (project-relative).

    Returns:
        dict with keys:
            ma_count   (int)                     — count of detected MAs (>= 0)
            ma_overlay (np.ndarray, uint8, HWC)  — BGR image with MA locations marked

    Raises:
        FileNotFoundError:          If metadata.json is missing from model_dir.
        ModelContractError:         If metadata.json is invalid or incomplete.
        ModelArtifactNotFoundError: If the ONNX FP-reducer model file is not yet present.
        ValueError:                 If preprocessed_image has an unexpected shape,
                                    or if candidate_extraction_method is unsupported.
    """
    model_dir = Path(model_dir)

    # ---- 1. Load and validate contract ----
    try:
        contract = load_contract(model_dir, "ma_detector")
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            f"model artifact missing — Phase 2 MA detection cannot run: "
            f"metadata.json not found in '{model_dir}'. "
            f"(Original error: {exc})"
        ) from exc

    # ---- 2. Resolve FP-reducer ONNX model path — fail loudly if absent ----
    # The MA detector contract uses 'fp_reducer_model_file' (a mandatory contract
    # field for ma_detector type) rather than the generic 'model_file'.
    fp_reducer_filename: str = contract["fp_reducer_model_file"]
    fp_reducer_path = model_dir / fp_reducer_filename
    if not fp_reducer_path.is_file():
        raise ModelArtifactNotFoundError(
            f"model artifact missing — Phase 2 MA detection cannot run: "
            f"FP-reducer ONNX model '{fp_reducer_filename}' not found in '{model_dir}'. "
            f"Deliver the MATLAB-exported ONNX artifact to complete Phase 2."
        )

    if preprocessed_image.ndim != 3:
        raise ValueError(
            f"preprocessed_image must be a 3-D HWC array, "
            f"got shape {preprocessed_image.shape}"
        )

    # ---- 3. Step A — classical candidate extraction ----
    method: str = contract["candidate_extraction_method"].strip().lower()

    if method == "top_hat":
        disk_radius      = int(contract.get("tophat_disk_radius", 6))
        threshold_factor = float(contract.get("tophat_threshold_factor", 2.0))
        candidates = _extract_candidates_tophat(
            preprocessed_image,
            disk_radius=disk_radius,
            threshold_factor=threshold_factor,
        )
    elif method == "matched_filter":
        sigma            = float(contract.get("matched_filter_sigma", 1.0))
        threshold_factor = float(contract.get("matched_filter_threshold_factor", 2.0))
        candidates = _extract_candidates_matched_filter(
            preprocessed_image,
            sigma=sigma,
            threshold_factor=threshold_factor,
        )
    else:
        raise ValueError(
            f"Unsupported candidate_extraction_method "
            f"'{contract['candidate_extraction_method']}' "
            f"in contract at '{model_dir / 'metadata.json'}'. "
            f"Supported methods: 'top_hat', 'matched_filter'."
        )

    # ---- 4. Step B — CNN FP-reducer on each candidate patch ----
    patch_size:         int = int(contract.get("patch_size", 32))
    positive_class_idx: int = int(contract.get("ma_positive_class_index", 1))

    true_ma_locations: list = []

    for (row, col) in candidates:
        patch_input = _prepare_patch_input(
            preprocessed_image, row, col, patch_size, contract
        )
        if patch_input is None:
            # Candidate too close to image border — skip, do not fabricate
            continue

        raw_out = _run_onnx_inference(str(fp_reducer_path), patch_input)

        output_format: str = contract.get("output_format", "softmax").lower()
        if output_format == "softmax":
            probs = raw_out.flatten()
        elif output_format in ("sigmoid", "logits"):
            probs = 1.0 / (1.0 + np.exp(-raw_out.flatten()))
        else:
            probs = raw_out.flatten()

        if len(probs) > positive_class_idx:
            predicted_class = int(np.argmax(probs))
        else:
            # Single-output: treat as MA probability
            predicted_class = 1 if float(probs[0]) >= 0.5 else 0

        if predicted_class == positive_class_idx:
            true_ma_locations.append((row, col))

    # ---- 5. Build output ----
    ma_count:   int           = len(true_ma_locations)
    ma_overlay: np.ndarray    = _draw_ma_overlay(preprocessed_image, true_ma_locations)

    return {
        "ma_count":   ma_count,
        "ma_overlay": ma_overlay,
    }
