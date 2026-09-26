"""
training/train_grading.py — NETRA-DR Phase 3 DR grading model training (Final Model
Stack Stage 7 + 9). Training-side only: never imported by app/ or pipeline/.

Trains an ICDR 0-4 severity classifier on the combined APTOS 2019 + IDRiD
grading-train split (training/prepare_grading_splits.py — DDR excluded per
instruction, IDRiD grading-test is the sealed set and is never read here),
fits temperature scaling on the validation split, and exports:

    models/grading/grading_model.onnx        — two ONNX outputs: logits, features
    models/grading/gradcam_fc_weights.npy    — final FC layer weights, for exact
                                                class activation mapping in pipeline/explain.py
    models/grading/metadata.json             — model contract (pipeline/contract.py)
    configs/calibration.json                 — fitted temperature scaling
    models/grading/training_history.json     — per-epoch metrics + run config

Train/serve preprocessing consistency: every image is passed through
pipeline.preprocessing.preprocess() (FOV crop -> resize -> CLAHE -> normalize)
via training/preprocessing_cache.py — the SAME function pipeline/quality.py
calls at inference — before augmentation and model-input resize/normalize.
This was a real bug in the previous version of this script (raw PIL resize,
no FOV crop/CLAHE) and is fixed here.

Architecture: ResNet-50, ImageNet-pretrained (torchvision), GPU (CUDA) training.
Body (conv1...layer4) -> global average pool -> single Linear head. This
GAP->FC structure is what makes the exact class activation mapping in
pipeline/explain.py valid (Zhou et al. 2016 CAM) with no backward pass needed
at inference — the FC layer's weight row for the predicted class is exported
alongside the model (gradcam_fc_weights.npy).

Usage:
    python training/train_grading.py --epochs 25 --backbone resnet50
"""

from __future__ import annotations

import argparse
import copy
import csv
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from training.metrics import (
    confusion_matrix,
    macro_f1,
    per_class_sensitivity_specificity,
    quadratic_weighted_kappa,
    referable_sensitivity_specificity,
)
from training.preprocessing_cache import get_canonical_image

IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]
NUM_CLASSES = 5


# ---------------------------------------------------------------------------
# Dataset — reads the combined split manifest, goes through the SAME
# canonical preprocessing the live app uses (see training/preprocessing_cache.py)
# ---------------------------------------------------------------------------

def _load_split(csv_path: Path) -> List[Dict]:
    with open(csv_path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class GradingDataset:
    """Module-level (not nested) so Windows' spawn-based multiprocessing can
    pickle it for DataLoader num_workers > 0 — a nested class defined inside a
    function cannot be pickled on Windows and crashes every worker process."""

    def __init__(self, rows: List[Dict], transform, preprocessing_config: Path):
        self.rows = rows
        self.transform = transform
        self.preprocessing_config = preprocessing_config

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, idx):
        from PIL import Image

        row = self.rows[idx]
        raw_path = PROJECT_ROOT / "data" / "raw" / row["image_path"]
        canonical = get_canonical_image(
            dataset=row["dataset"], item_id=row["id_code"], raw_path=raw_path,
            config_path=self.preprocessing_config,
        )  # HWC uint8, FOV-cropped + CLAHE'd + resized to configs/preprocessing.json target_size
        pil_img = Image.fromarray(canonical, mode="RGB")
        tensor = self.transform(pil_img)
        return tensor, int(row["diagnosis"])


