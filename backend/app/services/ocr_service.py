"""OCR extraction of *labelled* measurements from medical report images/PDFs.

Rules enforced here:
* A value is extracted only when it appears on the same line as, and after,
  a recognised label (e.g. "Glucose: 148 mg/dL"). Unlabelled numbers are
  never used.
* Nothing is filled in for fields that were not found; they are returned as
  missing so the user must enter them.
* Every extracted value is re-checked against the field schema and returned
  for user review — extraction never triggers a prediction by itself.
* Uploads are processed in memory; nothing is written to disk.
"""

from __future__ import annotations

import io
import re

import cv2
import numpy as np
from PIL import Image

from app.services.validation import check_field
from app.utils.responses import ApiError
from ml.feature_specs import DISEASES

Image.MAX_IMAGE_PIXELS = 40_000_000  # decompression-bomb guard
MAX_PDF_PAGES = 3

MAGIC = {
    b"\x89PNG\r\n\x1a\n": "png",
    b"\xff\xd8\xff": "jpeg",
    b"%PDF-": "pdf",
}
ALLOWED_EXT = {"png": "png", "jpg": "jpeg", "jpeg": "jpeg", "pdf": "pdf"}

# Label synonyms per field. Longer/more specific phrases win when several match a line.
SYNONYMS: dict[str, dict[str, list[str]]] = {
    "heart": {
        "age": ["age"],
        "sex": ["sex", "gender"],
        "trestbps": ["resting blood pressure", "resting bp", "systolic blood pressure", "systolic bp", "trestbps"],
        "chol": ["serum cholesterol", "total cholesterol", "cholesterol", "chol"],
        "thalach": ["maximum heart rate", "max heart rate", "peak heart rate", "thalach"],
        "oldpeak": ["st depression", "oldpeak"],
        "cp": ["chest pain type", "chest pain"],
        "fbs": ["fasting blood sugar"],
        "restecg": ["resting ecg", "resting electrocardiogram", "resting ecg result"],
        "exang": ["exercise induced angina", "exercise-induced angina", "exercise angina"],
        "slope": ["slope of peak exercise st segment", "st segment slope", "st slope"],
        "ca": ["major vessels coloured by fluoroscopy", "major vessels colored by fluoroscopy", "major vessels"],
        "thal": ["thallium stress test", "thallium scan", "thalassemia", "thal"],
    },
    "diabetes": {
        "pregnancies": ["pregnancies", "number of pregnancies", "gravida"],
        "glucose": ["plasma glucose", "glucose", "blood sugar", "ogtt"],
        "blood_pressure": ["diastolic blood pressure", "diastolic bp", "diastolic"],
        "skin_thickness": ["skin thickness", "triceps skin fold", "skinfold"],
        "insulin": ["serum insulin", "insulin"],
        "bmi": ["bmi", "body mass index"],
        "dpf": ["diabetes pedigree function", "pedigree function", "dpf"],
        "age": ["age"],
    },
    "kidney": {
        "age": ["age"],
        "bp": ["blood pressure", "diastolic bp", "bp"],
        "sg": ["specific gravity"],
        "al": ["urine albumin", "albumin (urine)", "albumin"],
        "su": ["urine sugar", "sugar (urine)"],
        "bgr": ["random blood glucose", "blood glucose random", "random glucose", "glucose random"],
        "bu": ["blood urea", "urea"],
        "sc": ["serum creatinine", "creatinine"],
        "sod": ["sodium", "na+"],
        "pot": ["potassium", "k+"],
        "hemo": ["haemoglobin", "hemoglobin", "hb"],
        "pcv": ["packed cell volume", "pcv", "haematocrit", "hematocrit"],
        "wc": ["white blood cell count", "wbc count", "total leucocyte count", "tlc", "wbc"],
        "rc": ["red blood cell count", "rbc count"],
        "rbc": ["red blood cells in urine", "urine rbc", "rbc (urine)"],
        "pc": ["pus cells", "pus cell"],
        "pcc": ["pus cell clumps"],
        "ba": ["bacteria"],
        "htn": ["hypertension"],
        "dm": ["diabetes mellitus"],
        "cad": ["coronary artery disease"],
        "appet": ["appetite"],
        "pe": ["pedal oedema", "pedal edema"],
        "ane": ["anaemia", "anemia"],
    },
    "liver": {
        "age": ["age"],
        "gender": ["sex", "gender"],
        "total_bilirubin": ["total bilirubin", "bilirubin total", "bilirubin, total", "s. bilirubin total"],
        "direct_bilirubin": ["direct bilirubin", "bilirubin direct", "bilirubin, direct", "conjugated bilirubin"],
        "alkaline_phosphatase": ["alkaline phosphatase", "alk phos", "alp"],
        "alt": ["alanine aminotransferase", "sgpt", "alt"],
        "ast": ["aspartate aminotransferase", "sgot", "ast"],
        "total_proteins": ["total proteins", "total protein", "protein total"],
        "albumin": ["serum albumin", "albumin"],
        "ag_ratio": ["albumin/globulin ratio", "a/g ratio", "aig ratio", "a:g ratio", "a g ratio", "albumin globulin ratio", "ag ratio"],
    },
}

NUMBER = r"(-?\d+(?:[.,]\d+)?)"


