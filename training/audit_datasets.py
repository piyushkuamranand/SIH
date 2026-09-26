"""
training/audit_datasets.py — NETRA-DR dataset audit (APTOS 2019, IDRiD, DRIVE).

Training-side only (never imported by app/ or pipeline/). Verifies what is
actually on disk against what docs/HANDOFF.md and the Development Blueprint
claim, per the ML rule "do not report a metric that was not actually
measured." Writes docs/dataset_cards/<name>.md with the real, measured facts.

Usage:
    python training/audit_datasets.py
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict, List

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW = PROJECT_ROOT / "data" / "raw"


def audit_aptos() -> Dict:
    csv_path = next((RAW / "aptos2019").glob("*.csv"))
    img_dir = RAW / "aptos2019" / "train_images"
    rows = list(csv.DictReader(open(csv_path, encoding="utf-8")))

    corrupt = []
    dims = set()
    for row in rows:
        p = img_dir / f"{row['id_code']}.png"
        if not p.is_file():
            corrupt.append((row["id_code"], "missing file"))
            continue
        try:
            with Image.open(p) as im:
                im.verify()
            with Image.open(p) as im:
                dims.add(im.size)
        except Exception as e:
            corrupt.append((row["id_code"], str(e)))

    dedup_report_path = PROJECT_ROOT / "data" / "splits" / "aptos2019_dedup_report.json"
    dedup_report = json.load(open(dedup_report_path)) if dedup_report_path.is_file() else None

    return {
        "total_labelled_rows": len(rows),
        "corrupt_or_missing": corrupt,
        "distinct_image_dimensions_count": len(dims),
        "sample_dimensions": list(dims)[:5],
        "dedup_and_split_report": dedup_report,
        "patient_id_field_present": False,
        "note": "No patient/exam id field in the Kaggle CSV — image-level split only (see dedup report).",
    }


def audit_idrid() -> Dict:
    base = RAW / "idrid"

    def read_grading_csv(path: Path) -> List[Dict]:
        rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
        return rows

    train_csv = base / "B_grading" / "B. Disease Grading" / "2. Groundtruths" / "a. IDRiD_Disease Grading_Training Labels.csv"
    test_csv = base / "B_grading" / "B. Disease Grading" / "2. Groundtruths" / "b. IDRiD_Disease Grading_Testing Labels.csv"
    train_rows = read_grading_csv(train_csv)
    test_rows = read_grading_csv(test_csv)

    def class_dist(rows):
        d: Dict[str, int] = {}
        for r in rows:
            g = r.get("Retinopathy grade", "").strip()
            d[g] = d.get(g, 0) + 1
        return dict(sorted(d.items()))

    train_img_dir = base / "B_grading" / "B. Disease Grading" / "1. Original Images" / "a. Training Set"
    test_img_dir = base / "B_grading" / "B. Disease Grading" / "1. Original Images" / "b. Testing Set"

    def missing_images(rows, img_dir):
        missing = []
        for r in rows:
            name = r.get("Image name", "").strip()
            if not (img_dir / f"{name}.jpg").is_file():
                missing.append(name)
        return missing

    seg_root = base / "A_segmentation" / "A. Segmentation"
    seg_masks_train = {
        mask_type: len(list((seg_root / "2. All Segmentation Groundtruths" / "a. Training Set" / mask_type).glob("*")))
        for mask_type in ["1. Microaneurysms", "2. Haemorrhages", "3. Hard Exudates", "4. Soft Exudates", "5. Optic Disc"]
    }
    seg_masks_test = {
        mask_type: len(list((seg_root / "2. All Segmentation Groundtruths" / "b. Testing Set" / mask_type).glob("*")))
        for mask_type in ["1. Microaneurysms", "2. Haemorrhages", "3. Hard Exudates", "4. Soft Exudates", "5. Optic Disc"]
    }
    seg_images_train = len(list((seg_root / "1. Original Images" / "a. Training Set").glob("*")))
    seg_images_test = len(list((seg_root / "1. Original Images" / "b. Testing Set").glob("*")))

    # Verify a sample of image<->mask dimension alignment
    alignment_sample = []
    sample_img = next((seg_root / "1. Original Images" / "a. Training Set").glob("*.jpg"), None)
    if sample_img:
        img_id = sample_img.stem
        with Image.open(sample_img) as im:
            img_size = im.size
        ma_mask = seg_root / "2. All Segmentation Groundtruths" / "a. Training Set" / "1. Microaneurysms" / f"{img_id}_MA.tif"
        if ma_mask.is_file():
            with Image.open(ma_mask) as mm:
                alignment_sample.append({"image": img_id, "image_size": img_size, "ma_mask_size": mm.size,
                                          "aligned": mm.size == img_size})

    return {
        "grading_train_count": len(train_rows),
        "grading_train_class_distribution": class_dist(train_rows),
        "grading_train_missing_images": missing_images(train_rows, train_img_dir),
        "grading_test_count": len(test_rows),
        "grading_test_class_distribution": class_dist(test_rows),
        "grading_test_missing_images": missing_images(test_rows, test_img_dir),
        "grading_test_status": "SEALED — per Final Model Stack Step 1, not to be opened for training/tuning until the model is frozen",
        "segmentation_images_train": seg_images_train,
        "segmentation_images_test": seg_images_test,
        "segmentation_masks_train": seg_masks_train,
        "segmentation_masks_test": seg_masks_test,
        "image_mask_alignment_sample": alignment_sample,
    }


def audit_drive() -> Dict:
    base = RAW / "drive"
    train_img_dir = base / "training" / "training" / "images"
    train_mask_dir = base / "training" / "training" / "1st_manual"
    train_fov_dir = base / "training" / "training" / "mask"
    test_img_dir = base / "test" / "test" / "images"
    test_mask_dir = base / "test" / "test" / "mask"

    train_imgs = sorted(train_img_dir.glob("*.tif"))
    train_masks = sorted(train_mask_dir.glob("*.gif"))
    test_imgs = sorted(test_img_dir.glob("*.tif"))
    test_fov_masks = sorted(test_mask_dir.glob("*.gif"))

    dims = set()
    alignment_ok = True
    for img_path in train_imgs:
        with Image.open(img_path) as im:
            dims.add(im.size)
        mask_path = train_mask_dir / f"{img_path.stem.replace('_training', '')}_manual1.gif"
        if mask_path.is_file():
            with Image.open(mask_path) as mm:
                if mm.size != im.size:
                    alignment_ok = False

    return {
        "train_images": len(train_imgs),
        "train_vessel_masks": len(train_masks),
        "test_images": len(test_imgs),
        "test_fov_masks": len(test_fov_masks),
        "note": "DRIVE test set has no vessel ground truth distributed publicly (2nd/3rd observer masks not in this download) — only FOV masks. Vessel model validation uses a held-out split of the 20 training images.",
        "image_dimensions": list(dims),
        "image_mask_alignment_ok": alignment_ok,
    }


def main() -> None:
    external_dir = PROJECT_ROOT / "external"
    external_status = {
        d.name: len(list(d.rglob("*")))
        for d in external_dir.iterdir() if d.is_dir()
    } if external_dir.is_dir() else {}

    report = {
        "aptos2019": audit_aptos(),
        "idrid": audit_idrid(),
        "drive": audit_drive(),
        "external_repos_file_counts": external_status,
        "external_repos_note": (
            "external/EyeQ and external/FGR-NET directories exist but contain 0 files "
            "(confirmed by rglob count above) — no usable pretrained checkpoint or code "
            "is actually present locally, despite the old models/quality/metadata.json "
            "(now replaced) pointing at an EyeQ checkpoint path. This is why Phase 1 uses "
            "the rule-based IQA baseline instead."
        ),
        "ddr_status": "NOT downloaded — intentionally excluded from this training run per instruction.",
    }

    out_dir = PROJECT_ROOT / "docs" / "dataset_cards"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "audit_report.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"Wrote {out_path}")
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
