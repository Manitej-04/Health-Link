"""Reproducible training pipeline for all four Health-Link disease modules.

Usage (from the ``backend`` directory):

    python -m ml.training.train            # train every disease
    python -m ml.training.train heart      # train one disease

Procedure per disease (see docs/ML_METHODOLOGY.md):
 1. Load + deterministic cleaning, drop exact duplicate rows.
 2. Integrity / leakage checks.
 3. Stratified 80/20 train/test split (seed 42). The test set is touched once.
 4. Model selection by repeated stratified 5-fold CV ROC-AUC on the training set.
 5. Final model = selected pipeline wrapped in sigmoid (Platt) calibration with
    internal 5-fold CV, fit on the training set only.
 6. Held-out evaluation: discrimination, calibration, confusion matrix,
    bootstrap CI. Eligibility rules decide availability and whether
    probabilities are shown.
 7. Persist the pipeline (joblib), metadata.json and plots.
"""

from __future__ import annotations

import hashlib
import json
import platform
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import sklearn  # noqa: E402
from sklearn.calibration import CalibratedClassifierCV, calibration_curve  # noqa: E402
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.metrics import roc_curve  # noqa: E402
from sklearn.model_selection import RepeatedStratifiedKFold, cross_validate, train_test_split  # noqa: E402
from sklearn.neighbors import KNeighborsClassifier  # noqa: E402
from sklearn.svm import SVC  # noqa: E402
from sklearn.tree import DecisionTreeClassifier  # noqa: E402

from ml.evaluation import integrity  # noqa: E402
from ml.evaluation.metrics import bootstrap_auc_ci, calibration_table, classification_metrics  # noqa: E402
from ml.feature_specs import DISEASES, DISEASE_KEYS, feature_names  # noqa: E402
from ml.preprocessing.loaders import DATASET_FILES, RAW_DIR, load  # noqa: E402
from ml.preprocessing.pipeline import build_pipeline  # noqa: E402

SEED = 42
TEST_SIZE = 0.20
ARTIFACT_DIR = Path(__file__).resolve().parents[1] / "artifacts"
REPORTS_DIR = Path(__file__).resolve().parents[3] / "reports"

# ---- Eligibility rules (documented in ML_METHODOLOGY) ----
# Integrity findings (ml.evaluation.integrity) are recorded as "data_caveats"
# and surfaced to users; they do not change a module's status.
MIN_AUC_AVAILABLE = 0.70      # CV and held-out ROC-AUC needed for "available"
MIN_AUC_EXPERIMENTAL = 0.60   # below this the module is "unavailable"
MAX_ECE_FOR_PROBABILITY = 0.10
SIMPLICITY_TOLERANCE = 0.01   # prefer a simpler model if within this CV AUC of the best

# Candidates in order of increasing complexity (used for tie-breaking).
CANDIDATES = {
    "logistic_regression": lambda: LogisticRegression(max_iter=2000, C=1.0),
    "decision_tree": lambda: DecisionTreeClassifier(max_depth=4, min_samples_leaf=5, random_state=SEED),
    "knn": lambda: KNeighborsClassifier(n_neighbors=15, weights="distance"),
    "svm_rbf": lambda: SVC(kernel="rbf", C=1.0, gamma="scale", probability=False, random_state=SEED),
    "random_forest": lambda: RandomForestClassifier(n_estimators=300, min_samples_leaf=3, random_state=SEED, n_jobs=-1),
    "gradient_boosting": lambda: GradientBoostingClassifier(n_estimators=150, max_depth=2, learning_rate=0.05, random_state=SEED),
}
PRETTY = {
    "logistic_regression": "Logistic Regression",
    "decision_tree": "Decision Tree",
    "knn": "K-Nearest Neighbors",
    "svm_rbf": "Support Vector Machine (RBF)",
    "random_forest": "Random Forest",
    "gradient_boosting": "Gradient Boosting",
}