def build_datasets(train_csv: Path, val_csv: Path, image_size: int, preprocessing_config: Path):
    from torchvision import transforms

    train_transform = transforms.Compose([
        transforms.Resize((image_size, image_size)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomVerticalFlip(),
        transforms.RandomRotation(25),
        transforms.ColorJitter(brightness=0.15, contrast=0.15),
        transforms.ToTensor(),
        transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
    ])
    val_transform = transforms.Compose([
        transforms.Resize((image_size, image_size)),
        transforms.ToTensor(),
        transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
    ])

    train_rows = _load_split(train_csv)
    val_rows = _load_split(val_csv)
    return (GradingDataset(train_rows, train_transform, preprocessing_config),
            GradingDataset(val_rows, val_transform, preprocessing_config))


# ---------------------------------------------------------------------------
# Model: backbone -> (feature_map before GAP, logits after GAP+FC)
# CAM-compatible by construction (Zhou et al. 2016) — see pipeline/explain.py.
# ---------------------------------------------------------------------------

def build_model(backbone: str, pretrained: bool, num_classes: int = NUM_CLASSES):
    import torch.nn as nn
    from torchvision import models

    if backbone == "resnet18":
        weights = models.ResNet18_Weights.IMAGENET1K_V1 if pretrained else None
        net = models.resnet18(weights=weights)
        feat_channels = 512
    elif backbone == "resnet50":
        weights = models.ResNet50_Weights.IMAGENET1K_V2 if pretrained else None
        net = models.resnet50(weights=weights)
        feat_channels = 2048
    else:
        raise ValueError(f"Unsupported backbone: {backbone}")

    body = nn.Sequential(net.conv1, net.bn1, net.relu, net.maxpool,
                          net.layer1, net.layer2, net.layer3, net.layer4)

    class GradableCAMNet(nn.Module):
        def __init__(self, body, feat_channels, num_classes):
            super().__init__()
            self.body = body
            self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
            self.fc = nn.Linear(feat_channels, num_classes)

        def forward(self, x):
            features = self.body(x)               # (N, C, h, w) — last conv block
            pooled = self.avgpool(features).flatten(1)  # (N, C)
            logits = self.fc(pooled)               # (N, num_classes)
            return logits, features

    return GradableCAMNet(body, feat_channels, num_classes), feat_channels


# ---------------------------------------------------------------------------
# GPU smoke test — run BEFORE any long training job (directive Section 7A)
# ---------------------------------------------------------------------------

def run_smoke_test(model, dataset, device, batch_size: int = 4) -> None:
    import torch
    from torch.utils.data import DataLoader

    print(f"\n=== GPU smoke test (batch_size={batch_size}) ===")
    assert device.type == "cuda", "Smoke test expects a CUDA device — refusing to silently fall back to CPU."

    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
    images, labels = next(iter(loader))
    images, labels = images.to(device), labels.to(device)
    print(f"Batch loaded: images {tuple(images.shape)} labels {tuple(labels.shape)} on {images.device}")

    model = model.to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4)
    criterion = torch.nn.CrossEntropyLoss()

    logits, features = model(images)
    loss = criterion(logits, labels)
    assert torch.isfinite(loss).item(), f"Smoke test loss is not finite: {loss.item()}"
    loss.backward()
    optimizer.step()
    optimizer.zero_grad()

    mem_alloc = torch.cuda.memory_allocated(device) / 1e9
    mem_reserved = torch.cuda.memory_reserved(device) / 1e9
    print(f"Forward+backward+step OK. loss={loss.item():.4f} finite=True")
    print(f"Logits shape: {tuple(logits.shape)}  Features shape: {tuple(features.shape)}")
    print(f"GPU memory: allocated={mem_alloc:.3f} GB reserved={mem_reserved:.3f} GB")

    ckpt_test_path = PROJECT_ROOT / "models" / "grading" / "_smoke_test_checkpoint.pt"
    torch.save(model.state_dict(), ckpt_test_path)
    assert ckpt_test_path.is_file() and ckpt_test_path.stat().st_size > 0, "Checkpoint write failed."
    print(f"Checkpoint write OK: {ckpt_test_path} ({ckpt_test_path.stat().st_size / 1e6:.1f} MB)")
    ckpt_test_path.unlink()
    print("=== Smoke test PASSED ===\n")


