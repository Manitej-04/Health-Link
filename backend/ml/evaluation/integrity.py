"""Dataset integrity / leakage checks run before every training job.

The checks are deliberately simple and transparent. A flag does not prove
leakage; it means the dataset shows a pattern that makes a high score
untrustworthy, and the module is downgraded to "experimental".
"""

from __future__ import annotations

import pandas as pd
from sklearn.metrics import roc_auc_score

# Thresholds fixed before any model was trained (see docs/ML_METHODOLOGY.md).
SINGLE_FEATURE_AUC_FLAG = 0.95   # one raw column almost determines the label
MISSINGNESS_AUC_FLAG = 0.75      # how much data is *missing* predicts the label
PERFECT_SEPARATION_FLAG = 0.99   # held-out ROC-AUC this high on small clinical data is implausible


def _auc_either_direction(y, x) -> float:
    a = roc_auc_score(y, x)
    return max(a, 1 - a)


def run_checks(X: pd.DataFrame, y: pd.Series) -> dict:
    report: dict = {"flags": []}

    data = X.assign(__target=y.values)
    exact_dups = int(data.duplicated().sum())
    conflicting = int(
        data[X.duplicated(keep=False)].groupby(list(X.columns), dropna=False)["__target"].nunique().gt(1).sum()
    ) if X.duplicated().any() else 0
    report["exact_duplicate_rows"] = exact_dups
    report["conflicting_label_duplicates"] = conflicting
    if conflicting:
        report["flags"].append(f"{conflicting} identical feature vectors carry different labels")

    report["class_counts"] = {str(k): int(v) for k, v in y.value_counts().sort_index().items()}
    report["missing_percent"] = {c: round(float(v) * 100, 1) for c, v in X.isna().mean().items() if v > 0}

    aucs = {}
    for col in X.columns:
        mask = X[col].notna()
        if mask.sum() > 20 and y[mask].nunique() == 2 and X.loc[mask, col].nunique() > 1:
            aucs[col] = round(_auc_either_direction(y[mask], X.loc[mask, col]), 3)
    report["single_feature_auc"] = dict(sorted(aucs.items(), key=lambda kv: -kv[1]))
    strong = [c for c, a in aucs.items() if a >= SINGLE_FEATURE_AUC_FLAG]
    if strong:
        report["flags"].append(
            f"Single raw features separate the classes almost perfectly: {', '.join(strong)} "
            f"(AUC >= {SINGLE_FEATURE_AUC_FLAG})"
        )

    miss_count = X.isna().sum(axis=1)
    if miss_count.nunique() > 1:
        m_auc = round(_auc_either_direction(y, miss_count), 3)
        report["missingness_auc"] = m_auc
        report["mean_missing_per_row_by_class"] = {
            str(k): round(float(v), 2) for k, v in miss_count.groupby(y).mean().items()
        }
        if m_auc >= MISSINGNESS_AUC_FLAG:
            report["flags"].append(
                f"The number of missing values per record predicts the label (AUC {m_auc}); "
                "records were likely collected differently for each class"
            )
    return report
