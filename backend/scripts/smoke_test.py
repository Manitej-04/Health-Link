"""Smoke-test a running Health-Link backend end to end (standard library only).

    python scripts/smoke_test.py                 # against http://127.0.0.1:5000
    python scripts/smoke_test.py http://host:port
"""
import http.cookiejar
import json
import sys
import time
import urllib.error
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5000").rstrip("/")
jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

SAMPLES = {  # real records from the public datasets
    "heart": {"age": 63, "sex": 1, "cp": 1, "trestbps": 145, "chol": 233, "fbs": 1, "restecg": 2, "thalach": 150,
              "exang": 0, "oldpeak": 2.3, "slope": 3, "ca": 0, "thal": 6},
    "diabetes": {"pregnancies": 1, "glucose": 85, "blood_pressure": 66, "skin_thickness": 29, "insulin": None,
                 "bmi": 26.6, "dpf": 0.351, "age": 31},
    "kidney": {"age": 48, "bp": 80, "sg": 1.02, "al": 1, "su": 0, "rbc": None, "pc": 0, "pcc": 0, "ba": 0, "bgr": 121,
               "bu": 36, "sc": 1.2, "sod": None, "pot": None, "hemo": 15.4, "pcv": 44, "wc": 7800, "rc": 5.2,
               "htn": 1, "dm": 1, "cad": 0, "appet": 0, "pe": 0, "ane": 0},
    "liver": {"age": 62, "gender": 1, "total_bilirubin": 10.9, "direct_bilirubin": 5.5, "alkaline_phosphatase": 699,
              "alt": 64, "ast": 100, "total_proteins": 7.5, "albumin": 3.2, "ag_ratio": 0.74},
}


def call(method, path, body=None):
    headers = {"Content-Type": "application/json"}
    csrf = next((c.value for c in jar if c.name == "csrf_access_token"), None)
    if csrf and method != "GET":
        headers["X-CSRF-TOKEN"] = csrf
    req = urllib.request.Request(BASE + path, method=method, headers=headers,
                                 data=json.dumps(body).encode() if body is not None else None)
    try:
        with opener.open(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def main():
    s, h = call("GET", "/api/health")
    print("health", s, h.get("data"))
    email = f"smoke{int(time.time())}@example.com"
    s, _ = call("POST", "/api/auth/register", {"name": "Smoke Test", "email": email, "password": "Smoke12345"})
    print("register", s)
    for d, f in SAMPLES.items():
        s, r = call("POST", f"/api/predict/{d}", {"features": f})
        data = r.get("data") or r.get("error")
        print(f"predict {d:<8}", s, {k: data.get(k) for k in ("predicted_label", "probability", "risk_category", "model_status", "message")})
    s, r = call("GET", "/api/history")
    print("history", s, "total =", r["data"]["total"])
    s, _ = call("POST", "/api/auth/logout")
    print("logout", s, "| me after logout:", call("GET", "/api/auth/me")[0])


if __name__ == "__main__":
    main()
