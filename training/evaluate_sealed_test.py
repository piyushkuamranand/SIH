"""
training/evaluate_sealed_test.py — ONE-TIME evaluation of the frozen production
grading model on the sealed IDRiD grading-test split (103 images).

This is the "open the sealed test exactly once, after everything is frozen"
step from the Final Model Stack (Step 12) and blueprint MLR-003. It must
only ever be run once the architecture, weights, calibration, and decision
thresholds are already frozen — which they are: this script does not fit,
tune, or select anything against this data. It only measures.

Independence of this test set was verified separately and BEFORE this script
was run: training/verify_sealed_test_independence.py confirmed zero
perceptual near-duplicates between these 103 images and every image used in
training/validation/calibration (see its output, referenced in
docs/checkpoints/final_system_verification.md).

Uses the EXACT SAME production code path as the live app for every image:
  pipeline.quality.run_quality_gate()   (real quality gate, same rule-based baseline)
  pipeline.grading.run_grading()        (frozen ResNet-50 ONNX)
  pipeline.grading.apply_calibration()  (the actual fitted configs/calibration.json)
  pipeline.decision.run_decision_fusion() (the actual documented decision policy)

Per the Final Model Stack's own reporting instruction (Section 6), results
are reported TWICE:
  (a) gradable images only (GOOD/BORDERLINE quality)
  (b) including ungradable (REJECT) images, auto-referred (counted as REFER)

And, per Section 3, TWO referable decisions are reported side by side:
  (a) grade-alone (argmax ICDR class >= 2)
  (b) the fused/production decision (quality-tier probability threshold —
      the actual current decision layer; no fitted MA/HE/EX fusion model
      exists, so this is NOT a learned fusion, and is labelled as such)

Never imported by app/ or pipeline/.
"""

from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path
from typing import Dict, List

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.quality import run_quality_gate
from pipeline.grading import run_grading, apply_calibration
from pipeline.decision import run_decision_fusion
from training.metrics import confusion_matrix, quadratic_weighted_kappa, macro_f1

REFERABLE_GRADES = {2, 3, 4}


def confusion_counts(y_true_referable: np.ndarray, y_pred_referable: np.ndarray) -> Dict[str, int]:
    tp = int(np.sum((y_true_referable == 1) & (y_pred_referable == 1)))
    tn = int(np.sum((y_true_referable == 0) & (y_pred_referable == 0)))
    fp = int(np.sum((y_true_referable == 0) & (y_pred_referable == 1)))
    fn = int(np.sum((y_true_referable == 1) & (y_pred_referable == 0)))
    return {"TP": tp, "TN": tn, "FP": fp, "FN": fn}


def binary_metrics(c: Dict[str, int]) -> Dict[str, float]:
    tp, tn, fp, fn = c["TP"], c["TN"], c["FP"], c["FN"]
    n = tp + tn + fp + fn
    sens = tp / (tp + fn) if (tp + fn) > 0 else float("nan")
    spec = tn / (tn + fp) if (tn + fp) > 0 else float("nan")
    precision = tp / (tp + fp) if (tp + fp) > 0 else float("nan")
    npv = tn / (tn + fn) if (tn + fn) > 0 else float("nan")
    accuracy = (tp + tn) / n if n > 0 else float("nan")
    f1 = 2 * precision * sens / (precision + sens) if (precision + sens) > 0 and not (np.isnan(precision) or np.isnan(sens)) else float("nan")
    return {"sensitivity": sens, "specificity": spec, "precision": precision,
            "npv": npv, "accuracy": accuracy, "f1": f1}


def roc_auc(y_true: np.ndarray, scores: np.ndarray) -> float:
    """Dependency-free ROC-AUC via the Mann-Whitney U statistic (rank-based, exact for no ties handling via average ranks)."""
    order = np.argsort(scores)
    ranks = np.empty(len(scores))
    ranks[order] = np.arange(1, len(scores) + 1)
    # average ranks for ties
    _, inv, counts = np.unique(scores, return_inverse=True, return_counts=True)
    sums = np.zeros(len(counts))
    np.add.at(sums, inv, ranks)
    avg_ranks = (sums / counts)[inv]
    n_pos = np.sum(y_true == 1)
    n_neg = np.sum(y_true == 0)
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    sum_ranks_pos = np.sum(avg_ranks[y_true == 1])
    auc = (sum_ranks_pos - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)
    return float(auc)


