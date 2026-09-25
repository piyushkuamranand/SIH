"""
pipeline/grading.py — NETRA-DR Phase 3: DR Grading Model Integration
Rewritten 2026-09-26: loads from REAL native checkpoints, no ONNX expected.

Primary grader:
  drdetect GradingModule (EfficientNet-B0) loaded from
  best.ckpt cached at:
    ~/.cache/huggingface/hub/models--adarshcod30--drdetect-dr-screening/
  Source code:
    netra-dr-models/Diabetic-Retinopathy-Detection/src/drdetect/

NOTE: sakshamkr1/ResNet50-APTOS-DR returns 404 on HuggingFace — that model ID
does not exist.  The EfficientNet-B0 drdetect model is the only trained grader
available.  The GRADER_BACKEND config toggle is preserved but both values
("resnet50", "efficientnet_b0") now route to the same drdetect checkpoint
until a valid ResNet-50 APTOS-DR model is located.

Temperature calibration (apply_calibration) is unchanged.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------

_VENV_SITE   = Path(r"C:\Users\PIYUSH KUMAR\netra-dr-models\venv\Lib\site-packages")
_DRDETECT_SRC = Path(
    r"C:\Users\PIYUSH KUMAR\netra-dr-models\Diabetic-Retinopathy-Detection\src"
)

_BEST_CKPT = Path(
    r"C:\Users\PIYUSH KUMAR\.cache\huggingface\hub"
    r"\models--adarshcod30--drdetect-dr-screening"
    r"\snapshots\f1ad9f790312cec657782f097f499e9bda5755fa"
    r"\best.ckpt"
)

# Input resolution the drdetect EfficientNet-B0 was trained on
_DRDETECT_INPUT_H = 512
_DRDETECT_INPUT_W = 512

# ImageNet normalisation (what timm EfficientNet-B0 pretrained uses)
_IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
_IMAGENET_STD  = np.array([0.229, 0.224, 0.225], dtype=np.float32)

_PATHS_INJECTED = False


def _ensure_venv_packages() -> None:
    import sys
    global _PATHS_INJECTED
    if _PATHS_INJECTED:
        return
    for p in [str(_VENV_SITE), str(_DRDETECT_SRC)]:
        if p not in sys.path:
            sys.path.insert(0, p)
    _PATHS_INJECTED = True


# ---------------------------------------------------------------------------
# drdetect model loader (cached singleton)
# ---------------------------------------------------------------------------

_cached_module = None


def _load_drdetect_module():
    """
    Load the drdetect GradingModule from best.ckpt.

    Uses GradingModule.load_from_checkpoint() which re-creates the
    EfficientNet-B0 backbone from the hyperparameters saved in the checkpoint.
    """
    global _cached_module
    if _cached_module is not None:
        return _cached_module

    _ensure_venv_packages()

    if not _BEST_CKPT.is_file():
        raise FileNotFoundError(
            f"drdetect best.ckpt not found at expected cache path: {_BEST_CKPT}\n"
            "Run:\n"
            "  from huggingface_hub import hf_hub_download\n"
            "  hf_hub_download('adarshcod30/drdetect-dr-screening', 'best.ckpt')\n"
            "to re-download."
        )

    try:
        from drdetect.grading.module import GradingModule
        from drdetect.grading.model import build_model
    except ImportError as exc:
        raise ImportError(
            f"Cannot import drdetect.grading.module. "
            f"Check that {_DRDETECT_SRC} is on sys.path. Error: {exc}"
        ) from exc

    import torch
    backbone = build_model("efficientnet_b0", num_outputs=1, pretrained=False)
    module = GradingModule.load_from_checkpoint(
        str(_BEST_CKPT),
        model=backbone,
        map_location="cpu",
        strict=True,
    )
    module.eval()
    logger.info("drdetect GradingModule loaded from %s", _BEST_CKPT.name)
    _cached_module = module
    return module


# ---------------------------------------------------------------------------
# Preprocessing for drdetect EfficientNet-B0
# ---------------------------------------------------------------------------

from pipeline.contract import (
    ModelArtifactNotFoundError,
    ModelContractError,
    load_contract,
    resolve_model_path,
)


def _prepare_grading_input(
    image: Union[np.ndarray, str, Path],
    contract: Optional[Dict[str, Any]] = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Resize and normalise an input image for grading.

    Input:  HWC numpy (float32 [0,1] or uint8 [0,255]), or file path.
    Output: Tuple of (NCHW float32 numpy, raw_arr HWC uint8).
    """
    import cv2
    from PIL import Image as PILImage

    if isinstance(image, (str, Path)):
        img_path = Path(image)
        if not img_path.is_file():
            raise FileNotFoundError(f"Input image not found: {img_path}")
        try:
            with PILImage.open(img_path) as pil_img:
                raw_arr = np.array(pil_img.convert("RGB"), dtype=np.uint8)
        except Exception as exc:
            raise ValueError(
                f"Corrupted or unsupported image file: {img_path}. Details: {exc}"
            ) from exc
    elif isinstance(image, np.ndarray):
        if image.ndim != 3 or image.shape[2] != 3:
            raise ValueError(
                f"preprocessed_image must be HWC with 3 channels, got {image.shape}"
            )
        if image.dtype == np.float32 or image.dtype == np.float64:
            raw_arr = (np.clip(image, 0.0, 1.0) * 255.0).astype(np.uint8)
        else:
            raw_arr = np.clip(image, 0, 255).astype(np.uint8)
    else:
        raise ValueError(f"Expected np.ndarray, str, or Path; got {type(image).__name__}")

    if contract is not None:
        input_size = contract.get("input_size", [_DRDETECT_INPUT_H, _DRDETECT_INPUT_W])
        target_h, target_w = int(input_size[0]), int(input_size[1])
        norm_spec = contract.get("normalization", {})
        norm_mean = norm_spec.get("mean", _IMAGENET_MEAN.tolist()) if isinstance(norm_spec, dict) else _IMAGENET_MEAN.tolist()
        norm_std = norm_spec.get("std", _IMAGENET_STD.tolist()) if isinstance(norm_spec, dict) else _IMAGENET_STD.tolist()
        mean_arr = np.array(norm_mean, dtype=np.float32).reshape(1, 1, 3)
        std_arr = np.array(norm_std, dtype=np.float32).reshape(1, 1, 3)
    else:
        target_h, target_w = _DRDETECT_INPUT_H, _DRDETECT_INPUT_W
        mean_arr, std_arr = _IMAGENET_MEAN, _IMAGENET_STD

    resized = cv2.resize(raw_arr, (target_w, target_h), interpolation=cv2.INTER_LINEAR)
    img_float = resized.astype(np.float32) / 255.0
    img_float = (img_float - mean_arr) / std_arr

    # HWC -> NCHW
    nchw = np.transpose(img_float, (2, 0, 1))[np.newaxis, ...].astype(np.float32)
    return nchw, raw_arr


