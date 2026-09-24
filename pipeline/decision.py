"""
pipeline/decision.py — NETRA-DR Phase 3: Decision Fusion & Referral Decision

Combines calibrated grade probabilities (from TASK-011) with structural lesion evidence
(MA count, HE presence, EX area from Phase 2) and the intake quality tier (Phase 1)
into a final refer/no-refer screening recommendation.

Key requirements & design principles:
1. Transparent decision logic: Computes both `referable_decision` (quality-aware / fused)
   and `grade_alone_decision` (naive single threshold at Grade >= 2) side by side for reporting.
2. Quality-tier-aware thresholds: Applies a stricter (higher-sensitivity) referral cutoff
   for Borderline-quality images (e.g. threshold 0.35) than Good-quality images (threshold 0.50).
3. Quality safety gate: Reject-quality images never receive an automated decision
   (they are stopped in Phase 1 for recapture). Passing a Reject-quality image raises an error.
4. Honest fallback handling: If a trained logistic regression model artifact does not exist
   in models/decision_fusion/, the system falls back to the quality-tier-aware decision rule
   and explicitly records `fitted = False` and `fusion_status = "using grade-alone fallback, fusion model not yet trained"`.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np

logger = logging.getLogger(__name__)


def _load_decision_config(config_path: Union[str, Path] = "configs/decision_rule.json") -> Dict[str, Any]:
    """Load decision configuration from JSON file or return default fallback config."""
    cfg_file = Path(config_path)
    if cfg_file.is_file():
        try:
            with open(cfg_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            logger.warning(f"Failed to load decision config from {config_path}: {exc}. Using defaults.")

    return {
        "fusion_model_fitted": False,
        "method": "grade_alone_fallback",
        "referable_grades": [2, 3, 4],
        "thresholds": {
            "good_quality": {"referable_prob_threshold": 0.50},
            "borderline_quality": {"referable_prob_threshold": 0.35},
        },
    }


def _check_fitted_fusion_model(model_dir: Union[str, Path] = "models/decision_fusion") -> Optional[Dict[str, Any]]:
    """
    Check if a trained logistic regression fusion model is available in model_dir.

    Returns:
        Contract/model dict if available and fitted, otherwise None.
    """
    metadata_path = Path(model_dir) / "metadata.json"
    if not metadata_path.is_file():
        return None

    try:
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)
        if metadata.get("fitted", False) is True and "weights" in metadata and "intercept" in metadata:
            return metadata
    except Exception as exc:
        logger.warning(f"Error reading fusion model metadata at {metadata_path}: {exc}")
    
    return None


def run_decision_fusion(
    calibrated_probabilities: Union[List[float], np.ndarray, Dict[str, Any]],
    ma_count: int = 0,
    he_presence: Union[bool, int] = False,
    ex_area: float = 0.0,
    quality_label: str = "Good",
    config_path: Union[str, Path] = "configs/decision_rule.json",
    model_dir: Union[str, Path] = "models/decision_fusion",
) -> Dict[str, Any]:
    """
    Execute Phase 3 decision fusion to generate the final screening referral recommendation.

    Args:
        calibrated_probabilities: 5-element array/list of calibrated ICDR grade probabilities
                                  [P(Grade 0), P(Grade 1), P(Grade 2), P(Grade 3), P(Grade 4)],
                                  or dict containing "calibrated_probabilities" from apply_calibration().
        ma_count:                 Integer microaneurysm count from Phase 2 (TASK-008).
        he_presence:              Boolean or int indicating hemorrhage presence from Phase 2 (TASK-007).
        ex_area:                  Normalized pixel area fraction of hard exudates [0.0, 1.0] (TASK-007).
        quality_label:            Quality gate assessment ("Good", "Borderline", or "Reject").
        config_path:              Path to decision rule configuration file.
        model_dir:                Path to decision fusion model directory.

    Returns:
        Dict containing:
            referable_decision       (str)         — "REFER" or "NO REFER" (quality-aware / fused decision)
            grade_alone_decision     (str)         — "REFER" or "NO REFER" (naive single threshold on grade alone)
            is_referable             (bool)        — True if referable_decision == "REFER"
            grade_alone_referable    (bool)        — True if grade_alone_decision == "REFER"
            predicted_grade          (int)         — Predicted ICDR grade index (0–4)
            calibrated_probabilities (List[float]) — 5-element calibrated class probabilities
            referable_probability    (float)       — Sum of calibrated P(Grade >= 2)
            quality_tier             (str)         — "Good" or "Borderline"
            threshold_applied        (float)       — Threshold used for referable_decision
            evidence                 (dict)        — Extracted lesion features (ma_count, he_presence, ex_area)
            fusion_status            (str)         — Description of fusion mode (fallback or fitted)
            fitted                   (bool)        — Whether a trained fusion model was used
            reason                   (str)         — Detailed clinical & algorithmic explanation of the decision

    Raises:
        ValueError: If quality_label is 'Reject' (Reject images must stop at Phase 1),
                    or if probabilities or input evidence are invalid.
    """
    # 1. Quality safety gate verification
    norm_quality = str(quality_label).strip().capitalize()
    if norm_quality.lower() == "reject":
        raise ValueError(
            "Reject-quality image cannot receive an automated referral decision. "
            "Phase 1 quality gate rejected this image; recapture is required."
        )
    if norm_quality not in ("Good", "Borderline"):
        raise ValueError(
            f"Invalid quality_label '{quality_label}'. Must be 'Good', 'Borderline', or 'Reject'."
        )

    # 2. Extract and validate calibrated probabilities
    if isinstance(calibrated_probabilities, dict):
        if "calibrated_probabilities" in calibrated_probabilities:
            raw_probs = calibrated_probabilities["calibrated_probabilities"]
        elif "probabilities" in calibrated_probabilities:
            raw_probs = calibrated_probabilities["probabilities"]
        else:
            raise ValueError(
                "Input dictionary must contain 'calibrated_probabilities' or 'probabilities'."
            )
    else:
        raw_probs = calibrated_probabilities

    probs = np.asarray(raw_probs, dtype=np.float64)
    if probs.ndim != 1 or len(probs) != 5:
        raise ValueError(
            f"calibrated_probabilities must be a 5-element array (ICDR grades 0–4), got shape {probs.shape} with {len(probs)} elements."
        )
    if np.any(probs < 0.0) or np.any(np.isnan(probs)):
        raise ValueError(f"All probabilities must be valid non-negative numbers, got {probs}.")
    
    total_p = float(np.sum(probs))
    if total_p <= 0.0:
        raise ValueError("Sum of probabilities must be strictly positive.")
    
    # Normalize if minor float rounding occurred
    probs = probs / total_p
    calibrated_prob_list = [float(p) for p in probs]

    # 3. Extract evidence features
    ma_count_val = int(max(0, ma_count))
    he_presence_val = bool(he_presence)
    ex_area_val = float(max(0.0, min(1.0, ex_area)))
    predicted_grade = int(np.argmax(probs))

    # Referable DR probability: sum of Grade 2 (Moderate), Grade 3 (Severe), Grade 4 (Proliferative)
    # Referable grades per ICDR are Grade 2, 3, 4
    referable_probability = float(np.sum(probs[2:]))

    # 4. Naive grade-alone decision (standard 0.50 cutoff on P(Grade >= 2) without quality tier adjustment)
    grade_alone_threshold = 0.50
    grade_alone_referable = bool(referable_probability >= grade_alone_threshold or predicted_grade >= 2)
    grade_alone_decision = "REFER" if grade_alone_referable else "NO REFER"

    # 5. Check for fitted fusion model vs fallback explicit rule
    fitted_model = _check_fitted_fusion_model(model_dir)
    config = _load_decision_config(config_path)

    evidence_dict = {
        "ma_count": ma_count_val,
        "he_presence": he_presence_val,
        "ex_area": ex_area_val,
    }

    if fitted_model is not None:
        # A trained logistic regression model exists and is marked fitted
        weights = np.asarray(fitted_model["weights"], dtype=np.float64)
        intercept = float(fitted_model["intercept"])
        is_borderline_val = 1.0 if norm_quality == "Borderline" else 0.0

        # Feature vector: [P(Grade >= 2), ma_count, he_presence, ex_area, is_borderline]
        features = np.array([
            referable_probability,
            float(ma_count_val),
            1.0 if he_presence_val else 0.0,
            ex_area_val,
            is_borderline_val,
        ], dtype=np.float64)

        if len(weights) != len(features):
            raise ValueError(
                f"Fusion model weights dimension mismatch: expected {len(features)}, got {len(weights)}."
            )

        logit = float(intercept + np.dot(weights, features))
        fusion_prob = float(1.0 / (1.0 + np.exp(-logit)))
        model_threshold = float(fitted_model.get("threshold", 0.50))
        
        is_referable = bool(fusion_prob >= model_threshold)
        referable_decision = "REFER" if is_referable else "NO REFER"
        threshold_applied = model_threshold
        fitted = True
        fusion_status = "fitted_logistic_regression"
        reason = (
            f"Fitted logistic regression decision: fused probability = {fusion_prob:.3f} "
            f"(threshold: {model_threshold:.2f}). Evidence: P(Grade>=2)={referable_probability:.3f}, "
            f"MAs={ma_count_val}, HE={he_presence_val}, EX_area={ex_area_val:.4f}, Quality={norm_quality}."
        )
    else:
        # Honest fallback: rule-based decision combining calibrated probabilities and quality tier
        thresholds_cfg = config.get("thresholds", {})
        if norm_quality == "Borderline":
            threshold_applied = float(
                thresholds_cfg.get("borderline_quality", {}).get("referable_prob_threshold", 0.35)
            )
        else:
            threshold_applied = float(
                thresholds_cfg.get("good_quality", {}).get("referable_prob_threshold", 0.50)
            )

        # Stricter evaluation for Borderline quality ensures higher sensitivity / clinical safety
        is_referable = bool(referable_probability >= threshold_applied or predicted_grade >= 2)
        referable_decision = "REFER" if is_referable else "NO REFER"
        fitted = False
        fusion_status = "using grade-alone fallback, fusion model not yet trained"

        if is_referable:
            reason = (
                f"Referral recommended ({norm_quality} quality tier): calibrated P(Grade>=2) = {referable_probability:.3f} "
                f">= threshold {threshold_applied:.2f} (predicted ICDR Grade {predicted_grade}). "
                f"Lesion evidence logged: {ma_count_val} MAs, HE present={he_presence_val}, EX area={ex_area_val:.4f}."
            )
        else:
            reason = (
                f"No referral needed ({norm_quality} quality tier): calibrated P(Grade>=2) = {referable_probability:.3f} "
                f"< threshold {threshold_applied:.2f} (predicted ICDR Grade {predicted_grade}). "
                f"Lesion evidence logged: {ma_count_val} MAs, HE present={he_presence_val}, EX area={ex_area_val:.4f}."
            )

    return {
        "referable_decision": referable_decision,
        "grade_alone_decision": grade_alone_decision,
        "is_referable": is_referable,
        "grade_alone_referable": grade_alone_referable,
        "predicted_grade": predicted_grade,
        "calibrated_probabilities": calibrated_prob_list,
        "referable_probability": referable_probability,
        "quality_tier": norm_quality,
        "threshold_applied": threshold_applied,
        "evidence": evidence_dict,
        "fusion_status": fusion_status,
        "fitted": fitted,
        "reason": reason,
    }


# Alias for intuitive importing across pipeline modules
make_referral_decision = run_decision_fusion
