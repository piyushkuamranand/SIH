"""
NETRA-DR: Phase 1 Deterministic Preprocessing Pipeline.

Implements FOV crop -> resize -> CLAHE -> normalize deterministically for any
input retinal fundus image. No ML models are involved in this module.
All behavior is driven by configs/preprocessing.json.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple, Union

import cv2
import numpy as np
from PIL import Image


def load_config(config_path: Union[str, Path] = "configs/preprocessing.json") -> Dict[str, Any]:
    """
    Load preprocessing configuration from a JSON file.

    Args:
        config_path: Path to the JSON configuration file.

    Returns:
        Dict containing configuration parameters.

    Raises:
        FileNotFoundError: If the configuration file does not exist.
        ValueError: If configuration JSON is malformed.
    """
    path = Path(config_path)
    if not path.is_file():
        raise FileNotFoundError(f"Preprocessing configuration file not found: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Corrupted or invalid JSON in preprocessing config {path}: {e}") from e

    if not isinstance(config, dict):
        raise ValueError(f"Preprocessing config must be a JSON object, got {type(config).__name__}")

    return config


def load_image(source: Union[str, Path, np.ndarray, Image.Image]) -> np.ndarray:
    """
    Load and validate an image from file path, numpy array, or PIL Image.
    Returns standard RGB uint8 numpy array with shape (H, W, 3).

    Args:
        source: Image file path, numpy array, or PIL Image.

    Returns:
        RGB uint8 numpy array of shape (H, W, 3).

    Raises:
        FileNotFoundError: If source path does not exist.
        ValueError: If file is corrupted, unreadable, or invalid array.
        TypeError: If source type is unsupported.
    """
    if isinstance(source, (str, Path)):
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"Image file not found: {path}")
        if not path.is_file():
            raise ValueError(f"Provided path is not a regular file: {path}")

        try:
            with Image.open(path) as img:
                img.verify()
            with Image.open(path) as img:
                rgb_img = img.convert("RGB")
                arr = np.array(rgb_img, dtype=np.uint8)
        except Exception as e:
            raise ValueError(
                f"Corrupted, invalid, or unsupported image file: {path}. Details: {e}"
            ) from e

        if arr.size == 0 or arr.ndim != 3 or arr.shape[2] != 3:
            raise ValueError(f"Decoded image has invalid dimensions: {arr.shape}")
        return arr

    if isinstance(source, Image.Image):
        rgb_img = source.convert("RGB")
        arr = np.array(rgb_img, dtype=np.uint8)
        if arr.size == 0:
            raise ValueError("Input PIL Image is empty.")
        return arr

    if isinstance(source, np.ndarray):
        if source.size == 0:
            raise ValueError("Input image array is empty.")

        # Convert float to uint8 if scaled [0, 1]
        arr = source
        if np.issubdtype(arr.dtype, np.floating):
            if arr.max() <= 1.0 and arr.min() >= 0.0:
                arr = (arr * 255.0).round().astype(np.uint8)
            else:
                arr = np.clip(arr, 0, 255).astype(np.uint8)
        elif arr.dtype != np.uint8:
            arr = np.clip(arr, 0, 255).astype(np.uint8)

        if arr.ndim == 2:
            return cv2.cvtColor(arr, cv2.COLOR_GRAY2RGB)
        elif arr.ndim == 3:
            if arr.shape[2] == 1:
                return cv2.cvtColor(arr, cv2.COLOR_GRAY2RGB)
            elif arr.shape[2] == 3:
                return arr.copy()
            elif arr.shape[2] == 4:
                # RGBA -> RGB
                return arr[:, :, :3].copy()
            else:
                raise ValueError(
                    f"Unsupported number of image channels: {arr.shape[2]} (expected 1, 3, or 4)"
                )
        else:
            raise ValueError(f"Unsupported image array dimensions: {arr.ndim} (expected 2 or 3)")

    raise TypeError(
        f"Unsupported image input type: {type(source).__name__}. Expected str, Path, np.ndarray, or PIL.Image."
    )


def crop_fov(image: np.ndarray, threshold: int = 10, margin: int = 0) -> np.ndarray:
    """
    Crop the image to the circular field-of-view (FOV) bounding box, removing black borders.

    Args:
        image: RGB uint8 image array (H, W, 3).
        threshold: Intensity threshold below which pixels are considered background.
        margin: Optional pixel margin around the detected bounding box.

    Returns:
        Cropped RGB image array.

    Raises:
        ValueError: If no pixels exceed the threshold (image entirely black / empty FOV).
    """
    if image.size == 0:
        raise ValueError("Cannot crop empty image.")

    # Grayscale representation for mask detection
    if image.ndim == 3 and image.shape[2] == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    elif image.ndim == 2:
        gray = image
    else:
        gray = image[:, :, 0]

    mask = gray > threshold
    if not np.any(mask):
        raise ValueError(
            f"Image contains no detectable fundus field of view (all pixels below threshold {threshold})."
        )

    y_indices, x_indices = np.where(mask)
    ymin, ymax = int(y_indices.min()), int(y_indices.max())
    xmin, xmax = int(x_indices.min()), int(x_indices.max())

    h, w = image.shape[:2]
    ymin = max(0, ymin - margin)
    ymax = min(h, ymax + 1 + margin)
    xmin = max(0, xmin - margin)
    xmax = min(w, xmax + 1 + margin)

    return image[ymin:ymax, xmin:xmax]


def resize(image: np.ndarray, target_size: Sequence[int]) -> np.ndarray:
    """
    Resize image to the target size (height, width).

    Args:
        image: Image array.
        target_size: Sequence of (height, width).

    Returns:
        Resized image array of shape (height, width, channels) or (height, width).

    Raises:
        ValueError: If target_size is invalid.
    """
    if len(target_size) != 2:
        raise ValueError(f"target_size must have 2 elements [height, width], got {target_size}")
    target_h, target_w = int(target_size[0]), int(target_size[1])
    if target_h <= 0 or target_w <= 0:
        raise ValueError(f"target_size dimensions must be positive, got ({target_h}, {target_w})")

    curr_h, curr_w = image.shape[:2]
    if curr_h == target_h and curr_w == target_w:
        return image.copy()

    # Use INTER_AREA when downsampling for anti-aliasing; INTER_LINEAR when upsampling
    interp = cv2.INTER_AREA if (target_h < curr_h or target_w < curr_w) else cv2.INTER_LINEAR
    # cv2.resize expects (width, height)
    return cv2.resize(image, (target_w, target_h), interpolation=interp)


def apply_clahe(
    image: np.ndarray,
    clip_limit: float = 2.0,
    tile_grid_size: Sequence[int] = (8, 8),
    channel: str = "L",
) -> np.ndarray:
    """
    Apply Contrast-Limited Adaptive Histogram Equalization (CLAHE).
    For RGB images, applies CLAHE to the Luminance (L) channel in LAB color space
    to enhance local contrast while preserving color balance.

    Args:
        image: RGB uint8 image array (H, W, 3) or grayscale uint8 (H, W).
        clip_limit: Threshold for contrast limiting.
        tile_grid_size: Grid size for histogram equalization (rows, cols).
        channel: Channel to apply CLAHE to ('L' for LAB lightness, 'gray' for single channel).

    Returns:
        Enhanced image array.
    """
    if len(tile_grid_size) != 2:
        raise ValueError(f"tile_grid_size must be a 2-element sequence, got {tile_grid_size}")
    grid_size = (int(tile_grid_size[0]), int(tile_grid_size[1]))
    clahe = cv2.createCLAHE(clipLimit=float(clip_limit), tileGridSize=grid_size)

    if image.ndim == 2:
        return clahe.apply(image)

    if image.ndim == 3 and image.shape[2] == 3:
        # Convert RGB to LAB, equalize L channel, convert back
        lab = cv2.cvtColor(image, cv2.COLOR_RGB2LAB)
        l_chan, a_chan, b_chan = cv2.split(lab)
        cl_chan = clahe.apply(l_chan)
        merged = cv2.merge((cl_chan, a_chan, b_chan))
        return cv2.cvtColor(merged, cv2.COLOR_LAB2RGB)

    raise ValueError(f"Unsupported image shape for CLAHE: {image.shape}")


def normalize(
    image: np.ndarray,
    range_min: float = 0.0,
    range_max: float = 1.0,
    dtype: str = "float32",
) -> np.ndarray:
    """
    Scale image values to [range_min, range_max].

    Args:
        image: Image array (typically uint8 in range [0, 255]).
        range_min: Minimum value of output range.
        range_max: Maximum value of output range.
        dtype: Output numpy datatype string (e.g. 'float32').

    Returns:
        Normalized image array of specified dtype.
    """
    if range_max <= range_min:
        raise ValueError(f"range_max ({range_max}) must be greater than range_min ({range_min})")

    img_float = image.astype(np.float32)
    # If image is uint8 range (0..255), standard scale
    if image.dtype == np.uint8 or img_float.max() > 1.0:
        scaled = (img_float / 255.0) * (range_max - range_min) + range_min
    else:
        # Already in [0, 1]
        scaled = img_float * (range_max - range_min) + range_min

    scaled = np.clip(scaled, range_min, range_max)
    return scaled.astype(np.dtype(dtype))


def preprocess(
    image: Union[str, Path, np.ndarray, Image.Image],
    config_path: Union[str, Path] = "configs/preprocessing.json",
) -> np.ndarray:
    """
    Execute the full Phase 1 deterministic preprocessing pipeline:
    load -> FOV crop -> resize -> CLAHE -> normalize.

    Args:
        image: Input raw fundus image (file path, numpy array, or PIL Image).
        config_path: Path to preprocessing configuration JSON.

    Returns:
        Preprocessed image array ready for model inference (H, W, 3) in float32.

    Raises:
        FileNotFoundError: If image file or config file is missing.
        ValueError: If image is corrupted, unreadable, or invalid.
    """
    config = load_config(config_path)

    # 1. Load image to standard RGB uint8
    raw_rgb = load_image(image)

    # 2. Crop circular FOV
    fov_cfg = config.get("fov_crop", {})
    threshold = fov_cfg.get("threshold", 10)
    margin = fov_cfg.get("margin", 0)
    cropped = crop_fov(raw_rgb, threshold=threshold, margin=margin)

    # 3. Resize to target size
    target_size = config.get("target_size", [512, 512])
    resized = resize(cropped, target_size=target_size)

    # 4. Contrast enhancement via CLAHE
    clahe_cfg = config.get("clahe", {})
    clip_limit = clahe_cfg.get("clip_limit", 2.0)
    tile_grid_size = clahe_cfg.get("tile_grid_size", [8, 8])
    channel = clahe_cfg.get("channel", "L")
    enhanced = apply_clahe(
        resized,
        clip_limit=clip_limit,
        tile_grid_size=tile_grid_size,
        channel=channel,
    )

    # 5. Normalize
    norm_cfg = config.get("normalization", {})
    range_vals = norm_cfg.get("range", [0.0, 1.0])
    dtype = norm_cfg.get("dtype", "float32")
    preprocessed_image = normalize(
        enhanced,
        range_min=float(range_vals[0]),
        range_max=float(range_vals[1]),
        dtype=dtype,
    )

    return preprocessed_image