def _softmax(logits: np.ndarray) -> np.ndarray:
    """Numerically stable softmax for 1D logits."""
    shifted = logits - np.max(logits)
    exp = np.exp(shifted)
    return exp / np.sum(exp)


# ---------------------------------------------------------------------------
# Public API — run_grading
# ---------------------------------------------------------------------------

def run_grading(
    preprocessed_image: Union[np.ndarray, str, Path],
    model_dir: Union[str, Path] = "models/grading",
) -> Dict[str, Any]:
    """
    Phase 3 DR grading inference.

    Executes grading inference to predict ICDR severity (0–4) and class probability distribution.
    Supports ONNX model contracts and native PyTorch checkpoints.

    Args:
        preprocessed_image: HWC float32/uint8 numpy array or path to image.
        model_dir:          Directory containing metadata.json or model checkpoints.

    Returns:
        dict with:
            severity_class (int)         — argmax of probabilities
            probabilities  (List[float]) — raw uncalibrated 5-class probabilities
            model_name     (str)         — model architecture identifier
            model_version  (str)         — model version string
            class_labels   (List[str])   — ICDR class label strings
            metadata       (dict)        — model metadata dictionary

    Raises:
        FileNotFoundError: If model_dir has no metadata.json or image file does not exist.
        ModelContractError: If contract metadata.json is invalid or missing required fields.
        ModelArtifactNotFoundError: If the ONNX model artifact specified in contract does not exist.
        ValueError: If preprocessed_image has invalid dimensions or type.
    """
    model_dir_path = Path(model_dir)
    has_metadata = (model_dir_path / "metadata.json").is_file()
    is_custom_dir = (str(model_dir) != "models/grading" and str(model_dir) != "models\\grading")

    # If a custom model_dir is provided or metadata.json exists, follow model contract rules
    if is_custom_dir or has_metadata:
        if not has_metadata:
            raise FileNotFoundError(
                f"model artifact missing — Phase 3 metadata.json not found in '{model_dir_path}'"
            )
        contract = load_contract(model_dir_path, model_type="classifier")
        try:
            model_path = resolve_model_path(model_dir_path, contract)
        except ModelArtifactNotFoundError as exc:
            raise ModelArtifactNotFoundError(
                f"model artifact missing — Phase 3 model file '{contract.get('model_file')}' not found in '{model_dir_path}'"
            ) from exc

        inp, _ = _prepare_grading_input(preprocessed_image, contract=contract)

        try:
            import onnxruntime as ort
            session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
            input_name = session.get_inputs()[0].name
            outputs = session.run(None, {input_name: inp})
            raw = np.asarray(outputs[0]).squeeze()
        except Exception as exc:
            if not isinstance(exc, (ModelContractError, ModelArtifactNotFoundError, FileNotFoundError)):
                logger.debug("ONNX session failed (%s)", exc)
            raise

        out_fmt = str(contract.get("output_format", "softmax")).lower()
        if "logit" in out_fmt:
            probabilities = _softmax(raw)
        else:
            if np.isclose(float(np.sum(raw)), 1.0, atol=1e-2):
                probabilities = raw
            else:
                probabilities = _softmax(raw)

        if probabilities.ndim != 1 or len(probabilities) != 5:
            if probabilities.ndim == 0 or len(probabilities) == 1:
                grade_pred = float(np.clip(float(probabilities), 0.0, 4.0))
                sigma = 0.6
                classes = np.arange(5, dtype=np.float32)
                dist_sq = (classes - grade_pred) ** 2
                unnorm_probs = np.exp(-0.5 * dist_sq / (sigma ** 2))
                probabilities = unnorm_probs / np.sum(unnorm_probs)
            else:
                p5 = np.zeros(5, dtype=np.float32)
                p5[:min(5, len(probabilities))] = probabilities[:5]
                probabilities = p5 / max(float(p5.sum()), 1e-8)

        probs_list = [float(p) for p in probabilities]
        severity_class = int(np.argmax(probs_list))
        class_labels = contract.get("class_labels", ["0", "1", "2", "3", "4"])
        metadata_out = dict(contract)
        if "backbone" not in metadata_out:
            metadata_out["backbone"] = str(contract.get("model_name", "dr_grading"))

        return {
            "severity_class": severity_class,
            "probabilities":  probs_list,
            "model_name":     str(contract.get("model_name", "dr_grading")),
            "model_version":  str(contract.get("model_version", "1.0.0")),
            "class_labels":   class_labels,
            "metadata":       metadata_out,
        }

    # Default model_dir: Load native PyTorch drdetect GradingModule
    _ensure_venv_packages()
    import torch

    module = _load_drdetect_module()
    inp, _ = _prepare_grading_input(preprocessed_image)

    inp_tensor = torch.from_numpy(inp)
    with torch.inference_mode():
        logits = module(inp_tensor)  # (1, num_classes)

    raw = logits.squeeze(0).float().cpu().numpy()  # (num_classes,)

    num_classes = raw.shape[0]
    if num_classes == 5:
        probabilities = _softmax(raw)
    elif num_classes == 1:
        grade_pred = float(np.clip(raw[0], 0.0, 4.0))
        sigma = 0.6
        classes = np.arange(5, dtype=np.float32)
        dist_sq = (classes - grade_pred) ** 2
        unnorm_probs = np.exp(-0.5 * dist_sq / (sigma ** 2))
        probabilities = unnorm_probs / np.sum(unnorm_probs)
    else:
        probabilities = _softmax(raw)
        if len(probabilities) != 5:
            p5 = np.zeros(5, dtype=np.float32)
            p5[:min(5, len(probabilities))] = probabilities[:5]
            probabilities = p5 / p5.sum()

    severity_class = int(np.argmax(probabilities))
    class_labels = ["0", "1", "2", "3", "4"]

    return {
        "severity_class": severity_class,
        "probabilities":  [float(p) for p in probabilities],
        "model_name":     "EfficientNet-B0 (drdetect/adarshcod30)",
        "model_version":  "best.ckpt",
        "class_labels":   class_labels,
        "metadata": {
            "backbone":         "efficientnet_b0",
            "model_version":    "best.ckpt",
            "framework":        "pytorch_lightning",
            "training_dataset": "EyePACS / drdetect",
            "output_format":    "softmax",
            "ckpt_path":        str(_BEST_CKPT),
        },
    }