def detect_type(data: bytes, filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXT:
        raise ApiError("unsupported_file", "Upload a PNG, JPEG or PDF file.", 415)
    kind = next((k for sig, k in MAGIC.items() if data.startswith(sig)), None)
    if kind is None or kind != ALLOWED_EXT[ext]:
        raise ApiError("unsupported_file", "The file content does not match its extension or is not a supported type.", 415)
    return kind


def _preprocess(img: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    h, w = gray.shape[:2]
    if w < 1400:
        scale = 1400 / w
        gray = cv2.resize(gray, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC)
    # No median blur: on printed reports it erases decimal points (1.1 -> 11).
    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return bw


def _images(data: bytes, kind: str) -> list[np.ndarray]:
    if kind == "pdf":
        import pypdfium2 as pdfium
        try:
            pdf = pdfium.PdfDocument(data)
        except Exception as exc:
            raise ApiError("unreadable_file", "The PDF could not be opened.", 422) from exc
        pages = []
        try:
            for i in range(min(len(pdf), MAX_PDF_PAGES)):
                pil = pdf[i].render(scale=2.5).to_pil().convert("RGB")
                pages.append(cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR))
        finally:
            pdf.close()
        return pages
    try:
        with Image.open(io.BytesIO(data)) as im:
            im.verify()
        with Image.open(io.BytesIO(data)) as im:
            rgb = im.convert("RGB")
    except Exception as exc:
        raise ApiError("unreadable_file", "The image could not be read.", 422) from exc
    return [cv2.cvtColor(np.array(rgb), cv2.COLOR_RGB2BGR)]


def ocr_text(data: bytes, kind: str) -> str:
    import os

    import pytesseract
    if os.getenv("TESSERACT_CMD"):
        pytesseract.pytesseract.tesseract_cmd = os.getenv("TESSERACT_CMD")
    try:
        return "\n".join(pytesseract.image_to_string(_preprocess(img), config="--psm 6") for img in _images(data, kind))
    except pytesseract.TesseractNotFoundError as exc:
        raise ApiError("ocr_unavailable", "Tesseract OCR is not installed on the server. See README → OCR.", 503) from exc


def _label_pattern(label: str) -> re.Pattern:
    return re.compile(r"(?<![a-z])" + re.escape(label) + r"(?![a-z])")


OPTION_ALIASES = {"male": 1, "m": 1, "female": 0, "f": 0}


def _match_option(f: dict, segment: str):
    """Pick the option whose label appears earliest in the text after the
    field label (longest label wins on a tie). Falls back to M/F for sex and
    to a bare number for numeric option codes."""
    best = None
    candidates = [(o["label"].lower(), o["value"]) for o in f["options"]]
    if f["name"] in ("sex", "gender"):
        candidates += list(OPTION_ALIASES.items())
    for label, value in candidates:
        m = re.search(r"(?<![a-z0-9.])" + re.escape(label) + r"(?![a-z0-9])", segment)
        if m and (best is None or m.start() < best[0] or (m.start() == best[0] and len(label) > best[1])):
            best = (m.start(), len(label), value)
    if best is not None:
        return best[2]
    m = re.search(NUMBER, segment)
    return m.group(1) if m else None


def parse_measurements(text: str, disease: str) -> dict:
    spec = {f["name"]: f for f in DISEASES[disease]["features"]}
    synonyms = SYNONYMS[disease]
    found: dict[str, dict] = {}

    for raw_line in text.splitlines():
        line = raw_line.strip()
        low = line.lower()
        if not low:
            continue
        # Collect every label occurrence, keep the most specific (longest)
        # among overlapping ones, then read each value only from the text
        # between its label and the next label on the same line.
        hits = []
        for field, labels in synonyms.items():
            for label in labels:
                for m in _label_pattern(label).finditer(low):
                    hits.append((m.start(), m.end(), field))
        hits.sort(key=lambda h: (h[0], -(h[1] - h[0])))
        chosen = []
        for h in hits:
            if chosen and h[0] < chosen[-1][1]:
                if (h[1] - h[0]) > (chosen[-1][1] - chosen[-1][0]):
                    chosen[-1] = h
                continue
            chosen.append(h)
        for i, (_, end, field) in enumerate(chosen):
            if field in found:
                continue
            segment = low[end: chosen[i + 1][0] if i + 1 < len(chosen) else len(low)]
            # Common OCR confusion: a lone "o"/"O" where the report printed 0;
            # "Nil"/"None" is how many labs print a zero result.
            segment = re.sub(r"(?<![a-z0-9])o+(?![a-z0-9])", "0", segment)
            segment = re.sub(r"(?<![a-z])(nil|none)(?![a-z])", "0", segment)
            f = spec[field]
            if f["type"] == "select":
                value = _match_option(f, segment)
                if value is None:
                    continue
            else:
                m = re.search(NUMBER, segment)
                if not m:
                    continue
                value = m.group(1).replace(",", ".")
            checked, err = check_field(f, value)
            found[field] = {
                "field": field,
                "label": f["label"],
                "value": checked if err is None else value,
                "valid": err is None,
                "error": err,
                "source_line": line[:200],
            }

    missing = [{"field": n, "label": f["label"], "required": f.get("required", True)}
               for n, f in spec.items() if n not in found]
    return {"extracted": list(found.values()), "missing": missing}


def extract(data: bytes, filename: str, disease: str) -> dict:
    if disease not in DISEASES:
        raise ApiError("unknown_disease", f"Unknown disease module '{disease}'.", 404)
    if not data:
        raise ApiError("empty_file", "The uploaded file is empty.", 400)
    kind = detect_type(data, filename)
    text = ocr_text(data, kind)
    parsed = parse_measurements(text, disease)
    parsed["disease"] = disease
    parsed["characters_recognised"] = len(text.strip())
    parsed["text_preview"] = text.strip()[:1500]
    return parsed