def find_safe_batch_size(backbone: str, pretrained: bool, image_size: int, device,
                          candidates=(64, 48, 32, 24, 16, 12, 8, 4)) -> int:
    """Empirically finds the largest batch size that fits in VRAM with a forward+backward
    pass, rather than guessing. Frees CUDA memory between attempts."""
    import torch

    print("\n=== Auto batch-size search (RTX 3050 6GB) ===")
    for bs in candidates:
        try:
            torch.cuda.empty_cache()
            model, _ = build_model(backbone, pretrained)
            model = model.to(device)
            optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4)
            dummy_x = torch.randn(bs, 3, image_size, image_size, device=device)
            dummy_y = torch.randint(0, NUM_CLASSES, (bs,), device=device)
            logits, _ = model(dummy_x)
            loss = torch.nn.functional.cross_entropy(logits, dummy_y)
            loss.backward()
            optimizer.step()
            peak = torch.cuda.max_memory_allocated(device) / 1e9
            print(f"  batch_size={bs}: OK (peak GPU memory {peak:.2f} GB)")
            del model, optimizer, dummy_x, dummy_y, logits, loss
            torch.cuda.empty_cache()
            torch.cuda.reset_peak_memory_stats(device)
            # Always back off one notch from the largest that fit, regardless of
            # whether it succeeded on the first try — a smoke-test-only forward+
            # backward pass underestimates peak memory during a real multi-hour
            # run (allocator fragmentation, cuDNN autotune workspace, OS/display
            # VRAM contention). On a 6GB card this margin matters.
            idx = candidates.index(bs)
            safe_bs = candidates[min(idx + 1, len(candidates) - 1)]
            print(f"Selected batch_size={safe_bs} (backed off one safety step from {bs}).")
            return safe_bs
        except RuntimeError as e:
            if "out of memory" in str(e).lower():
                print(f"  batch_size={bs}: OOM, trying smaller")
                torch.cuda.empty_cache()
                torch.cuda.reset_peak_memory_stats(device)
                continue
            raise
    raise RuntimeError("Could not find a working batch size even at the smallest candidate — hardware problem.")


# ---------------------------------------------------------------------------
# Training loop
# ---------------------------------------------------------------------------

def run_epoch(model, loader, criterion, optimizer, device, train: bool, scaler=None):
    import torch

    model.train(train)
    total_loss, n = 0.0, 0
    all_true, all_pred = [], []

    context = torch.enable_grad() if train else torch.no_grad()
    with context:
        for images, labels in loader:
            images = images.to(device, non_blocking=True)
            labels = labels.to(device, non_blocking=True)

            if train:
                optimizer.zero_grad(set_to_none=True)
                if scaler is not None:
                    with torch.autocast(device_type="cuda", dtype=torch.float16):
                        logits, _ = model(images)
                        loss = criterion(logits, labels)
                    scaler.scale(loss).backward()
                    scaler.step(optimizer)
                    scaler.update()
                else:
                    logits, _ = model(images)
                    loss = criterion(logits, labels)
                    loss.backward()
                    optimizer.step()
            else:
                logits, _ = model(images)
                loss = criterion(logits, labels)

            total_loss += float(loss.item()) * images.size(0)
            n += images.size(0)
            preds = logits.argmax(dim=1)
            all_true.extend(labels.detach().cpu().numpy().tolist())
            all_pred.extend(preds.detach().cpu().numpy().tolist())

    return total_loss / max(n, 1), np.array(all_true), np.array(all_pred)


def fit_temperature(logits: np.ndarray, labels: np.ndarray) -> Tuple[float, float, float]:
    """1-parameter temperature scaling fit by grid + local refinement on NLL (no scipy dependency).
    Returns (best_T, pre_calibration_nll, post_calibration_nll)."""
    def nll(T: float) -> float:
        z = logits / T
        z = z - z.max(axis=1, keepdims=True)
        p = np.exp(z) / np.exp(z).sum(axis=1, keepdims=True)
        eps = 1e-12
        return float(-np.mean(np.log(np.clip(p[np.arange(len(labels)), labels], eps, 1.0))))

    pre_nll = nll(1.0)
    candidates = np.concatenate([np.linspace(0.3, 3.0, 55), [1.0]])
    best_T, best_nll = 1.0, pre_nll
    for T in candidates:
        val = nll(float(T))
        if val < best_nll:
            best_nll, best_T = val, float(T)

    lo, hi = max(0.05, best_T - 0.1), best_T + 0.1
    for T in np.linspace(lo, hi, 41):
        val = nll(float(T))
        if val < best_nll:
            best_nll, best_T = val, float(T)
    return best_T, pre_nll, best_nll