def pr_auc(y_true: np.ndarray, scores: np.ndarray) -> float:
    """Dependency-free PR-AUC via trapezoidal integration over score-sorted thresholds."""
    order = np.argsort(-scores)
    y_sorted = y_true[order]
    tp_cum = np.cumsum(y_sorted == 1)
    fp_cum = np.cumsum(y_sorted == 0)
    n_pos = np.sum(y_true == 1)
    if n_pos == 0:
        return float("nan")
    recall = tp_cum / n_pos
    precision = tp_cum / (tp_cum + fp_cum)
    # prepend (recall=0, precision=1) for standard PR-AUC convention
    recall = np.concatenate([[0.0], recall])
    precision = np.concatenate([[1.0], precision])
    return float(np.trapz(precision, recall))


def main() -> None:
    test_csv = (PROJECT_ROOT / "data" / "raw" / "idrid" / "B_grading" / "B. Disease Grading" /
                "2. Groundtruths" / "b. IDRiD_Disease Grading_Testing Labels.csv")
    test_img_dir = (PROJECT_ROOT / "data" / "raw" / "idrid" / "B_grading" / "B. Disease Grading" /
                     "1. Original Images" / "b. Testing Set")

    rows = list(csv.DictReader(open(test_csv, encoding="utf-8-sig")))
    print(f"Sealed IDRiD grading-test set: {len(rows)} images")

    results: List[Dict] = []
    start = time.time()
    for i, row in enumerate(rows):
        image_id = row["Image name"].strip()
        true_grade = int(row["Retinopathy grade"])
        img_path = test_img_dir / f"{image_id}.jpg"

        entry = {"image_id": image_id, "true_grade": true_grade}
        try:
            q = run_quality_gate(str(img_path))
            entry["quality_label"] = q["quality_label"]

            if q["quality_label"].strip().upper() == "REJECT":
                entry["gradable"] = False
            else:
                entry["gradable"] = True
                g = run_grading(q["preprocessed_image"])
                cal = apply_calibration(g["probabilities"])
                d = run_decision_fusion(
                    calibrated_probabilities=cal["calibrated_probabilities"],
                    ma_count=0, he_presence=False, ex_area=0.0,  # evidence fusion unfitted in production; matches live default when Phase 2 evidence is not separately re-run here (grading-only evaluation, as specified: SAME grading model + calibration + decision code path)
                    quality_label=q["quality_label"],
                )
                entry["predicted_grade"] = g["severity_class"]
                entry["calibrated_probabilities"] = cal["calibrated_probabilities"]
                entry["referable_probability"] = float(np.sum(cal["calibrated_probabilities"][2:]))
                entry["grade_alone_decision"] = d["grade_alone_decision"]
                entry["fused_decision"] = d["referable_decision"]
        except Exception as e:
            entry["error"] = f"{type(e).__name__}: {e}"

        results.append(entry)
        if (i + 1) % 20 == 0:
            print(f"  {i + 1}/{len(rows)}")

    elapsed = time.time() - start
    print(f"Evaluation wall time: {elapsed:.1f}s ({elapsed/len(rows):.2f}s/image)")

    # ---- Split into gradable vs ungradable ----
    gradable = [r for r in results if r.get("gradable")]
    ungradable = [r for r in results if not r.get("gradable")]
    errored = [r for r in results if "error" in r]
    print(f"Gradable: {len(gradable)}  Ungradable (REJECT): {len(ungradable)}  Errored: {len(errored)}")

    def build_report(subset: List[Dict], include_ungradable_as_refer: bool, label: str) -> Dict:
        y_true = np.array([1 if r["true_grade"] in REFERABLE_GRADES else 0 for r in subset])
        y_pred_grade_alone = np.array([1 if r["grade_alone_decision"] == "REFER" else 0 for r in subset])
        y_pred_fused = np.array([1 if r["fused_decision"] == "REFER" else 0 for r in subset])
        scores = np.array([r["referable_probability"] for r in subset])

        if include_ungradable_as_refer and ungradable:
            y_true_u = np.array([1 if r["true_grade"] in REFERABLE_GRADES else 0 for r in ungradable])
            y_true = np.concatenate([y_true, y_true_u])
            y_pred_grade_alone = np.concatenate([y_pred_grade_alone, np.ones(len(ungradable), dtype=int)])
            y_pred_fused = np.concatenate([y_pred_fused, np.ones(len(ungradable), dtype=int)])
            scores = np.concatenate([scores, np.ones(len(ungradable))])

        cm_grade_alone = confusion_counts(y_true, y_pred_grade_alone)
        cm_fused = confusion_counts(y_true, y_pred_fused)

        report = {
            "label": label,
            "n_images": int(len(y_true)),
            "n_referable_ground_truth": int(np.sum(y_true)),
            "n_non_referable_ground_truth": int(len(y_true) - np.sum(y_true)),
            "grade_alone": {"confusion": cm_grade_alone, "metrics": binary_metrics(cm_grade_alone)},
            "fused": {"confusion": cm_fused, "metrics": binary_metrics(cm_fused)},
            "roc_auc_referable_probability": roc_auc(y_true, scores),
            "pr_auc_referable_probability": pr_auc(y_true, scores),
        }
        return report

    report_gradable_only = build_report(gradable, include_ungradable_as_refer=False,
                                         label="Gradable images only (GOOD/BORDERLINE quality)")
    report_including_ungradable = build_report(gradable, include_ungradable_as_refer=True,
                                                label="Including ungradable images (auto-referred as REFER)")

    # 5-class stats on gradable images (secondary, not the headline referable metric)
    y_true_5 = np.array([r["true_grade"] for r in gradable])
    y_pred_5 = np.array([r["predicted_grade"] for r in gradable])
    qwk = quadratic_weighted_kappa(y_true_5, y_pred_5, 5)
    cm5 = confusion_matrix(y_true_5, y_pred_5, 5)
    mf1 = macro_f1(cm5)

    final_report = {
        "dataset": "IDRiD grading-test (folder B, 'b. Testing Set') — the project's sealed external test set",
        "n_total_images": len(rows),
        "n_gradable": len(gradable),
        "n_ungradable_reject": len(ungradable),
        "n_errored": len(errored),
        "errored_details": errored,
        "model_checkpoint": "models/grading/grading_model.onnx",
        "model_metadata": json.load(open(PROJECT_ROOT / "models" / "grading" / "metadata.json"))["model_name"],
        "model_version": json.load(open(PROJECT_ROOT / "models" / "grading" / "metadata.json"))["model_version"],
        "calibration_config": json.load(open(PROJECT_ROOT / "configs" / "calibration.json")),
        "decision_rule_config": json.load(open(PROJECT_ROOT / "configs" / "decision_rule.json")),
        "evaluation_wall_time_sec": elapsed,
        "five_class_stats_on_gradable": {
            "qwk": qwk, "macro_f1": mf1, "confusion_matrix_5class": cm5.tolist(),
        },
        "gradable_only": report_gradable_only,
        "including_ungradable": report_including_ungradable,
        "note": (
            "This evaluation reuses the same MA/HE/EX evidence defaults (0/False/0.0) as the live decision "
            "layer's fallback would use if Phase 2 evidence were absent, since decision fusion is documented "
            "as grader-only-plus-quality-tier fallback (fusion_model_fitted=false) — no fitted evidence-fusion "
            "model exists to bypass. This matches production behavior exactly for this decision layer version."
        ),
    }

    out_path = PROJECT_ROOT / "docs" / "checkpoints" / "sealed_test_evaluation.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(final_report, f, indent=2, default=str)
    print(f"\nWrote {out_path}")

    raw_path = PROJECT_ROOT / "docs" / "checkpoints" / "sealed_test_raw_results.json"
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"Wrote {raw_path}")

    print("\n=== GRADABLE-ONLY (fused decision) ===")
    print(json.dumps(report_gradable_only["fused"], indent=2))
    print("\n=== INCLUDING UNGRADABLE (fused decision) ===")
    print(json.dumps(report_including_ungradable["fused"], indent=2))


if __name__ == "__main__":
    main()
