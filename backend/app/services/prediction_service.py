"""Runs inference for a validated feature payload and builds the
standardized result object shared by all four disease modules."""

from __future__ import annotations

import numpy as np
import pandas as pd
from flask import current_app

from app.services.model_registry import get_registry
from app.services.risk import bands_from_config
from app.utils.responses import ApiError
from ml.feature_specs import DISEASES, feature_names

DISCLAIMER = (
    "Health-Link is an educational prototype only. Its predictions are not clinically validated and must not "
    "be used for diagnosis, treatment decisions, or emergencies. Consult a qualified healthcare professional "
    "for medical concerns."
)


def _labels(disease: str) -> dict[str, str]:
    return {f["name"]: f["label"] for f in DISEASES[disease]["features"]}


def _factors(model, X: pd.DataFrame, disease: str, skip: set[str]) -> list[dict] | None:
    """Approximate per-feature contributions for linear models: the change in
    log-odds attributable to each input relative to an average training
    patient, averaged over the calibration folds. Not causal; not shown for
    non-linear models."""
    totals: dict[str, float] = {}
    folds = getattr(model, "calibrated_classifiers_", [])
    for cc in folds:
        pipe = cc.estimator
        est = pipe.named_steps.get("model")
        if not hasattr(est, "coef_"):
            return None
        pre = pipe.named_steps["preprocess"]
        names = pre.get_feature_names_out()
        x = np.asarray(pre.transform(X))[0]
        coef = est.coef_[0]
        contrib = coef * x
        # One-hot groups: centre each group's coefficients so a category's
        # contribution is relative to the average category, not to zero.
        for orig in set(n.split("_")[0] for n in names if "_" in n and n.split("_")[0] in X.columns and n not in X.columns):
            idx = [i for i, n in enumerate(names) if n.startswith(orig + "_")]
            group = coef[idx]
            for i in idx:
                contrib[i] = (coef[i] - group.mean()) * x[i]
        for n, c in zip(names, contrib):
            orig = n if n in X.columns else n.rsplit("_", 1)[0]
            totals[orig] = totals.get(orig, 0.0) + float(c) / len(folds)
    if not totals:
        return None
    labels = _labels(disease)
    ranked = sorted(((k, v) for k, v in totals.items() if k not in skip and abs(v) > 0.05), key=lambda kv: -abs(kv[1]))
    return [{"feature": k, "label": labels.get(k, k), "direction": "increases" if v > 0 else "decreases",
             "weight": round(abs(v), 3)} for k, v in ranked[:5]]


def run_prediction(disease: str, clean: dict, not_provided: list[str]) -> dict:
    entry = get_registry().get(disease)
    if entry is None or not entry.usable:
        reason = entry.reason if entry else "Unknown module."
        raise ApiError("model_unavailable", f"The {DISEASES[disease]['name']} model is currently unavailable. {reason}", 503)

    spec = DISEASES[disease]
    row = {name: (np.nan if clean.get(name) is None else float(clean[name])) for name in feature_names(disease)}
    X = pd.DataFrame([row], columns=feature_names(disease))

    try:
        prob = float(entry.model.predict_proba(X)[0, 1])
    except Exception as exc:
        current_app.logger.exception("Inference failed for %s", disease)
        raise ApiError("inference_failed", "The model could not process this input.", 500) from exc
    if not np.isfinite(prob):
        raise ApiError("inference_failed", "The model returned an invalid output.", 500)

    threshold = float(entry.metadata.get("decision_threshold", 0.5))
    predicted_class = int(prob >= threshold)
    predicted_label = spec["positive_label"] if predicted_class else spec["negative_label"]

    bands = bands_from_config(current_app.config)
    labels = _labels(disease)
    result = {
        "disease": disease,
        "disease_name": spec["name"],
        "predicted_class": predicted_class,
        "predicted_label": predicted_label,
        "model_status": entry.status,
        "model_algorithm": entry.metadata.get("algorithm_name"),
        "model_version": entry.metadata.get("trained_at"),
        "not_provided": [{"feature": n, "label": labels[n]} for n in not_provided],
        "disclaimer": DISCLAIMER,
    }

    if entry.probability_supported:
        risk = bands.classify(prob)
        result.update({
            "probability": round(prob, 4),
            "risk_category": risk,
            "risk_bands": bands.describe(),
            "explanation": (
                f"The {entry.metadata.get('algorithm_name')} model, after probability calibration, estimated a "
                f"{prob * 100:.1f}% probability that this profile resembles patients with "
                f"{spec['name'].lower()} in its training data. Health-Link places estimates in the "
                f"application-defined {risk} band ({next(b['range'] for b in bands.describe() if b['category'] == risk)}). "
                "These bands are educational and are not clinical thresholds."
            ),
        })
    else:
        result.update({
            "probability": None,
            "risk_category": None,
            "risk_unavailable_reason": entry.metadata.get("probability_reason"),
            "explanation": (
                "This module reports the model's predicted class only. A probability and a LOW/MODERATE/HIGH band "
                "are not shown, because the module did not meet Health-Link's criteria for trustworthy probabilities."
            ),
        })

    if entry.status == "experimental":
        result["experimental_notice"] = (
            "This module is EXPERIMENTAL. Integrity checks on its training data found problems that make its "
            "accuracy figures untrustworthy: " + "; ".join(entry.metadata.get("status_reasons", []))
        )

    if not_provided:
        result["imputation_notice"] = (
            "You marked these optional values as not available: "
            + ", ".join(labels[n] for n in not_provided)
            + ". The model substituted the median value from its training data for them, which makes this "
              "estimate less reliable."
        )

    result["factors"] = _factors(entry.model, X, disease, set(not_provided)) if entry.status == "available" else None
    return result