def _scores(model, X):
    if hasattr(model, "predict_proba"):
        return model.predict_proba(X)[:, 1]
    return model.decision_function(X)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _plots(disease: str, out: Path, y_test, p_test, cm: dict) -> list[str]:
    name = DISEASES[disease]["name"]
    files = []

    fig, ax = plt.subplots(figsize=(4.2, 4))
    fpr, tpr, _ = roc_curve(y_test, p_test)
    ax.plot(fpr, tpr, color="#0f766e", lw=2)
    ax.plot([0, 1], [0, 1], ls="--", color="#94a3b8", lw=1)
    ax.set(xlabel="False positive rate", ylabel="True positive rate", title=f"{name} — ROC (held-out)")
    fig.tight_layout(); fig.savefig(out / "roc_curve.png", dpi=120); plt.close(fig)
    files.append("roc_curve.png")

    fig, ax = plt.subplots(figsize=(4.2, 4))
    frac, mean_pred = calibration_curve(y_test, p_test, n_bins=5, strategy="uniform")
    ax.plot(mean_pred, frac, marker="o", color="#0f766e", lw=2)
    ax.plot([0, 1], [0, 1], ls="--", color="#94a3b8", lw=1)
    ax.set(xlabel="Mean predicted probability", ylabel="Observed positive rate",
           title=f"{name} — calibration (held-out)", xlim=(0, 1), ylim=(0, 1))
    fig.tight_layout(); fig.savefig(out / "calibration_curve.png", dpi=120); plt.close(fig)
    files.append("calibration_curve.png")

    fig, ax = plt.subplots(figsize=(3.6, 3.2))
    m = np.array([[cm["tn"], cm["fp"]], [cm["fn"], cm["tp"]]])
    ax.imshow(m, cmap="Greens")
    for (i, j), v in np.ndenumerate(m):
        ax.text(j, i, str(v), ha="center", va="center", fontsize=13)
    ax.set(xticks=[0, 1], yticks=[0, 1], xticklabels=["Pred neg", "Pred pos"],
           yticklabels=["Actual neg", "Actual pos"], title=f"{name} — confusion matrix")
    fig.tight_layout(); fig.savefig(out / "confusion_matrix.png", dpi=120); plt.close(fig)
    files.append("confusion_matrix.png")
    return files


