"""Dataset loaders: read each raw public dataset and return a clean feature
frame ``X`` (columns named as in ``ml.feature_specs``) and a binary target ``y``
(1 = disease indicated).

Only *deterministic, row-local* cleaning happens here (renaming, decoding the
raw text encodings, turning documented "missing" sentinels into NaN). Anything
that learns from data — imputation, scaling, encoding — lives inside the
scikit-learn Pipeline so it is fit on training folds only.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from ml.feature_specs import feature_names

RAW_DIR = Path(__file__).resolve().parents[1] / "datasets" / "raw"

DATASET_FILES = {
    "heart": "heart_cleveland.csv",
    "diabetes": "pima_diabetes.csv",
    "kidney": "kidney_disease.csv",
    "liver": "ilpd.csv",
}


class DatasetMissingError(FileNotFoundError):
    pass


def _path(disease: str, raw_dir: Path | None = None) -> Path:
    p = (raw_dir or RAW_DIR) / DATASET_FILES[disease]
    if not p.exists():
        raise DatasetMissingError(
            f"Dataset file not found: {p}. See backend/ml/datasets/SOURCES.md for how to obtain it."
        )
    return p


def load_heart(raw_dir: Path | None = None) -> tuple[pd.DataFrame, pd.Series]:
    df = pd.read_csv(_path("heart", raw_dir))
    # UCI 'num' is 0 (no disease) .. 4; the standard binary task is num > 0.
    y = (df["num"] > 0).astype(int)
    X = df[feature_names("heart")].astype(float)
    return X, y


def load_diabetes(raw_dir: Path | None = None) -> tuple[pd.DataFrame, pd.Series]:
    cols = ["pregnancies", "glucose", "blood_pressure", "skin_thickness", "insulin", "bmi", "dpf", "age", "outcome"]
    df = pd.read_csv(_path("diabetes", raw_dir), header=None, names=cols)
    # In this dataset a value of 0 is physiologically impossible for these
    # columns and is documented as a missing-value code.
    for c in ["glucose", "blood_pressure", "skin_thickness", "insulin", "bmi"]:
        df[c] = df[c].replace(0, np.nan)
    y = df["outcome"].astype(int)
    X = df[feature_names("diabetes")].astype(float)
    return X, y


_KIDNEY_BINARY = {
    "rbc": {"normal": 0, "abnormal": 1},
    "pc": {"normal": 0, "abnormal": 1},
    "pcc": {"notpresent": 0, "present": 1},
    "ba": {"notpresent": 0, "present": 1},
    "htn": {"no": 0, "yes": 1},
    "dm": {"no": 0, "yes": 1},
    "cad": {"no": 0, "yes": 1},
    "appet": {"good": 0, "poor": 1},
    "pe": {"no": 0, "yes": 1},
    "ane": {"no": 0, "yes": 1},
}


def load_kidney(raw_dir: Path | None = None) -> tuple[pd.DataFrame, pd.Series]:
    df = pd.read_csv(_path("kidney", raw_dir), dtype=str)
    df = df.drop(columns=["id"], errors="ignore")
    # The UCI file contains stray tabs/spaces ("\tyes", "ckd\t") and "?" markers.
    df = df.apply(lambda s: s.str.strip().str.replace("\t", "", regex=False))
    df = df.replace({"?": np.nan, "": np.nan})
    y = df["classification" if "classification" in df.columns else "class"].map({"ckd": 1, "notckd": 0})
    if y.isna().any():
        raise ValueError("Unexpected kidney target labels")
    for col, mapping in _KIDNEY_BINARY.items():
        bad = set(df[col].dropna().unique()) - set(mapping)
        if bad:
            raise ValueError(f"Unexpected values in kidney column {col}: {bad}")
        df[col] = df[col].map(mapping)
    X = df[feature_names("kidney")].apply(pd.to_numeric, errors="raise").astype(float)
    # Physiologically impossible entries in the raw file (e.g. sodium 4.5 mEq/L,
    # potassium 39-47 mEq/L) are recording errors; treat them as missing.
    X.loc[X["sod"] < 100, "sod"] = np.nan
    X.loc[X["pot"] > 10, "pot"] = np.nan
    return X, y.astype(int)


def load_liver(raw_dir: Path | None = None) -> tuple[pd.DataFrame, pd.Series]:
    cols = ["age", "gender", "total_bilirubin", "direct_bilirubin", "alkaline_phosphatase", "alt", "ast",
            "total_proteins", "albumin", "ag_ratio", "selector"]
    df = pd.read_csv(_path("liver", raw_dir), header=None, names=cols)
    df["gender"] = df["gender"].map({"Female": 0, "Male": 1})
    # ILPD selector: 1 = liver patient, 2 = non liver patient.
    y = df["selector"].map({1: 1, 2: 0})
    if y.isna().any() or df["gender"].isna().any():
        raise ValueError("Unexpected liver labels or gender values")
    X = df[feature_names("liver")].astype(float)
    return X, y.astype(int)


LOADERS = {"heart": load_heart, "diabetes": load_diabetes, "kidney": load_kidney, "liver": load_liver}


def load(disease: str, raw_dir: Path | None = None) -> tuple[pd.DataFrame, pd.Series]:
    return LOADERS[disease](raw_dir)
