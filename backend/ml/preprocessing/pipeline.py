"""Leak-free preprocessing: every learned step lives inside the sklearn
Pipeline, so cross-validation and the final fit only ever learn imputation
values, scaling statistics and one-hot categories from training rows."""

from __future__ import annotations

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from ml.feature_specs import feature_names

# Nominal (unordered, multi-level) categorical columns are one-hot encoded.
# Binary flags and ordinal codes (e.g. urine albumin 0-5) stay numeric.
NOMINAL = {
    "heart": ["cp", "restecg", "slope", "thal"],
    "diabetes": [],
    "kidney": [],
    "liver": [],
}


def build_preprocessor(disease: str) -> ColumnTransformer:
    nominal = NOMINAL[disease]
    numeric = [c for c in feature_names(disease) if c not in nominal]
    transformers = [
        ("num", Pipeline([
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
        ]), numeric),
    ]
    if nominal:
        transformers.append(("cat", Pipeline([
            ("impute", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]), nominal))
    return ColumnTransformer(transformers, remainder="drop", verbose_feature_names_out=False)


def build_pipeline(disease: str, estimator) -> Pipeline:
    return Pipeline([("preprocess", build_preprocessor(disease)), ("model", estimator)])
