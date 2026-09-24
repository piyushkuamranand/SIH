"""
NETRA-DR: Phase 1 — IQA (Image Quality Assessment) Gate.

Loads the quality-gate classifier via the model contract, runs ONNX inference on
the raw fundus image, and returns the quality decision together with the preprocessed
image produced by pipeline.preprocessing.preprocess().

Contract schema required for models/quality/metadata.json (type: classifier):
    model_name, model_version, input_size, channels, normalization, model_file,
    framework, training_dataset, preprocessing, eval_metrics,
    class_labels, output_format, threshold

Raises a clear "model artifact missing" error when the ONNX file is not yet
present — it never fabricates a result.
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
from pipeline.preprocessing import preprocess


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _prepare_model_input(
    image_path: Union[str, Path],
    contract: Dict[str, Any],
) -> np.ndarray:
    """
    Resize and normalize the raw image specifically for the quality model,
    using the model contract's own input_size and normalization spec.

    The contract is authoritative — these values may differ from the general
    preprocessing config used for downstream phases.

    Args:
        image_path: Path to the raw fundus image.
        contract:   Validated contract dict for the quality model.

    Returns:
        NCHW float32 numpy array ready for ONNX inference, shape (1, C, H, W).

    Raises:
        ValueError: If image loading or normalization parameters are invalid.
        FileNotFoundError: If image_path does not exist.
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

    # Resize to contract input_size [H, W]
    input_size: List[int] = contract["input_size"]
    if len(input_size) != 2:
        raise ValueError(
            f"Contract input_size must be [H, W] (2 elements), got {input_size}"
        )
    target_h, target_w = int(input_size[0]), int(input_size[1])
    resized = cv2.resize(raw_arr, (target_w, target_h), interpolation=cv2.INTER_LINEAR)

    # Normalize using contract spec
    norm_spec = contract["normalization"]
    if isinstance(norm_spec, dict):
        norm_mean = norm_spec.get("mean", [0.0, 0.0, 0.0])
        norm_std  = norm_spec.get("std",  [1.0, 1.0, 1.0])
    else:
        # Fallback: treat as simple [0, 1] scaling
        norm_mean = [0.0, 0.0, 0.0]
        norm_std  = [1.0, 1.0, 1.0]

    img_float = resized.astype(np.float32) / 255.0
    mean = np.array(norm_mean, dtype=np.float32).reshape(1, 1, 3)
    std  = np.array(norm_std,  dtype=np.float32).reshape(1, 1, 3)
    img_float = (img_float - mean) / std

    # HWC -> NCHW
    img_nchw = np.transpose(img_float, (2, 0, 1))[np.newaxis, ...]  # (1, C, H, W)
    return img_nchw.astype(np.float32)


def _run_onnx_inference(
    model_path: str,
    input_array: np.ndarray,
) -> np.ndarray:
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
    # Expect outputs[0] shape (1, N) or (N,) for N classes
    raw = np.array(outputs[0], dtype=np.float32).flatten()
    return raw


def _softmax(logits: np.ndarray) -> np.ndarray:
    """Numerically stable softmax."""
    shifted = logits - logits.max()
    exp = np.exp(shifted)
    return exp / exp.sum()


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
    2. Resolve the ONNX model path (raises ModelArtifactNotFoundError if absent).
    3. Prepare model input from the raw image using contract input_size/normalization.
    4. Run ONNX inference; map output to class_labels from the contract.
    5. Independently call preprocessing.preprocess() to produce the downstream image.

    Args:
        image_path:           Path to the raw fundus image (jpg / png).
        model_dir:            Directory containing quality_model.onnx + metadata.json.
                              Defaults to 'models/quality' (project-relative).
        preprocessing_config: Path to configs/preprocessing.json used for the downstream
                              preprocessed_image (independent of model input preparation).

    Returns:
        dict with keys:
            quality_label      (str)  — one of the contract's class_labels
            quality_score      (float)— confidence for the predicted class in [0, 1]
            preprocessed_image (np.ndarray) — float32 array from preprocessing.preprocess()

    Raises:
        FileNotFoundError:          If metadata.json is missing from model_dir.
        ModelContractError:         If metadata.json is invalid or incomplete.
        ModelArtifactNotFoundError: If the ONNX model file is not yet present.
        FileNotFoundError:          If image_path does not exist.
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

    # ---- 2. Resolve ONNX model path — fail loudly if absent ----
    try:
        model_path = resolve_model_path(model_dir, contract)
    except ModelArtifactNotFoundError as exc:
        raise ModelArtifactNotFoundError(
            f"model artifact missing — Phase 1 cannot run: "
            f"ONNX model file '{contract.get('model_file')}' not found in '{model_dir}'. "
            f"Deliver the MATLAB-exported ONNX artifact to complete Phase 1. "
            f"(Original error: {exc})"
        ) from exc

    # ---- 3. Prepare model input (contract-driven, not config-driven) ----
    model_input = _prepare_model_input(image_path, contract)

    # ---- 4. ONNX inference ----
    raw_scores = _run_onnx_inference(model_path, model_input)
    probabilities = _softmax(raw_scores)
    predicted_idx = int(np.argmax(probabilities))

    class_labels: List[str] = contract["class_labels"]
    if predicted_idx >= len(class_labels):
        raise ValueError(
            f"Model output index {predicted_idx} is out of range for "
            f"class_labels {class_labels} (length {len(class_labels)})."
        )

    quality_label: str = class_labels[predicted_idx]
    quality_score: float = float(probabilities[predicted_idx])

    # ---- 5. Preprocessed image for downstream phases (TASK-003 path) ----
    preprocessed_image: np.ndarray = preprocess(image_path, config_path=preprocessing_config)

    return {
        "quality_label": quality_label,
        "quality_score": quality_score,
        "preprocessed_image": preprocessed_image,
    }
