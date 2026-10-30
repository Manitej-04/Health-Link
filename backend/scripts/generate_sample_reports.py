"""Generate sample lab-report documents (PNG + PDF) for demonstrating the
Health-Link OCR and prediction workflow.

    python scripts/generate_sample_reports.py            # writes ../sample_reports/

Every case is built from a real, de-identified record of the public training
dataset (row number given), occasionally with one or two values adjusted to
land in a particular risk band (stated in the report and in the answer key).
Names, IDs and the laboratory are fictitious. These are demo documents, not
medical reports.

After writing the files the script OCRs every PNG and PDF with the app's own
OCR service and runs the current model, so the answer key reflects what the
application actually returns.
"""

from __future__ import annotations

import csv
import io
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

import pandas as pd  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.pdfbase import pdfmetrics  # noqa: E402
from reportlab.pdfbase.ttfonts import TTFont  # noqa: E402
from reportlab.pdfgen import canvas  # noqa: E402

from ml.feature_specs import DISEASES  # noqa: E402
from ml.preprocessing.loaders import load  # noqa: E402

OUT = BACKEND.parent / "sample_reports"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
LAB = "Health-Link Demo Diagnostics (fictitious sample laboratory)"
NOTICE = "SAMPLE TEST DOCUMENT for the Health-Link educational demo. Not a real medical report."

# (printed label, field, unit, reference range). Labels match the OCR parser.
ROWS = {
    "heart": [
        ("Resting blood pressure", "trestbps", "mm Hg", "90 - 120"),
        ("Serum cholesterol", "chol", "mg/dL", "125 - 200"),
        ("Fasting blood sugar (>120 mg/dL)", "fbs", "", ""),
        ("Chest pain type", "cp", "", ""),
        ("Resting ECG", "restecg", "", ""),
        ("Maximum heart rate achieved", "thalach", "bpm", ""),
        ("Exercise-induced angina", "exang", "", ""),
        ("ST depression (exercise vs rest)", "oldpeak", "mm", ""),
        ("Slope of peak exercise ST segment", "slope", "", ""),
        ("Major vessels coloured by fluoroscopy", "ca", "", ""),
        ("Thallium stress test", "thal", "", ""),
    ],
    "diabetes": [
        ("Number of pregnancies", "pregnancies", "", ""),
        ("Plasma glucose (OGTT)", "glucose", "mg/dL", "70 - 140"),
        ("Diastolic blood pressure", "blood_pressure", "mm Hg", "60 - 80"),
        ("Triceps skin fold thickness", "skin_thickness", "mm", ""),
        ("Serum insulin", "insulin", "uU/mL", "16 - 166"),
        ("BMI", "bmi", "kg/m2", "18.5 - 24.9"),
        ("Diabetes pedigree function", "dpf", "", ""),
    ],
    "kidney": [
        ("Blood pressure (diastolic)", "bp", "mm Hg", "60 - 80"),
        ("Urine specific gravity", "sg", "", "1.005 - 1.030"),
        ("Urine albumin (dipstick)", "al", "grade", ""),
        ("Urine sugar (dipstick)", "su", "grade", ""),
        ("Red blood cells in urine", "rbc", "", ""),
        ("Pus cells", "pc", "", ""),
        ("Pus cell clumps", "pcc", "", ""),
        ("Bacteria", "ba", "", ""),
        ("Random blood glucose", "bgr", "mg/dL", "70 - 140"),
        ("Blood urea", "bu", "mg/dL", "15 - 40"),
        ("Serum creatinine", "sc", "mg/dL", "0.6 - 1.2"),
        ("Sodium", "sod", "mEq/L", "135 - 145"),
        ("Potassium", "pot", "mEq/L", "3.5 - 5.0"),
        ("Haemoglobin", "hemo", "g/dL", "12.0 - 17.0"),
        ("Packed cell volume", "pcv", "%", "36 - 50"),
        ("White blood cell count", "wc", "cells/cumm", "4000 - 11000"),
        ("Red blood cell count", "rc", "millions/cmm", "4.2 - 5.9"),
        ("Hypertension", "htn", "", ""),
        ("Diabetes mellitus", "dm", "", ""),
        ("Coronary artery disease", "cad", "", ""),
        ("Appetite", "appet", "", ""),
        ("Pedal oedema", "pe", "", ""),
        ("Anaemia", "ane", "", ""),
    ],
    "liver": [
        ("Total bilirubin", "total_bilirubin", "mg/dL", "0.3 - 1.2"),
        ("Direct bilirubin", "direct_bilirubin", "mg/dL", "0.0 - 0.3"),
        ("Alkaline phosphatase (ALP)", "alkaline_phosphatase", "IU/L", "44 - 147"),
        ("SGPT / ALT", "alt", "IU/L", "7 - 56"),
        ("SGOT / AST", "ast", "IU/L", "8 - 48"),
        ("Total proteins", "total_proteins", "g/dL", "6.0 - 8.3"),
        ("Albumin", "albumin", "g/dL", "3.5 - 5.0"),
        ("A/G ratio", "ag_ratio", "", "1.0 - 2.1"),
    ],
}

