"""
training/train_lesion.py — NETRA-DR Phase 2 lesion segmentation training
(Final Model Stack Stage 5). Training-side only, never imported by app/ or
pipeline/. Fills pipeline/structure.py's run_lesion_segmentation() contract
(models/lesion_seg/, type "segmentation", 3-channel output [HE, EX, SE]).

Data: IDRiD Segmentation set (folder A) — 54 training / 27 testing images with
pixel masks for Haemorrhages (HE), Hard Exudates (EX), Soft Exudates (SE).
This is the PUBLISHED IDRiD segmentation train/test split (NOT the IDRiD
grading test split, which is the project's separate sealed set — see
docs/dataset_cards/audit_summary.md). The 27-image segmentation test set is
used here as validation, per the dataset's own standard usage.

A missing mask file for an image means "no lesion of that type present" (SE
masks especially — only ~half of images have soft exudates) and is treated as
an all-zero mask, not an error or a skipped image (blueprint: no silent drops).

Architecture: same compact U-Net family as training/train_vessel.py, adapted
to a 3-channel sigmoid output (multi-label, not softmax — HE/EX/SE regions
can be spatially independent and are never merged per project rules). Global
resize to 512x512 (same canonical space as the rest of the pipeline) rather
than native-resolution patch training — documented deviation from blueprint
K.7's stated preference, driven by the time budget for this run; IDRiD's
native 4288x2848 is ~8x this resolution, so this materially reduces fine
lesion boundary detail (acceptable for HE/EX which are usually larger lesions;
microaneurysms are handled separately by training/train_ma_detector.py, not
by this model).

Usage:
    python training/train_lesion.py --epochs 150
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

SEG_ROOT = PROJECT_ROOT / "data" / "raw" / "idrid" / "A_segmentation" / "A. Segmentation"
MASK_DIR_NAMES = {"HE": "2. Haemorrhages", "EX": "3. Hard Exudates", "SE": "4. Soft Exudates"}
LABEL_ORDER = ["HE", "EX", "SE"]  # fixed channel order — written into mask_labels in metadata.json


def list_idrid_segmentation(split: str) -> List[Tuple[str, Path, Dict[str, Optional[Path]]]]:
    """split: 'a. Training Set' or 'b. Testing Set'. Returns [(image_id, image_path, {label: mask_path_or_None})]."""
    img_dir = SEG_ROOT / "1. Original Images" / split
    gt_dir = SEG_ROOT / "2. All Segmentation Groundtruths" / split
    items = []
    for img_path in sorted(img_dir.glob("*.jpg")):
        image_id = img_path.stem
        masks = {}
        for label, dirname in MASK_DIR_NAMES.items():
            mask_path = gt_dir / dirname / f"{image_id}_{label}.tif"
            masks[label] = mask_path if mask_path.is_file() else None
        items.append((image_id, img_path, masks))
    return items


class LesionDataset:
    """Module-level (Windows spawn-safe)."""

    def __init__(self, items, image_size: int, augment: bool, preprocessing_config: Path):
        self.items = items
        self.image_size = image_size
        self.augment = augment
        self.preprocessing_config = preprocessing_config

    def __len__(self):
        return len(self.items)

    def __getitem__(self, idx):
        import cv2
        import torch
        from pipeline.preprocessing import resize, apply_clahe, load_config

        image_id, img_path, mask_paths = self.items[idx]
        config = load_config(self.preprocessing_config)

        bgr = cv2.imread(str(img_path), cv2.IMREAD_COLOR)
        if bgr is None:
            raise ValueError(f"OpenCV failed to decode {img_path}")
        raw_rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

        raw_masks = {}
        for label in LABEL_ORDER:
            mp = mask_paths[label]
            if mp is not None:
                m = cv2.imread(str(mp), cv2.IMREAD_GRAYSCALE)
                raw_masks[label] = (m > 0).astype(np.uint8)
            else:
                raw_masks[label] = np.zeros(raw_rgb.shape[:2], dtype=np.uint8)

        fov_cfg = config.get("fov_crop", {})
        threshold = fov_cfg.get("threshold", 10)
        gray = cv2.cvtColor(raw_rgb, cv2.COLOR_RGB2GRAY)
        fov_mask = gray > threshold
        ys, xs = np.where(fov_mask)
        y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        cropped_img = raw_rgb[y0:y1, x0:x1]

        target_size = config.get("target_size", [512, 512])
        resized_img = resize(cropped_img, target_size)
        clahe_cfg = config.get("clahe", {})
        enhanced_img = apply_clahe(resized_img, clip_limit=clahe_cfg.get("clip_limit", 2.0),
                                    tile_grid_size=clahe_cfg.get("tile_grid_size", [8, 8]))
        img = enhanced_img.astype(np.float32) / 255.0

        resized_masks = []
        for label in LABEL_ORDER:
            cropped_mask = raw_masks[label][y0:y1, x0:x1]
            rm = cv2.resize(cropped_mask, (target_size[1], target_size[0]), interpolation=cv2.INTER_NEAREST)
            resized_masks.append(rm)
        mask_stack = np.stack(resized_masks, axis=-1).astype(np.float32)  # HWC (3 channels)

        if self.image_size != target_size[0]:
            img = cv2.resize(img, (self.image_size, self.image_size), interpolation=cv2.INTER_AREA)
            mask_stack = cv2.resize(mask_stack, (self.image_size, self.image_size), interpolation=cv2.INTER_NEAREST)
            if mask_stack.ndim == 2:  # cv2 drops the channel dim if it becomes 1
                mask_stack = mask_stack[:, :, np.newaxis]

        if self.augment:
            if np.random.rand() < 0.5:
                img, mask_stack = img[:, ::-1].copy(), mask_stack[:, ::-1].copy()
            if np.random.rand() < 0.5:
                img, mask_stack = img[::-1, :].copy(), mask_stack[::-1, :].copy()
            k = np.random.randint(0, 4)
            img, mask_stack = np.rot90(img, k).copy(), np.rot90(mask_stack, k).copy()

        img_t = torch.from_numpy(np.transpose(img, (2, 0, 1))).float()
        mask_t = torch.from_numpy(np.transpose(mask_stack, (2, 0, 1))).float()  # (3, H, W)
        return img_t, mask_t


def build_unet(out_channels: int = 3):
    import torch.nn as nn

    def conv_block(in_c, out_c):
        return nn.Sequential(
            nn.Conv2d(in_c, out_c, 3, padding=1), nn.BatchNorm2d(out_c), nn.ReLU(inplace=True),
            nn.Conv2d(out_c, out_c, 3, padding=1), nn.BatchNorm2d(out_c), nn.ReLU(inplace=True),
        )

    class UNet(nn.Module):
        def __init__(self, base=32):
            super().__init__()
            self.enc1 = conv_block(3, base)
            self.enc2 = conv_block(base, base * 2)
            self.enc3 = conv_block(base * 2, base * 4)
            self.enc4 = conv_block(base * 4, base * 8)
            self.pool = nn.MaxPool2d(2)
            self.bottleneck = conv_block(base * 8, base * 16)
            self.up4 = nn.ConvTranspose2d(base * 16, base * 8, 2, stride=2)
            self.dec4 = conv_block(base * 16, base * 8)
            self.up3 = nn.ConvTranspose2d(base * 8, base * 4, 2, stride=2)
            self.dec3 = conv_block(base * 8, base * 4)
            self.up2 = nn.ConvTranspose2d(base * 4, base * 2, 2, stride=2)
            self.dec2 = conv_block(base * 4, base * 2)
            self.up1 = nn.ConvTranspose2d(base * 2, base, 2, stride=2)
            self.dec1 = conv_block(base * 2, base)
            self.out_conv = nn.Conv2d(base, out_channels, 1)

        def forward(self, x):
            import torch
            e1 = self.enc1(x)
            e2 = self.enc2(self.pool(e1))
            e3 = self.enc3(self.pool(e2))
            e4 = self.enc4(self.pool(e3))
            b = self.bottleneck(self.pool(e4))
            d4 = self.dec4(torch.cat([self.up4(b), e4], dim=1))
            d3 = self.dec3(torch.cat([self.up3(d4), e3], dim=1))
            d2 = self.dec2(torch.cat([self.up2(d3), e2], dim=1))
            d1 = self.dec1(torch.cat([self.up1(d2), e1], dim=1))
            logits = self.out_conv(d1)
            return torch.sigmoid(logits)  # per-channel independent probabilities (multi-label)

    return UNet()


def dice_loss_multilabel(pred, target, eps=1e-6):
    # Per-channel Dice, averaged — channels are independent (multi-label).
    pred_flat = pred.reshape(pred.size(0), pred.size(1), -1)
    target_flat = target.reshape(target.size(0), target.size(1), -1)
    intersection = (pred_flat * target_flat).sum(dim=2)
    denom = pred_flat.sum(dim=2) + target_flat.sum(dim=2)
    dice = (2 * intersection + eps) / (denom + eps)
    return 1 - dice.mean()


def dice_per_channel(pred_binary: np.ndarray, target: np.ndarray) -> np.ndarray:
    # pred_binary, target: (C, H, W)
    dices = []
    for c in range(pred_binary.shape[0]):
        inter = np.sum(pred_binary[c] * target[c])
        denom = np.sum(pred_binary[c]) + np.sum(target[c])
        if target[c].sum() == 0 and pred_binary[c].sum() == 0:
            dices.append(np.nan)  # no lesion present and none predicted — undefined, exclude from mean
        else:
            dices.append((2 * inter + 1e-6) / (denom + 1e-6))
    return np.array(dices)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image-size", type=int, default=512)
    parser.add_argument("--epochs", type=int, default=150)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--patience", type=int, default=25)
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

    train_items = list_idrid_segmentation("a. Training Set")
    val_items = list_idrid_segmentation("b. Testing Set")
    print(f"IDRiD segmentation: {len(train_items)} train / {len(val_items)} val "
          f"(published train/test split, NOT the sealed grading-test split)")
    for label in LABEL_ORDER:
        n_train_pos = sum(1 for _, _, m in train_items if m[label] is not None)
        n_val_pos = sum(1 for _, _, m in val_items if m[label] is not None)
        print(f"  {label}: {n_train_pos}/{len(train_items)} train images have a mask, "
              f"{n_val_pos}/{len(val_items)} val images")

    preprocessing_config = PROJECT_ROOT / "configs" / "preprocessing.json"
    train_ds = LesionDataset(train_items, args.image_size, augment=True, preprocessing_config=preprocessing_config)
    val_ds = LesionDataset(val_items, args.image_size, augment=False, preprocessing_config=preprocessing_config)

    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=1, shuffle=False, num_workers=0)

    model = build_unet(out_channels=3).to(device)
    print(f"Model params: {sum(p.numel() for p in model.parameters()):,}")

    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-5)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)
    bce = nn.BCELoss()

    out_dir = PROJECT_ROOT / "models" / "lesion_seg"
    out_dir.mkdir(parents=True, exist_ok=True)
    ckpt_path = out_dir / "_best_checkpoint.pt"

    best_mean_dice = -1.0
    best_epoch = -1
    epochs_without_improvement = 0
    history = []
    start_time = time.time()

    for epoch in range(1, args.epochs + 1):
        t0 = time.time()
        model.train()
        train_loss_sum, n_batches = 0.0, 0
        for images, masks in train_loader:
            images, masks = images.to(device), masks.to(device)
            optimizer.zero_grad()
            preds = model(images)
            loss = bce(preds, masks) + dice_loss_multilabel(preds, masks)
            loss.backward()
            optimizer.step()
            train_loss_sum += loss.item()
            n_batches += 1
        scheduler.step()

        model.eval()
        per_channel_dices = []
        with torch.no_grad():
            for images, masks in val_loader:
                images = images.to(device)
                pred = model(images).cpu().numpy()[0]  # (3, H, W)
                target = masks.numpy()[0]
                pred_binary = (pred >= 0.5).astype(np.uint8)
                per_channel_dices.append(dice_per_channel(pred_binary, target))

        per_channel_dices = np.array(per_channel_dices)  # (n_val, 3)
        mean_dice_per_class = np.nanmean(per_channel_dices, axis=0)
        overall_mean_dice = float(np.nanmean(mean_dice_per_class))
        epoch_time = time.time() - t0

        if epoch % 10 == 0 or epoch == 1:
            print(f"[epoch {epoch}/{args.epochs}] train_loss={train_loss_sum/n_batches:.4f} "
                  f"val_dice(HE/EX/SE)={mean_dice_per_class[0]:.3f}/{mean_dice_per_class[1]:.3f}/"
                  f"{mean_dice_per_class[2]:.3f} mean={overall_mean_dice:.4f} ({epoch_time:.1f}s)")

        history.append({"epoch": epoch, "train_loss": train_loss_sum / n_batches,
                         "val_dice_he": float(mean_dice_per_class[0]),
                         "val_dice_ex": float(mean_dice_per_class[1]),
                         "val_dice_se": float(mean_dice_per_class[2]),
                         "val_mean_dice": overall_mean_dice, "epoch_time_sec": epoch_time})

        if overall_mean_dice > best_mean_dice:
            best_mean_dice = overall_mean_dice
            best_epoch = epoch
            epochs_without_improvement = 0
            torch.save(model.state_dict(), ckpt_path)
        else:
            epochs_without_improvement += 1
        if epochs_without_improvement >= args.patience:
            print(f"No mean-Dice improvement for {args.patience} epochs, early stopping after epoch {epoch}.")
            break

    total_time = time.time() - start_time
    print(f"\nBest epoch: {best_epoch} (mean Dice={best_mean_dice:.4f}). Training time: {total_time/60:.1f} min.")
    model.load_state_dict(torch.load(ckpt_path, map_location=device))
    model.eval()

    per_channel_dices = []
    with torch.no_grad():
        for images, masks in val_loader:
            images = images.to(device)
            pred = model(images).cpu().numpy()[0]
            target = masks.numpy()[0]
            pred_binary = (pred >= 0.5).astype(np.uint8)
            per_channel_dices.append(dice_per_channel(pred_binary, target))
    per_channel_dices = np.array(per_channel_dices)
    final_dice_per_class = np.nanmean(per_channel_dices, axis=0)
    print(f"Final Dice — HE: {final_dice_per_class[0]:.4f}  EX: {final_dice_per_class[1]:.4f}  "
          f"SE: {final_dice_per_class[2]:.4f}")

    dummy = torch.randn(1, 3, args.image_size, args.image_size, device=device)
    onnx_path = out_dir / "lesion_model.onnx"
    model_cpu = model.cpu().eval()
    torch.onnx.export(
        model_cpu, dummy.cpu(), str(onnx_path),
        input_names=["input"], output_names=["lesion_probs"],
        opset_version=17, dynamic_axes=None, dynamo=False,
    )
    print(f"Wrote {onnx_path}")

    onnx_parity = {}
    try:
        import onnxruntime as ort
        session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
        ort_out = session.run(["lesion_probs"], {"input": dummy.cpu().numpy()})[0]
        with torch.no_grad():
            torch_out = model_cpu(dummy.cpu()).numpy()
        diff = float(np.max(np.abs(ort_out - torch_out)))
        onnx_parity = {"max_abs_diff": diff}
        print(f"ONNX <-> PyTorch max abs diff: {diff:.6f}")
    except ImportError:
        print("onnxruntime not installed — skipping export sanity check.")

    metadata = {
        "model_name": "unet_lesion_seg_he_ex_se",
        "model_version": "1.0.0",
        "input_size": [args.image_size, args.image_size],
        "channels": 3,
        "normalization": {"mean": [0.0, 0.0, 0.0], "std": [1.0, 1.0, 1.0]},
        "model_file": "lesion_model.onnx",
        "framework": "onnx",
        "training_dataset": (
            f"IDRiD Segmentation (folder A) published train/test split: "
            f"{len(train_items)} train, {len(val_items)} val (val = IDRiD's own "
            f"'Testing Set', NOT the sealed grading-test split). Missing mask files "
            f"(e.g. many images have no Soft Exudates) treated as all-zero, not dropped."
        ),
        "preprocessing": ["fov_crop", "resize", "clahe", "normalize", "resize_to_input_size"],
        "eval_metrics": {
            "val_dice_he": float(final_dice_per_class[0]),
            "val_dice_ex": float(final_dice_per_class[1]),
            "val_dice_se": float(final_dice_per_class[2]),
            "best_epoch": best_epoch,
            "total_epochs_run": len(history),
            "total_training_time_minutes": total_time / 60.0,
            "n_train_images": len(train_items),
            "n_val_images": len(val_items),
            "gpu": torch.cuda.get_device_name(0),
            "onnx_parity": onnx_parity,
            "note": (
                "Dice computed only over images where either ground truth or prediction is "
                "non-empty for that class (images with neither are excluded, not counted as "
                "perfect). SE has far fewer positive examples than HE/EX (see 'training_dataset') "
                "so its Dice is measured on a smaller effective sample."
            ),
        },
        "mask_labels": LABEL_ORDER,
        "output_format": "multi_channel_mask",
        "mask_resolution": [args.image_size, args.image_size],
        "he_presence_threshold": 50,
        "threshold": 0.5,
    }
    meta_path = out_dir / "metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    print(f"Wrote {meta_path}")

    history_path = out_dir / "training_history.json"
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump({"args": vars(args), "history": history}, f, indent=2)
    print(f"Wrote {history_path}")


if __name__ == "__main__":
    main()
