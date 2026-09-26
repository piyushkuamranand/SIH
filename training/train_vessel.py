"""
training/train_vessel.py — NETRA-DR Phase 2 vessel segmentation training
(Final Model Stack Stage 3). Training-side only, never imported by app/ or
pipeline/. Fills pipeline/structure.py's run_vessel_segmentation() contract
(models/vessel_seg/, type "segmentation").

Data: DRIVE (20 training images + 1st-observer manual masks). DRIVE's 20
training images are one eye per subject (40 total subjects across train+test)
— an image-level split of these 20 IS a patient-level split, unlike APTOS/IDRiD
grading. The 20-image "test" folder has no publicly distributed vessel ground
truth in this download (see docs/dataset_cards/audit_report.json), so model
selection uses a held-out subset of the 20 training images instead.

Architecture: compact U-Net (4 down/up blocks, ~2M params — small by design:
20 training images cannot support a large network without overfitting),
trained on the SAME 512x512 canonical preprocessing space
(pipeline.preprocessing.preprocess()) the rest of the pipeline uses, so
train/serve resolution matches exactly (DRIVE's native 565x584 is close to
512x512 — a full patch-based native-resolution pipeline was not built given
the time budget for this run; documented as a deviation from blueprint K.5's
stated preference, not hidden).

Loss: BCE + Dice (standard for extreme foreground/background imbalance —
vessels are a small fraction of pixels). Sigmoid baked into the exported ONNX
graph so the single output is already a probability map, matching
pipeline/structure.py's _threshold_to_binary_mask() contract.

Metrics: Dice AND thin-vessel sensitivity (recall restricted to thin
skeleton pixels, via mask erosion-based width estimate) — average Dice alone
hides thin-vessel failure (blueprint K.5 / evidence review Section 2).

Usage:
    python training/train_vessel.py --epochs 150
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

DRIVE_TRAIN_IMG = PROJECT_ROOT / "data" / "raw" / "drive" / "training" / "training" / "images"
DRIVE_TRAIN_MASK = PROJECT_ROOT / "data" / "raw" / "drive" / "training" / "training" / "1st_manual"


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

def list_drive_pairs() -> List[Tuple[Path, Path]]:
    pairs = []
    for img_path in sorted(DRIVE_TRAIN_IMG.glob("*.tif")):
        stem = img_path.stem.replace("_training", "")
        mask_path = DRIVE_TRAIN_MASK / f"{stem}_manual1.gif"
        if mask_path.is_file():
            pairs.append((img_path, mask_path))
    return pairs


class VesselDataset:
    """Module-level (not nested) — required for Windows spawn-based DataLoader workers."""

    def __init__(self, pairs: List[Tuple[Path, Path]], image_size: int, augment: bool,
                 preprocessing_config: Path):
        self.pairs = pairs
        self.image_size = image_size
        self.augment = augment
        self.preprocessing_config = preprocessing_config

    def __len__(self):
        return len(self.pairs)

    def __getitem__(self, idx):
        import cv2
        import torch
        from PIL import Image
        from pipeline.preprocessing import resize, apply_clahe, load_config

        img_path, mask_path = self.pairs[idx]
        config = load_config(self.preprocessing_config)

        # DRIVE's .tif images crash Pillow's convert('RGB') natively on this
        # Windows/libtiff build (silently kills the process — no Python
        # exception, no traceback, buffered stdout lost). cv2.imread() decodes
        # the same files fine; use it instead of pipeline.preprocessing.load_image()
        # for this one dataset. The mask (.gif, small, single-frame) is unaffected —
        # Pillow handles those normally.
        bgr = cv2.imread(str(img_path), cv2.IMREAD_COLOR)
        if bgr is None:
            raise ValueError(f"OpenCV failed to decode {img_path}")
        raw_rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        with Image.open(mask_path) as m:
            raw_mask = np.array(m.convert("L"), dtype=np.uint8)

        # Apply the SAME fov_crop as pipeline.preprocessing.preprocess(), but to
        # image+mask jointly (crop_fov alone would desync mask<->image sizes).
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
        resized_mask = cv2.resize(cropped_mask, (target_size[1], target_size[0]),
                                   interpolation=cv2.INTER_NEAREST)

        clahe_cfg = config.get("clahe", {})
        enhanced_img = apply_clahe(resized_img, clip_limit=clahe_cfg.get("clip_limit", 2.0),
                                    tile_grid_size=clahe_cfg.get("tile_grid_size", [8, 8]))

        img = enhanced_img.astype(np.float32) / 255.0  # HWC [0,1], matches preprocess() normalize step
        mask = (resized_mask > 127).astype(np.float32)  # HW binary

        if self.image_size != target_size[0]:
            img = cv2.resize(img, (self.image_size, self.image_size), interpolation=cv2.INTER_AREA)
            mask = cv2.resize(mask, (self.image_size, self.image_size), interpolation=cv2.INTER_NEAREST)

        if self.augment:
            if np.random.rand() < 0.5:
                img, mask = img[:, ::-1].copy(), mask[:, ::-1].copy()
            if np.random.rand() < 0.5:
                img, mask = img[::-1, :].copy(), mask[::-1, :].copy()
            k = np.random.randint(0, 4)
            img, mask = np.rot90(img, k).copy(), np.rot90(mask, k).copy()

        img_t = torch.from_numpy(np.transpose(img, (2, 0, 1))).float()
        mask_t = torch.from_numpy(mask).float().unsqueeze(0)
        return img_t, mask_t


# ---------------------------------------------------------------------------
# Compact U-Net
# ---------------------------------------------------------------------------

def build_unet():
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
            self.out_conv = nn.Conv2d(base, 1, 1)

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
            return torch.sigmoid(logits)  # baked-in sigmoid — ONNX output is already a probability map

    return UNet()


def dice_loss(pred, target, eps=1e-6):
    import torch
    pred_flat = pred.reshape(pred.size(0), -1)
    target_flat = target.reshape(target.size(0), -1)
    intersection = (pred_flat * target_flat).sum(dim=1)
    denom = pred_flat.sum(dim=1) + target_flat.sum(dim=1)
    dice = (2 * intersection + eps) / (denom + eps)
    return 1 - dice.mean()


def dice_coefficient(pred_binary: np.ndarray, target: np.ndarray) -> float:
    intersection = np.sum(pred_binary * target)
    denom = np.sum(pred_binary) + np.sum(target)
    return float((2 * intersection + 1e-6) / (denom + 1e-6))


def thin_vessel_sensitivity(pred_binary: np.ndarray, target: np.ndarray, thin_max_width: int = 3) -> float:
    """Sensitivity restricted to thin vessels: erode the ground-truth mask by
    (thin_max_width // 2) iterations and take target minus the eroded mask as
    the 'thin-vessel' pixel set (a standard cheap proxy for width-stratified
    evaluation without a distance-transform skeletonization dependency)."""
    import cv2
    target_u8 = (target * 255).astype(np.uint8)
    kernel = np.ones((3, 3), np.uint8)
    eroded = cv2.erode(target_u8, kernel, iterations=max(1, thin_max_width // 2))
    thin_mask = ((target_u8 > 0) & (eroded == 0)).astype(np.uint8)
    if thin_mask.sum() == 0:
        return float("nan")
    tp = np.sum((pred_binary > 0) & (thin_mask > 0))
    return float(tp) / float(thin_mask.sum())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image-size", type=int, default=512)
    parser.add_argument("--val-count", type=int, default=4, help="Held out from the 20 training images")
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

    pairs = list_drive_pairs()
    if len(pairs) != 20:
        print(f"WARNING: expected 20 DRIVE training pairs, found {len(pairs)}.")
    rng = np.random.RandomState(args.seed)
    order = rng.permutation(len(pairs))
    val_idx = set(order[:args.val_count].tolist())
    train_pairs = [p for i, p in enumerate(pairs) if i not in val_idx]
    val_pairs = [p for i, p in enumerate(pairs) if i in val_idx]
    print(f"DRIVE: {len(train_pairs)} train / {len(val_pairs)} val "
          f"(image-level split = patient-level here — DRIVE is one eye per subject)")

    preprocessing_config = PROJECT_ROOT / "configs" / "preprocessing.json"
    train_ds = VesselDataset(train_pairs, args.image_size, augment=True, preprocessing_config=preprocessing_config)
    val_ds = VesselDataset(val_pairs, args.image_size, augment=False, preprocessing_config=preprocessing_config)

    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=1, shuffle=False, num_workers=0)

    model = build_unet().to(device)
    n_params = sum(p.numel() for p in model.parameters())
    print(f"Model params: {n_params:,}")

    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-5)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)
    bce = nn.BCELoss()

    out_dir = PROJECT_ROOT / "models" / "vessel_seg"
    out_dir.mkdir(parents=True, exist_ok=True)
    ckpt_path = out_dir / "_best_checkpoint.pt"

    best_dice = -1.0
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
            loss = bce(preds, masks) + dice_loss(preds, masks)
            loss.backward()
            optimizer.step()
            train_loss_sum += loss.item()
            n_batches += 1
        scheduler.step()

        model.eval()
        dices, thin_sens = [], []
        with torch.no_grad():
            for images, masks in val_loader:
                images = images.to(device)
                pred = model(images).cpu().numpy()[0, 0]
                target = masks.numpy()[0, 0]
                pred_binary = (pred >= 0.5).astype(np.uint8)
                dices.append(dice_coefficient(pred_binary, target))
                ts = thin_vessel_sensitivity(pred_binary, target)
                if not np.isnan(ts):
                    thin_sens.append(ts)

        mean_dice = float(np.mean(dices)) if dices else 0.0
        mean_thin_sens = float(np.mean(thin_sens)) if thin_sens else float("nan")
        epoch_time = time.time() - t0

        if epoch % 10 == 0 or epoch == 1:
            print(f"[epoch {epoch}/{args.epochs}] train_loss={train_loss_sum/n_batches:.4f} "
                  f"val_dice={mean_dice:.4f} val_thin_vessel_sens={mean_thin_sens:.4f} ({epoch_time:.1f}s)")

        history.append({"epoch": epoch, "train_loss": train_loss_sum / n_batches,
                         "val_dice": mean_dice, "val_thin_vessel_sensitivity": mean_thin_sens,
                         "epoch_time_sec": epoch_time})

        if mean_dice > best_dice:
            best_dice = mean_dice
            best_epoch = epoch
            epochs_without_improvement = 0
            torch.save(model.state_dict(), ckpt_path)
        else:
            epochs_without_improvement += 1
        if epochs_without_improvement >= args.patience:
            print(f"No Dice improvement for {args.patience} epochs, early stopping after epoch {epoch}.")
            break

    total_time = time.time() - start_time
    print(f"\nBest epoch: {best_epoch} (Dice={best_dice:.4f}). Training time: {total_time/60:.1f} min.")
    model.load_state_dict(torch.load(ckpt_path, map_location=device))
    model.eval()

    # Final metrics with best checkpoint
    dices, thin_sens = [], []
    with torch.no_grad():
        for images, masks in val_loader:
            images = images.to(device)
            pred = model(images).cpu().numpy()[0, 0]
            target = masks.numpy()[0, 0]
            pred_binary = (pred >= 0.5).astype(np.uint8)
            dices.append(dice_coefficient(pred_binary, target))
            ts = thin_vessel_sensitivity(pred_binary, target)
            if not np.isnan(ts):
                thin_sens.append(ts)
    final_dice = float(np.mean(dices))
    final_thin_sens = float(np.mean(thin_sens)) if thin_sens else float("nan")
    print(f"Final: Dice={final_dice:.4f}  thin-vessel sensitivity={final_thin_sens:.4f}")

    # ---- ONNX export (single input, single sigmoid-probability output) ----
    dummy = torch.randn(1, 3, args.image_size, args.image_size, device=device)
    onnx_path = out_dir / "vessel_model.onnx"
    model_cpu = model.cpu().eval()
    torch.onnx.export(
        model_cpu, dummy.cpu(), str(onnx_path),
        input_names=["input"], output_names=["vessel_prob"],
        opset_version=17, dynamic_axes=None, dynamo=False,
    )
    print(f"Wrote {onnx_path}")

    onnx_parity = {}
    try:
        import onnxruntime as ort
        session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
        ort_out = session.run(["vessel_prob"], {"input": dummy.cpu().numpy()})[0]
        with torch.no_grad():
            torch_out = model_cpu(dummy.cpu()).numpy()
        diff = float(np.max(np.abs(ort_out - torch_out)))
        onnx_parity = {"max_abs_diff": diff}
        print(f"ONNX <-> PyTorch max abs diff: {diff:.6f}")
    except ImportError:
        print("onnxruntime not installed — skipping export sanity check.")

    metadata = {
        "model_name": "unet_vessel_seg",
        "model_version": "1.0.0",
        "input_size": [args.image_size, args.image_size],
        "channels": 3,
        "normalization": {"mean": [0.0, 0.0, 0.0], "std": [1.0, 1.0, 1.0]},
        "model_file": "vessel_model.onnx",
        "framework": "onnx",
        "training_dataset": (
            f"DRIVE (train={len(train_pairs)}, val={len(val_pairs)} of the 20-image training set; "
            "DRIVE test-set folder has no publicly distributed vessel ground truth in this download). "
            "Split is image-level, which IS patient-level here (DRIVE = one eye per subject)."
        ),
        "preprocessing": ["fov_crop", "resize", "clahe", "normalize", "resize_to_input_size"],
        "eval_metrics": {
            "val_dice": final_dice,
            "val_thin_vessel_sensitivity": final_thin_sens,
            "best_epoch": best_epoch,
            "total_epochs_run": len(history),
            "total_training_time_minutes": total_time / 60.0,
            "n_train_images": len(train_pairs),
            "n_val_images": len(val_pairs),
            "gpu": torch.cuda.get_device_name(0),
            "onnx_parity": onnx_parity,
            "note": (
                "Validated on a 4-image held-out subset of DRIVE's 20 training images (no vessel "
                "ground truth exists for DRIVE's test folder in this download). Not cross-checked "
                "against STARE/CHASE_DB1 (not downloaded)."
            ),
        },
        "mask_labels": ["vessel"],
        "output_format": "binary_mask",
        "mask_resolution": [args.image_size, args.image_size],
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
