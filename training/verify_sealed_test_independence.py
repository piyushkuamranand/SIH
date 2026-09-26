"""
training/verify_sealed_test_independence.py — one-time verification that the
IDRiD grading-test split (103 images) is genuinely independent of every image
used anywhere in training, model selection, or calibration.

This does NOT open the test set's LABELS or run the model on it — it only
perceptual-hashes the raw images and checks for near-duplicates against the
training pool (APTOS 3,662 + IDRiD grading-train 413 = 4,075 images). This
check must complete and show zero near-duplicates BEFORE the sealed test is
opened for real evaluation (see training/evaluate_sealed_test.py).

Never imported by app/ or pipeline/.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

import numpy as np
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW = PROJECT_ROOT / "data" / "raw"


def average_hash(image_path: Path, hash_size: int = 16) -> int:
    with Image.open(image_path) as img:
        gray = img.convert("L").resize((hash_size, hash_size), Image.LANCZOS)
        arr = np.asarray(gray, dtype=np.float32)
    mean = arr.mean()
    bits = (arr > mean).flatten()
    h = 0
    for b in bits:
        h = (h << 1) | int(b)
    return h


def hamming_distance(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def main() -> None:
    # Training pool: exactly the images used in data/splits/grading_train.csv + grading_val.csv
    pool_paths: List[Path] = []
    for split_file in ["grading_train.csv", "grading_val.csv"]:
        for row in csv.DictReader(open(PROJECT_ROOT / "data" / "splits" / split_file, encoding="utf-8")):
            pool_paths.append(RAW / row["image_path"])
    print(f"Training pool: {len(pool_paths)} images (APTOS + IDRiD grading-train, as actually used)")

    # Sealed test set
    test_img_dir = RAW / "idrid" / "B_grading" / "B. Disease Grading" / "1. Original Images" / "b. Testing Set"
    test_paths = sorted(test_img_dir.glob("*.jpg"))
    print(f"Sealed test set: {len(test_paths)} images")

    print("Hashing training pool...")
    pool_hashes = []
    for i, p in enumerate(pool_paths):
        pool_hashes.append(average_hash(p))
        if (i + 1) % 1000 == 0:
            print(f"  {i + 1}/{len(pool_paths)}")

    print("Hashing sealed test set...")
    test_hashes = {p.stem: average_hash(p) for p in test_paths}

    print("\nChecking for near-duplicates (Hamming distance <= 4) between sealed test and training pool...")
    max_distance = 4
    near_dup_found = []
    for test_id, test_hash in test_hashes.items():
        for pool_hash in pool_hashes:
            if hamming_distance(test_hash, pool_hash) <= max_distance:
                near_dup_found.append(test_id)
                break

    print(f"\nRESULT: {len(near_dup_found)} / {len(test_hashes)} sealed test images have a near-duplicate "
          f"in the training pool (threshold: Hamming distance <= {max_distance}).")
    if near_dup_found:
        print(f"Near-duplicate test image IDs: {near_dup_found}")
        print("These images MUST be excluded from the final sealed-test evaluation (documented, not silently dropped).")
    else:
        print("CLEAN: zero near-duplicates found. The sealed test set is independent of the training pool.")


if __name__ == "__main__":
    main()
