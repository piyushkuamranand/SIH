"""
training/prepare_grading_splits.py — combined APTOS 2019 + IDRiD grading split.

The Final Model Stack's original recipe for the grading model is "APTOS 2019 +
DDR grading set" (Stage 7). DDR is intentionally excluded from this training
run; IDRiD's B_grading TRAINING set (413 images, ICDR 0-4) is the approved
substitute already on disk — the IDRiD grading TEST set (103 images) is the
project's SEALED external test set and is never read by this script.

Per blueprint DAT-004 ("perceptual-hash near-duplicate check across
APTOS/IDRiD/DDR before building splits"), this script hashes both datasets'
TRAIN-eligible images together and keeps any cross-dataset or within-dataset
near-duplicate group entirely inside one split.

Output: data/splits/grading_train.csv, data/splits/grading_val.csv with
columns [dataset, id_code, diagnosis, image_path] (image_path relative to
data/raw/), plus data/splits/grading_dedup_report.json.

Usage:
    python training/prepare_grading_splits.py --val-fraction 0.15
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


def collect_aptos() -> List[Dict]:
    csv_path = next((RAW / "aptos2019").glob("*.csv"))
    img_dir = RAW / "aptos2019" / "train_images"
    rows = []
    for row in csv.DictReader(open(csv_path, encoding="utf-8")):
        rows.append({
            "dataset": "aptos2019",
            "id_code": row["id_code"],
            "diagnosis": int(row["diagnosis"]),
            "image_path": str((img_dir / f"{row['id_code']}.png").relative_to(RAW)),
        })
    return rows


def collect_idrid_grading_train() -> List[Dict]:
    csv_path = (RAW / "idrid" / "B_grading" / "B. Disease Grading" / "2. Groundtruths" /
                "a. IDRiD_Disease Grading_Training Labels.csv")
    img_dir = RAW / "idrid" / "B_grading" / "B. Disease Grading" / "1. Original Images" / "a. Training Set"
    rows = []
    for row in csv.DictReader(open(csv_path, encoding="utf-8-sig")):
        name = row["Image name"].strip()
        rows.append({
            "dataset": "idrid_grading_train",
            "id_code": name,
            "diagnosis": int(row["Retinopathy grade"]),
            "image_path": str((img_dir / f"{name}.jpg").relative_to(RAW)),
        })
    return rows


def find_duplicate_groups(hashes: Dict[str, int], max_distance: int) -> Dict[str, str]:
    ids = list(hashes.keys())
    parent = {i: i for i in ids}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[rx] = ry

    buckets: Dict[int, List[str]] = defaultdict(list)
    for i in ids:
        buckets[hashes[i] >> 240].append(i)

    for bucket_ids in buckets.values():
        for a in range(len(bucket_ids)):
            for b in range(a + 1, len(bucket_ids)):
                x, y = bucket_ids[a], bucket_ids[b]
                if hamming_distance(hashes[x], hashes[y]) <= max_distance:
                    union(x, y)
    return {i: find(i) for i in ids}


def stratified_group_split(rows, group_of, val_fraction, seed=42):
    rng = random.Random(seed)
    group_rows: Dict[str, List[Dict]] = defaultdict(list)
    for row in rows:
        group_rows[group_of[row["_key"]]].append(row)

    groups_by_class: Dict[int, List[str]] = defaultdict(list)
    for gid, grows in group_rows.items():
        groups_by_class[grows[0]["diagnosis"]].append(gid)

    val_groups = set()
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
    parser.add_argument("--val-fraction", type=float, default=0.15)
    parser.add_argument("--hash-distance", type=int, default=4)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    aptos_rows = collect_aptos()
    idrid_rows = collect_idrid_grading_train()
    print(f"APTOS: {len(aptos_rows)} images | IDRiD grading (train, non-sealed): {len(idrid_rows)} images")

    all_rows = aptos_rows + idrid_rows
    for r in all_rows:
        r["_key"] = f"{r['dataset']}::{r['id_code']}"

    print("Hashing all images for cross-dataset near-duplicate check (this includes IDRiD's "
          "large 4288x2848 originals, so it is slower than the APTOS-only script)...")
    hashes = {}
    for i, row in enumerate(all_rows):
        img_path = RAW / row["image_path"]
        hashes[row["_key"]] = average_hash(img_path)
        if (i + 1) % 500 == 0:
            print(f"  hashed {i + 1}/{len(all_rows)}")

    group_of = find_duplicate_groups(hashes, args.hash_distance)
    n_groups = len(set(group_of.values()))
    cross_dataset_dups = 0
    group_datasets: Dict[str, set] = defaultdict(set)
    for row in all_rows:
        group_datasets[group_of[row["_key"]]].add(row["dataset"])
    for gid, dsets in group_datasets.items():
        if len(dsets) > 1:
            cross_dataset_dups += 1
    print(f"{len(all_rows)} images -> {n_groups} dedup groups ({cross_dataset_dups} groups span >1 dataset)")

    train_rows, val_rows = stratified_group_split(all_rows, group_of, args.val_fraction, args.seed)
    for r in train_rows + val_rows:
        r.pop("_key", None)
    print(f"Combined split: {len(train_rows)} train / {len(val_rows)} val")

    splits_dir = PROJECT_ROOT / "data" / "splits"
    splits_dir.mkdir(parents=True, exist_ok=True)
    for name, split_rows in [("train", train_rows), ("val", val_rows)]:
        out_path = splits_dir / f"grading_{name}.csv"
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["dataset", "id_code", "diagnosis", "image_path"])
            writer.writeheader()
            writer.writerows(split_rows)
        print(f"Wrote {out_path} ({len(split_rows)} rows)")

    def class_counts(rows):
        d = defaultdict(int)
        for r in rows:
            d[r["diagnosis"]] += 1
        return dict(sorted(d.items()))

    def dataset_counts(rows):
        d = defaultdict(int)
        for r in rows:
            d[r["dataset"]] += 1
        return dict(d)

    report = {
        "sources": {"aptos2019": len(aptos_rows), "idrid_grading_train": len(idrid_rows)},
        "excluded": {"ddr": "not downloaded, excluded per instruction",
                     "idrid_grading_test": "SEALED (103 images) — never read by this script"},
        "total_images": len(all_rows),
        "dedup_groups": n_groups,
        "cross_dataset_duplicate_groups": cross_dataset_dups,
        "hash_max_distance": args.hash_distance,
        "train_count": len(train_rows),
        "val_count": len(val_rows),
        "train_class_distribution": class_counts(train_rows),
        "val_class_distribution": class_counts(val_rows),
        "train_dataset_distribution": dataset_counts(train_rows),
        "val_dataset_distribution": dataset_counts(val_rows),
        "seed": args.seed,
        "limitation": (
            "Neither APTOS nor IDRiD grading CSVs expose a patient/exam id; this is a "
            "near-duplicate-aware (aHash, cross-dataset), class-stratified IMAGE-level "
            "split, not a patient-level split."
        ),
    }
    report_path = splits_dir / "grading_dedup_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"Wrote {report_path}")


if __name__ == "__main__":
    main()