TITLES = {
    "heart": "Cardiac Risk Panel",
    "diabetes": "Diabetes Screening Panel",
    "kidney": "Renal Function Panel",
    "liver": "Liver Function Test",
}

# (dataset row, target band, adjustments). Row numbers index the raw dataset files.
CASES = {
    "heart": [(149, "LOW", {}), (172, "MODERATE", {}), (174, "HIGH", {}), (60, "MODERATE", {})],
    "diabetes": [(514, "LOW", {}), (428, "MODERATE", {}), (487, "HIGH", {}), (693, "MODERATE", {})],
    "kidney": [(254, "LOW", {}), (266, "MODERATE", {"hemo": 12.2, "pcv": 38}), (181, "HIGH", {}),
               (266, "MODERATE", {"hemo": 11.0, "pcv": 34})],
    # The liver model never gives an estimate below 30% (its training data is
    # 71% positive), so no LOW case exists; case 1 is the lowest-scoring record.
    "liver": [(435, "MODERATE", {}), (334, "MODERATE", {}), (387, "MODERATE", {}), (89, "HIGH", {})],
}

FIRST = ["Aarav", "Diya", "Rohan", "Ananya", "Kabir", "Isha", "Vihaan", "Meera"]
LAST = ["Sample", "Demo", "Testcase", "Example"]


def display(disease: str, field: str, value) -> str:
    f = next(x for x in DISEASES[disease]["features"] if x["name"] == field)
    if f["type"] == "select":
        return next(o["label"] for o in f["options"] if float(o["value"]) == float(value))
    if f["type"] == "integer" or float(value).is_integer() and field in ("chol", "trestbps", "thalach", "bgr", "wc",
                                                                         "alkaline_phosphatase", "alt", "ast", "bp",
                                                                         "glucose", "blood_pressure", "pregnancies",
                                                                         "skin_thickness", "insulin", "bu", "sod"):
        return str(int(round(float(value))))
    return f"{float(value):g}"


def build_cases():
    cases = []
    for disease, items in CASES.items():
        X, _ = load(disease)
        for n, (row, band, adjust) in enumerate(items, start=1):
            values = X.loc[row].to_dict()
            values.update(adjust)
            if values.get("age") is not None:
                values["age"] = int(values["age"])
            sex = None
            if disease == "heart":
                sex = "Male" if values["sex"] == 1 else "Female"
            elif disease == "liver":
                sex = "Male" if values["gender"] == 1 else "Female"
            elif disease == "diabetes":
                sex = "Female"
            idx = len(cases)
            cases.append({
                "id": f"{disease}_{n:02d}_{band.lower()}",
                "disease": disease, "band": band, "row": row, "adjust": adjust, "values": values, "sex": sex,
                "name": f"{FIRST[idx % len(FIRST)]} {LAST[idx % len(LAST)]}",
                "sample_id": f"HLD-{disease[:2].upper()}-{1000 + idx}",
            })
    return cases


def lines_for(case):
    d = case["disease"]
    rows = []
    for label, field, unit, ref in ROWS[d]:
        shown = display(d, field, case["values"][field])
        if field in ("al", "su") and shown == "0":
            shown = "Nil"  # how labs usually print a zero dipstick grade
        rows.append((label, shown, unit, ref))
    header = [f"Patient: {case['name']}", f"Sample ID: {case['sample_id']}    Collected: 30 Oct 2026"]
    agesex = f"Age: {case['values']['age']} Years" + (f"    Sex: {case['sex']}" if case["sex"] else "")
    header.append(agesex)
    src = f"Source: public dataset record #{case['row']}"
    if case["adjust"]:
        src += " (adjusted: " + ", ".join(f"{k}" for k in case["adjust"]) + ")"
    return header, rows, src


S = 1.35                      # render scale (1240 px layout -> ~1670 px wide image)
COLS = [60, 560, 770, 930]    # x positions in layout units


def render_png(case, path: Path):
    header, rows, src = lines_for(case)
    W = 1240
    H = 520 + 54 * len(rows)
    img = Image.new("RGB", (int(W * S), int(H * S)), "white")
    d = ImageDraw.Draw(img)
    f = lambda size, b=False: ImageFont.truetype(FONT_BOLD if b else FONT_REG, int(size * S))  # noqa: E731
    P = lambda *xy: [int(v * S) for v in xy]  # noqa: E731
    d.rectangle(P(0, 0, W, 110), fill="#0d6b66")
    d.text(P(60, 28), "Health-Link Demo Diagnostics", fill="white", font=f(38, True))
    d.text(P(60, 76), "Fictitious sample laboratory", fill="#d6f0ec", font=f(20))
    y = 140
    d.text(P(60, y), TITLES[case["disease"]], fill="#15233f", font=f(34, True)); y += 60
    for h in header:
        d.text(P(60, y), h, fill="#15233f", font=f(26)); y += 40
    y += 16
    d.line(P(60, y, W - 60, y), fill="#15233f", width=2); y += 14
    for x, t in zip(COLS, ["Test", "Result", "Unit", "Reference range"]):
        d.text(P(x, y), t, fill="#4a5a70", font=f(22, True))
    y += 40
    d.line(P(60, y, W - 60, y), fill="#b5c6c3", width=1); y += 12
    for label, value, unit, ref in rows:
        d.text(P(COLS[0], y), label, fill="#15233f", font=f(25))
        d.text(P(COLS[1], y), value, fill="#15233f", font=f(25, True))
        d.text(P(COLS[2], y), unit, fill="#4a5a70", font=f(22))
        d.text(P(COLS[3], y), ref, fill="#4a5a70", font=f(22))
        y += 54
    y += 10
    d.line(P(60, y, W - 60, y), fill="#b5c6c3", width=1); y += 20
    d.text(P(60, y), src, fill="#6b7a8c", font=f(18)); y += 30
    d.text(P(60, y), NOTICE, fill="#a86a12", font=f(18, True))
    img.save(path)


