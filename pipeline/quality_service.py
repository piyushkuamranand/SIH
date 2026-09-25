"""
pipeline/quality_service.py — NETRA-DR Phase 1: EyeQ Quality Assessment Service

Wraps the external EyeQ EfficientNet-B4 ensemble model into a reusable,
cached service layer for the NETRA-DR prototype.

Design:
- Model is loaded ONCE at first use and cached for all subsequent requests.
- Inference runs in eval mode with torch.no_grad().
- Supports CUDA if available, CPU fallback otherwise.
- Does NOT use EyeQ's run_grading() (which moves files into directories).
- Does NOT invent quality thresholds — uses EyeQ argmax decision.
- Provides seamless subprocess fallback when running in a Python environment
  where PyTorch is installed in external/EyeQ/.venv.

EyeQ class meanings (original):
    0 = good quality
    1 = uncertain quality (usable)
    2 = bad quality

NETRA terminology mapping:
    good      → GOOD
    uncertain → BORDERLINE
    bad       → REJECT
"""

from __future__ import annotations

import io
import json
import logging
import os
import subprocess
import sys
import time
import threading
from pathlib import Path
from typing import Any, Dict, Optional, Union

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level singleton for the cached service
# ---------------------------------------------------------------------------
_model_lock = threading.Lock()
_cached_service: Optional[Union["EyeQQualityService", "SubprocessEyeQQualityService"]] = None

# ---------------------------------------------------------------------------
# EyeQ class ↔ NETRA label mappings
# ---------------------------------------------------------------------------
EYEQ_CLASS_LABELS = ["good", "uncertain", "bad"]
NETRA_QUALITY_LABELS = ["GOOD", "BORDERLINE", "REJECT"]

EYEQ_TO_NETRA = {
    0: "GOOD",        # EyeQ "good"      → NETRA "GOOD"
    1: "BORDERLINE",  # EyeQ "uncertain"  → NETRA "BORDERLINE"
    2: "REJECT",      # EyeQ "bad"        → NETRA "REJECT"
}


class QualityServiceError(RuntimeError):
    """Raised when the quality service encounters an unrecoverable error."""
    pass