def train_disease(disease: str, artifact_dir: Path = ARTIFACT_DIR, raw_dir: Path | None = None,
                  cv_repeats: int = 3, verbose: bool = True) -> dict:
    log = print if verbose else (lambda *a, **k: None)
    log(f"\n=== {DISEASES[disease]['name']} ===")
    X, y = load(disease, raw_dir)
    n_raw = len(X)

    data = X.assign(__y=y.values)
    keep = ~data.duplicated()
    X, y = X[keep].reset_index(drop=True), y[keep].reset_index(drop=True)
    log(f"rows: {n_raw} raw, {len(X)} after removing {n_raw - len(X)} exact duplicates")

    integ = integrity.run_checks(X, y)
    for f in integ["flags"]:
        log(f"  INTEGRITY FLAG: {f}")

    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=TEST_SIZE, stratify=y, random_state=SEED)
    prevalence = float(y_tr.mean())

    cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=cv_repeats, random_state=SEED)
    cv_results = {}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for key, make in CANDIDATES.items():
            res = cross_validate(build_pipeline(disease, make()), X_tr, y_tr, cv=cv,
                                 scoring=["roc_auc", "accuracy", "f1", "recall", "precision"])
            cv_results[key] = {m: {"mean": float(np.mean(res[f"test_{m}"])), "std": float(np.std(res[f"test_{m}"]))}
                               for m in ["roc_auc", "accuracy", "f1", "recall", "precision"]}
            log(f"  CV {PRETTY[key]:<32} AUC {cv_results[key]['roc_auc']['mean']:.3f} ± {cv_results[key]['roc_auc']['std']:.3f}")

    best_auc = max(r["roc_auc"]["mean"] for r in cv_results.values())
    selected = next(k for k in CANDIDATES if cv_results[k]["roc_auc"]["mean"] >= best_auc - SIMPLICITY_TOLERANCE)
    log(f"  selected: {PRETTY[selected]} (best CV AUC {best_auc:.3f})")

    # Informational: every candidate refit on train, scored on test (NOT used for selection).
    test_all = {}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for key, make in CANDIDATES.items():
            m = build_pipeline(disease, make()).fit(X_tr, y_tr)
            s = _scores(m, X_te)
            pred = m.predict(X_te)
            from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
            test_all[key] = {"roc_auc": float(roc_auc_score(y_te, s)), "accuracy": float(accuracy_score(y_te, pred)),
                             "precision": float(precision_score(y_te, pred, zero_division=0)),
                             "recall": float(recall_score(y_te, pred, zero_division=0)),
                             "f1": float(f1_score(y_te, pred, zero_division=0))}

    final = CalibratedClassifierCV(build_pipeline(disease, CANDIDATES[selected]()), method="sigmoid", cv=5)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        final.fit(X_tr, y_tr)
    p_te = final.predict_proba(X_te)[:, 1]
    test = classification_metrics(y_te, p_te, prevalence)
    test["roc_auc_95ci"] = bootstrap_auc_ci(y_te, p_te)
    test["calibration_table"] = calibration_table(y_te, p_te)
    log(f"  held-out: AUC {test['roc_auc']:.3f} acc {test['accuracy']:.3f} F1 {test['f1']:.3f} "
        f"Brier {test['brier']:.3f} BSS {test['brier_skill_score']:.3f} ECE {test['ece']:.3f}")

    # ---- Eligibility ----
    reasons = []
    cv_auc = cv_results[selected]["roc_auc"]["mean"]
    if test["roc_auc"] >= integrity.PERFECT_SEPARATION_FLAG:
        integ["flags"].append(f"Held-out ROC-AUC {test['roc_auc']:.3f} indicates near-perfect separation")
    if min(cv_auc, test["roc_auc"]) < MIN_AUC_EXPERIMENTAL:
        status = "unavailable"; reasons.append("Discrimination below the minimum threshold")
    elif min(cv_auc, test["roc_auc"]) < MIN_AUC_AVAILABLE:
        status = "experimental"; reasons.append(f"ROC-AUC below {MIN_AUC_AVAILABLE}")
    else:
        status = "available"

    prob_ok = status == "available" and test["brier_skill_score"] > 0 and test["ece"] <= MAX_ECE_FOR_PROBABILITY
    if status != "available":
        prob_reason = "Probability output is withheld because the module is not fully available: " + "; ".join(reasons)
    elif not prob_ok:
        prob_reason = (f"Calibration criteria not met (ECE {test['ece']:.3f} > {MAX_ECE_FOR_PROBABILITY} "
                       f"or Brier skill score {test['brier_skill_score']:.3f} <= 0)")
    else:
        prob_reason = (f"Sigmoid-calibrated probabilities met the criteria on held-out data "
                       f"(ECE {test['ece']:.3f} <= {MAX_ECE_FOR_PROBABILITY}, Brier skill score {test['brier_skill_score']:.3f} > 0)")
    log(f"  status: {status}; probability supported: {prob_ok}")

    out = artifact_dir / disease
    out.mkdir(parents=True, exist_ok=True)
    joblib.dump(final, out / "model.joblib")
    plots = _plots(disease, out, y_te, p_te, test["confusion_matrix"])

    raw_path = (raw_dir or RAW_DIR) / DATASET_FILES[disease]
    meta = {
        "disease": disease,
        "name": DISEASES[disease]["name"],
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": status,
        "status_reasons": reasons,
        # Integrity findings are reported as data caveats. They are shown on the
        # Model performance page and in the docs but do not change the status.
        "data_caveats": list(integ["flags"]),
        "probability_supported": bool(prob_ok),
        "probability_reason": prob_reason,
        "features": feature_names(disease),
        # Verified by the API before unpickling, so a corrupted or swapped
        # artifact is refused instead of being loaded.
        "model_sha256": _sha256(out / "model.joblib"),
        "algorithm": selected,
        "algorithm_name": PRETTY[selected],
        "calibration": "sigmoid (Platt) via CalibratedClassifierCV, cv=5, fit on training split only",
        "decision_threshold": 0.5,
        "dataset": {
            "description": DISEASES[disease]["dataset"],
            "file": DATASET_FILES[disease],
            "sha256": _sha256(raw_path),
            "rows_raw": int(n_raw),
            "rows_used": int(len(X)),
            "train_rows": int(len(X_tr)),
            "test_rows": int(len(X_te)),
            "train_prevalence": prevalence,
        },
        "integrity": integ,
        "cv": {"scheme": f"RepeatedStratifiedKFold(5 folds x {cv_repeats} repeats), training split only",
               "results": cv_results},
        "selection_rule": f"highest mean CV ROC-AUC; simplest model within {SIMPLICITY_TOLERANCE} preferred",
        "test_metrics": test,
        "test_all_candidates_informational": test_all,
        "eligibility_rules": {
            "min_auc_available": MIN_AUC_AVAILABLE,
            "min_auc_experimental": MIN_AUC_EXPERIMENTAL,
            "max_ece_for_probability": MAX_ECE_FOR_PROBABILITY,
            "single_feature_auc_flag": integrity.SINGLE_FEATURE_AUC_FLAG,
            "missingness_auc_flag": integrity.MISSINGNESS_AUC_FLAG,
            "perfect_separation_flag": integrity.PERFECT_SEPARATION_FLAG,
        },
        "plots": plots,
        "environment": {
            "python": platform.python_version(),
            "scikit_learn": sklearn.__version__,
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "joblib": joblib.__version__,
        },
    }
    (out / "metadata.json").write_text(json.dumps(meta, indent=2))
    return meta


