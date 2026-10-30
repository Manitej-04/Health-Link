"""Loads trained model artifacts once at startup and reports per-module
availability. A module whose artifact is missing, corrupt, tampered with or
built by an incompatible scikit-learn version is marked *unavailable* with a
reason — the API never fabricates a prediction for it."""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

import joblib
import sklearn

from ml.feature_specs import DISEASES, DISEASE_KEYS, feature_names

log = logging.getLogger("healthlink")


@dataclass
class ModelEntry:
    disease: str
    status: str                      # available | experimental | unavailable
    reason: str = ""
    model: object = None
    metadata: dict = field(default_factory=dict)

    @property
    def usable(self) -> bool:
        return self.model is not None and self.status in ("available", "experimental")

    @property
    def probability_supported(self) -> bool:
        return self.usable and bool(self.metadata.get("probability_supported"))

    def public_info(self) -> dict:
        spec = DISEASES[self.disease]
        md = self.metadata or {}
        t = md.get("test_metrics", {})
        info = {
            "key": self.disease,
            "name": spec["name"],
            "short": spec["short"],
            "dataset": spec["dataset"],
            "population_note": spec.get("population_note"),
            "status": self.status,
            "status_reasons": md.get("status_reasons", []) if self.status != "unavailable" else [self.reason],
            "data_caveats": md.get("data_caveats", []),
            "probability_supported": self.probability_supported,
            "probability_reason": md.get("probability_reason") if self.usable else self.reason,
            "algorithm": md.get("algorithm_name"),
            "trained_at": md.get("trained_at"),
            "features": spec["features"],
        }
        if t:
            info["metrics"] = {k: t.get(k) for k in ("n", "roc_auc", "roc_auc_95ci", "accuracy", "precision",
                                                       "recall", "specificity", "f1", "brier", "ece",
                                                       "majority_baseline_accuracy")}
        return info


class ModelRegistry:
    def __init__(self):
        self.entries: dict[str, ModelEntry] = {}

    def load_all(self, model_dir: Path) -> None:
        self.entries = {d: self._load_one(d, Path(model_dir)) for d in DISEASE_KEYS}
        for d, e in self.entries.items():
            log.info("model %-8s status=%s %s", d, e.status, e.reason)

    def _load_one(self, disease: str, model_dir: Path) -> ModelEntry:
        folder = model_dir / disease
        model_path, meta_path = folder / "model.joblib", folder / "metadata.json"
        if not model_path.exists() or not meta_path.exists():
            return ModelEntry(disease, "unavailable",
                              "Model artifact not found. Train it with: python -m ml.training.train " + disease)
        try:
            meta = json.loads(meta_path.read_text())
        except (OSError, ValueError):
            return ModelEntry(disease, "unavailable", "Model metadata is unreadable. Retrain the model.")

        expected = meta.get("model_sha256")
        actual = hashlib.sha256(model_path.read_bytes()).hexdigest()
        if not expected or expected != actual:
            return ModelEntry(disease, "unavailable",
                              "Model artifact failed its integrity check (checksum mismatch). Retrain the model.", metadata=meta)

        trained_with = meta.get("environment", {}).get("scikit_learn")
        if trained_with != sklearn.__version__:
            return ModelEntry(disease, "unavailable",
                              f"Model was trained with scikit-learn {trained_with} but {sklearn.__version__} is installed. "
                              f"Retrain locally: python -m ml.training.train", metadata=meta)

        if meta.get("features") != feature_names(disease):
            return ModelEntry(disease, "unavailable",
                              "Model feature schema does not match the application schema. Retrain the model.", metadata=meta)

        try:
            model = joblib.load(model_path)
            if not hasattr(model, "predict_proba"):
                raise TypeError("artifact has no predict_proba")
        except Exception:  # corrupt pickle, wrong object type, ...
            log.exception("Failed to load model for %s", disease)
            return ModelEntry(disease, "unavailable", "Model artifact could not be loaded. Retrain the model.", metadata=meta)

        status = meta.get("status", "unavailable")
        if status == "unavailable":
            return ModelEntry(disease, "unavailable", "; ".join(meta.get("status_reasons", [])) or
                              "Model did not meet the minimum evaluation criteria.", metadata=meta)
        return ModelEntry(disease, status, "", model=model, metadata=meta)

    def get(self, disease: str) -> ModelEntry | None:
        return self.entries.get(disease)

    def summary(self) -> list[dict]:
        return [e.public_info() for e in self.entries.values()]


def get_registry() -> ModelRegistry:
    from flask import current_app
    return current_app.extensions["model_registry"]
