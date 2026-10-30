"""Server-side validation of disease feature payloads, driven by
``ml.feature_specs`` so it always matches the trained model's schema."""

from __future__ import annotations

import math

from ml.feature_specs import DISEASES
from app.utils.responses import ApiError


def _to_number(value):
    if isinstance(value, bool) or value is None:
        raise ValueError
    if isinstance(value, str):
        value = value.strip()
        if not value:
            raise ValueError
    num = float(value)
    if math.isnan(num) or math.isinf(num):
        raise ValueError
    return num


def check_field(f: dict, raw) -> tuple[float | int | None, str | None]:
    """Validate a single non-empty value against its field spec."""
    try:
        num = _to_number(raw)
    except (TypeError, ValueError):
        return None, "Must be a number."
    if f["type"] == "select":
        allowed = [o["value"] for o in f["options"]]
        match = next((a for a in allowed if math.isclose(float(a), num, abs_tol=1e-9)), None)
        if match is None:
            return None, "Choose one of the listed options."
        return match, None
    if f["type"] == "integer" and not float(num).is_integer():
        return None, "Must be a whole number."
    if num < f["min"] or num > f["max"]:
        unit = f" {f['unit']}" if f.get("unit") else ""
        return None, f"Must be between {f['min']} and {f['max']}{unit}."
    return (int(num) if f["type"] == "integer" else num), None


def validate_features(disease: str, features) -> tuple[dict, list[str]]:
    """Return (clean_values, not_provided_optional_fields).

    * Unknown fields are rejected.
    * Required fields must be present and valid.
    * Optional fields may be null/absent; they are reported back so the
      result can disclose that the model substituted a training-set value.
    """
    if disease not in DISEASES:
        raise ApiError("unknown_disease", f"Unknown disease module '{disease}'.", 404)
    if not isinstance(features, dict):
        raise ApiError("validation_error", "'features' must be an object of field values.", 400)

    spec = DISEASES[disease]["features"]
    known = {f["name"] for f in spec}
    errors: dict[str, str] = {}
    for key in features:
        if key not in known:
            errors[key] = "Unknown field."

    clean: dict[str, float | int | None] = {}
    not_provided: list[str] = []
    for f in spec:
        name = f["name"]
        raw = features.get(name)
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            if f.get("required", True):
                errors[name] = "This field is required."
            else:
                clean[name] = None
                not_provided.append(name)
            continue
        value, err = check_field(f, raw)
        if err:
            errors[name] = err
        else:
            clean[name] = value

    if errors:
        raise ApiError("validation_error", "Some values are missing or invalid.", 400, errors)
    return clean, not_provided
