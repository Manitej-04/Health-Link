import pytest

from app.services.risk import HIGH, LOW, MODERATE, RiskBands
from app.services.validation import validate_features
from app.utils.responses import ApiError
from tests.conftest import SAMPLES


# ---------- risk classification ----------

@pytest.mark.parametrize("p,expected", [
    (0.0, LOW), (0.2999, LOW), (0.30, MODERATE), (0.5, MODERATE), (0.6999, MODERATE), (0.70, HIGH), (1.0, HIGH),
])
def test_risk_band_boundaries(p, expected):
    assert RiskBands(0.30, 0.70).classify(p) == expected


@pytest.mark.parametrize("p", [-0.01, 1.01, None])
def test_risk_rejects_invalid_probability(p):
    with pytest.raises(ValueError):
        RiskBands().classify(p)


@pytest.mark.parametrize("lo,hi", [(0.7, 0.3), (0.0, 0.5), (0.3, 1.0), (0.5, 0.5)])
def test_risk_rejects_invalid_thresholds(lo, hi):
    with pytest.raises(ValueError):
        RiskBands(lo, hi)


def test_risk_describe_is_documented():
    bands = RiskBands(0.30, 0.70).describe()
    assert [b["category"] for b in bands] == [LOW, MODERATE, HIGH]
    assert bands[0]["range"] == "below 30%"


# ---------- feature validation ----------

@pytest.mark.parametrize("disease", list(SAMPLES))
def test_valid_samples_pass(disease):
    clean, not_provided = validate_features(disease, SAMPLES[disease])
    assert set(clean) == set(SAMPLES[disease])
    assert not_provided == [k for k, v in SAMPLES[disease].items() if v is None]


def _errors(disease, features):
    with pytest.raises(ApiError) as e:
        validate_features(disease, features)
    return e.value.details


def test_required_field_missing():
    f = dict(SAMPLES["heart"]); del f["chol"]
    assert _errors("heart", f) == {"chol": "This field is required."}


def test_required_field_cannot_be_null():
    f = dict(SAMPLES["liver"], albumin=None)
    assert "albumin" in _errors("liver", f)


def test_unknown_field_rejected():
    f = dict(SAMPLES["heart"], favourite_colour=3)
    assert _errors("heart", f) == {"favourite_colour": "Unknown field."}


@pytest.mark.parametrize("value,msg", [(5, "between"), (700, "between"), ("abc", "number"),
                                       (True, "number"), (float("nan"), "number"), ("1e309", "number")])
def test_numeric_errors(value, msg):
    f = dict(SAMPLES["heart"], trestbps=value)
    assert msg in _errors("heart", f)["trestbps"]


def test_integer_field_rejects_fraction():
    f = dict(SAMPLES["heart"], age=45.5)
    assert "whole number" in _errors("heart", f)["age"]


def test_select_rejects_unlisted_option():
    f = dict(SAMPLES["heart"], cp=9)
    assert "options" in _errors("heart", f)["cp"]


def test_numeric_strings_accepted():
    f = {k: (str(v) if v is not None else None) for k, v in SAMPLES["kidney"].items()}
    clean, _ = validate_features("kidney", f)
    assert clean["sg"] == 1.02 and clean["hemo"] == 15.4


def test_features_must_be_object():
    with pytest.raises(ApiError):
        validate_features("heart", [1, 2, 3])