# ---------------------------------------------------------------------------
# apply_calibration — unchanged logic, no model dependency
# ---------------------------------------------------------------------------

def apply_calibration(
    probabilities: Union[List[float], np.ndarray],
    temperature: Optional[float] = None,
    config_path: Union[str, Path] = "configs/calibration.json",
) -> Dict[str, Any]:
    """
    Apply temperature scaling to raw grading probabilities.

    T=1.0 → no-op (identity).
    T>1.0 → soften distribution (reduce peak probability).
    T<1.0 → sharpen distribution (increase peak probability).

    Args:
        probabilities: 1D array/list of raw probabilities (5 ICDR classes).
        temperature:   Scalar T > 0. If None, read from config_path.
        config_path:   Path to calibration.json.

    Returns:
        dict with:
            calibrated_probabilities (List[float])
            confidence               (float) — max calibrated probability
            temperature              (float)
            fitted                   (bool)
    """
    probs = np.asarray(probabilities, dtype=np.float64)
    if probs.ndim != 1 or len(probs) == 0:
        raise ValueError("probabilities must be a non-empty 1D array or list.")
    if np.any(probs < 0.0):
        raise ValueError(f"All probabilities must be non-negative, got {probabilities}.")

    prob_sum = float(np.sum(probs))
    if prob_sum <= 0.0:
        raise ValueError("Sum of probabilities must be strictly positive.")
    norm_probs = probs / prob_sum

    if temperature is None:
        cfg_file = Path(config_path)
        if cfg_file.is_file():
            with open(cfg_file, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            temp_val  = float(cfg.get("temperature", 1.0))
            is_fitted = bool(cfg.get("fitted", False))
        else:
            temp_val  = 1.0
            is_fitted = False
    else:
        temp_val  = float(temperature)
        cfg_file  = Path(config_path)
        is_fitted = (temp_val != 1.0)
        if cfg_file.is_file():
            try:
                with open(cfg_file, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                if float(cfg.get("temperature", 1.0)) == temp_val:
                    is_fitted = bool(cfg.get("fitted", False))
            except Exception:
                pass

    if temp_val <= 0.0:
        raise ValueError(f"Temperature must be strictly positive (> 0), got {temp_val}.")

    if np.isclose(temp_val, 1.0):
        calibrated = norm_probs.astype(np.float32)
    else:
        eps = 1e-12
        logits = np.log(np.clip(norm_probs, eps, 1.0))
        scaled = logits / temp_val
        shifted = scaled - np.max(scaled)
        exp = np.exp(shifted)
        calibrated = (exp / np.sum(exp)).astype(np.float32)

    return {
        "calibrated_probabilities": [float(p) for p in calibrated],
        "confidence":               float(np.max(calibrated)),
        "temperature":              float(temp_val),
        "fitted":                   is_fitted,
    }