def write_report(metas: list[dict], path: Path) -> None:
    lines = ["# Model Evaluation Report", "",
             "Generated automatically by `python -m ml.training.train`. All figures are real outputs of the "
             "training run on the stated public datasets. They are **not** evidence of clinical validity.", ""]
    lines += ["| Module | Status | Algorithm | Test n | ROC-AUC (95% CI) | Accuracy | Precision | Recall | F1 | Brier | ECE | Probability shown |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for m in metas:
        t = m["test_metrics"]
        lo, hi = t["roc_auc_95ci"]
        lines.append(f"| {m['name']} | {m['status']} | {m['algorithm_name']} | {t['n']} | {t['roc_auc']:.3f} ({lo:.3f}–{hi:.3f}) | "
                     f"{t['accuracy']:.3f} | {t['precision']:.3f} | {t['recall']:.3f} | {t['f1']:.3f} | {t['brier']:.3f} | "
                     f"{t['ece']:.3f} | {'yes' if m['probability_supported'] else 'no'} |")
    for m in metas:
        t = m["test_metrics"]; cm = t["confusion_matrix"]
        lines += ["", f"## {m['name']}", "",
                  f"- Dataset: {m['dataset']['description']} — {m['dataset']['rows_raw']} rows, "
                  f"{m['dataset']['rows_used']} after de-duplication; train {m['dataset']['train_rows']} / test {m['dataset']['test_rows']}",
                  f"- Status: **{m['status']}**" + (f" — {'; '.join(m['status_reasons'])}" if m["status_reasons"] else ""),
                  f"- Probability: {m['probability_reason']}",
                  f"- Selected model: {m['algorithm_name']} + sigmoid calibration",
                  f"- Held-out confusion matrix: TN {cm['tn']}, FP {cm['fp']}, FN {cm['fn']}, TP {cm['tp']}; specificity {t['specificity']:.3f}; "
                  f"Brier skill score {t['brier_skill_score']:.3f}; majority-class baseline accuracy {t['majority_baseline_accuracy']:.3f}",
                  "", "Cross-validation on the training split (mean ± sd):", "",
                  "| Algorithm | ROC-AUC | Accuracy | F1 | Recall | Precision |", "|---|---|---|---|---|---|"]
        for k, r in m["cv"]["results"].items():
            mark = " **(selected)**" if k == m["algorithm"] else ""
            lines.append(f"| {PRETTY[k]}{mark} | {r['roc_auc']['mean']:.3f} ± {r['roc_auc']['std']:.3f} | "
                         f"{r['accuracy']['mean']:.3f} | {r['f1']['mean']:.3f} | {r['recall']['mean']:.3f} | {r['precision']['mean']:.3f} |")
        lines += ["", "Held-out test scores of every candidate (informational only — not used for selection):", "",
                  "| Algorithm | ROC-AUC | Accuracy | Precision | Recall | F1 |", "|---|---|---|---|---|---|"]
        for k, r in m["test_all_candidates_informational"].items():
            lines.append(f"| {PRETTY[k]} | {r['roc_auc']:.3f} | {r['accuracy']:.3f} | {r['precision']:.3f} | {r['recall']:.3f} | {r['f1']:.3f} |")
        integ = m["integrity"]
        lines += ["", f"Integrity checks: exact duplicates {integ['exact_duplicate_rows']} (removed before split), "
                      f"conflicting-label duplicates {integ['conflicting_label_duplicates']}, "
                      f"missingness AUC {integ.get('missingness_auc', 'n/a')}, strongest single-feature AUC "
                      f"{next(iter(integ['single_feature_auc'].items()))}."]
        if integ["flags"]:
            lines += ["", "Data caveats (integrity findings, reported but not used to downgrade the module):"] + [f"- {f}" for f in integ["flags"]]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


def main(argv: list[str]) -> int:
    diseases = argv or list(DISEASE_KEYS)
    bad = [d for d in diseases if d not in DISEASE_KEYS]
    if bad:
        print(f"Unknown disease(s): {bad}. Choose from {DISEASE_KEYS}")
        return 2
    metas = [train_disease(d) for d in diseases]
    if set(diseases) == set(DISEASE_KEYS):
        write_report(metas, REPORTS_DIR / "model_evaluation.md")
        print(f"\nReport written to {REPORTS_DIR / 'model_evaluation.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
