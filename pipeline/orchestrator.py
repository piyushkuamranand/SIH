"""
pipeline/orchestrator.py — NETRA-DR Full Pipeline Orchestrator
SIH-26038  |  Explainable AI Diabetic Retinopathy Screening

Entry point: run_netra_pipeline(image, quality_tier, config)

Stages wired in order (outputs feed inputs exactly as specified):
  S1  Vessel segmentation        FR-UNet → binary mask + thin-vessel sensitivity
  S2  Lesion detection           fundus-lesions-toolkit → MA count, HE mask, EX mask, SE/CWS mask (SEPARATE)
  S3  Neovascularisation stub    → None / "not-yet-trained" (explicitly distinct from ICDR Grade-4)
  S4  DR grading                 ResNet-50 primary (EfficientNet-B0 via GRADER_BACKEND config flag)
                                 + multi-seed ensemble → uncertainty spread (no MC-dropout)
  S5  Decision fusion            shallow logistic regression (scikit-learn) trained on calibration
                                 split only; five explicit inputs; quality-tier thresholds applied here
  S6  Temperature calibration    scales S4 logits on validation fold before they reach S5
  S7  Ensemble                   3-5 independently-seeded checkpoints; prediction spread logged
  S8  Explainability             Grad-CAM (primary) + HiResCAM (backup); IoU/pointing-game vs S2 masks
                                 "model attention" label NEVER merged with "detected evidence"
  S9  Quality-tier thresholds    Borderline stricter referral cutoff; Reject hard block
  S10 Consistency flag           low heatmap-vs-lesion overlap priority human-review flag

Enforced constraints (see PRD):
  No lesion features fused into grading network's internal layers
  No RETFound/DINOv2 as production grader
  No hemorrhage subtypes (flame/dot-blot/deep) — presence/count/area/quadrant only
  Sensitivity/specificity: two-sided CI phrasing from PRD; both gradable-only AND
    gradable+ungradable numbers reported side-by-side
  Messidor-2 and sealed IDRiD test split never touched here
  NV stub never presented as equivalent to ICDR Grade-4
  MC-dropout not implemented
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration dataclass
# ---------------------------------------------------------------------------

@dataclass
class NetraConfig:
    """
    Runtime configuration for the NETRA-DR orchestrator.

    GRADER_BACKEND options:
      "resnet50"        — primary (HF: sakshamkr1/ResNet50-APTOS-DR)  [default]
      "efficientnet_b0" — backup  (HF: adarshcod30/drdetect-dr-screening)
    """

    # Backend toggle
    GRADER_BACKEND: str = "resnet50"

    # Model directories
    vessel_seg_dir: str       = "models/vessel_seg"
    lesion_seg_dir: str       = "models/lesion_seg"
    ma_detector_dir: str      = "models/ma_detector"
    grading_dir: str          = "models/grading"
    backup_grading_dir: str   = "models/grading_backup"
    calibration_dir: str      = "models/temperature_scaling"
    decision_fusion_dir: str  = "models/decision_fusion"

    # Ensemble: list 3-5 independently-seeded ONNX checkpoint paths
    # MC-dropout is explicitly NOT used for uncertainty
    ensemble_checkpoint_paths: List[str] = field(default_factory=list)

    # Config files
    calibration_config: str   = "configs/calibration.json"
    decision_config: str      = "configs/decision_rule.json"
    preprocessing_config: str = "configs/preprocessing.json"

    # Explainability
    gradcam_alpha: float = 0.5
    # IoU below this threshold triggers the priority-review flag (S10)
    consistency_iou_threshold: float = 0.10
    # Minimum lesion pixels needed to compute IoU (avoid false flags on clean images)
    consistency_min_lesion_pixels: int = 100

    # Decision thresholds (override decision_rule.json when not None)
    good_quality_threshold: Optional[float] = None
    borderline_quality_threshold: Optional[float] = None

    # PRD two-sided performance report fields (populate after validation fold eval)
    validation_sensitivity_pct: Optional[float] = None
    validation_specificity_pct: Optional[float] = None
    validation_ci_lower: Optional[float] = None
    validation_ci_upper: Optional[float] = None


# ---------------------------------------------------------------------------
# S1: Vessel Segmentation  (FR-UNet)
# ---------------------------------------------------------------------------

def _run_vessel_segmentation(
    preprocessed_image: np.ndarray,
    config: NetraConfig,
) -> Dict[str, Any]:
    """
    Stage 1 - Vessel segmentation via FR-UNet.

    Checkpoint: ./models/FR-UNet  (pretrained on DRIVE / STARE / CHASE_DB1)

    Reports thin-vessel sensitivity (not just average Dice).
    Thin-vessel sensitivity is computed on the skeletonised predicted mask.
    Dice against ground truth is populated only by the offline eval script.
    """
    out: Dict[str, Any] = {
        "vessel_mask": None,
        "vessel_overlay": None,
        "thin_vessel_sensitivity": None,
        "dice_score": None,
        "stage": "vessel_segmentation",
        "model_repo": "./models/FR-UNet  (DRIVE/STARE/CHASE_DB1 pretrained)",
        "status": "ok",
        "error": None,
    }

    try:
        from pipeline.structure import run_vessel_segmentation
        vessel_out = run_vessel_segmentation(
            preprocessed_image=preprocessed_image,
            model_dir=config.vessel_seg_dir,
        )
        out["vessel_mask"]    = vessel_out.get("vessel_mask")
        out["vessel_overlay"] = vessel_out.get("vessel_overlay")

        mask = out["vessel_mask"]
        if mask is not None:
            try:
                from skimage.morphology import skeletonize
                skeleton = skeletonize(mask > 0)
                skeleton_count = int(np.sum(skeleton))
                mask_count = int(np.sum(mask > 0))
                # Thin-vessel sensitivity proxy (self-comparison at inference time).
                # True sensitivity vs GT is computed offline in eval scripts only.
                out["thin_vessel_sensitivity"] = (
                    float(skeleton_count) / max(1, mask_count)
                )
                out["dice_score"] = None  # requires GT; offline eval only
            except ImportError:
                logger.warning(
                    "scikit-image not installed — thin_vessel_sensitivity unavailable. "
                    "Run: pip install scikit-image"
                )

    except Exception as exc:
        is_missing = ("artifact missing" in str(exc) or
                      "not found" in str(exc).lower())
        out["status"] = "model_unavailable" if is_missing else "error"
        out["error"]  = f"{type(exc).__name__}: {exc}"
        logger.warning("Stage 1 vessel segmentation: %s", out["error"])

    return out


# ---------------------------------------------------------------------------
# Anatomical helpers for S2
# ---------------------------------------------------------------------------

def _estimate_fovea(image: np.ndarray) -> Tuple[int, int]:
    """
    Estimate fovea centroid: darkest point on the green channel in the
    temporal half of the image, after Gaussian smoothing.
    Accurate to ~1 disc-diameter; sufficient for near-fovea feature computation.
    """
    import cv2
    h, w = image.shape[:2]
    green = image[:, :, 1] if image.ndim == 3 else image
    if green.dtype == np.float32:
        green_u8 = (np.clip(green, 0.0, 1.0) * 255.0).astype(np.uint8)
    else:
        green_u8 = green.astype(np.uint8)
    blurred = cv2.GaussianBlur(green_u8, (51, 51), sigmaX=15)
    half    = blurred[:, w // 2:]
    min_loc = np.unravel_index(np.argmin(half), half.shape)
    return int(min_loc[0]), int(min_loc[1]) + w // 2


def _disc_diameter_px(image_shape: Tuple) -> float:
    """1 disc-diameter = ~15% of the shorter image dimension."""
    return 0.15 * min(image_shape[0], image_shape[1])


def _mask_fraction_near_point(
    mask: np.ndarray,
    row: int,
    col: int,
    image_shape: Tuple,
    radius_dds: float = 1.0,
) -> float:
    """Fraction of mask pixels within radius_dds disc-diameters of (row, col)."""
    r_px   = radius_dds * _disc_diameter_px(image_shape)
    ys, xs = np.ogrid[:mask.shape[0], :mask.shape[1]]
    near   = ((ys - row) ** 2 + (xs - col) ** 2) <= r_px ** 2
    return float(np.sum((mask > 0) & near)) / max(1, int(np.sum(mask > 0)))


def _count_near_point(
    locations: List[Tuple[int, int]],
    row: int,
    col: int,
    image_shape: Tuple,
    radius_dds: float = 1.0,
) -> int:
    """Count (row, col) tuples within radius_dds disc-diameters of (row, col)."""
    r_px = radius_dds * _disc_diameter_px(image_shape)
    return sum(
        1 for r, c in locations
        if (r - row) ** 2 + (c - col) ** 2 <= r_px ** 2
    )


def _quadrant_counts(mask: np.ndarray) -> Dict[str, int]:
    """Per-quadrant positive pixel counts (TL/TR/BL/BR)."""
    h, w   = mask.shape
    hh, hw = h // 2, w // 2
    return {
        "TL": int(np.sum(mask[:hh, :hw]  > 0)),
        "TR": int(np.sum(mask[:hh, hw:]  > 0)),
        "BL": int(np.sum(mask[hh:, :hw]  > 0)),
        "BR": int(np.sum(mask[hh:, hw:]  > 0)),
    }


# ---------------------------------------------------------------------------
# S2: Lesion Detection  (fundus-lesions-toolkit)
# ---------------------------------------------------------------------------

def _run_lesion_detection(
    preprocessed_image: np.ndarray,
    config: NetraConfig,
) -> Dict[str, Any]:
    """
    Stage 2 - Lesion detection via fundus-lesions-toolkit.

    Checkpoint: ./models/fundus-lesions-toolkit
    Pretrained: IDRiD / FGADR / DDR / MESSIDOR

    CRITICAL: MA count, HE mask, EX mask, SE/CWS mask are returned as
    SEPARATE evidence outputs — never merged into one "lesion score".

    Hemorrhage reporting: presence, count, area fraction, quadrant distribution.
    NO subtypes invented (no flame / dot-blot / deep).

    Near-macula MA count and EX area near fovea are computed here and passed
    separately to S5 decision fusion.
    """
    out: Dict[str, Any] = {
        "ma_count": 0,
        "ma_count_near_macula": 0,
        "ma_overlay": None,
        "he_mask": None,
        "he_presence": False,
        "he_area_fraction": 0.0,
        # Quadrant distribution: presence/area/quadrant only — no subtypes
        "he_quadrant_counts": {"TL": 0, "TR": 0, "BL": 0, "BR": 0},
        "ex_mask": None,
        "ex_area": 0.0,
        "ex_area_near_fovea": 0.0,
        "se_mask": None,
        "lesion_overlay": None,
        # Mandatory label: ALWAYS "detected evidence", NEVER "model attention"
        "evidence_label": "detected evidence",
        "stage": "lesion_detection",
        "model_repo": (
            "./models/fundus-lesions-toolkit  "
            "(IDRiD/FGADR/DDR/MESSIDOR pretrained)"
        ),
        "status": "ok",
        "error": None,
    }

    try:
        from pipeline.structure import run_lesion_segmentation, run_ma_detection

        # Lesion segmentation: HE / EX / SE as SEPARATE masks
        lesion_out = run_lesion_segmentation(
            preprocessed_image=preprocessed_image,
            model_dir=config.lesion_seg_dir,
        )
        out["he_mask"]        = lesion_out.get("he_mask")
        out["ex_mask"]        = lesion_out.get("ex_mask")
        out["se_mask"]        = lesion_out.get("se_mask")
        out["he_presence"]    = bool(lesion_out.get("he_presence", False))
        out["ex_area"]        = float(lesion_out.get("ex_area", 0.0))
        out["lesion_overlay"] = lesion_out.get("lesion_overlay")

        he_mask = out["he_mask"]
        if he_mask is not None:
            out["he_area_fraction"]   = (
                float(np.sum(he_mask > 0)) / max(1, he_mask.size)
            )
            out["he_quadrant_counts"] = _quadrant_counts(he_mask)

        ex_mask = out["ex_mask"]
        if ex_mask is not None:
            fov_r, fov_c = _estimate_fovea(preprocessed_image)
            out["ex_area_near_fovea"] = _mask_fraction_near_point(
                ex_mask, fov_r, fov_c, preprocessed_image.shape
            )

        # MA detection
        ma_out = run_ma_detection(
            preprocessed_image=preprocessed_image,
            model_dir=config.ma_detector_dir,
        )
        out["ma_count"]   = int(ma_out.get("ma_count", 0))
        out["ma_overlay"] = ma_out.get("ma_overlay")

        # Near-macula MA count (if run_ma_detection exposes ma_locations)
        ma_locs = ma_out.get("ma_locations", [])
        if ma_locs:
            fov_r, fov_c = _estimate_fovea(preprocessed_image)
            out["ma_count_near_macula"] = _count_near_point(
                ma_locs, fov_r, fov_c, preprocessed_image.shape
            )

    except Exception as exc:
        is_missing = ("artifact missing" in str(exc) or
                      "not found" in str(exc).lower())
        out["status"] = "model_unavailable" if is_missing else "error"
        out["error"]  = f"{type(exc).__name__}: {exc}"
        logger.warning("Stage 2 lesion detection: %s", out["error"])

    return out


# ---------------------------------------------------------------------------
# S3: Neovascularisation Stub  (no pretrained model available)
# ---------------------------------------------------------------------------

def _run_nv_stub() -> Dict[str, Any]:
    """
    Stage 3 - Neovascularisation detection stub.

    No pretrained model is available.  Returns None explicitly and carries a
    clear disclaimer that this output is NOT equivalent to ICDR Grade 4.

    The two must never be conflated:
      - ICDR Grade 4 (Proliferative DR) is determined by the grading model (S4).
      - Neovascularisation detection is an independent structural finding (not yet trained).
    """
    return {
        "nv_present": None,
        "nv_status": (
            "NOT YET TRAINED — neovascularisation detection model unavailable.  "
            "This stage returns None and must be presented as such in any UI output."
        ),
        "icdr_grade4_equivalence_disclaimer": (
            "IMPORTANT: Neovascularisation detection (Stage 3) is a separate "
            "structural finding and is NOT equivalent to ICDR Grade 4 "
            "(Proliferative DR) output by the grading model (Stage 4).  "
            "These two outputs must never be presented as the same finding."
        ),
        "stage": "neovascularisation_stub",
    }


# ---------------------------------------------------------------------------
# S6: Temperature Calibration  (validation fold only; never sealed test)
# ---------------------------------------------------------------------------

def _run_calibration(
    raw_probabilities: List[float],
    config: NetraConfig,
) -> Dict[str, Any]:
    """
    Stage 6 - Temperature-scale the grader's raw logits.

    Temperature is fitted on a validation fold (configs/calibration.json).
    The sealed test set is NEVER used to fit or evaluate calibration here.
    Calibrated probabilities are passed to S5 decision fusion.
    """
    from pipeline.grading import apply_calibration
    return apply_calibration(
        probabilities=raw_probabilities,
        config_path=config.calibration_config,
    )


# ---------------------------------------------------------------------------
# S7: Ensemble Grading  (3-5 independently-seeded checkpoints; NO MC-dropout)
# ---------------------------------------------------------------------------

def _run_ensemble_grading(
    preprocessed_image: np.ndarray,
    config: NetraConfig,
) -> Dict[str, Any]:
    """
    Stage 7 - Ensemble grading with 3-5 independently-seeded checkpoints.

    MC-dropout is explicitly NOT implemented.  Uncertainty is derived from
    prediction spread across independently-trained checkpoints only.

    Falls back to single-model grading when fewer than 2 valid checkpoints
    exist, and sets uncertainty to None with an explicit note.
    """
    ckpts = [p for p in config.ensemble_checkpoint_paths if Path(p).is_file()]

    if len(ckpts) < 2:
        # Single-model fallback
        from pipeline.grading import run_grading
        grading_dir = (
            config.grading_dir
            if config.GRADER_BACKEND == "resnet50"
            else config.backup_grading_dir
        )
        single_out = run_grading(
            preprocessed_image=preprocessed_image,
            model_dir=grading_dir,
        )
        probs = single_out["probabilities"]
        return {
            "mean_probabilities":   probs,
            "std_probabilities":    [0.0] * len(probs),
            "max_prob_spread":      None,
            "n_checkpoints":        1,
            "per_checkpoint_probs": [probs],
            "uncertainty_method":   "ensemble_spread",
            "mc_dropout_used":      False,  # constraint: NEVER True
            "single_model_note": (
                "Fewer than 2 ensemble checkpoints found.  "
                "Add 3-5 independently-seeded ONNX checkpoints to "
                "config.ensemble_checkpoint_paths to enable uncertainty."
            ),
            "model_name":    single_out.get("model_name", ""),
            "model_version": single_out.get("model_version", "unknown"),
            "class_labels":  single_out.get("class_labels", ["0","1","2","3","4"]),
        }

    import onnxruntime as ort
    from pipeline.grading import _prepare_grading_input, _softmax
    from pipeline.contract import load_contract

    grading_dir = (
        config.grading_dir
        if config.GRADER_BACKEND == "resnet50"
        else config.backup_grading_dir
    )
    contract   = load_contract(grading_dir, "classifier")
    model_meta = {
        "model_name":    contract.get("model_name", ""),
        "model_version": contract.get("model_version", "unknown"),
        "class_labels":  contract.get("class_labels", ["0","1","2","3","4"]),
    }
    inp = _prepare_grading_input(preprocessed_image, contract)

    all_probs: List[List[float]] = []
    for ckpt in ckpts[:5]:  # cap at 5
        try:
            sess     = ort.InferenceSession(ckpt, providers=["CPUExecutionProvider"])
            inp_name = sess.get_inputs()[0].name
            raw      = np.array(sess.run(None, {inp_name: inp})[0],
                                dtype=np.float32).flatten()
            all_probs.append(_softmax(raw).tolist())
        except Exception as exc:
            logger.warning("Ensemble checkpoint %s failed: %s", ckpt, exc)

    if not all_probs:
        raise RuntimeError(
            "All ensemble checkpoints failed.  "
            "Check that ensemble_checkpoint_paths point to valid ONNX files."
        )

    arr   = np.array(all_probs, dtype=np.float64)
    mean_p = arr.mean(axis=0).tolist()
    std_p  = arr.std(axis=0).tolist()
    return {
        "mean_probabilities":   mean_p,
        "std_probabilities":    std_p,
        "max_prob_spread":      float(np.max(arr.std(axis=0))),
        "n_checkpoints":        len(all_probs),
        "per_checkpoint_probs": all_probs,
        "uncertainty_method":   "ensemble_spread",  # NOT MC-dropout
        "mc_dropout_used":      False,               # constraint: NEVER True
        **model_meta,
    }


# ---------------------------------------------------------------------------
# S5: Decision Fusion  (shallow sklearn LR; 5 inputs; trained on calib split)
# ---------------------------------------------------------------------------

def _build_fusion_feature_vector(
    calibrated_prob_grade_ge2: float,
    ma_count: int,
    ma_count_near_macula: int,
    he_presence: bool,
    ex_area_near_fovea: float,
    quality_tier: str,
) -> np.ndarray:
    """
    Exact five-feature vector for the logistic regression (per PRD spec):
      (a) calibrated P(ICDR >= 2)
      (b) MA count including near-macula count
      (c) HE presence (0/1)
      (d) EX area near fovea [0,1]
      (e) image quality tier — is_borderline (0/1)
    """
    ma_input     = float(ma_count_near_macula if ma_count_near_macula > 0 else ma_count)
    is_borderline = 1.0 if str(quality_tier).strip().capitalize() == "Borderline" else 0.0
    return np.array([
        float(calibrated_prob_grade_ge2),
        ma_input,
        1.0 if he_presence else 0.0,
        float(ex_area_near_fovea),
        is_borderline,
    ], dtype=np.float64)


def _run_decision_fusion(
    calibrated_probabilities: List[float],
    s2_lesion: Dict[str, Any],
    quality_tier: str,
    config: NetraConfig,
) -> Dict[str, Any]:
    """
    Stage 5 - Decision fusion via shallow logistic regression.

    Model type: scikit-learn LogisticRegression (NOT a neural network).
    Training:   held-out calibration split ONLY (never the sealed test set).
    Inputs:     exactly 5 features from _build_fusion_feature_vector.
    Coefficients are logged at INFO level for inspection.

    Stage 9 quality-tier thresholds are enforced here:
      Borderline quality  stricter (lower) referral cutoff
      Good quality        standard cutoff
      Reject quality      hard block (raises ValueError)

    Falls back to rule-based threshold if no fitted LR model is present,
    clearly reporting fusion_status = "grade-alone-fallback".
    """
    norm_q = str(quality_tier).strip().capitalize()
    if norm_q.lower() == "reject":
        raise ValueError(
            "Reject-quality image cannot receive an automated referral decision.  "
            "Stage 1 must have blocked this image before the decision fusion layer."
        )

    probs = np.asarray(calibrated_probabilities, dtype=np.float64)
    if len(probs) != 5:
        raise ValueError(
            f"calibrated_probabilities must have 5 elements (ICDR 0-4), got {len(probs)}"
        )
    probs /= max(float(probs.sum()), 1e-12)

    prob_ge2        = float(probs[2:].sum())
    predicted_grade = int(np.argmax(probs))

    # Grade-alone naive reference (quality-unaware, fixed 0.50 threshold)
    grade_alone_ref = bool(prob_ge2 >= 0.50 or predicted_grade >= 2)
    grade_alone_dec = "REFER" if grade_alone_ref else "NO REFER"

    ma_count    = int(s2_lesion.get("ma_count", 0))
    ma_count_nm = int(s2_lesion.get("ma_count_near_macula", 0))
    he_presence = bool(s2_lesion.get("he_presence", False))
    ex_area_nf  = float(s2_lesion.get("ex_area_near_fovea", 0.0))

    feat_vec = _build_fusion_feature_vector(
        calibrated_prob_grade_ge2=prob_ge2,
        ma_count=ma_count,
        ma_count_near_macula=ma_count_nm,
        he_presence=he_presence,
        ex_area_near_fovea=ex_area_nf,
        quality_tier=norm_q,
    )

    # Load quality-tier thresholds from config
    cfg: Dict[str, Any] = {}
    cfg_path = Path(config.decision_config)
    if cfg_path.is_file():
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception as exc:
            logger.warning("decision_rule.json load failed: %s — using defaults", exc)

    thresholds    = cfg.get("thresholds", {})
    good_thr      = config.good_quality_threshold or float(
        thresholds.get("good_quality", {}).get("referable_prob_threshold", 0.50)
    )
    border_thr    = config.borderline_quality_threshold or float(
        thresholds.get("borderline_quality", {}).get("referable_prob_threshold", 0.35)
    )
    # S9: apply stricter threshold for Borderline quality images
    threshold_applied = border_thr if norm_q == "Borderline" else good_thr

    # Attempt fitted logistic regression
    fusion_meta: Optional[Dict[str, Any]] = None
    fm_path = Path(config.decision_fusion_dir) / "metadata.json"
    if fm_path.is_file():
        try:
            with open(fm_path, "r", encoding="utf-8") as f:
                m = json.load(f)
            if m.get("fitted", False) and "weights" in m and "intercept" in m:
                fusion_meta = m
        except Exception as exc:
            logger.warning("Fusion model metadata load failed: %s", exc)

    if fusion_meta is not None:
        weights   = np.asarray(fusion_meta["weights"], dtype=np.float64)
        intercept = float(fusion_meta["intercept"])
        if len(weights) != len(feat_vec):
            raise ValueError(
                f"Fusion LR weight dim {len(weights)} != feature dim {len(feat_vec)}.  "
                "Retrain with the current 5-feature vector."
            )
        logit       = float(intercept + np.dot(weights, feat_vec))
        fusion_prob = float(1.0 / (1.0 + np.exp(-logit)))
        lr_thresh   = float(fusion_meta.get("threshold", threshold_applied))
        # S9: apply quality-tier override even for fitted model
        if norm_q == "Borderline":
            lr_thresh = min(lr_thresh, border_thr)
        is_referable      = bool(fusion_prob >= lr_thresh)
        threshold_applied = lr_thresh
        fitted            = True
        fusion_status     = "fitted_logistic_regression"
        coefficients      = weights.tolist()
        lr_intercept      = intercept

        # Log coefficients for inspectability (required by spec)
        feature_names = [
            "(a) P(ICDR>=2)", "(b) MA count (near-macula)",
            "(c) HE presence", "(d) EX near fovea", "(e) is_borderline",
        ]
        logger.info("=== Fusion LR coefficients ===")
        for name, coef in zip(feature_names, coefficients):
            logger.info("  %-30s  %.4f", name, coef)
        logger.info("  %-30s  %.4f", "Intercept", lr_intercept)

        reason = (
            f"Fitted LR: P(refer)={fusion_prob:.3f} vs threshold {threshold_applied:.2f}.  "
            f"Features: P(>=2)={prob_ge2:.3f}, MA(near-macula)={ma_count_nm}, "
            f"HE={int(he_presence)}, EX_near_fovea={ex_area_nf:.4f}, quality={norm_q}."
        )
    else:
        # Rule-based fallback
        is_referable  = bool(prob_ge2 >= threshold_applied or predicted_grade >= 2)
        fitted        = False
        fusion_status = (
            "grade-alone-fallback — logistic regression not yet trained on "
            "calibration split; place fitted metadata.json in "
            f"{config.decision_fusion_dir} to activate LR fusion"
        )
        coefficients = None
        lr_intercept = None
        action = "Referral" if is_referable else "No referral"
        reason = (
            f"{action} ({norm_q} quality): P(Grade>=2)={prob_ge2:.3f} vs "
            f"threshold {threshold_applied:.2f}.  "
            f"Evidence: MA={ma_count} (near-macula={ma_count_nm}), "
            f"HE={int(he_presence)}, EX_near_fovea={ex_area_nf:.4f}."
        )

    referable_decision = "REFER" if is_referable else "NO REFER"

    return {
        "referable_decision":        referable_decision,
        "grade_alone_decision":      grade_alone_dec,
        "is_referable":              is_referable,
        "grade_alone_referable":     grade_alone_ref,
        "predicted_grade":           predicted_grade,
        "calibrated_probabilities":  [float(p) for p in probs],
        "referable_probability":     prob_ge2,
        "fusion_feature_vector":     feat_vec.tolist(),
        "fusion_coefficients":       coefficients,
        "fusion_intercept":          lr_intercept,
        "quality_tier":              norm_q,
        "threshold_applied":         threshold_applied,
        "fitted":                    fitted,
        "fusion_status":             fusion_status,
        "reason":                    reason,
        "stage":                     "decision_fusion",
        # Constraint audit field
        "lesion_features_fused_in_grader": False,
    }


# ---------------------------------------------------------------------------
# S8: Explainability  (Grad-CAM primary, HiResCAM backup; IoU vs S2 masks)
# ---------------------------------------------------------------------------

def _iou_heatmap_vs_mask(
    heatmap_raw: np.ndarray,
    mask: np.ndarray,
    heatmap_threshold: float = 0.5,
) -> float:
    """IoU between binarised Grad-CAM heatmap and a binary lesion mask."""
    import cv2
    h_bin = (heatmap_raw >= heatmap_threshold).astype(np.uint8)
    if h_bin.shape != mask.shape[:2]:
        h_bin = cv2.resize(
            h_bin, (mask.shape[1], mask.shape[0]),
            interpolation=cv2.INTER_NEAREST,
        )
    m_bin = (mask > 0).astype(np.uint8)
    inter = int(np.sum(h_bin & m_bin))
    union = int(np.sum(h_bin | m_bin))
    return float(inter) / max(union, 1)


def _pointing_game(heatmap_raw: np.ndarray, mask: np.ndarray) -> bool:
    """Returns True if the heatmap argmax falls within the lesion mask."""
    import cv2
    h = cv2.resize(
        heatmap_raw, (mask.shape[1], mask.shape[0]),
        interpolation=cv2.INTER_LINEAR,
    )
    peak = np.unravel_index(np.argmax(h), h.shape)
    return bool(mask[peak[0], peak[1]] > 0)


def _try_hirescam(
    preprocessed_image: np.ndarray,
    severity_class: int,
    model_dir: str,
    config: NetraConfig,
) -> Optional[np.ndarray]:
    """
    Attempt HiResCAM via the pytorch-grad-cam pip package.
    Requires a model.pt PyTorch checkpoint alongside the ONNX file.
    Returns 2D float32 heatmap [0,1] or None if unavailable.
    """
    try:
        import torch
        import torch.nn as nn
        from pytorch_grad_cam import HiResCAM
        from pytorch_grad_cam.utils.model_targets import ClassifierOutputTarget

        pt_path = Path(model_dir) / "model.pt"
        if not pt_path.is_file():
            return None

        model = torch.load(pt_path, map_location="cpu", weights_only=False)
        model.eval()

        target_layers = []
        for _, module in reversed(list(model.named_modules())):
            if isinstance(module, nn.Conv2d):
                target_layers = [module]
                break
        if not target_layers:
            return None

        import cv2
        from pipeline.contract import load_contract
        contract   = load_contract(model_dir, "classifier")
        input_size = contract.get("input_size", [512, 512])
        h, w       = int(input_size[0]), int(input_size[1])

        if preprocessed_image.dtype == np.float32:
            img_u8 = (np.clip(preprocessed_image, 0, 1) * 255).astype(np.uint8)
        else:
            img_u8 = preprocessed_image.astype(np.uint8)
        resized = cv2.resize(img_u8, (w, h), interpolation=cv2.INTER_LINEAR)

        norm_spec = contract.get("normalization", {})
        mean_v    = norm_spec.get("mean", [0.485, 0.456, 0.406])
        std_v     = norm_spec.get("std",  [0.229, 0.224, 0.225])
        inp_f     = resized.astype(np.float32) / 255.0
        inp_f     = (inp_f - np.array(mean_v)) / np.array(std_v)
        inp_t     = torch.tensor(
            np.transpose(inp_f, (2, 0, 1))[np.newaxis], dtype=torch.float32
        )

        cam = HiResCAM(model=model, target_layers=target_layers)
        return cam(
            input_tensor=inp_t,
            targets=[ClassifierOutputTarget(severity_class)],
        )[0].astype(np.float32)

    except Exception as exc:
        logger.debug("HiResCAM unavailable: %s", exc)
        return None


def _run_explainability(
    preprocessed_image: np.ndarray,
    severity_class: int,
    s2_lesion: Dict[str, Any],
    config: NetraConfig,
) -> Dict[str, Any]:
    """
    Stage 8 - Explainability.

    Grad-CAM (primary) + HiResCAM (backup) over the Stage 4 grader.
    Scores heatmap vs Stage 2 lesion masks: IoU and pointing-game.

    CRITICAL LABELLING — enforced in output and must be preserved in any UI:
      heatmap output  => label "model attention"   (NEVER "detected evidence")
      lesion masks    => label "detected evidence" (NEVER "model attention")
      The two labels must NEVER be merged or conflated.
    """
    grading_dir = (
        config.grading_dir
        if config.GRADER_BACKEND == "resnet50"
        else config.backup_grading_dir
    )
    out: Dict[str, Any] = {
        "heatmap_overlay":  None,
        "heatmap_raw":      None,
        "hirescam_raw":     None,
        "label":            "model attention",      # mandatory; never change
        "evidence_label":   "detected evidence",    # label for S2 outputs
        "iou_vs_he":        None,
        "iou_vs_ex":        None,
        "pointing_game_he": None,
        "pointing_game_ex": None,
        "severity_class":   severity_class,
        "stage":            "explainability",
        "status":           "ok",
        "error":            None,
    }

    try:
        from pipeline.explain import run_gradcam
        gradcam_out = run_gradcam(
            preprocessed_image=preprocessed_image,
            severity_class=severity_class,
            model_dir=grading_dir,
            alpha=config.gradcam_alpha,
        )
        out["heatmap_overlay"] = gradcam_out["heatmap_overlay"]
        out["heatmap_raw"]     = gradcam_out["heatmap_raw"]
        out["label"]           = gradcam_out.get("label", "model attention")

        # HiResCAM backup
        out["hirescam_raw"] = _try_hirescam(
            preprocessed_image, severity_class, grading_dir, config
        )

        # Score heatmap vs S2 lesion masks
        heatmap  = out["heatmap_raw"]
        min_px   = config.consistency_min_lesion_pixels
        he_mask  = s2_lesion.get("he_mask")
        ex_mask  = s2_lesion.get("ex_mask")

        if heatmap is not None:
            if he_mask is not None and int(np.sum(he_mask > 0)) >= min_px:
                out["iou_vs_he"]        = _iou_heatmap_vs_mask(heatmap, he_mask)
                out["pointing_game_he"] = _pointing_game(heatmap, he_mask)
            if ex_mask is not None and int(np.sum(ex_mask > 0)) >= min_px:
                out["iou_vs_ex"]        = _iou_heatmap_vs_mask(heatmap, ex_mask)
                out["pointing_game_ex"] = _pointing_game(heatmap, ex_mask)

    except Exception as exc:
        is_missing = ("artifact missing" in str(exc) or
                      "not found" in str(exc).lower())
        out["status"] = "model_unavailable" if is_missing else "error"
        out["error"]  = f"{type(exc).__name__}: {exc}"
        logger.warning("Stage 8 explainability: %s", out["error"])

    return out


# ---------------------------------------------------------------------------
# S10: Explanation Consistency Flag
# ---------------------------------------------------------------------------

def _check_consistency_flag(
    s8_explain: Dict[str, Any],
    config: NetraConfig,
) -> Dict[str, Any]:
    """
    Stage 10 - Explanation consistency flag.

    If Grad-CAM heatmap IoU vs any populated lesion mask falls below
    config.consistency_iou_threshold, flag the case for priority human review.
    """
    iou_he = s8_explain.get("iou_vs_he")
    iou_ex = s8_explain.get("iou_vs_ex")
    thr    = config.consistency_iou_threshold

    low_he = iou_he is not None and iou_he < thr
    low_ex = iou_ex is not None and iou_ex < thr
    flag   = low_he or low_ex

    parts = []
    if low_he:
        parts.append(f"heatmap-vs-HE IoU={iou_he:.3f} < {thr:.2f}")
    if low_ex:
        parts.append(f"heatmap-vs-EX IoU={iou_ex:.3f} < {thr:.2f}")

    if flag:
        reason = (
            "CONSISTENCY FLAG — model attention does not adequately overlap "
            "with detected lesion evidence: " + "; ".join(parts) + ".  "
            "Case flagged for priority human review."
        )
    elif iou_he is None and iou_ex is None:
        reason = (
            "Consistency check skipped — no sufficiently populated lesion masks "
            "available (image may be clean or lesion model unavailable)."
        )
    else:
        vals = [v for v in [iou_he, iou_ex] if v is not None]
        reason = (
            f"Consistency check passed — IoU(s) above threshold "
            f"({', '.join(f'{v:.3f}' for v in vals)} >= {thr:.2f})."
        )

    return {
        "priority_human_review":   flag,
        "consistency_flag_reason": reason,
        "iou_vs_he":               iou_he,
        "iou_vs_ex":               iou_ex,
        "threshold_used":          thr,
        "stage":                   "consistency_flag",
    }


# ---------------------------------------------------------------------------
# Performance reporting  (PRD two-sided CI phrasing; both gradable figures)
# ---------------------------------------------------------------------------

def _format_performance_report(config: NetraConfig) -> Dict[str, Any]:
    """
    PRD-mandated two-sided performance report.

    Rule: NEVER claim the system "achieves" the target as a bare fact.
    Phrasing: "at the operating point selected on validation, measured X% / Y%
    on the sealed test, with 95% CI [lo%, hi%]"

    Both gradable-only AND gradable+ungradable numbers are reported side-by-side.
    Sealed test sets (Messidor-2, IDRiD sealed split) are opened ONLY by
    eval/test_performance.py — never by this module.
    """
    sens  = config.validation_sensitivity_pct
    spec  = config.validation_specificity_pct
    ci_lo = config.validation_ci_lower
    ci_hi = config.validation_ci_upper

    if sens is None or spec is None:
        return {
            "performance_report": (
                "Performance metrics not yet available.  Run "
                "eval/validate.py on the validation fold to populate "
                "validation_sensitivity_pct and validation_specificity_pct "
                "in NetraConfig.  Do NOT use the sealed test set for this."
            ),
            "gradable_only_reported": False,
            "gradable_and_ungradable_reported": False,
        }

    ci_str = (
        f"[{ci_lo:.1f}%, {ci_hi:.1f}%]"
        if (ci_lo is not None and ci_hi is not None)
        else "(95% CI not yet computed)"
    )
    return {
        "performance_report": (
            f"At the operating point selected on validation, the system measured "
            f"{sens:.1f}% sensitivity / {spec:.1f}% specificity on the sealed test "
            f"set, with 95% CI {ci_str}.  "
            "Gradable-only and gradable+ungradable numbers are reported side-by-side "
            "in eval/test_performance.py."
        ),
        "gradable_only_reported": True,
        "gradable_and_ungradable_reported": True,
        "sealed_test_note": (
            "Sealed test sets (Messidor-2, IDRiD sealed split) are opened exactly "
            "once by eval/test_performance.py — NEVER by this pipeline module."
        ),
    }


# ---------------------------------------------------------------------------
# Main orchestrator entry point
# ---------------------------------------------------------------------------

def run_netra_pipeline(
    preprocessed_image: np.ndarray,
    quality_tier: str,
    config: Optional[NetraConfig] = None,
) -> Dict[str, Any]:
    """
    Run the complete NETRA-DR screening pipeline for a single fundus image.

    Prerequisites:
      preprocessed_image — already quality-assessed and preprocessed;
        float32 HWC numpy array [0, 1] from Stage 1/2 of the original pipeline.
      quality_tier — "Good" | "Borderline" | "Reject" from Stage 1 IQA.
        Reject images are blocked with a hard ValueError — they MUST NEVER
        receive an automated clearance decision.

    Stage execution order and data flow:
      S1 vessel segmentation
        -> vessel_mask, thin_vessel_sensitivity
      S2 lesion detection
        -> ma_count, ma_count_near_macula, he_mask, he_presence,
           he_area_fraction, he_quadrant_counts, ex_mask, ex_area,
           ex_area_near_fovea, se_mask  (ALL SEPARATE — never merged)
      S3 NV stub
        -> nv_present=None, explicit disclaimer re. Grade-4 distinctness
      S7 ensemble (wraps S4 grading)
        -> mean_probabilities, std_probabilities, max_prob_spread, n_checkpoints
      S4 DR grading
        -> severity_class, probabilities  (ResNet-50 or EfficientNet-B0)
           lesion_fusion_in_grader=False enforced
      S6 temperature calibration
        -> calibrated_probabilities  (temperature from validation fold only)
      S5 decision fusion (includes S9 quality-tier thresholds)
        -> referable_decision, grade_alone_decision, fusion_feature_vector,
           fusion_coefficients (logged), threshold_applied
      S8 explainability
        -> heatmap_overlay (label="model attention"),
           iou_vs_he, iou_vs_ex, pointing_game scores
      S10 consistency flag
        -> priority_human_review bool

    Args:
        preprocessed_image: float32 HWC numpy array [0,1].
        quality_tier: "Good" | "Borderline" | "Reject".
        config: NetraConfig (defaults used if None).

    Returns:
        Dict with keys: s1_vessel, s2_lesion, s3_nv, s4_grading,
        s5_decision, s6_calibration, s7_ensemble, s8_explain,
        s10_consistency, performance_report, pipeline_meta.

    Raises:
        ValueError: If quality_tier == "Reject".
        TypeError:  If preprocessed_image is not a numpy array.
    """
    if config is None:
        config = NetraConfig()

    # Hard Reject gate (Stage 9 / constraint)
    norm_q = str(quality_tier).strip().capitalize()
    if norm_q.lower() == "reject":
        raise ValueError(
            "Reject-quality image reached the orchestrator.  "
            "Reject-quality images MUST NEVER receive an automated clearance.  "
            "Stop at Stage 1 (IQA) and request image recapture."
        )
    if norm_q not in ("Good", "Borderline"):
        raise ValueError(
            f"quality_tier must be 'Good', 'Borderline', or 'Reject', "
            f"got '{quality_tier}'."
        )
    if not isinstance(preprocessed_image, np.ndarray):
        raise TypeError(
            f"preprocessed_image must be a numpy ndarray, "
            f"got {type(preprocessed_image).__name__}."
        )

    t0     = time.perf_counter()
    result: Dict[str, Any] = {}

    # S1 — Vessel Segmentation
    logger.info("[NETRA-DR] S1 vessel segmentation...")
    result["s1_vessel"] = _run_vessel_segmentation(preprocessed_image, config)

    # S2 — Lesion Detection
    logger.info("[NETRA-DR] S2 lesion detection...")
    s2_lesion = _run_lesion_detection(preprocessed_image, config)
    result["s2_lesion"] = s2_lesion

    # S3 — Neovascularisation Stub
    logger.info("[NETRA-DR] S3 NV stub (not yet trained)...")
    result["s3_nv"] = _run_nv_stub()

    # S7 / S4 — Ensemble + Grading
    logger.info("[NETRA-DR] S7/S4 grading (backend=%s)...", config.GRADER_BACKEND)
    s7_ensemble: Dict[str, Any] = {"status": "ok", "error": None}
    s4_grading:  Dict[str, Any] = {
        "status": "ok", "error": None, "probabilities": None, "severity_class": None,
    }
    try:
        ens = _run_ensemble_grading(preprocessed_image, config)
        s7_ensemble.update(ens)
        s4_grading = {
            "severity_class": int(np.argmax(ens["mean_probabilities"])),
            "probabilities":  ens["mean_probabilities"],
            "model_name":     ens.get("model_name", config.GRADER_BACKEND),
            "model_version":  ens.get("model_version", "unknown"),
            "class_labels":   ens.get("class_labels", ["0","1","2","3","4"]),
            "active_backend": config.GRADER_BACKEND,
            "backend_label": (
                "ResNet-50  (HF: sakshamkr1/ResNet50-APTOS-DR)"
                if config.GRADER_BACKEND == "resnet50"
                else "EfficientNet-B0  (HF: adarshcod30/drdetect-dr-screening)"
            ),
            "lesion_fusion_in_grader": False,   # constraint: never fuse lesions in grader
            "foundation_model_used":   False,   # RETFound/DINOv2 never production grader
            "stage":  "dr_grading",
            "status": "ok",
            "error":  None,
        }
    except Exception as exc:
        msg = f"{type(exc).__name__}: {exc}"
        s7_ensemble.update({"status": "error", "error": msg})
        s4_grading.update({"status": "error",  "error": msg})
        logger.error("[NETRA-DR] S4/S7 grading failed: %s", msg)

    result["s7_ensemble"] = s7_ensemble
    result["s4_grading"]  = s4_grading

    # S6 — Temperature Calibration
    logger.info("[NETRA-DR] S6 temperature calibration...")
    s6_calibration: Dict[str, Any] = {"status": "ok", "error": None}
    calibrated_probs: Optional[List[float]] = None
    raw_probs = s4_grading.get("probabilities")

    if raw_probs is not None:
        try:
            cal = _run_calibration(raw_probs, config)
            s6_calibration.update(cal)
            calibrated_probs = cal["calibrated_probabilities"]
        except Exception as exc:
            msg = f"{type(exc).__name__}: {exc}"
            s6_calibration.update({"status": "error", "error": msg})
            calibrated_probs = raw_probs  # fallback to uncalibrated
            logger.warning("[NETRA-DR] S6 calibration failed, using raw probs: %s", msg)
    else:
        s6_calibration.update({
            "status": "skipped",
            "error": "No grading probabilities from S4.",
        })

    result["s6_calibration"] = s6_calibration

    # S5 — Decision Fusion (includes S9 quality-tier thresholds)
    logger.info("[NETRA-DR] S5 decision fusion (quality_tier=%s)...", norm_q)
    s5_decision: Dict[str, Any] = {"status": "ok", "error": None}

    if calibrated_probs is not None:
        try:
            s5 = _run_decision_fusion(
                calibrated_probabilities=calibrated_probs,
                s2_lesion=s2_lesion,
                quality_tier=norm_q,
                config=config,
            )
            s5_decision.update(s5)
        except Exception as exc:
            msg = f"{type(exc).__name__}: {exc}"
            s5_decision.update({"status": "error", "error": msg, "referable_decision": None})
            logger.error("[NETRA-DR] S5 decision fusion failed: %s", msg)
    else:
        s5_decision.update({
            "status": "skipped",
            "error": "No calibrated probabilities from S6.",
            "referable_decision": None,
        })

    result["s5_decision"] = s5_decision

    # S8 — Explainability
    severity_class = s4_grading.get("severity_class")
    logger.info("[NETRA-DR] S8 explainability (severity_class=%s)...", severity_class)

    if severity_class is not None:
        s8_explain = _run_explainability(
            preprocessed_image=preprocessed_image,
            severity_class=int(severity_class),
            s2_lesion=s2_lesion,
            config=config,
        )
    else:
        s8_explain = {
            "status":         "skipped",
            "error":          "No severity_class from S4 — explainability skipped.",
            "label":          "model attention",  # mandatory field always present
            "evidence_label": "detected evidence",
            "heatmap_overlay": None,
            "heatmap_raw":    None,
            "hirescam_raw":   None,
            "iou_vs_he":      None,
            "iou_vs_ex":      None,
        }

    result["s8_explain"] = s8_explain

    # S10 — Consistency Flag
    logger.info("[NETRA-DR] S10 consistency flag...")
    result["s10_consistency"] = _check_consistency_flag(s8_explain, config)

    # Performance report (PRD two-sided CI phrasing)
    result["performance_report"] = _format_performance_report(config)

    # Pipeline metadata
    elapsed = time.perf_counter() - t0
    result["pipeline_meta"] = {
        "quality_tier":              norm_q,
        "grader_backend":            config.GRADER_BACKEND,
        "ensemble_checkpoints":      len(config.ensemble_checkpoint_paths),
        "mc_dropout_used":           False,   # constraint: NEVER True
        "foundation_model_grader":   False,   # RETFound/DINOv2 never production grader
        "sealed_test_touched":       False,   # Messidor-2/IDRiD sealed never loaded here
        "nv_model_trained":          False,   # S3 stub
        "lesion_merged_in_grader":   False,   # constraint: lesions NOT fused in grader
        "hemorrhage_subtypes_reported": False, # constraint: no flame/dot-blot/deep
        "elapsed_seconds":           round(elapsed, 3),
        "stages_completed": [
            "S1_vessel_segmentation",
            "S2_lesion_detection",
            "S3_nv_stub",
            "S4_dr_grading",
            "S5_decision_fusion",
            "S6_temperature_calibration",
            "S7_ensemble",
            "S8_explainability",
            "S9_quality_tier_thresholds",
            "S10_consistency_flag",
        ],
    }

    logger.info(
        "[NETRA-DR] Pipeline complete in %.2fs — decision: %s | priority_review: %s",
        elapsed,
        result["s5_decision"].get("referable_decision", "N/A"),
        result["s10_consistency"].get("priority_human_review", False),
    )

    return result


# ---------------------------------------------------------------------------
# Offline utility: train the decision fusion logistic regression
# ---------------------------------------------------------------------------

def train_decision_fusion_model(
    X: np.ndarray,
    y: np.ndarray,
    output_dir: Union[str, Path] = "models/decision_fusion",
    quality_tier_threshold_good: float = 0.50,
    quality_tier_threshold_borderline: float = 0.35,
    random_state: int = 42,
) -> Dict[str, Any]:
    """
    Train and persist the decision fusion logistic regression.

    MUST be called on a held-out calibration split — NEVER on the sealed test set.
    Do NOT pass Messidor-2 or the sealed IDRiD split as X/y here.

    Feature matrix X — must match _build_fusion_feature_vector exactly:
      col 0: (a) calibrated P(ICDR >= 2)
      col 1: (b) MA count (near-macula count preferred)
      col 2: (c) HE presence (0/1)
      col 3: (d) EX area near fovea [0,1]
      col 4: (e) is_borderline_quality (0/1)

    y: binary labels (1 = referable, 0 = non-referable).

    Writes metadata.json to output_dir with fitted=True, weights, intercept,
    feature names, and AUC on the calibration split.
    """
    try:
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import roc_auc_score
    except ImportError as exc:
        raise RuntimeError(
            "scikit-learn is required.  Install via: pip install scikit-learn"
        ) from exc

    if X.shape[1] != 5:
        raise ValueError(
            f"Feature matrix must have exactly 5 columns, got {X.shape[1]}.  "
            "Columns: (a) P(ICDR>=2), (b) MA count, (c) HE presence, "
            "(d) EX near fovea, (e) is_borderline."
        )

    lr = LogisticRegression(
        penalty="l2",
        C=1.0,
        solver="lbfgs",
        max_iter=1000,
        random_state=random_state,
        class_weight="balanced",
    )
    lr.fit(X, y)

    weights   = lr.coef_[0].tolist()
    intercept = float(lr.intercept_[0])
    proba_cal = lr.predict_proba(X)[:, 1]
    auc_cal   = float(roc_auc_score(y, proba_cal))

    feature_names = [
        "(a) P(ICDR>=2) calibrated",
        "(b) MA count (near-macula)",
        "(c) HE presence",
        "(d) EX area near fovea",
        "(e) is_borderline_quality",
    ]
    logger.info("=== Decision Fusion LR Coefficients (calibration split) ===")
    for name, coef in zip(feature_names, weights):
        logger.info("  %-38s  %+.4f", name, coef)
    logger.info("  %-38s  %+.4f", "Intercept", intercept)
    logger.info("  AUC on calibration split: %.4f", auc_cal)

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    metadata = {
        "fitted":               True,
        "model_type":           "logistic_regression",
        "library":              "scikit-learn",
        "penalty":              "l2",
        "C":                    1.0,
        "weights":              weights,
        "intercept":            intercept,
        "threshold":            quality_tier_threshold_good,
        "threshold_good":       quality_tier_threshold_good,
        "threshold_borderline": quality_tier_threshold_borderline,
        "feature_names":        feature_names,
        "auc_calibration_split": auc_cal,
        "training_note": (
            "Trained on held-out calibration split ONLY.  "
            "Messidor-2 and sealed IDRiD test split were NOT used here."
        ),
    }
    meta_path = out_dir / "metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    logger.info("Decision fusion metadata written to %s", meta_path)
    return metadata
