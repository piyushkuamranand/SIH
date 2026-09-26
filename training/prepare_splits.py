"""
training/prepare_splits.py — NETRA-DR dataset manifest, near-duplicate check, and split builder.

Training-side only script (never imported by app/ or pipeline/). Builds a
deduplicated, stratified train/validation split for the APTOS 2019 grading
dataset, per docs/SIH26038_Development_Blueprint.md Section J (Data Pipeline):
"Run a perceptual-hash near-duplicate check ... before splitting."

Known limitation (documented, not hidden): the APTOS 2019 Kaggle CSV provides
only an image id (`id_code`), no patient/exam id — a true patient-level split
(blueprint DAT-004) is not possible from this file alone. This script performs
a near-duplicate-aware, class-stratified *image-level* split instead, and
keeps every near-duplicate group entirely inside one split so no near-identical
image pair straddles train/validation.

Usage:
    python training/prepare_splits.py --dataset aptos2019 --val-fraction 0.15

Outputs:
    data/splits/aptos2019_train.csv   (id_code, diagnosis)
    data/splits/aptos2019_val.csv     (id_code, diagnosis)
    data/splits/aptos2019_dedup_report.json
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def average_hash(image_path: Path, hash_size: int = 16) -> int:
    """Compute a simple average-hash (aHash) perceptual fingerprint, no extra deps."""
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


def find_duplicate_groups(hashes: Dict[str, int], max_distance: int = 4) -> Dict[str, str]:
    """
    Greedy near-duplicate clustering: returns {id_code: group_id}. Images whose
    aHash Hamming distance is <= max_distance are placed in the same group.
    O(n^2) — fine for a few thousand images; documented as a simple baseline,
    not a scalable production dedup (would use LSH/bucketing at larger scale).
    """
    ids = list(hashes.keys())
    parent = {i: i for i in ids}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: str, y: str) -> None:
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[rx] = ry

    # Bucket by top bits of hash to cut comparisons down from full O(n^2).
    buckets: Dict[int, List[str]] = defaultdict(list)
    for i in ids:
        buckets[hashes[i] >> 240].append(i)  # coarse bucket on high bits (256-bit hash for 16x16)

    for bucket_ids in buckets.values():
        for a_idx in range(len(bucket_ids)):
            for b_idx in range(a_idx + 1, len(bucket_ids)):
                a, b = bucket_ids[a_idx], bucket_ids[b_idx]
                if hamming_distance(hashes[a], hashes[b]) <= max_distance:
                    union(a, b)

    return {i: find(i) for i in ids}


def stratified_group_split(
    rows: List[Dict[str, str]],
    group_of: Dict[str, str],
    val_fraction: float,
    seed: int = 42,
) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    """Assign whole dedup groups to train/val, stratified by each group's (first member's) class."""
    rng = random.Random(seed)

    group_rows: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for row in rows:
        group_rows[group_of[row["id_code"]]].append(row)

    # Stratify groups by the diagnosis of their first member.
    groups_by_class: Dict[str, List[str]] = defaultdict(list)
    for gid, grows in group_rows.items():
        groups_by_class[grows[0]["diagnosis"]].append(gid)

    val_groups: set = set()
    for cls, gids in groups_by_class.items():
        rng.shuffle(gids)
        n_val = max(1, round(len(gids) * val_fraction))
        val_groups.update(gids[:n_val])

    train_rows, val_rows = [], []
    for gid, grows in group_rows.items():
        (val_rows if gid in val_groups else train_rows).extend(grows)

    return train_rows, val_rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default="aptos2019")
    parser.add_argument("--val-fraction", type=float, default=0.15)
    parser.add_argument("--hash-distance", type=int, default=4)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    raw_dir = PROJECT_ROOT / "data" / "raw" / args.dataset
    csv_candidates = sorted(raw_dir.glob("*.csv"))
    if not csv_candidates:
        raise FileNotFoundError(f"No CSV label file found under {raw_dir}")
    csv_path = csv_candidates[0]
    img_dir = raw_dir / "train_images"

    with open(csv_path, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    print(f"Loaded {len(rows)} rows from {csv_path.name}")

    # ---- 1. Perceptual hash every image ----
    hashes: Dict[str, int] = {}
    missing = []
    for i, row in enumerate(rows):
        img_path = img_dir / f"{row['id_code']}.png"
        if not img_path.is_file():
            img_path = img_dir / f"{row['id_code']}.jpg"
        if not img_path.is_file():
            missing.append(row["id_code"])
            continue
        hashes[row["id_code"]] = average_hash(img_path)
        if (i + 1) % 500 == 0:
            print(f"  hashed {i + 1}/{len(rows)}")

    if missing:
        print(f"WARNING: {len(missing)} rows had no matching image file; excluded.")
    rows = [r for r in rows if r["id_code"] in hashes]

    # ---- 2. Near-duplicate clustering ----
    group_of = find_duplicate_groups(hashes, max_distance=args.hash_distance)
    n_groups = len(set(group_of.values()))
    n_dup_groups = sum(1 for g in set(group_of.values())
                        if sum(1 for v in group_of.values() if v == g) > 1)
    print(f"{len(rows)} images -> {n_groups} dedup groups ({n_dup_groups} groups with >1 near-duplicate)")

    # ---- 3. Stratified, dedup-aware split ----
    train_rows, val_rows = stratified_group_split(rows, group_of, args.val_fraction, args.seed)
    print(f"Split: {len(train_rows)} train / {len(val_rows)} val")

    splits_dir = PROJECT_ROOT / "data" / "splits"
    splits_dir.mkdir(parents=True, exist_ok=True)

    for name, split_rows in [("train", train_rows), ("val", val_rows)]:
        out_path = splits_dir / f"{args.dataset}_{name}.csv"
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["id_code", "diagnosis"])
            writer.writeheader()
            for row in split_rows:
                writer.writerow({"id_code": row["id_code"], "diagnosis": row["diagnosis"]})
        print(f"Wrote {out_path} ({len(split_rows)} rows)")

    # Class distribution report
    def class_counts(split_rows):
        c = defaultdict(int)
        for r in split_rows:
            c[r["diagnosis"]] += 1
        return dict(sorted(c.items()))

    report = {
        "dataset": args.dataset,
        "source_csv": csv_path.name,
        "total_images": len(rows),
        "missing_image_files": missing,
        "dedup_groups": n_groups,
        "dedup_groups_with_duplicates": n_dup_groups,
        "hash_max_distance": args.hash_distance,
        "val_fraction_requested": args.val_fraction,
        "train_count": len(train_rows),
        "val_count": len(val_rows),
        "train_class_distribution": class_counts(train_rows),
        "val_class_distribution": class_counts(val_rows),
        "seed": args.seed,
        "limitation": (
            "APTOS 2019 Kaggle CSV has no patient/exam id field; this is a "
            "near-duplicate-aware, class-stratified IMAGE-level split, not a "
            "patient-level split. Near-duplicate groups (aHash Hamming distance "
            f"<= {args.hash_distance}) are kept entirely within one split."
        ),
    }
    report_path = splits_dir / f"{args.dataset}_dedup_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"Wrote {report_path}")


if __name__ == "__main__":
    main()
