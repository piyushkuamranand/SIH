"""
training/train_ma_detector.py — NETRA-DR Phase 2 microaneurysm (MA) hybrid
detector training (Final Model Stack Stage 4). Training-side only, never
imported by app/ or pipeline/. Fills pipeline/structure.py's
run_ma_detection() contract (models/ma_detector/, type "ma_detector").

Reuses pipeline.structure's ALREADY-IMPLEMENTED Stage A classical candidate
extraction (_extract_candidates_tophat) and patch preparation
(_prepare_patch_input) directly — not a re-implementation — so training-time
candidate generation is byte-for-byte identical to what run_ma_detection()
does at inference. Only Stage B (the CNN false-positive reducer) is trained
here.

Data: IDRiD Segmentation set (folder A), 54 train / 27 test images, both with
per-pixel MA masks (81 total images with MA masks matches the Final Model
Stack's stated "IDRiD 81 MA-masked images"). The 27-image test set here is
IDRiD's own published segmentation test split — NOT the sealed grading-test
split (see docs/dataset_cards/audit_summary.md).

Labelling: for each classical candidate (row, col) on a TRAIN image, label it
TRUE MA if it falls within a small radius of any ground-truth MA pixel
(masks are dilated slightly to tolerate the classical extractor's centroid
not landing exactly on the annotated pixel), else FALSE POSITIVE. This is the
standard way to train an FP-reducer: the classifier only ever needs to
distinguish "candidate is near real GT" from "candidate is textural noise",
which is exactly what the classical extractor over-generates.

Evaluation: LESION-LEVEL FROC on the 27 held-out test images (connected
components of the dilated GT mask = "lesions"), sweeping the FP-reducer's
decision threshold — reporting sensitivity at 1/8, 1/4, 1/2, 1, 2, 4, 8 false
positives per image, per blueprint K.6 / the evidence review's stated
protocol. Average Dice/pixel-AUPR is NOT used as the headline metric (a few-
pixel-wide object makes pixel metrics unstable) — this matches the published
IDRiD-challenge convention this project is compared against.

Usage:
    python training/train_ma_detector.py --epochs 30
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.structure import _extract_candidates_tophat, _prepare_patch_input
from training.train_lesion import list_idrid_segmentation  # reuse the same IDRiD file listing

# Candidate-extraction parameters — must match what's written into
# models/ma_detector/metadata.json, since pipeline.structure.run_ma_detection()
# reads them from the contract at inference time, not from this script.
TOPHAT_DISK_RADIUS = 6
TOPHAT_THRESHOLD_FACTOR = 2.0
PATCH_SIZE = 32
GT_MATCH_RADIUS = 3  # pixels — tolerance between a candidate centroid and the nearest GT MA pixel


def load_canonical_image_and_ma_mask(img_path: Path, ma_mask_path, preprocessing_config: Path):
    """Returns (preprocessed_image HWC float32 [0,1] 512x512, ma_mask_binary HW uint8 512x512 aligned to it)."""
    import cv2
    from pipeline.preprocessing import resize, apply_clahe, load_config

    config = load_config(preprocessing_config)
    bgr = cv2.imread(str(img_path), cv2.IMREAD_COLOR)
    raw_rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

    if ma_mask_path is not None:
        raw_mask = cv2.imread(str(ma_mask_path), cv2.IMREAD_GRAYSCALE)
        raw_mask = (raw_mask > 0).astype(np.uint8)
    else:
        raw_mask = np.zeros(raw_rgb.shape[:2], dtype=np.uint8)

    fov_cfg = config.get("fov_crop", {})
    threshold = fov_cfg.get("threshold", 10)
    gray = cv2.cvtColor(raw_rgb, cv2.COLOR_RGB2GRAY)
    fov_mask = gray > threshold
    ys, xs = np.where(fov_mask)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    cropped_img = raw_rgb[y0:y1, x0:x1]
    cropped_mask = raw_mask[y0:y1, x0:x1]

    target_size = config.get("target_size", [512, 512])
    resized_img = resize(cropped_img, target_size)
    resized_mask = cv2.resize(cropped_mask, (target_size[1], target_size[0]), interpolation=cv2.INTER_NEAREST)

    clahe_cfg = config.get("clahe", {})
    enhanced_img = apply_clahe(resized_img, clip_limit=clahe_cfg.get("clip_limit", 2.0),
                                tile_grid_size=clahe_cfg.get("tile_grid_size", [8, 8]))
    img_float = enhanced_img.astype(np.float32) / 255.0
    return img_float, resized_mask


def get_ma_mask_path(image_id: str, split: str):
    from training.train_lesion import SEG_ROOT
    p = SEG_ROOT / "2. All Segmentation Groundtruths" / split / "1. Microaneurysms" / f"{image_id}_MA.tif"
    return p if p.is_file() else None


def label_candidates(candidates: List[Tuple[int, int]], dilated_mask: np.ndarray) -> List[int]:
    return [1 if dilated_mask[r, c] > 0 else 0 for (r, c) in candidates]


def connected_components(mask: np.ndarray) -> List[np.ndarray]:
    """Returns a list of boolean masks, one per connected component (a 'lesion')."""
    import cv2
    n_labels, labels = cv2.connectedComponents(mask.astype(np.uint8))
    return [labels == i for i in range(1, n_labels)]


class PatchDataset:
    def __init__(self, patches: np.ndarray, labels: np.ndarray):
        self.patches = patches  # (N, patch, patch, 3) float32 [0,1]
        self.labels = labels

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        import torch
        patch = self.patches[idx]
        tensor = torch.from_numpy(np.transpose(patch, (2, 0, 1))).float()
        return tensor, int(self.labels[idx])


def build_fp_reducer_cnn():
    import torch.nn as nn

    class SmallCNN(nn.Module):
        def __init__(self):
            super().__init__()
            self.features = nn.Sequential(
                nn.Conv2d(3, 16, 3, padding=1), nn.BatchNorm2d(16), nn.ReLU(inplace=True), nn.MaxPool2d(2),
                nn.Conv2d(16, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(inplace=True), nn.MaxPool2d(2),
                nn.Conv2d(32, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(inplace=True), nn.AdaptiveAvgPool2d(4),
            )
            self.classifier = nn.Sequential(
                nn.Flatten(), nn.Linear(64 * 4 * 4, 64), nn.ReLU(inplace=True),
                nn.Dropout(0.3), nn.Linear(64, 2),
            )

        def forward(self, x):
            import torch
            logits = self.classifier(self.features(x))
            return torch.softmax(logits, dim=1)  # baked-in softmax — matches contract output_format="softmax"

    return SmallCNN()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--max-negatives-per-image", type=int, default=60,
                         help="Cap classical-extractor false positives per training image (extreme imbalance otherwise)")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is not available — refusing to silently fall back to CPU.")
    device = torch.device("cuda")
    print(f"Device: {device} ({torch.cuda.get_device_name(0)})")

    preprocessing_config = PROJECT_ROOT / "configs" / "preprocessing.json"
    train_items = list_idrid_segmentation("a. Training Set")
    test_items = list_idrid_segmentation("b. Testing Set")
    print(f"IDRiD segmentation: {len(train_items)} train / {len(test_items)} test images "
          f"(candidate labelling uses MA masks on both)")

    # ---- Generate training patches by running the REAL candidate extractor ----
    print("\n=== Generating training patches via pipeline.structure's classical extractor ===")
    all_patches, all_labels = [], []
    n_pos_total, n_neg_total = 0, 0
    for image_id, img_path, _ in train_items:
        ma_mask_path = get_ma_mask_path(image_id, "a. Training Set")
        img, mask = load_canonical_image_and_ma_mask(img_path, ma_mask_path, preprocessing_config)
        candidates = _extract_candidates_tophat(img, disk_radius=TOPHAT_DISK_RADIUS,
                                                 threshold_factor=TOPHAT_THRESHOLD_FACTOR)
        import cv2
        dilated = cv2.dilate(mask, np.ones((2 * GT_MATCH_RADIUS + 1, 2 * GT_MATCH_RADIUS + 1), np.uint8))
        labels = label_candidates(candidates, dilated)

        pos_idx = [i for i, l in enumerate(labels) if l == 1]
        neg_idx = [i for i, l in enumerate(labels) if l == 0]
        if len(neg_idx) > args.max_negatives_per_image:
            neg_idx = list(np.random.choice(neg_idx, args.max_negatives_per_image, replace=False))

        contract_stub = {"normalization": {"mean": [0.0, 0.0, 0.0], "std": [1.0, 1.0, 1.0]}}
        for i in pos_idx + neg_idx:
            row, col = candidates[i]
            patch = _prepare_patch_input(img, row, col, PATCH_SIZE, contract_stub)
            if patch is None:
                continue
            patch_hwc = np.transpose(patch[0], (1, 2, 0))  # (patch, patch, 3)
            all_patches.append(patch_hwc)
            all_labels.append(labels[i])
        n_pos_total += len(pos_idx)
        n_neg_total += len(neg_idx)

    print(f"Total training patches: {len(all_patches)} ({n_pos_total} positive, {n_neg_total} negative, "
          f"pre-cap negatives may have been larger per image)")
    all_patches = np.array(all_patches, dtype=np.float32)
    all_labels = np.array(all_labels, dtype=np.int64)

    # ---- Train/val split of PATCHES (image-independent val comes from the FROC eval on test_items below) ----
    n = len(all_labels)
    perm = np.random.RandomState(args.seed).permutation(n)
    n_val = max(1, int(0.15 * n))
    val_idx, train_idx = perm[:n_val], perm[n_val:]

    train_ds = PatchDataset(all_patches[train_idx], all_labels[train_idx])
    val_ds = PatchDataset(all_patches[val_idx], all_labels[val_idx])
    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False, num_workers=0)

    class_counts = np.bincount(all_labels[train_idx], minlength=2).astype(np.float64)
    class_weights = class_counts.sum() / (2 * np.maximum(class_counts, 1))
    print(f"Patch class weights (train): {class_weights.tolist()}")

    model = build_fp_reducer_cnn().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    criterion = nn.NLLLoss(weight=torch.tensor(class_weights, dtype=torch.float32, device=device))

    out_dir = PROJECT_ROOT / "models" / "ma_detector"
    out_dir.mkdir(parents=True, exist_ok=True)
    ckpt_path = out_dir / "_best_checkpoint.pt"

    best_val_acc = -1.0
    best_epoch = -1
    history = []
    start_time = time.time()

    for epoch in range(1, args.epochs + 1):
        t0 = time.time()
        model.train()
        train_loss_sum, n_batches = 0.0, 0
        for patches, labels in train_loader:
            patches, labels = patches.to(device), labels.to(device)
            optimizer.zero_grad()
            probs = model(patches)
            loss = criterion(torch.log(probs.clamp_min(1e-12)), labels)
            loss.backward()
            optimizer.step()
            train_loss_sum += loss.item()
            n_batches += 1

        model.eval()
        correct, total = 0, 0
        with torch.no_grad():
            for patches, labels in val_loader:
                patches, labels = patches.to(device), labels.to(device)
                probs = model(patches)
                preds = probs.argmax(dim=1)
                correct += (preds == labels).sum().item()
                total += labels.size(0)
        val_acc = correct / max(total, 1)
        epoch_time = time.time() - t0

        if epoch % 5 == 0 or epoch == 1:
            print(f"[epoch {epoch}/{args.epochs}] train_loss={train_loss_sum/n_batches:.4f} "
                  f"val_patch_acc={val_acc:.4f} ({epoch_time:.1f}s)")
        history.append({"epoch": epoch, "train_loss": train_loss_sum / n_batches,
                         "val_patch_accuracy": val_acc, "epoch_time_sec": epoch_time})

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            best_epoch = epoch
            torch.save(model.state_dict(), ckpt_path)

    total_time = time.time() - start_time
    print(f"\nBest epoch: {best_epoch} (val patch acc={best_val_acc:.4f}). Training time: {total_time/60:.1f} min.")
    model.load_state_dict(torch.load(ckpt_path, map_location=device))
    model.eval()

    # ---- ONNX export ----
    dummy = torch.randn(1, 3, PATCH_SIZE, PATCH_SIZE, device=device)
    onnx_path = out_dir / "ma_fp_reducer.onnx"
    model_cpu = model.cpu().eval()
    torch.onnx.export(
        model_cpu, dummy.cpu(), str(onnx_path),
        input_names=["input"], output_names=["probs"],
        opset_version=17, dynamic_axes=None, dynamo=False,
    )
    print(f"Wrote {onnx_path}")

    onnx_parity = {}
    try:
        import onnxruntime as ort
        session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
        ort_out = session.run(["probs"], {"input": dummy.cpu().numpy()})[0]
        with torch.no_grad():
            torch_out = model_cpu(dummy.cpu()).numpy()
        diff = float(np.max(np.abs(ort_out - torch_out)))
        onnx_parity = {"max_abs_diff": diff}
        print(f"ONNX <-> PyTorch max abs diff: {diff:.6f}")
    except ImportError:
        pass

    # ---- Write contract BEFORE FROC eval, so pipeline.structure functions can be
    # exercised through the real contract during evaluation (fresh-process style) ----
    metadata = {
        "model_name": "ma_hybrid_tophat_cnn",
        "model_version": "1.0.0",
        "input_size": [512, 512],
        "channels": 3,
        "normalization": {"mean": [0.0, 0.0, 0.0], "std": [1.0, 1.0, 1.0]},
        "model_file": "ma_fp_reducer.onnx",
        "framework": "onnx",
        "training_dataset": (
            f"IDRiD Segmentation MA masks: {len(train_items)} train images used to generate "
            f"labelled candidate patches ({n_pos_total} positive / capped negatives per image); "
            f"{len(test_items)} test images used for lesion-level FROC evaluation below "
            "(IDRiD's own published segmentation test split, NOT the sealed grading-test split)."
        ),
        "preprocessing": ["fov_crop", "resize", "clahe", "normalize"],
        "eval_metrics": {},  # filled in after FROC eval below
        "candidate_extraction_method": "top_hat",
        "tophat_disk_radius": TOPHAT_DISK_RADIUS,
        "tophat_threshold_factor": TOPHAT_THRESHOLD_FACTOR,
        "fp_reducer_model_file": "ma_fp_reducer.onnx",
        "patch_size": PATCH_SIZE,
        "ma_positive_class_index": 1,
        "output_format": "softmax",
        "threshold": 0.5,
    }

    # ---- Lesion-level FROC on the 27-image test split (real pipeline.structure call) ----
    print("\n=== Lesion-level FROC evaluation on IDRiD segmentation test set (27 images) ===")
    meta_path = out_dir / "metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    from pipeline.contract import load_contract
    contract = load_contract(out_dir, "ma_detector")

    fp_targets = [1 / 8, 1 / 4, 1 / 2, 1, 2, 4, 8]
    per_image_results = []
    for image_id, img_path, _ in test_items:
        ma_mask_path = get_ma_mask_path(image_id, "b. Testing Set")
        img, mask = load_canonical_image_and_ma_mask(img_path, ma_mask_path, preprocessing_config)
        candidates = _extract_candidates_tophat(img, disk_radius=TOPHAT_DISK_RADIUS,
                                                 threshold_factor=TOPHAT_THRESHOLD_FACTOR)
        import cv2
        dilated = cv2.dilate(mask, np.ones((2 * GT_MATCH_RADIUS + 1, 2 * GT_MATCH_RADIUS + 1), np.uint8))
        lesions = connected_components(dilated)  # ground-truth "lesions" for this image

        # Score every candidate with the trained FP-reducer (probability of being a true MA)
        scored = []
        for (row, col) in candidates:
            patch = _prepare_patch_input(img, row, col, PATCH_SIZE, contract)
            if patch is None:
                continue
            with torch.no_grad():
                t = torch.from_numpy(patch).float()
                prob = model_cpu(t).numpy()[0, 1]
            scored.append((row, col, float(prob)))
        per_image_results.append({"lesions": lesions, "scored_candidates": scored})

    froc_report = {}
    for target_fp in fp_targets:
        # Find the score threshold that yields (approximately) target_fp average FPs/image
        all_scores = sorted({s for r in per_image_results for (_, _, s) in r["scored_candidates"]}, reverse=True)
        best_thresh, best_sens, best_fp = 0.5, 0.0, None
        for thresh in [1.01] + all_scores + [0.0]:
            total_lesions, detected_lesions, total_fp = 0, 0, 0
            for r in per_image_results:
                hit = np.zeros(len(r["lesions"]), dtype=bool)
                for (row, col, score) in r["scored_candidates"]:
                    if score >= thresh:
                        matched = False
                        for li, lesion_mask in enumerate(r["lesions"]):
                            if lesion_mask[row, col]:
                                hit[li] = True
                                matched = True
                                break
                        if not matched:
                            total_fp += 1
                total_lesions += len(r["lesions"])
                detected_lesions += int(hit.sum())
            fp_per_image = total_fp / max(len(per_image_results), 1)
            sens = detected_lesions / max(total_lesions, 1)
            if fp_per_image <= target_fp and sens >= best_sens:
                best_sens, best_thresh, best_fp = sens, thresh, fp_per_image
        froc_report[f"sens_at_{target_fp}_fp_per_image"] = {
            "sensitivity": best_sens, "actual_fp_per_image": best_fp, "threshold": best_thresh,
        }
        print(f"  Sensitivity at <= {target_fp} FP/image: {best_sens:.3f} "
              f"(actual {best_fp}, threshold {best_thresh:.3f})" if best_fp is not None else
              f"  Sensitivity at <= {target_fp} FP/image: unreachable")

    metadata["eval_metrics"] = {
        "froc": froc_report,
        "n_test_images": len(test_items),
        "onnx_parity": onnx_parity,
        "best_val_patch_accuracy": best_val_acc,
        "best_epoch": best_epoch,
        "total_epochs_run": len(history),
        "total_training_time_minutes": total_time / 60.0,
        "gpu": torch.cuda.get_device_name(0),
        "note": (
            "FROC computed with the SAME classical extractor + patch preparation as "
            "pipeline.structure.run_ma_detection() (imported directly, not reimplemented). "
            "FROC numbers depend on the fixed connected-component protocol used here "
            f"(GT dilated by {GT_MATCH_RADIUS}px) — see training/train_ma_detector.py."
        ),
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    print(f"Wrote {meta_path}")

    history_path = out_dir / "training_history.json"
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump({"args": vars(args), "history": history}, f, indent=2)
    print(f"Wrote {history_path}")


if __name__ == "__main__":
    main()
