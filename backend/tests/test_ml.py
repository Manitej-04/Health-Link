import numpy as np
import pandas as pd
import pytest

from ml.evaluation.integrity import run_checks
from ml.evaluation.metrics import classification_metrics, expected_calibration_error
from ml.feature_specs import DISEASES, feature_names
from ml.preprocessing.loaders import DatasetMissingError, load
from ml.preprocessing.pipeline import build_pipeline

# Published dataset statistics used to verify the files are the genuine datasets.
EXPECTED = {
    "heart": (303, 139),     # Cleveland: 139 with num > 0
    "diabetes": (768, 268),
    "kidney": (400, 250),
    "liver": (583, 416),
}


@pytest.mark.parametrize("disease", list(EXPECTED))
def test_dataset_matches_published_statistics(disease):
    X, y = load(disease)
    rows, positives = EXPECTED[disease]
    assert len(X) == rows and int(y.sum()) == positives
    assert list(X.columns) == feature_names(disease)
    assert set(y.unique()) == {0, 1}


def test_missing_dataset_gives_clear_error(tmp_path):
    with pytest.raises(DatasetMissingError, match="SOURCES.md"):
        load("heart", tmp_path)


def test_diabetes_zero_codes_become_missing():
    X, _ = load("diabetes")
    assert (X[["glucose", "blood_pressure", "skin_thickness", "insulin", "bmi"]] == 0).sum().sum() == 0
    assert X["insulin"].isna().sum() == 374


def test_kidney_text_cleaning():
    X, y = load("kidney")
    for col in ["htn", "dm", "cad"]:
        assert set(X[col].dropna().unique()) <= {0, 1}
    assert X["sod"].min() >= 100 and X["pot"].max() <= 10


def test_integrity_flags_kidney_and_not_heart():
    Xk, yk = load("kidney")
    flags = run_checks(Xk, yk)["flags"]
    assert any("missing values" in f for f in flags) and any("Single raw features" in f for f in flags)
    Xh, yh = load("heart")
    assert run_checks(Xh, yh)["flags"] == []


def test_integrity_detects_label_leak():
    rng = np.random.default_rng(0)
    y = pd.Series(rng.integers(0, 2, 200))
    X = pd.DataFrame({"noise": rng.normal(size=200), "leak": y * 10 + rng.normal(scale=0.1, size=200)})
    assert any("leak" in f for f in run_checks(X, y)["flags"])


def test_pipeline_learns_only_from_training_rows():
    X, y = load("heart")
    pipe = build_pipeline("heart", __import__("sklearn.linear_model", fromlist=["x"]).LogisticRegression(max_iter=500))
    pipe.fit(X.iloc[:200], y.iloc[:200])
    scaler = pipe.named_steps["preprocess"].named_transformers_["num"].named_steps["scale"]
    num_cols = pipe.named_steps["preprocess"].transformers_[0][2]
    assert np.allclose(scaler.mean_, X.iloc[:200][num_cols].fillna(X.iloc[:200][num_cols].median()).mean().values)


def test_ece_perfect_and_bad_calibration():
    y = np.array([0, 0, 1, 1] * 50)
    assert expected_calibration_error(y, np.where(y == 1, 1.0, 0.0)) == pytest.approx(0.0)
    assert expected_calibration_error(y, np.full(len(y), 0.9)) == pytest.approx(0.4)


def test_classification_metrics_confusion():
    m = classification_metrics([0, 0, 1, 1], [0.1, 0.6, 0.4, 0.9], 0.5)
    assert m["confusion_matrix"] == {"tn": 1, "fp": 1, "fn": 1, "tp": 1}
    assert m["accuracy"] == 0.5 and m["majority_baseline_accuracy"] == 0.5


def test_artifact_metadata_records_real_evaluation():
    import json
    from pathlib import Path
    base = Path(__file__).resolve().parents[1] / "ml" / "artifacts"
    for d in DISEASES:
        meta = json.loads((base / d / "metadata.json").read_text())
        t = meta["test_metrics"]
        cm = t["confusion_matrix"]
        assert cm["tn"] + cm["fp"] + cm["fn"] + cm["tp"] == t["n"] == meta["dataset"]["test_rows"]
        assert 0.5 <= t["roc_auc"] <= 1.0
        assert meta["status"] in ("available", "experimental", "unavailable")