class EyeQQualityService:
    """
    In-process cached EyeQ quality assessment service.
    Loads the 8-model EfficientNet-B4 ensemble once and caches it.
    """

    def __init__(
        self,
        checkpoint_dir: Union[str, Path] = "external/EyeQ/checkpoints/efficientnet/",
        device: Optional[str] = None,
    ):
        self._load_start = time.perf_counter()

        try:
            import torch
        except ImportError as exc:
            raise QualityServiceError(
                "PyTorch is not installed in the current environment."
            ) from exc

        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)

        self.checkpoint_dir = Path(checkpoint_dir)
        if not self.checkpoint_dir.is_dir():
            raise QualityServiceError(
                f"EyeQ checkpoint directory not found: {self.checkpoint_dir}"
            )

        eyeq_root = Path("external/EyeQ")
        eyeq_src = eyeq_root / "src"
        for p in [str(eyeq_root.resolve()), str(eyeq_src.resolve())]:
            if p not in sys.path:
                sys.path.insert(0, p)

        try:
            from EyeQ.model import EyeQ
            # Suppress stdout noise during checkpoint loading if desired
            self._model = EyeQ(
                checkpoint_path="checkpoints/efficientnet/",
                pretrained=True,
                lightweight=False,
                mode="eval",
                verbose=False,
                return_probs=True,
                resize=520,
            ).to(self.device)
            self._model.eval()
        except Exception as exc:
            raise QualityServiceError(
                f"Failed to load EyeQ ensemble model: {type(exc).__name__}: {exc}"
            ) from exc

        self.ensemble_size = len(self._model.models)
        self._load_time = time.perf_counter() - self._load_start

        logger.info(
            "EyeQ quality service initialized: %d models on %s (%.2fs)",
            self.ensemble_size, self.device, self._load_time,
        )

    @property
    def model_info(self) -> Dict[str, Any]:
        return {
            "name": "EyeQ-EfficientNetB4",
            "ensemble_size": self.ensemble_size,
            "input_size": [520, 520],
            "channels": 3,
            "normalization": "non-zero pixel mean/std",
            "framework": "pytorch",
            "source_class_labels": EYEQ_CLASS_LABELS,
            "netra_class_labels": NETRA_QUALITY_LABELS,
            "decision_policy": "argmax (NOT calibrated for NETRA clinical use)",
            "device": str(self.device),
            "load_time_seconds": round(self._load_time, 3),
        }

    def predict(self, image_path: Union[str, Path]) -> Dict[str, Any]:
        import torch
        from PIL import Image
        from torchvision import transforms

        image_path = Path(image_path)
        if not image_path.is_file():
            raise FileNotFoundError(f"Image file not found: {image_path}")

        try:
            pil_img = Image.open(image_path)
            pil_img.verify()
            pil_img = Image.open(image_path).convert("RGB")
        except Exception as exc:
            raise ValueError(
                f"Cannot decode image file: {image_path}. Details: {exc}"
            ) from exc

        w, h = pil_img.size
        if w <= 0 or h <= 0:
            raise ValueError(f"Image has invalid dimensions: {w}×{h}")

        to_tensor = transforms.ToTensor()
        img_tensor = to_tensor(pil_img)
        img_tensor = img_tensor.unsqueeze(0).to(self.device)

        t_start = time.perf_counter()
        try:
            with torch.no_grad():
                probs = self._model(img_tensor)
        except Exception as exc:
            raise QualityServiceError(
                f"EyeQ inference failed: {type(exc).__name__}: {exc}"
            ) from exc
        inference_time_ms = (time.perf_counter() - t_start) * 1000.0

        prob_vec = probs[0].cpu().numpy().astype(float)
        if prob_vec.shape != (3,):
            raise QualityServiceError(
                f"Unexpected model output shape: {prob_vec.shape}, expected (3,)"
            )
        if not np.isfinite(prob_vec).all():
            raise QualityServiceError(
                f"Model produced non-finite probabilities: {prob_vec}"
            )

        predicted_class = int(np.argmax(prob_vec))
        netra_label = EYEQ_TO_NETRA[predicted_class]
        eyeq_label = EYEQ_CLASS_LABELS[predicted_class]
        confidence = float(prob_vec[predicted_class])

        return {
            "netra_label": netra_label,
            "netra_probabilities": {
                "good": float(prob_vec[0]),
                "borderline": float(prob_vec[1]),
                "reject": float(prob_vec[2]),
            },
            "eyeq_class": predicted_class,
            "eyeq_label": eyeq_label,
            "eyeq_probabilities": {
                "good": float(prob_vec[0]),
                "uncertain": float(prob_vec[1]),
                "bad": float(prob_vec[2]),
            },
            "confidence": confidence,
            "inference_time_ms": round(inference_time_ms, 2),
            "device": str(self.device),
        }


