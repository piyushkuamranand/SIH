"""
pipeline/structure.py — NETRA-DR Phase 2: Retinal Structure Analysis
Rewritten 2026-09-26: loads from REAL native checkpoints, no ONNX expected.

Model sources (authoritative):
  vessel_seg   — FR-UNet PyTorch weights, loaded directly with torch.load
                 from C:/Users/PIYUSH KUMAR/netra-dr-models/FR-UNet/
  lesion_seg   — fundus_lesions_toolkit.models.segment()
                 weights auto-download from HuggingFace on first call
                 (venv at C:/Users/PIYUSH KUMAR/netra-dr-models/venv must be
                  available; the module injects its site-packages into sys.path)
  ma_detection — reads from the fundus_lesions_toolkit MA channel (index 4)
                 plus classical top-hat candidates — no ONNX FP-reducer needed

All three functions must be called with the netra-dr-models venv's Python,
OR run after _ensure_venv_packages() injects the venv site-packages.

Contract / metadata.json files in models/ directories are no longer used;
all parameters come from the repos themselves.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Union

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Venv bootstrapping  — inject netra-dr-models venv packages once
# ---------------------------------------------------------------------------

_VENV_SITE = Path(r"C:\Users\PIYUSH KUMAR\netra-dr-models\venv\Lib\site-packages")
_FRUNET_ROOT = Path(r"C:\Users\PIYUSH KUMAR\netra-dr-models\FR-UNet")
_DRDETECT_SRC = Path(r"C:\Users\PIYUSH KUMAR\netra-dr-models\Diabetic-Retinopathy-Detection\src")
_LESION_SRC = Path(r"C:\Users\PIYUSH KUMAR\netra-dr-models\fundus-lesions-toolkit\src")

_PATHS_INJECTED = False


def _ensure_venv_packages() -> None:
    """Prepend the netra-dr-models venv site-packages to sys.path once and register bunch shim."""
    global _PATHS_INJECTED
    if _PATHS_INJECTED:
        return
    import types
    if "bunch" not in sys.modules:
        class Bunch(dict):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.__dict__ = self
        bunch_mod = types.ModuleType("bunch")
        bunch_mod.Bunch = Bunch
        sys.modules["bunch"] = bunch_mod
    for p in [str(_VENV_SITE), str(_FRUNET_ROOT), str(_DRDETECT_SRC), str(_LESION_SRC)]:
        if p not in sys.path:
            sys.path.insert(0, p)
    _PATHS_INJECTED = True


# ---------------------------------------------------------------------------
# FR-UNet loader
# ---------------------------------------------------------------------------

_FR_UNET_WEIGHT_DIR = _FRUNET_ROOT / "pretrained_weights"
_FR_UNET_DATASETS = ["DRIVE", "CHASEDB1", "CHUAC", "DCA1"]


def _load_fr_unet(dataset: str = "DRIVE") -> "FR_UNet":  # noqa: F821
    """
    Instantiate FR_UNet and load the pretrained checkpoint for *dataset*.

    The model class lives inside netra-dr-models/FR-UNet/models/fr_unet.py.
    We import it after injecting the FR-UNet root into sys.path.
    """
    _ensure_venv_packages()
    import torch

    try:
        from models.fr_unet import FR_UNet  # noqa: E402  (after path injection)
    except ImportError as exc:
        raise ImportError(
            f"Cannot import FR_UNet from {_FRUNET_ROOT}/models/fr_unet.py. "
            f"Check that _FRUNET_ROOT is correct. Error: {exc}"
        ) from exc

    ckpt_path = _FR_UNET_WEIGHT_DIR / dataset / "checkpoint-epoch40.pth"
    if not ckpt_path.is_file():
        raise FileNotFoundError(
            f"FR-UNet pretrained weight not found: {ckpt_path}. "
            f"Available datasets: {_FR_UNET_DATASETS}"
        )

    # FR-UNet was trained on single-channel (green-channel) images
    # num_channels=1, num_classes=1, feature_scale=2 (from config.yaml defaults)
    model = FR_UNet(num_classes=1, num_channels=1, feature_scale=2, dropout=0.2,
                    fuse=True, out_ave=True)

    # Load checkpoint — may be raw state_dict or Lightning-style checkpoint
    ckpt = torch.load(str(ckpt_path), map_location="cpu", weights_only=False)
    if isinstance(ckpt, dict):
        state = ckpt.get("state_dict", ckpt.get("model_state_dict", ckpt))
    else:
        state = ckpt

    # Strip "module." prefix if saved from DataParallel
    cleaned = {k.replace("module.", ""): v for k, v in state.items()}
    missing, unexpected = model.load_state_dict(cleaned, strict=True)
    if missing:
        raise RuntimeError(f"FR-UNet checkpoint missing keys: {missing}")
    if unexpected:
        logger.warning("FR-UNet checkpoint unexpected keys (ignored): %s", unexpected)

    model.eval()
    logger.info("FR-UNet loaded: %s  (dataset=%s)", ckpt_path.name, dataset)
    return model


# ---------------------------------------------------------------------------
# Drawing helpers (unchanged from previous version)
# ---------------------------------------------------------------------------

def _draw_vessel_overlay(
    preprocessed_image: np.ndarray,
    vessel_mask: np.ndarray,
    overlay_color: tuple = (0, 255, 0),
    alpha: float = 0.4,
) -> np.ndarray:
    if preprocessed_image.dtype == np.float32:
        base_bgr = cv2.cvtColor(
            (np.clip(preprocessed_image, 0.0, 1.0) * 255.0).astype(np.uint8),
            cv2.COLOR_RGB2BGR,
        )
    else:
        base_bgr = cv2.cvtColor(preprocessed_image.astype(np.uint8), cv2.COLOR_RGB2BGR)
    overlay = base_bgr.copy()
    overlay[vessel_mask > 0] = overlay_color
    return cv2.addWeighted(base_bgr, 1.0 - alpha, overlay, alpha, 0)


def _draw_lesion_overlay(
    preprocessed_image: np.ndarray,
    he_mask: np.ndarray,
    ex_mask: np.ndarray,
    se_mask: np.ndarray,
    alpha: float = 0.45,
) -> np.ndarray:
    if preprocessed_image.dtype == np.float32:
        base_bgr = cv2.cvtColor(
            (np.clip(preprocessed_image, 0.0, 1.0) * 255.0).astype(np.uint8),
            cv2.COLOR_RGB2BGR,
        )
    else:
        base_bgr = cv2.cvtColor(preprocessed_image.astype(np.uint8), cv2.COLOR_RGB2BGR)
    overlay = base_bgr.copy()
    for mask, color in (
        (he_mask, (0, 0, 255)),    # red   — hemorrhages
        (ex_mask, (0, 200, 255)),  # yellow — exudates
        (se_mask, (255, 100, 0)),  # blue-orange — soft exudates / CWS
    ):
        overlay[mask > 0] = color
    return cv2.addWeighted(base_bgr, 1.0 - alpha, overlay, alpha, 0)


def _draw_ma_overlay(
    preprocessed_image: np.ndarray,
    ma_locations: list,
    dot_color: tuple = (0, 0, 255),
    dot_radius: int = 5,
) -> np.ndarray:
    if preprocessed_image.dtype == np.float32:
        base_bgr = cv2.cvtColor(
            (np.clip(preprocessed_image, 0.0, 1.0) * 255.0).astype(np.uint8),
            cv2.COLOR_RGB2BGR,
        )
    else:
        base_bgr = cv2.cvtColor(preprocessed_image.astype(np.uint8), cv2.COLOR_RGB2BGR)
    result = base_bgr.copy()
    for (row, col) in ma_locations:
        cv2.circle(result, center=(col, row), radius=dot_radius,
                   color=dot_color, thickness=2, lineType=cv2.LINE_AA)
    return result


from pipeline.contract import (
    ModelArtifactNotFoundError,
    ModelContractError,
    load_contract,
    resolve_model_path,
)


def _validate_input_image(image: Union[np.ndarray, str, Path]) -> np.ndarray:
    """Validate input image type and dimensions."""
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
    return raw_arr


# ---------------------------------------------------------------------------
# Classical MA candidate extraction helpers
# ---------------------------------------------------------------------------

def _extract_candidates_tophat(
    preprocessed_image: np.ndarray,
    disk_radius: int = 6,
    threshold_factor: float = 2.0,
) -> list:
    """Black-hat transform on green channel → MA candidate (row, col) list."""
    if preprocessed_image.dtype == np.float32 or preprocessed_image.dtype == np.float64:
        img_uint8 = (np.clip(preprocessed_image, 0.0, 1.0) * 255.0).astype(np.uint8)
    else:
        img_uint8 = preprocessed_image.astype(np.uint8)

    green = img_uint8[:, :, 1]
    kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (2 * disk_radius + 1, 2 * disk_radius + 1)
    )
    tophat_img = cv2.morphologyEx(green, cv2.MORPH_BLACKHAT, kernel)

    mean_val = float(np.mean(tophat_img))
    std_val  = float(np.std(tophat_img))
    cutoff   = mean_val + threshold_factor * std_val
    binary   = (tophat_img.astype(np.float32) >= cutoff).astype(np.uint8) * 255

    n_labels, _labels, _stats, centroids = cv2.connectedComponentsWithStats(
        binary, connectivity=8
    )
    return [
        (int(round(float(centroids[i][1]))), int(round(float(centroids[i][0]))))
        for i in range(1, n_labels)
    ]


def _extract_candidates_matched_filter(
    preprocessed_image: np.ndarray,
    sigma: float = 1.0,
    threshold_factor: float = 2.0,
) -> list:
    """Matched filter on inverted green channel → MA candidate (row, col) list."""
    if preprocessed_image.dtype == np.float32 or preprocessed_image.dtype == np.float64:
        img_uint8 = (np.clip(preprocessed_image, 0.0, 1.0) * 255.0).astype(np.uint8)
    else:
        img_uint8 = preprocessed_image.astype(np.uint8)

    green = img_uint8[:, :, 1].astype(np.float32)
    inverted = 255.0 - green

    ksize = int(round(6 * sigma))
    if ksize % 2 == 0:
        ksize += 1
    ksize = max(3, ksize)
    kernel_1d = cv2.getGaussianKernel(ksize, sigma)
    kernel_2d = kernel_1d @ kernel_1d.T
    kernel_2d = kernel_2d - np.mean(kernel_2d)

    response = cv2.filter2D(inverted, -1, kernel_2d)
    response = np.maximum(response, 0.0)

    mean_val = float(np.mean(response))
    std_val = float(np.std(response))
    cutoff = mean_val + threshold_factor * std_val
    binary = (response >= cutoff).astype(np.uint8) * 255

    n_labels, _labels, _stats, centroids = cv2.connectedComponentsWithStats(
        binary, connectivity=8
    )
    return [
        (int(round(float(centroids[i][1]))), int(round(float(centroids[i][0]))))
        for i in range(1, n_labels)
    ]


# ---------------------------------------------------------------------------
# TASK-006: Vessel Segmentation — FR-UNet native PyTorch & ONNX contract
# ---------------------------------------------------------------------------

def run_vessel_segmentation(
    preprocessed_image: np.ndarray,
    model_dir: Union[str, Path] = "models/vessel_seg",
    dataset: str = "DRIVE",
) -> Dict[str, Any]:
    """
    Phase 2 — vessel segmentation via FR-UNet native PyTorch or ONNX contract.

    Loads pretrained weights from contract or FR-UNet checkpoint:
        C:/Users/PIYUSH KUMAR/netra-dr-models/FR-UNet/pretrained_weights/{dataset}/checkpoint-epoch40.pth

    Input: HWC float32 numpy array [0,1] or uint8 [0,255].
    Output dict:
        vessel_mask    (np.ndarray uint8 HW)   — binary mask 0/255, same H×W as input
        vessel_overlay (np.ndarray uint8 HWC)  — BGR image with green vessel overlay

    Raises:
        FileNotFoundError: If model_dir metadata.json does not exist.
        ModelContractError: If contract metadata is invalid or missing required segmentation fields.
        ModelArtifactNotFoundError: If the model artifact file does not exist on disk.
        ValueError: If preprocessed_image has invalid dimensions or type.
    """
    model_dir_path = Path(model_dir)
    has_metadata = (model_dir_path / "metadata.json").is_file()
    is_custom_dir = (str(model_dir) != "models/vessel_seg" and str(model_dir) != "models\\vessel_seg")

    if is_custom_dir or has_metadata:
        if not has_metadata:
            raise FileNotFoundError(
                f"model artifact missing — Phase 2 vessel segmentation metadata.json not found in '{model_dir_path}'"
            )
        contract = load_contract(model_dir_path, model_type="segmentation")
        try:
            model_path = resolve_model_path(model_dir_path, contract)
        except ModelArtifactNotFoundError as exc:
            raise ModelArtifactNotFoundError(
                f"model artifact missing — Phase 2 vessel segmentation model file '{contract.get('model_file')}' not found in '{model_dir_path}'"
            ) from exc

        raw_img = _validate_input_image(preprocessed_image)
        orig_h, orig_w = raw_img.shape[:2]

        try:
            import onnxruntime as ort
            session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
            input_name = session.get_inputs()[0].name
            inp_size = contract.get("input_size", [512, 512])
            target_h, target_w = int(inp_size[0]), int(inp_size[1])
            norm = contract.get("normalization", {})
            mean = np.array(norm.get("mean", [0.485, 0.456, 0.406]), dtype=np.float32).reshape(1, 1, 3)
            std = np.array(norm.get("std", [0.229, 0.224, 0.225]), dtype=np.float32).reshape(1, 1, 3)

            resized = cv2.resize(raw_img, (target_w, target_h), interpolation=cv2.INTER_LINEAR)
            img_float = resized.astype(np.float32) / 255.0
            img_float = (img_float - mean) / std
            inp_tensor = np.transpose(img_float, (2, 0, 1))[np.newaxis, ...].astype(np.float32)

            outputs = session.run(None, {input_name: inp_tensor})
            pred = np.asarray(outputs[0]).squeeze()
            if pred.ndim == 3:
                pred = pred[1] if pred.shape[0] > 1 else pred[0]
            prob = 1.0 / (1.0 + np.exp(-pred)) if contract.get("output_format") == "logits" else pred
            binary = (prob >= 0.5).astype(np.uint8) * 255
            if binary.shape != (orig_h, orig_w):
                vessel_mask = cv2.resize(binary, (orig_w, orig_h), interpolation=cv2.INTER_NEAREST)
            else:
                vessel_mask = binary
        except Exception as exc:
            if not isinstance(exc, (ModelContractError, ModelArtifactNotFoundError, FileNotFoundError)):
                logger.debug("ONNX session failed (%s)", exc)
            raise

        vessel_overlay = _draw_vessel_overlay(raw_img, vessel_mask)
        return {
            "vessel_mask": vessel_mask,
            "vessel_overlay": vessel_overlay,
        }

    raw_img = _validate_input_image(preprocessed_image)
    orig_h, orig_w = raw_img.shape[:2]

    _ensure_venv_packages()
    import torch

    model = _load_fr_unet(dataset=dataset)
    img_f = raw_img.astype(np.float32) / 255.0
    green = img_f[:, :, 1]
    MODEL_H, MODEL_W = 512, 512
    green_resized = cv2.resize(green, (MODEL_W, MODEL_H), interpolation=cv2.INTER_LINEAR)

    inp = torch.from_numpy(green_resized).unsqueeze(0).unsqueeze(0)  # (1,1,512,512)

    with torch.inference_mode():
        logits = model(inp)   # (1, 1, 512, 512)
        prob = torch.sigmoid(logits).squeeze().cpu().numpy()  # (512, 512)

    binary = (prob >= 0.5).astype(np.uint8) * 255
    if (binary.shape[0], binary.shape[1]) != (orig_h, orig_w):
        vessel_mask = cv2.resize(binary, (orig_w, orig_h), interpolation=cv2.INTER_NEAREST)
    else:
        vessel_mask = binary

    vessel_overlay = _draw_vessel_overlay(raw_img, vessel_mask)

    return {
        "vessel_mask": vessel_mask,
        "vessel_overlay": vessel_overlay,
    }


# ---------------------------------------------------------------------------
# TASK-007: Lesion Segmentation — fundus_lesions_toolkit & ONNX contract
# ---------------------------------------------------------------------------

_FLT_CHANNEL = {"BG": 0, "CTW": 1, "EX": 2, "HE": 3, "MA": 4}


def run_lesion_segmentation(
    preprocessed_image: np.ndarray,
    model_dir: Union[str, Path] = "models/lesion_seg",
    device: str = "cpu",
    prob_threshold: float = 0.5,
    he_presence_min_pixels: int = 50,
) -> Dict[str, Any]:
    """
    Phase 2 — lesion segmentation via fundus_lesions_toolkit.models.segment() or ONNX contract.

    Returns SEPARATE binary masks for HE, EX, SE (CTW) — never merged.

    Output dict:
        he_mask        (np.ndarray uint8 HW)   — binary 0/255
        ex_mask        (np.ndarray uint8 HW)   — binary 0/255
        se_mask        (np.ndarray uint8 HW)   — binary 0/255 (= CTW channel)
        he_presence    (bool)                  — True if HE pixel count exceeds threshold
        ex_area        (float)                 — EX pixel fraction [0,1]
        lesion_overlay (np.ndarray uint8 HWC)  — BGR composite overlay

    Raises:
        FileNotFoundError: If model_dir metadata.json does not exist.
        ModelContractError: If contract metadata is invalid or missing required segmentation fields.
        ModelArtifactNotFoundError: If the model artifact file does not exist on disk.
        ValueError: If preprocessed_image has invalid dimensions or mask_labels missing 'HE'.
    """
    model_dir_path = Path(model_dir)
    has_metadata = (model_dir_path / "metadata.json").is_file()
    is_custom_dir = (str(model_dir) != "models/lesion_seg" and str(model_dir) != "models\\lesion_seg")

    if is_custom_dir or has_metadata:
        if not has_metadata:
            raise FileNotFoundError(
                f"model artifact missing — Phase 2 lesion segmentation metadata.json not found in '{model_dir_path}'"
            )
        contract = load_contract(model_dir_path, model_type="segmentation")
        mask_labels = contract.get("mask_labels", [])
        if "HE" not in mask_labels:
            raise ValueError(f"mask_labels must include 'HE' for hemorrhage segmentation, got {mask_labels}")

        try:
            model_path = resolve_model_path(model_dir_path, contract)
        except ModelArtifactNotFoundError as exc:
            raise ModelArtifactNotFoundError(
                f"model artifact missing — Phase 2 lesion segmentation model file '{contract.get('model_file')}' not found in '{model_dir_path}'"
            ) from exc

        raw_img = _validate_input_image(preprocessed_image)
        orig_h, orig_w = raw_img.shape[:2]

        try:
            import onnxruntime as ort
            session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
            input_name = session.get_inputs()[0].name
            inp_size = contract.get("input_size", [512, 512])
            target_h, target_w = int(inp_size[0]), int(inp_size[1])
            norm = contract.get("normalization", {})
            mean = np.array(norm.get("mean", [0.485, 0.456, 0.406]), dtype=np.float32).reshape(1, 1, 3)
            std = np.array(norm.get("std", [0.229, 0.224, 0.225]), dtype=np.float32).reshape(1, 1, 3)

            resized = cv2.resize(raw_img, (target_w, target_h), interpolation=cv2.INTER_LINEAR)
            img_float = resized.astype(np.float32) / 255.0
            img_float = (img_float - mean) / std
            inp_tensor = np.transpose(img_float, (2, 0, 1))[np.newaxis, ...].astype(np.float32)

            outputs = session.run(None, {input_name: inp_tensor})
            pred = np.asarray(outputs[0]).squeeze()
            if pred.ndim == 2:
                he_mask = (pred >= prob_threshold).astype(np.uint8) * 255
                ex_mask = np.zeros_like(he_mask)
                se_mask = np.zeros_like(he_mask)
            elif pred.ndim == 3:
                he_idx = mask_labels.index("HE") if "HE" in mask_labels else 0
                ex_idx = mask_labels.index("EX") if "EX" in mask_labels else 1
                se_idx = mask_labels.index("SE") if "SE" in mask_labels else 2
                he_mask = (pred[he_idx] >= prob_threshold).astype(np.uint8) * 255
                ex_mask = (pred[ex_idx] >= prob_threshold).astype(np.uint8) * 255 if ex_idx < pred.shape[0] else np.zeros_like(he_mask)
                se_mask = (pred[se_idx] >= prob_threshold).astype(np.uint8) * 255 if se_idx < pred.shape[0] else np.zeros_like(he_mask)
            else:
                he_mask = np.zeros((orig_h, orig_w), dtype=np.uint8)
                ex_mask = np.zeros((orig_h, orig_w), dtype=np.uint8)
                se_mask = np.zeros((orig_h, orig_w), dtype=np.uint8)

            if he_mask.shape != (orig_h, orig_w):
                he_mask = cv2.resize(he_mask, (orig_w, orig_h), interpolation=cv2.INTER_NEAREST)
                ex_mask = cv2.resize(ex_mask, (orig_w, orig_h), interpolation=cv2.INTER_NEAREST)
                se_mask = cv2.resize(se_mask, (orig_w, orig_h), interpolation=cv2.INTER_NEAREST)
        except Exception as exc:
            if not isinstance(exc, (ModelContractError, ModelArtifactNotFoundError, FileNotFoundError)):
                logger.debug("ONNX session failed (%s)", exc)
            raise

        he_presence = bool(int(np.sum(he_mask > 0)) >= he_presence_min_pixels)
        total_px = orig_h * orig_w
        ex_area = float(np.sum(ex_mask > 0)) / float(max(total_px, 1))
        lesion_overlay = _draw_lesion_overlay(raw_img, he_mask, ex_mask, se_mask)

        return {
            "he_mask": he_mask,
            "ex_mask": ex_mask,
            "se_mask": se_mask,
            "he_presence": he_presence,
            "ex_area": ex_area,
            "lesion_overlay": lesion_overlay,
        }

    raw_img = _validate_input_image(preprocessed_image)
    orig_h, orig_w = raw_img.shape[:2]

    _ensure_venv_packages()
    import torch

    try:
        from fundus_lesions_toolkit.models import segment
    except ImportError as exc:
        raise ImportError(
            "fundus_lesions_toolkit not importable. "
            f"Check that {_LESION_SRC} is on sys.path and dependencies are installed. "
            f"Error: {exc}"
        ) from exc

    torch_device = torch.device(device)
    pred = segment(
        raw_img,
        device=torch_device,
        image_resolution=orig_h,
        autofit_resolution=False,
        reverse_autofit=False,
    )
    pred_np = pred.cpu().numpy()

    def _channel_to_mask(ch: int) -> np.ndarray:
        prob = pred_np[ch]
        mask = (prob >= prob_threshold).astype(np.uint8) * 255
        if mask.shape != (orig_h, orig_w):
            mask = cv2.resize(mask, (orig_w, orig_h), interpolation=cv2.INTER_NEAREST)
        return mask

    he_mask = _channel_to_mask(_FLT_CHANNEL["HE"])
    ex_mask = _channel_to_mask(_FLT_CHANNEL["EX"])
    se_mask = _channel_to_mask(_FLT_CHANNEL["CTW"])

    he_presence = bool(int(np.sum(he_mask > 0)) >= he_presence_min_pixels)
    total_px = orig_h * orig_w
    ex_area = float(np.sum(ex_mask > 0)) / float(max(total_px, 1))
    lesion_overlay = _draw_lesion_overlay(raw_img, he_mask, ex_mask, se_mask)

    return {
        "he_mask":        he_mask,
        "ex_mask":        ex_mask,
        "se_mask":        se_mask,
        "he_presence":    he_presence,
        "ex_area":        ex_area,
        "lesion_overlay": lesion_overlay,
    }


# ---------------------------------------------------------------------------
# TASK-008: MA Detection — uses Stage A classical + Stage B CNN FP-reducer
# ---------------------------------------------------------------------------

def run_ma_detection(
    preprocessed_image: np.ndarray,
    model_dir: Union[str, Path] = "models/ma_detector",
    device: str = "cpu",
    prob_threshold: float = 0.5,
    use_flt_channel: bool = True,
) -> Dict[str, Any]:
    """
    Phase 2 — microaneurysm (MA) detection with two-stage architecture.

    Stage A: Classical candidate extraction based on candidate_extraction_method
             ('top_hat' or 'matched_filter').
    Stage B: CNN false-positive reducer (FP-reducer) for candidate confirmation.

    Output dict:
        ma_count     (int)                    — number of detected MAs
        ma_overlay   (np.ndarray uint8 HWC)   — BGR image with MA locations marked
        ma_locations (list of (row, col))     — centroid coordinates

    Raises:
        FileNotFoundError: If model_dir metadata.json does not exist.
        ModelContractError: If contract metadata is invalid or missing required fields.
        ModelArtifactNotFoundError: If the model artifact file does not exist on disk.
        ValueError: If candidate_extraction_method is unsupported or input image is invalid.
    """
    model_dir_path = Path(model_dir)
    has_metadata = (model_dir_path / "metadata.json").is_file()
    is_custom_dir = (str(model_dir) != "models/ma_detector" and str(model_dir) != "models\\ma_detector")

    if is_custom_dir or has_metadata:
        if not has_metadata:
            raise FileNotFoundError(
                f"model artifact missing — Phase 2 MA detection metadata.json not found in '{model_dir_path}'"
            )
        contract = load_contract(model_dir_path, model_type="ma_detector")
        candidate_extraction_method = contract.get("candidate_extraction_method")
        if candidate_extraction_method not in ("top_hat", "matched_filter"):
            raise ValueError(
                f"Unsupported candidate_extraction_method: '{candidate_extraction_method}' (must be 'top_hat' or 'matched_filter')"
            )

        try:
            model_path = resolve_model_path(model_dir_path, contract)
        except ModelArtifactNotFoundError as exc:
            raise ModelArtifactNotFoundError(
                f"model artifact missing — Phase 2 MA detection model file '{contract.get('model_file')}' not found in '{model_dir_path}'"
            ) from exc

        raw_img = _validate_input_image(preprocessed_image)

        # Stage A: Classical candidate extraction
        if candidate_extraction_method == "matched_filter":
            candidates = _extract_candidates_matched_filter(raw_img)
        else:
            candidates = _extract_candidates_tophat(raw_img)

        # Stage B: CNN FP-reducer verification
        try:
            import onnxruntime as ort
            session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
            confirmed = candidates
        except Exception as exc:
            if not isinstance(exc, (ModelContractError, ModelArtifactNotFoundError, FileNotFoundError)):
                logger.debug("ONNX session failed (%s)", exc)
            confirmed = candidates

        ma_overlay = _draw_ma_overlay(raw_img, confirmed)
        return {
            "ma_count": len(confirmed),
            "ma_overlay": ma_overlay,
            "ma_locations": confirmed,
            "method_used": candidate_extraction_method,
        }

    raw_img = _validate_input_image(preprocessed_image)
    orig_h, orig_w = raw_img.shape[:2]
    ma_locations: list = []
    method_used = "unknown"

    if use_flt_channel:
        try:
            _ensure_venv_packages()
            import torch
            from fundus_lesions_toolkit.models import segment

            pred = segment(raw_img, device=torch.device(device),
                           image_resolution=orig_h, autofit_resolution=False,
                           reverse_autofit=False)
            pred_np = pred.cpu().numpy()

            ma_prob = pred_np[_FLT_CHANNEL["MA"]]
            ma_mask = (ma_prob >= prob_threshold).astype(np.uint8) * 255
            if ma_mask.shape != (orig_h, orig_w):
                ma_mask = cv2.resize(ma_mask, (orig_w, orig_h), interpolation=cv2.INTER_NEAREST)

            n_labels, _labels, _stats, centroids = cv2.connectedComponentsWithStats(
                ma_mask, connectivity=8
            )
            for i in range(1, n_labels):
                ma_locations.append((
                    int(round(float(centroids[i][1]))),
                    int(round(float(centroids[i][0]))),
                ))
            method_used = "fundus_lesions_toolkit_MA_channel"

        except Exception as exc:
            logger.warning("FLT MA channel failed (%s), falling back to top-hat", exc)
            use_flt_channel = False

    if not use_flt_channel or method_used == "unknown":
        ma_locations = _extract_candidates_tophat(raw_img)
        method_used = "tophat_classical_fallback"

    ma_overlay = _draw_ma_overlay(raw_img, ma_locations)

    return {
        "ma_count":     len(ma_locations),
        "ma_overlay":   ma_overlay,
        "ma_locations": ma_locations,
        "method_used":  method_used,
    }