def render_pdf(case, path: Path):
    header, rows, src = lines_for(case)
    pdfmetrics.registerFont(TTFont("DV", FONT_REG))
    pdfmetrics.registerFont(TTFont("DVB", FONT_BOLD))
    W, H = A4
    c = canvas.Canvas(str(path), pagesize=A4)
    c.setTitle(f"{TITLES[case['disease']]} - {case['sample_id']} (sample)")
    c.setFillColorRGB(0.05, 0.42, 0.40); c.rect(0, H - 70, W, 70, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1); c.setFont("DVB", 20); c.drawString(36, H - 40, "Health-Link Demo Diagnostics")
    c.setFont("DV", 10); c.drawString(36, H - 58, "Fictitious sample laboratory")
    c.setFillColorRGB(0.08, 0.14, 0.25)
    y = H - 105
    c.setFont("DVB", 16); c.drawString(36, y, TITLES[case["disease"]]); y -= 26
    c.setFont("DV", 12)
    for h in header:
        c.drawString(36, y, h); y -= 18
    y -= 6; c.line(36, y, W - 36, y); y -= 18
    cols = [36, 300, 405, 490]
    c.setFont("DVB", 10.5)
    for x, t in zip(cols, ["Test", "Result", "Unit", "Reference range"]):
        c.drawString(x, y, t)
    y -= 8; c.line(36, y, W - 36, y); y -= 18
    for label, value, unit, ref in rows:
        c.setFont("DV", 11.5); c.drawString(cols[0], y, label)
        c.setFont("DVB", 11.5); c.drawString(cols[1], y, value)
        c.setFont("DV", 10.5); c.drawString(cols[2], y, unit); c.drawString(cols[3], y, ref)
        y -= 23
    y -= 4; c.line(36, y, W - 36, y); y -= 18
    c.setFont("DV", 9); c.setFillColorRGB(0.42, 0.48, 0.55); c.drawString(36, y, src); y -= 14
    c.setFont("DVB", 9); c.setFillColorRGB(0.66, 0.42, 0.07); c.drawString(36, y, NOTICE)
    c.showPage(); c.save()


def verify(cases):
    """OCR every file with the app's own service and run the current model."""
    from app import create_app
    from app.services.ocr_service import extract
    from app.services.prediction_service import run_prediction
    from app.services.validation import validate_features

    app = create_app("testing")
    results = []
    with app.app_context():
        for case in cases:
            d = case["disease"]
            row = {}
            for ext in ("png", "pdf"):
                path = OUT / d / f"{case['id']}.{ext}"
                parsed = extract(path.read_bytes(), path.name, d)
                got = {e["field"]: e["value"] for e in parsed["extracted"] if e["valid"]}
                expected = {k: v for k, v in case["values"].items()}
                wrong = [k for k in expected if k not in got or abs(float(got[k]) - float(expected[k])) > 1e-6]
                row[ext] = "all fields read correctly" if not wrong else f"check: {', '.join(wrong)}"
            clean, missing = validate_features(d, {k: case["values"][k] for k in case["values"]})
            res = run_prediction(d, clean, missing)
            results.append({
                "file": f"{d}/{case['id']}", "disease": DISEASES[d]["name"], "patient": case["name"],
                "dataset_row": case["row"], "adjusted": ", ".join(f"{k}={v}" for k, v in case["adjust"].items()) or "",
                "expected_band": res["risk_category"], "probability": f"{res['probability'] * 100:.1f}%",
                "prediction": res["predicted_label"], "ocr_png": row["png"], "ocr_pdf": row["pdf"],
            })
    return results


def main():
    cases = build_cases()
    for case in cases:
        folder = OUT / case["disease"]
        folder.mkdir(parents=True, exist_ok=True)
        render_png(case, folder / f"{case['id']}.png")
        render_pdf(case, folder / f"{case['id']}.pdf")
    results = verify(cases)
    with open(OUT / "answer_key.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(results[0]))
        w.writeheader(); w.writerows(results)
    for r in results:
        print(f"{r['file']:<32} {r['expected_band']:<9} {r['probability']:>6}  png: {r['ocr_png']} | pdf: {r['ocr_pdf']}")
    return results


if __name__ == "__main__":
    main()
