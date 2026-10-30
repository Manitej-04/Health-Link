import io
import shutil

import pytest
from PIL import Image, ImageDraw, ImageFont

from app.services.ocr_service import parse_measurements

needs_tesseract = pytest.mark.skipif(shutil.which("tesseract") is None, reason="Tesseract binary not installed")


def _font(size=34):
    for path in ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "C:/Windows/Fonts/arial.ttf",
                 "/Library/Fonts/Arial.ttf", "/System/Library/Fonts/Supplemental/Arial.ttf"]:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _report_image(lines, fmt="PNG") -> bytes:
    img = Image.new("RGB", (1400, 90 + 60 * len(lines)), "white")
    d = ImageDraw.Draw(img)
    font = _font()
    for i, line in enumerate(lines):
        d.text((50, 40 + 60 * i), line, fill="black", font=font)
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


LIVER_REPORT = [
    "City Diagnostics - Liver Function Test",
    "Patient Age: 45 Years   Sex: Male",
    "Total Bilirubin 1.2 mg/dL",
    "Direct Bilirubin 0.4 mg/dL",
    "Alkaline Phosphatase 210 IU/L",
    "SGPT (ALT) 64 IU/L",
    "SGOT (AST) 58 IU/L",
    "Total Proteins 6.9 g/dL",
    "A/G Ratio 1.1",
    "Ref No 88213 Sample 4471",
]


# ---------- parser (no OCR engine needed) ----------

def test_parser_extracts_only_labelled_values():
    text = "Glucose: 148 mg/dL\nBMI 33.6\n72 35 0 0.627\nAge 50 years"
    out = parse_measurements(text, "diabetes")
    got = {e["field"]: e["value"] for e in out["extracted"]}
    assert got == {"glucose": 148.0, "bmi": 33.6, "age": 50}
    missing = {m["field"] for m in out["missing"]}
    assert {"blood_pressure", "insulin", "dpf", "pregnancies"} <= missing  # unlabelled numbers ignored


def test_parser_prefers_most_specific_label():
    out = parse_measurements("Direct Bilirubin 0.4\nTotal Bilirubin 1.2\nAlbumin/Globulin Ratio 1.1\nAlbumin 3.6",
                             "liver")
    got = {e["field"]: e["value"] for e in out["extracted"]}
    assert got["direct_bilirubin"] == 0.4 and got["total_bilirubin"] == 1.2
    assert got["ag_ratio"] == 1.1 and got["albumin"] == 3.6


def test_parser_flags_out_of_range_values():
    out = parse_measurements("Glucose 999", "diabetes")
    g = out["extracted"][0]
    assert g["valid"] is False and "between" in g["error"]


def test_parser_reads_sex_words():
    got = {e["field"]: e["value"] for e in parse_measurements("Sex: Female", "liver")["extracted"]}
    assert got["gender"] == 0


# ---------- endpoint ----------

def _upload(api, data, name, disease="liver"):
    return api.c.post("/api/ocr/extract", data={"disease": disease, "file": (io.BytesIO(data), name)},
                      headers=api._headers(), content_type="multipart/form-data")


@needs_tesseract
def test_ocr_endpoint_png(user_api):
    r = _upload(user_api, _report_image(LIVER_REPORT), "lft.png")
    assert r.status_code == 200, r.get_json()
    got = {e["field"]: e["value"] for e in r.get_json()["data"]["extracted"] if e["valid"]}
    assert got.get("total_bilirubin") == 1.2 and got.get("alkaline_phosphatase") == 210
    assert got.get("alt") == 64 and got.get("ast") == 58 and got.get("gender") == 1
    # albumin was not on the report -> must be reported missing, never filled in
    assert "albumin" in {m["field"] for m in r.get_json()["data"]["missing"]}


@needs_tesseract
def test_ocr_endpoint_pdf(user_api):
    r = _upload(user_api, _report_image(LIVER_REPORT, fmt="PDF"), "lft.pdf")
    assert r.status_code == 200, r.get_json()
    fields = {e["field"] for e in r.get_json()["data"]["extracted"]}
    assert "total_bilirubin" in fields


def test_ocr_rejects_wrong_type(user_api):
    assert _upload(user_api, b"MZ\x90\x00 executable", "report.exe").status_code == 415
    # extension says png, content is not
    assert _upload(user_api, b"%PDF-1.4 fake", "report.png").status_code == 415


def test_ocr_rejects_oversized(make_app):
    from tests.conftest import Api
    app = make_app(MAX_CONTENT_LENGTH=1024)
    a = Api(app.test_client()); a.register()
    r = _upload(a, b"\x89PNG\r\n\x1a\n" + b"0" * 5000, "big.png")
    assert r.status_code == 413


def test_ocr_requires_file_and_known_disease(user_api):
    r = user_api.c.post("/api/ocr/extract", data={"disease": "liver"}, headers=user_api._headers(),
                        content_type="multipart/form-data")
    assert r.status_code == 400
    assert _upload(user_api, _report_image(["Age 40"]), "a.png", disease="lung").status_code == 404
    assert _upload(user_api, b"", "a.png").status_code == 400


def test_ocr_rejects_corrupt_image(user_api):
    assert _upload(user_api, b"\x89PNG\r\n\x1a\n" + b"garbage", "x.png").status_code == 422


def test_ocr_requires_auth(client):
    r = client.post("/api/ocr/extract", data={"disease": "liver"}, content_type="multipart/form-data")
    assert r.status_code == 401


def test_parser_reads_categorical_fields_and_nil():
    text = ("Chest pain type  Asymptomatic\nFasting blood sugar (>120 mg/dL)  No\nResting ECG  Normal\n"
            "Exercise-induced angina  Yes\nSlope of peak exercise ST segment  Flat\n"
            "Major vessels coloured by fluoroscopy  2\nThallium stress test  Reversible defect")
    got = {e["field"]: e["value"] for e in parse_measurements(text, "heart")["extracted"]}
    assert got == {"cp": 4, "fbs": 0, "restecg": 0, "exang": 1, "slope": 2, "ca": 2, "thal": 7}
    text = "Urine albumin (dipstick)  Nil  grade\nPus cells  Abnormal\nBacteria  Not present\nAppetite  Poor"
    got = {e["field"]: e["value"] for e in parse_measurements(text, "kidney")["extracted"]}
    assert got == {"al": 0, "pc": 1, "ba": 0, "appet": 1}


SAMPLES_DIR = __import__("pathlib").Path(__file__).resolve().parents[2] / "sample_reports"


@needs_tesseract
@pytest.mark.skipif(not SAMPLES_DIR.exists(), reason="sample reports not generated")
@pytest.mark.parametrize("disease", ["heart", "diabetes", "kidney", "liver"])
def test_sample_report_fills_every_field(user_api, disease):
    from ml.feature_specs import feature_names
    pdf = sorted((SAMPLES_DIR / disease).glob("*.pdf"))[0]
    r = _upload(user_api, pdf.read_bytes(), pdf.name, disease=disease)
    assert r.status_code == 200
    data = r.get_json()["data"]
    assert data["missing"] == []
    assert {e["field"] for e in data["extracted"] if e["valid"]} == set(feature_names(disease))
