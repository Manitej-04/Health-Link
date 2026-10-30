"""Single source of truth for every disease module's input schema.

The training pipeline, the API validator and the frontend forms (served via
``GET /api/models``) all read from these definitions, so the form a user fills
in always matches the feature columns the model was trained on.

Field keys
----------
name       column name used by the model
label      human-readable label
type       "number" | "integer" | "select"
unit       display unit (optional)
min/max    accepted range for numeric inputs (inclusive). These are plausibility
           bounds for input validation, NOT clinical reference ranges.
options    list of {"value", "label"} for select fields
required   if False the user may explicitly mark the value as "not available";
           only allowed for fields that were heavily missing in the training data
           and are therefore handled by the pipeline's imputer. Every such
           substitution is disclosed in the prediction result.
help       short helper text shown under the field
"""

from __future__ import annotations

YES_NO = [{"value": 0, "label": "No"}, {"value": 1, "label": "Yes"}]

DISEASES: dict[str, dict] = {
    "heart": {
        "key": "heart",
        "name": "Heart Disease",
        "short": "Heart",
        "dataset": "UCI Heart Disease (Cleveland subset, 303 patients)",
        "positive_label": "Heart disease indicated",
        "negative_label": "No heart disease indicated",
        "features": [
            {"name": "age", "label": "Age", "type": "integer", "unit": "years", "min": 18, "max": 100, "required": True},
            {"name": "sex", "label": "Sex", "type": "select", "required": True,
             "options": [{"value": 0, "label": "Female"}, {"value": 1, "label": "Male"}]},
            {"name": "cp", "label": "Chest pain type", "type": "select", "required": True,
             "options": [
                 {"value": 1, "label": "Typical angina"},
                 {"value": 2, "label": "Atypical angina"},
                 {"value": 3, "label": "Non-anginal pain"},
                 {"value": 4, "label": "Asymptomatic"},
             ]},
            {"name": "trestbps", "label": "Resting blood pressure", "type": "number", "unit": "mm Hg",
             "min": 60, "max": 250, "required": True, "help": "Systolic pressure measured at rest"},
            {"name": "chol", "label": "Serum cholesterol", "type": "number", "unit": "mg/dL",
             "min": 80, "max": 700, "required": True},
            {"name": "fbs", "label": "Fasting blood sugar > 120 mg/dL", "type": "select", "required": True,
             "options": YES_NO},
            {"name": "restecg", "label": "Resting ECG result", "type": "select", "required": True,
             "options": [
                 {"value": 0, "label": "Normal"},
                 {"value": 1, "label": "ST-T wave abnormality"},
                 {"value": 2, "label": "Left ventricular hypertrophy"},
             ]},
            {"name": "thalach", "label": "Maximum heart rate achieved", "type": "number", "unit": "bpm",
             "min": 50, "max": 250, "required": True, "help": "Measured during an exercise stress test"},
            {"name": "exang", "label": "Exercise-induced angina", "type": "select", "required": True,
             "options": YES_NO},
            {"name": "oldpeak", "label": "ST depression (exercise vs rest)", "type": "number", "unit": "mm",
             "min": 0, "max": 10, "required": True},
            {"name": "slope", "label": "Slope of peak exercise ST segment", "type": "select", "required": True,
             "options": [
                 {"value": 1, "label": "Upsloping"},
                 {"value": 2, "label": "Flat"},
                 {"value": 3, "label": "Downsloping"},
             ]},
            {"name": "ca", "label": "Major vessels coloured by fluoroscopy", "type": "select", "required": True,
             "options": [{"value": i, "label": str(i)} for i in range(4)]},
            {"name": "thal", "label": "Thallium stress test result", "type": "select", "required": True,
             "options": [
                 {"value": 3, "label": "Normal"},
                 {"value": 6, "label": "Fixed defect"},
                 {"value": 7, "label": "Reversible defect"},
             ]},
        ],
    },
    "diabetes": {
        "key": "diabetes",
        "name": "Diabetes",
        "short": "Diabetes",
        "dataset": "Pima Indians Diabetes (768 female patients, age 21+)",
        "positive_label": "Diabetes indicated",
        "negative_label": "No diabetes indicated",
        "population_note": "Training data contains only women of Pima Indian heritage aged 21 or older.",
        "features": [
            {"name": "pregnancies", "label": "Number of pregnancies", "type": "integer", "min": 0, "max": 20, "required": True},
            {"name": "glucose", "label": "Plasma glucose (2-h oral glucose tolerance test)", "type": "number",
             "unit": "mg/dL", "min": 40, "max": 300, "required": True},
            {"name": "blood_pressure", "label": "Diastolic blood pressure", "type": "number", "unit": "mm Hg",
             "min": 30, "max": 140, "required": True},
            {"name": "skin_thickness", "label": "Triceps skin-fold thickness", "type": "number", "unit": "mm",
             "min": 5, "max": 100, "required": False,
             "help": "Optional — missing for ~30% of the training data"},
            {"name": "insulin", "label": "2-hour serum insulin", "type": "number", "unit": "µU/mL",
             "min": 10, "max": 900, "required": False,
             "help": "Optional — missing for ~49% of the training data"},
            {"name": "bmi", "label": "Body mass index", "type": "number", "unit": "kg/m²", "min": 12, "max": 70, "required": True},
            {"name": "dpf", "label": "Diabetes pedigree function", "type": "number", "min": 0.05, "max": 2.5,
             "required": True, "help": "Family-history score defined by the dataset authors (typical range 0.08–2.42)"},
            {"name": "age", "label": "Age", "type": "integer", "unit": "years", "min": 21, "max": 100, "required": True},
        ],
    },
    "kidney": {
        "key": "kidney",
        "name": "Chronic Kidney Disease",
        "short": "Kidney",
        "dataset": "UCI Chronic Kidney Disease (400 patients)",
        "positive_label": "Chronic kidney disease indicated",
        "negative_label": "No chronic kidney disease indicated",
        "features": [
            {"name": "age", "label": "Age", "type": "integer", "unit": "years", "min": 1, "max": 100, "required": True},
            {"name": "bp", "label": "Blood pressure (diastolic)", "type": "number", "unit": "mm Hg", "min": 40, "max": 180, "required": True},
            {"name": "sg", "label": "Urine specific gravity", "type": "select", "required": True,
             "options": [{"value": v, "label": f"{v:.3f}"} for v in (1.005, 1.010, 1.015, 1.020, 1.025)]},
            {"name": "al", "label": "Urine albumin (dipstick)", "type": "select", "required": True,
             "options": [{"value": i, "label": str(i)} for i in range(6)]},
            {"name": "su", "label": "Urine sugar (dipstick)", "type": "select", "required": True,
             "options": [{"value": i, "label": str(i)} for i in range(6)]},
            {"name": "rbc", "label": "Red blood cells in urine", "type": "select", "required": False,
             "options": [{"value": 0, "label": "Normal"}, {"value": 1, "label": "Abnormal"}],
             "help": "Optional — missing for 38% of the training data"},
            {"name": "pc", "label": "Pus cells in urine", "type": "select", "required": True,
             "options": [{"value": 0, "label": "Normal"}, {"value": 1, "label": "Abnormal"}]},
            {"name": "pcc", "label": "Pus cell clumps", "type": "select", "required": True,
             "options": [{"value": 0, "label": "Not present"}, {"value": 1, "label": "Present"}]},
            {"name": "ba", "label": "Bacteria in urine", "type": "select", "required": True,
             "options": [{"value": 0, "label": "Not present"}, {"value": 1, "label": "Present"}]},
            {"name": "bgr", "label": "Random blood glucose", "type": "number", "unit": "mg/dL", "min": 20, "max": 500, "required": True},
            {"name": "bu", "label": "Blood urea", "type": "number", "unit": "mg/dL", "min": 1, "max": 400, "required": True},
            {"name": "sc", "label": "Serum creatinine", "type": "number", "unit": "mg/dL", "min": 0.1, "max": 80, "required": True},
            {"name": "sod", "label": "Sodium", "type": "number", "unit": "mEq/L", "min": 100, "max": 170, "required": False,
             "help": "Optional — missing for 22% of the training data"},
            {"name": "pot", "label": "Potassium", "type": "number", "unit": "mEq/L", "min": 2, "max": 10, "required": False,
             "help": "Optional — missing for 22% of the training data"},
            {"name": "hemo", "label": "Haemoglobin", "type": "number", "unit": "g/dL", "min": 3, "max": 20, "required": True},
            {"name": "pcv", "label": "Packed cell volume", "type": "number", "unit": "%", "min": 9, "max": 60, "required": True},
            {"name": "wc", "label": "White blood cell count", "type": "number", "unit": "cells/cumm", "min": 2000, "max": 30000, "required": False,
             "help": "Optional — missing for 26% of the training data"},
            {"name": "rc", "label": "Red blood cell count", "type": "number", "unit": "millions/cmm", "min": 2, "max": 8.5, "required": False,
             "help": "Optional — missing for 33% of the training data"},
            {"name": "htn", "label": "Hypertension", "type": "select", "required": True, "options": YES_NO},
            {"name": "dm", "label": "Diabetes mellitus", "type": "select", "required": True, "options": YES_NO},
            {"name": "cad", "label": "Coronary artery disease", "type": "select", "required": True, "options": YES_NO},
            {"name": "appet", "label": "Appetite", "type": "select", "required": True,
             "options": [{"value": 0, "label": "Good"}, {"value": 1, "label": "Poor"}]},
            {"name": "pe", "label": "Pedal oedema", "type": "select", "required": True, "options": YES_NO},
            {"name": "ane", "label": "Anaemia", "type": "select", "required": True, "options": YES_NO},
        ],
    },
    "liver": {
        "key": "liver",
        "name": "Liver Disease",
        "short": "Liver",
        "dataset": "Indian Liver Patient Dataset (583 patients)",
        "positive_label": "Liver disease indicated",
        "negative_label": "No liver disease indicated",
        "features": [
            {"name": "age", "label": "Age", "type": "integer", "unit": "years", "min": 4, "max": 95, "required": True},
            {"name": "gender", "label": "Sex", "type": "select", "required": True,
             "options": [{"value": 0, "label": "Female"}, {"value": 1, "label": "Male"}]},
            {"name": "total_bilirubin", "label": "Total bilirubin", "type": "number", "unit": "mg/dL", "min": 0.1, "max": 80, "required": True},
            {"name": "direct_bilirubin", "label": "Direct bilirubin", "type": "number", "unit": "mg/dL", "min": 0.05, "max": 40, "required": True},
            {"name": "alkaline_phosphatase", "label": "Alkaline phosphatase (ALP)", "type": "number", "unit": "IU/L", "min": 20, "max": 2500, "required": True},
            {"name": "alt", "label": "Alanine aminotransferase (ALT / SGPT)", "type": "number", "unit": "IU/L", "min": 1, "max": 2500, "required": True},
            {"name": "ast", "label": "Aspartate aminotransferase (AST / SGOT)", "type": "number", "unit": "IU/L", "min": 1, "max": 5000, "required": True},
            {"name": "total_proteins", "label": "Total proteins", "type": "number", "unit": "g/dL", "min": 2, "max": 12, "required": True},
            {"name": "albumin", "label": "Albumin", "type": "number", "unit": "g/dL", "min": 0.5, "max": 7, "required": True},
            {"name": "ag_ratio", "label": "Albumin / globulin ratio", "type": "number", "min": 0.1, "max": 3.5, "required": True},
        ],
    },
}

DISEASE_KEYS = tuple(DISEASES.keys())


def feature_names(disease: str) -> list[str]:
    return [f["name"] for f in DISEASES[disease]["features"]]


def categorical_features(disease: str) -> list[str]:
    return [f["name"] for f in DISEASES[disease]["features"] if f["type"] == "select"]


def numeric_features(disease: str) -> list[str]:
    return [f["name"] for f in DISEASES[disease]["features"] if f["type"] != "select"]
