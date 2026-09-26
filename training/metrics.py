"""
training/metrics.py — dependency-free evaluation metrics for grading model selection.

No scikit-learn dependency (keeps the training environment install small on a
bandwidth-constrained machine). Implements exactly what
docs/SIH26038_Development_Blueprint.md Section K.12 lists as needed for model
selection on the internal validation split: confusion matrix, per-class /
macro sensitivity & specificity, referable (Grade>=2) sensitivity & specificity,
and quadratic weighted kappa (QWK).
"""

from __future__ import annotations

from typing import Dict, List

import numpy as np


def confusion_matrix(y_true: np.ndarray, y_pred: np.ndarray, num_classes: int = 5) -> np.ndarray:
    cm = np.zeros((num_classes, num_classes), dtype=np.int64)
    for t, p in zip(y_true, y_pred):
        cm[int(t), int(p)] += 1
    return cm


def quadratic_weighted_kappa(y_true: np.ndarray, y_pred: np.ndarray, num_classes: int = 5) -> float:
    """Standard QWK (Cohen's kappa with quadratic weights) — the ordinal agreement
    metric used throughout the DR grading literature (blueprint K.9)."""
    cm = confusion_matrix(y_true, y_pred, num_classes).astype(np.float64)
    n = cm.sum()
    if n == 0:
        return 0.0

    weights = np.zeros((num_classes, num_classes))
    for i in range(num_classes):
        for j in range(num_classes):
            weights[i, j] = ((i - j) ** 2) / ((num_classes - 1) ** 2)

    row_marg = cm.sum(axis=1)
    col_marg = cm.sum(axis=0)
    expected = np.outer(row_marg, col_marg) / n

    numerator = float(np.sum(weights * cm))
    denominator = float(np.sum(weights * expected))
    if denominator == 0:
        return 1.0
    return 1.0 - numerator / denominator


def per_class_sensitivity_specificity(cm: np.ndarray) -> List[Dict[str, float]]:
    """Per-class one-vs-rest sensitivity (recall) and specificity from a confusion matrix."""
    n = cm.sum()
    out = []
    for c in range(cm.shape[0]):
        tp = cm[c, c]
        fn = cm[c, :].sum() - tp
        fp = cm[:, c].sum() - tp
        tn = n - tp - fn - fp
        sens = float(tp) / float(tp + fn) if (tp + fn) > 0 else float("nan")
        spec = float(tn) / float(tn + fp) if (tn + fp) > 0 else float("nan")
        out.append({"class": c, "sensitivity": sens, "specificity": spec, "support": int(tp + fn)})
    return out


def referable_sensitivity_specificity(y_true: np.ndarray, y_pred: np.ndarray, referable_grades=(2, 3, 4)) -> Dict[str, float]:
    """
    Binary sensitivity/specificity for referable DR (ICDR Grade >= 2), the
    PS-required headline metric (>90% sensitivity, >85% specificity target).
    """
    true_bin = np.isin(y_true, referable_grades).astype(int)
    pred_bin = np.isin(y_pred, referable_grades).astype(int)

    tp = int(np.sum((true_bin == 1) & (pred_bin == 1)))
    fn = int(np.sum((true_bin == 1) & (pred_bin == 0)))
    fp = int(np.sum((true_bin == 0) & (pred_bin == 1)))
    tn = int(np.sum((true_bin == 0) & (pred_bin == 0)))

    sens = float(tp) / float(tp + fn) if (tp + fn) > 0 else float("nan")
    spec = float(tn) / float(tn + fp) if (tn + fp) > 0 else float("nan")
    return {
        "sensitivity": sens, "specificity": spec,
        "tp": tp, "fn": fn, "fp": fp, "tn": tn,
        "n_referable": int(tp + fn), "n_non_referable": int(tn + fp),
    }


def macro_f1(cm: np.ndarray) -> float:
    f1s = []
    for c in range(cm.shape[0]):
        tp = cm[c, c]
        fp = cm[:, c].sum() - tp
        fn = cm[c, :].sum() - tp
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        f1s.append(f1)
    return float(np.mean(f1s))
