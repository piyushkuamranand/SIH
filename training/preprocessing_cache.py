"""
training/preprocessing_cache.py — shared canonical-space preprocessing cache
for all NETRA-DR training scripts.

Ensures training sees EXACTLY what pipeline/quality.py's run_quality_gate()
produces at inference time (FOV crop -> resize -> CLAHE -> normalize, per
configs/preprocessing.json) — this is the same pipeline.preprocessing.preprocess()
function the live app calls, not a re-implementation. Caches the result to
data/processed/<dataset>/<id>.png (uint8) so repeated epochs don't re-run
CLAHE per image; the ~1/255 quantization from the float32->uint8 round trip
is negligible next to the augmentation noise applied on top during training.

Never imported by app/ or pipeline/ — training-side only.
"""

from __future__ import annotations

from pathlib import Path
from typing import Union

import numpy as np
from PIL import Image

import sys
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.preprocessing import preprocess as pipeline_preprocess


def get_canonical_image(
    dataset: str,
    item_id: str,
    raw_path: Union[str, Path],
    config_path: Union[str, Path] = "configs/preprocessing.json",
    processed_root: Union[str, Path] = None,
) -> np.ndarray:
    """
    Returns the canonical-space (FOV-crop + resize + CLAHE + normalize) image
    for one raw file, as HWC uint8, from cache if present, else computes it
    via pipeline.preprocessing.preprocess() (the exact inference-time function)
    and caches it.
    """
    processed_root = Path(processed_root) if processed_root else PROJECT_ROOT / "data" / "processed"
    cache_dir = processed_root / dataset
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"{item_id}.png"

    if cache_path.is_file():
        with Image.open(cache_path) as im:
            return np.array(im.convert("RGB"), dtype=np.uint8)

    float_img = pipeline_preprocess(raw_path, config_path=config_path)  # HWC float32 [0,1]
    uint8_img = np.clip(float_img * 255.0, 0, 255).astype(np.uint8)
    Image.fromarray(uint8_img, mode="RGB").save(cache_path)
    return uint8_img