def expected_calibration_error(probs: np.ndarray, labels: np.ndarray, n_bins: int = 10) -> float:
    confidences = probs.max(axis=1)
    predictions = probs.argmax(axis=1)
    accuracies = (predictions == labels).astype(np.float64)
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    for i in range(n_bins):
        mask = (confidences > bins[i]) & (confidences <= bins[i + 1])
        if mask.sum() == 0:
            continue
        bin_acc = accuracies[mask].mean()
        bin_conf = confidences[mask].mean()
        ece += (mask.sum() / len(labels)) * abs(bin_acc - bin_conf)
    return float(ece)


def brier_score(probs: np.ndarray, labels: np.ndarray, num_classes: int = NUM_CLASSES) -> float:
    onehot = np.eye(num_classes)[labels]
    return float(np.mean(np.sum((probs - onehot) ** 2, axis=1)))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split-prefix", default="grading",
                         help="Reads data/splits/<prefix>_train.csv and <prefix>_val.csv")
    parser.add_argument("--backbone", default="resnet50", choices=["resnet18", "resnet50"])
    parser.add_argument("--pretrained", action="store_true", default=True)
    parser.add_argument("--no-pretrained", dest="pretrained", action="store_false")
    parser.add_argument("--image-size", type=int, default=224)
    parser.add_argument("--batch-size", type=int, default=0, help="0 = auto-detect safe batch size")
    parser.add_argument("--epochs", type=int, default=25)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--patience", type=int, default=6, help="Early stop if val QWK doesn't improve for N epochs")
    parser.add_argument("--time-budget-minutes", type=float, default=0.0)
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--amp", action="store_true", default=False, help="Enable mixed precision (validated by smoke test first)")
    parser.add_argument("--skip-smoke-test", action="store_true", default=False)
    args = parser.parse_args()

    import torch
    import torch.nn as nn

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    if not torch.cuda.is_available():
        raise RuntimeError(
            "CUDA is not available. Refusing to silently fall back to CPU or a smaller "
            "architecture per project policy — fix the CUDA environment first "
            "(see docs/model_cards/grading.md for the environment history)."
        )
    device = torch.device("cuda")
    print(f"Device: {device} ({torch.cuda.get_device_name(0)})  |  torch {torch.__version__}  |  "
          f"CUDA {torch.version.cuda}  |  backbone={args.backbone}  pretrained={args.pretrained}  "
          f"image_size={args.image_size}")

    splits_dir = PROJECT_ROOT / "data" / "splits"
    train_csv = splits_dir / f"{args.split_prefix}_train.csv"
    val_csv = splits_dir / f"{args.split_prefix}_val.csv"
    if not train_csv.is_file() or not val_csv.is_file():
        raise FileNotFoundError(
            f"Split files not found ({train_csv}, {val_csv}). "
            "Run training/prepare_grading_splits.py first."
        )

    preprocessing_config = PROJECT_ROOT / "configs" / "preprocessing.json"
    train_ds, val_ds = build_datasets(train_csv, val_csv, args.image_size, preprocessing_config)
    print(f"Train: {len(train_ds)} images | Val: {len(val_ds)} images")

    train_rows = _load_split(train_csv)
    train_labels = np.array([int(r["diagnosis"]) for r in train_rows])
    class_counts = np.bincount(train_labels, minlength=NUM_CLASSES).astype(np.float64)
    class_weights = class_counts.sum() / (NUM_CLASSES * np.maximum(class_counts, 1))
    print(f"Class counts (train): {class_counts.tolist()}")
    print(f"Class weights (inverse-frequency): {np.round(class_weights, 3).tolist()}")

    # ---- Smoke test (Section 7A): pretrained weights, CUDA, real batch, forward+backward+step ----
    if not args.skip_smoke_test:
        smoke_model, _ = build_model(args.backbone, args.pretrained)
        run_smoke_test(smoke_model, train_ds, device, batch_size=4)
        del smoke_model
        torch.cuda.empty_cache()

    # ---- Auto batch size (Section 7B) ----
    batch_size = args.batch_size if args.batch_size > 0 else find_safe_batch_size(
        args.backbone, args.pretrained, args.image_size, device)
    print(f"Using batch_size={batch_size}")

    from torch.utils.data import DataLoader
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True,
                               num_workers=args.num_workers, drop_last=True, pin_memory=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False,
                             num_workers=args.num_workers, pin_memory=True)

    model, feat_channels = build_model(args.backbone, args.pretrained)
    model = model.to(device)

    # ---- Validate AMP correctness on a real batch before trusting it for the full run ----
    scaler = None
    if args.amp:
        print("\n=== Validating AMP (mixed precision) on a real batch ===")
        test_images, test_labels = next(iter(train_loader))
        test_images, test_labels = test_images.to(device), test_labels.to(device)
        with torch.autocast(device_type="cuda", dtype=torch.float16):
            test_logits, _ = model(test_images)
            test_loss = nn.functional.cross_entropy(test_logits, test_labels)
        if torch.isfinite(test_loss).item():
            scaler = torch.cuda.amp.GradScaler()
            print(f"AMP validated: loss={test_loss.item():.4f} is finite. Enabling AMP for training.")
        else:
            print(f"AMP produced a non-finite loss ({test_loss.item()}) — disabling AMP, using fp32.")
        del test_images, test_labels, test_logits, test_loss
        torch.cuda.empty_cache()

    criterion = nn.CrossEntropyLoss(weight=torch.tensor(class_weights, dtype=torch.float32, device=device))
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max(args.epochs, 1))

    out_dir = PROJECT_ROOT / "models" / "grading"
    out_dir.mkdir(parents=True, exist_ok=True)
    ckpt_path = out_dir / "_best_checkpoint.pt"

    best_qwk = -1.0
    best_epoch = -1
    epochs_without_improvement = 0
    history = []
    start_time = time.time()

    for epoch in range(1, args.epochs + 1):
        t0 = time.time()
        train_loss, _, _ = run_epoch(model, train_loader, criterion, optimizer, device, train=True, scaler=scaler)
        val_loss, y_true, y_pred = run_epoch(model, val_loader, criterion, optimizer, device, train=False)
        scheduler.step()

        qwk = quadratic_weighted_kappa(y_true, y_pred, NUM_CLASSES)
        ref = referable_sensitivity_specificity(y_true, y_pred)
        epoch_time = time.time() - t0
        gpu_mem = torch.cuda.max_memory_allocated(device) / 1e9

        print(f"[epoch {epoch}/{args.epochs}] train_loss={train_loss:.4f} val_loss={val_loss:.4f} "
              f"QWK={qwk:.4f} referable_sens={ref['sensitivity']:.3f} referable_spec={ref['specificity']:.3f} "
              f"({epoch_time:.1f}s, peak_gpu_mem={gpu_mem:.2f}GB)")

        history.append({
            "epoch": epoch, "train_loss": train_loss, "val_loss": val_loss,
            "qwk": qwk, "referable_sensitivity": ref["sensitivity"],
            "referable_specificity": ref["specificity"], "epoch_time_sec": epoch_time,
            "peak_gpu_memory_gb": gpu_mem,
        })

        if qwk > best_qwk:
            best_qwk = qwk
            best_epoch = epoch
            epochs_without_improvement = 0
            torch.save(model.state_dict(), ckpt_path)
            print(f"  -> new best QWK {qwk:.4f}, checkpoint saved.")
        else:
            epochs_without_improvement += 1

        if epochs_without_improvement >= args.patience:
            print(f"No QWK improvement for {args.patience} epochs, early stopping after epoch {epoch}.")
            break
        if args.time_budget_minutes > 0 and (time.time() - start_time) / 60.0 >= args.time_budget_minutes:
            print(f"Time budget of {args.time_budget_minutes} min reached, stopping early after epoch {epoch}.")
            break

    total_train_time_sec = time.time() - start_time
    print(f"\nBest epoch: {best_epoch} (QWK={best_qwk:.4f}). Total training time: {total_train_time_sec/60:.1f} min. "
          f"Reloading best checkpoint for export.")
    model.load_state_dict(torch.load(ckpt_path, map_location=device))
    model.eval()

    # ---- Final validation pass with the BEST checkpoint (for reported metrics + calibration) ----
    all_logits, all_true = [], []
    with torch.no_grad():
        for images, labels in val_loader:
            images = images.to(device)
            logits, _ = model(images)
            all_logits.append(logits.cpu().numpy())
            all_true.append(labels.numpy())
    all_logits = np.concatenate(all_logits, axis=0)
    all_true = np.concatenate(all_true, axis=0)
    all_pred = all_logits.argmax(axis=1)

    cm = confusion_matrix(all_true, all_pred, NUM_CLASSES)
    qwk = quadratic_weighted_kappa(all_true, all_pred, NUM_CLASSES)
    ref = referable_sensitivity_specificity(all_true, all_pred)
    per_class = per_class_sensitivity_specificity(cm)
    mf1 = macro_f1(cm)

    print("\n=== Final validation metrics (best checkpoint, uncalibrated) ===")
    print(f"QWK: {qwk:.4f}")
    print(f"Referable (Grade>=2) sensitivity: {ref['sensitivity']:.3f}  specificity: {ref['specificity']:.3f}")
    print(f"Macro F1: {mf1:.4f}")
    print(f"Confusion matrix:\n{cm}")

    # ---- Temperature scaling fit on the validation logits (blueprint K.10) ----
    temperature, pre_nll, post_nll = fit_temperature(all_logits, all_true)

    def softmax(z):
        z = z - z.max(axis=1, keepdims=True)
        e = np.exp(z)
        return e / e.sum(axis=1, keepdims=True)

    probs_uncalibrated = softmax(all_logits)
    probs_calibrated = softmax(all_logits / temperature)
    ece_before = expected_calibration_error(probs_uncalibrated, all_true)
    ece_after = expected_calibration_error(probs_calibrated, all_true)
    brier_before = brier_score(probs_uncalibrated, all_true)
    brier_after = brier_score(probs_calibrated, all_true)

    print(f"Fitted temperature: {temperature:.4f}")
    print(f"NLL before/after: {pre_nll:.4f} / {post_nll:.4f}")
    print(f"ECE before/after: {ece_before:.4f} / {ece_after:.4f}")
    print(f"Brier before/after: {brier_before:.4f} / {brier_after:.4f}")

    calibration_config = {
        "temperature": float(temperature),
        "fitted": True,
        "method": "temperature_scaling",
        "dataset": f"{args.split_prefix}_val ({len(all_true)} images: {train_ds.__class__.__name__})",
        "pre_calibration_metrics": {"nll": pre_nll, "ece": ece_before, "brier": brier_before},
        "post_calibration_metrics": {"nll": post_nll, "ece": ece_after, "brier": brier_after},
        "description": (
            f"Temperature scaling fitted by NLL minimization on the {args.split_prefix} validation "
            f"split ({len(all_true)} images) after training/train_grading.py. Backbone={args.backbone}, "
            f"pretrained={args.pretrained} (ImageNet), GPU-trained."
        ),
    }
    calib_path = PROJECT_ROOT / "configs" / "calibration.json"
    with open(calib_path, "w", encoding="utf-8") as f:
        json.dump(calibration_config, f, indent=2)
    print(f"Wrote {calib_path}")

    # ---- ONNX export: outputs = [logits, features] ----
    dummy = torch.randn(1, 3, args.image_size, args.image_size, device=device)
    onnx_path = out_dir / "grading_model.onnx"
    model_cpu = copy.deepcopy(model).cpu().eval()
    dummy_cpu = dummy.cpu()
    torch.onnx.export(
        model_cpu, dummy_cpu, str(onnx_path),
        input_names=["input"], output_names=["logits", "features"],
        opset_version=17,
        dynamic_axes=None,
        dynamo=False,  # legacy TorchScript-based exporter — avoids the onnxscript dependency
    )
    print(f"Wrote {onnx_path}")

    # ---- Sanity check: onnxruntime output must match the torch model ----
    onnx_parity = {}
    try:
        import onnxruntime as ort
        session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
        ort_logits, ort_features = session.run(["logits", "features"], {"input": dummy_cpu.numpy()})
        with torch.no_grad():
            torch_logits, torch_features = model_cpu(dummy_cpu)
        logit_diff = float(np.max(np.abs(ort_logits - torch_logits.numpy())))
        feat_diff = float(np.max(np.abs(ort_features - torch_features.numpy())))
        onnx_parity = {"logit_max_abs_diff": logit_diff, "feature_max_abs_diff": feat_diff}
        print(f"ONNX <-> PyTorch max abs diff: logits={logit_diff:.6f} features={feat_diff:.6f}")
        if logit_diff > 1e-3:
            print("WARNING: ONNX/PyTorch logits mismatch exceeds tolerance — investigate before shipping.")
    except ImportError:
        print("onnxruntime not installed — skipping export sanity check.")

    # ---- FC weights for exact class activation mapping (pipeline/explain.py) ----
    fc_weights = model.fc.weight.detach().cpu().numpy()  # (num_classes, feat_channels)
    fc_weights_path = out_dir / "gradcam_fc_weights.npy"
    np.save(fc_weights_path, fc_weights)
    print(f"Wrote {fc_weights_path} shape={fc_weights.shape}")

    # ---- Model contract (pipeline/contract.py) ----
    metadata = {
        "model_name": f"{args.backbone}_dr_grader" + ("_imagenet" if args.pretrained else "_scratch"),
        "model_version": "2.0.0",
        "input_size": [args.image_size, args.image_size],
        "channels": 3,
        "normalization": {"mean": IMAGENET_MEAN, "std": IMAGENET_STD},
        "model_file": "grading_model.onnx",
        "framework": "onnx",
        "training_dataset": (
            f"APTOS 2019 ({len(train_rows) - sum(1 for r in train_rows if r['dataset']!='aptos2019')} train rows) "
            f"+ IDRiD grading-train (non-sealed, 413 total images) combined, near-duplicate-aware "
            f"cross-dataset stratified split (train={len(train_ds)}, val={len(val_ds)}). "
            f"DDR NOT used. IDRiD grading-TEST (103 images, sealed) NOT used."
        ),
        "preprocessing": ["fov_crop", "resize", "clahe", "normalize", "resize_to_input_size", "imagenet_normalize"],
        "eval_metrics": {
            "val_qwk": float(qwk),
            "val_referable_sensitivity": float(ref["sensitivity"]),
            "val_referable_specificity": float(ref["specificity"]),
            "val_macro_f1": float(mf1),
            "val_confusion_matrix": cm.tolist(),
            "val_per_class": per_class,
            "calibration": {
                "temperature": float(temperature),
                "ece_before": ece_before, "ece_after": ece_after,
                "brier_before": brier_before, "brier_after": brier_after,
                "nll_before": pre_nll, "nll_after": post_nll,
            },
            "onnx_parity": onnx_parity,
            "best_epoch": best_epoch,
            "total_epochs_run": len(history),
            "total_training_time_minutes": total_train_time_sec / 60.0,
            "n_train_images": int(len(train_ds)),
            "n_val_images": int(len(all_true)),
            "gpu": torch.cuda.get_device_name(0),
            "note": (
                "Internal validation split only (APTOS+IDRiD-train held-out, image-level, cross-dataset "
                "near-duplicate-checked). NOT an external/sealed test result — do not report as the PS "
                "sensitivity/specificity claim. Sealed evaluation (Messidor-2 / IDRiD grading-test, 103 "
                "images) has not been run; that split is reserved until the full system is frozen."
            ),
        },
        "class_labels": ["0", "1", "2", "3", "4"],
        "output_format": "raw_logits",
        "threshold": 0.5,
        "gradcam_target_layer": "features",
        "gradcam_fc_weights_file": "gradcam_fc_weights.npy",
    }
    meta_path = out_dir / "metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    print(f"Wrote {meta_path}")

    history_path = out_dir / "training_history.json"
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump({"args": vars(args), "history": history}, f, indent=2)
    print(f"Wrote {history_path}")

    print("\nDone. Run the Flask app to see live 0-4 grading + Grad-CAM: python app/app.py")


if __name__ == "__main__":
    main()
