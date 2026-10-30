"""Shared risk-classification service.

Maps a *calibrated* model probability to an application-defined educational
band. The cut-offs are configuration (RISK_LOW_MAX, RISK_MODERATE_MAX), not
clinical thresholds, and are only applied when the model's probabilities
passed the calibration criteria at training time.
"""

from __future__ import annotations

from dataclasses import dataclass

LOW, MODERATE, HIGH = "LOW", "MODERATE", "HIGH"


@dataclass(frozen=True)
class RiskBands:
    low_max: float = 0.30
    moderate_max: float = 0.70

    def __post_init__(self):
        if not (0.0 < self.low_max < self.moderate_max < 1.0):
            raise ValueError("Risk thresholds must satisfy 0 < low_max < moderate_max < 1")

    def classify(self, probability: float) -> str:
        if probability is None:
            raise ValueError("A probability is required for risk classification")
        if not 0.0 <= probability <= 1.0:
            raise ValueError("Probability must be between 0 and 1")
        if probability < self.low_max:
            return LOW
        if probability < self.moderate_max:
            return MODERATE
        return HIGH

    def describe(self) -> list[dict]:
        lo, mid = round(self.low_max * 100), round(self.moderate_max * 100)
        return [
            {"category": LOW, "range": f"below {lo}%", "min": 0.0, "max": self.low_max},
            {"category": MODERATE, "range": f"{lo}% to below {mid}%", "min": self.low_max, "max": self.moderate_max},
            {"category": HIGH, "range": f"{mid}% and above", "min": self.moderate_max, "max": 1.0},
        ]


def bands_from_config(config) -> RiskBands:
    return RiskBands(config["RISK_LOW_MAX"], config["RISK_MODERATE_MAX"])