class SubprocessEyeQQualityService:
    """
    Subprocess fallback that runs inference using the Python interpreter in
    external/EyeQ/.venv when PyTorch is not available in the host environment.
    """

    def __init__(self, venv_python: Path):
        self.venv_python = venv_python
        self._load_time = 0.0

    @property
    def model_info(self) -> Dict[str, Any]:
        return {
            "name": "EyeQ-EfficientNetB4",
            "ensemble_size": 8,
            "input_size": [520, 520],
            "channels": 3,
            "normalization": "non-zero pixel mean/std",
            "framework": "pytorch (external venv)",
            "source_class_labels": EYEQ_CLASS_LABELS,
            "netra_class_labels": NETRA_QUALITY_LABELS,
            "decision_policy": "argmax (NOT calibrated for NETRA clinical use)",
            "device": "cpu",
            "load_time_seconds": 0.0,
        }

    def predict(self, image_path: Union[str, Path]) -> Dict[str, Any]:
        image_path = Path(image_path).resolve()
        if not image_path.is_file():
            raise FileNotFoundError(f"Image file not found: {image_path}")

        project_root = Path(__file__).resolve().parent.parent
        cmd = [
            str(self.venv_python),
            "-m",
            "pipeline.quality_service",
            str(image_path),
        ]

        proc = subprocess.run(
            cmd,
            cwd=str(project_root),
            capture_output=True,
            text=True,
        )

        if proc.returncode != 0:
            raise QualityServiceError(
                f"EyeQ subprocess inference failed (code {proc.returncode}):\n{proc.stderr}"
            )

        for line in proc.stdout.splitlines():
            if line.startswith("NETRA_RESULT_JSON:"):
                json_str = line[len("NETRA_RESULT_JSON:"):].strip()
                return json.loads(json_str)

        raise QualityServiceError(
            f"Failed to find result JSON in subprocess output:\nSTDOUT: {proc.stdout}\nSTDERR: {proc.stderr}"
        )


def _find_eyeq_venv_python() -> Optional[Path]:
    """Check common paths for the EyeQ virtual environment Python."""
    candidates = [
        Path("external/EyeQ/.venv/Scripts/python.exe"),
        Path("external/EyeQ/.venv/bin/python"),
    ]
    for c in candidates:
        if c.is_file():
            return c.resolve()
    return None


def get_quality_service(
    checkpoint_dir: Union[str, Path] = "external/EyeQ/checkpoints/efficientnet/",
    device: Optional[str] = None,
) -> Union[EyeQQualityService, SubprocessEyeQQualityService]:
    """
    Get or create the singleton EyeQ quality service.
    Thread-safe and supports both in-process and subprocess modes.
    """
    global _cached_service
    if _cached_service is not None:
        return _cached_service

    with _model_lock:
        if _cached_service is not None:
            return _cached_service

        try:
            import torch  # noqa: F401
            _cached_service = EyeQQualityService(
                checkpoint_dir=checkpoint_dir,
                device=device,
            )
            return _cached_service
        except (ImportError, QualityServiceError) as exc:
            venv_python = _find_eyeq_venv_python()
            if venv_python:
                logger.info(
                    "PyTorch not available in current environment; using EyeQ venv: %s",
                    venv_python,
                )
                _cached_service = SubprocessEyeQQualityService(venv_python)
                return _cached_service
            raise QualityServiceError(
                f"Cannot initialize EyeQ service: PyTorch is not available, and no EyeQ venv was found. ({exc})"
            ) from exc


def check_eyeq_availability() -> Dict[str, Any]:
    """Check whether the EyeQ model and checkpoints are ready."""
    checkpoint_dir = Path("external/EyeQ/checkpoints/efficientnet/")
    if not checkpoint_dir.is_dir():
        return {
            "available": False,
            "message": f"EyeQ checkpoint directory not found: {checkpoint_dir}",
        }

    import glob
    checkpoints = glob.glob(str(checkpoint_dir / "**" / "*.pth"), recursive=True)
    if len(checkpoints) == 0:
        return {
            "available": False,
            "message": "No .pth checkpoint files found in EyeQ directory.",
        }

    has_torch = False
    try:
        import torch  # noqa: F401
        has_torch = True
    except ImportError:
        pass

    venv_py = _find_eyeq_venv_python()
    if not has_torch and not venv_py:
        return {
            "available": False,
            "message": "PyTorch is not installed and EyeQ venv was not found.",
        }

    return {
        "available": True,
        "message": f"EyeQ ready — {len(checkpoints)} checkpoints found ({'in-process' if has_torch else 'subprocess venv'})",
        "checkpoint_count": len(checkpoints),
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m pipeline.quality_service <image_path>", file=sys.stderr)
        sys.exit(1)

    target_image = sys.argv[1]
    svc = EyeQQualityService()
    out = svc.predict(target_image)
    print("NETRA_RESULT_JSON:" + json.dumps(out))
