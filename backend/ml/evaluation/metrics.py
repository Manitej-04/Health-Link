"""Evaluation helpers: classification metrics, calibration metrics and
bootstrap confidence intervals. All functions operate on held-out data."""

from __future__ import annotations

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

DECISION_THRESHOLD = 0.5


def expected_calibration_error(y_true, y_prob, n_bins: int = 5) -> float:
    """Equal-width-bin ECE. Few bins are used because test sets are small
    (60-160 samples); more bins would leave most bins nearly empty."""
    y_true = np.asarray(y_true)
    y_prob = np.asarray(y_prob)
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (y_prob >= lo) & ((y_prob < hi) if hi < 1.0 else (y_prob <= hi))
        if mask.any():
            ece += mask.mean() * abs(y_prob[mask].mean() - y_true[mask].mean())
    return float(ece)


def calibration_table(y_true, y_prob, n_bins: int = 5) -> list[dict]:
    y_true = np.asarray(y_true)
    y_prob = np.asarray(y_prob)
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    rows = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (y_prob >= lo) & ((y_prob < hi) if hi < 1.0 else (y_prob <= hi))
        rows.append({
            "bin": f"{lo:.1f}-{hi:.1f}",
            "count": int(mask.sum()),
            "mean_predicted": float(y_prob[mask].mean()) if mask.any() else None,
            "observed_rate": float(y_true[mask].mean()) if mask.any() else None,
        })
    return rows


def classification_metrics(y_true, y_prob, baseline_prevalence: float) -> dict:
    y_true = np.asarray(y_true)
    y_prob = np.asarray(y_prob)
    y_pred = (y_prob >= DECISION_THRESHOLD).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    brier = brier_score_loss(y_true, y_prob)
    brier_ref = brier_score_loss(y_true, np.full_like(y_prob, baseline_prevalence, dtype=float))
    return {
        "n": int(len(y_true)),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        # Accuracy of always predicting the majority class — a model's accuracy
        # should be read against this on imbalanced data.
        "majority_baseline_accuracy": float(max(y_true.mean(), 1 - y_true.mean())),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "specificity": float(tn / (tn + fp)) if (tn + fp) else 0.0,
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, y_prob)),
        "brier": float(brier),
        "brier_reference": float(brier_ref),
        "brier_skill_score": float(1 - brier / brier_ref) if brier_ref > 0 else 0.0,
        "ece": expected_calibration_error(y_true, y_prob),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
    }


def bootstrap_auc_ci(y_true, y_prob, n_boot: int = 1000, seed: int = 42) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    y_true = np.asarray(y_true)
    y_prob = np.asarray(y_prob)
    scores = []
    n = len(y_true)
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        if len(np.unique(y_true[idx])) < 2:
            continue
        scores.append(roc_auc_score(y_true[idx], y_prob[idx]))
    return float(np.percentile(scores, 2.5)), float(np.percentile(scores, 97.5))
