# Machine-learning methodology

All numbers in this document come from `backend/ml/artifacts/<disease>/metadata.json`
and `reports/model_evaluation.md`, both written by the training script. Re-running
`python -m ml.training.train` regenerates them (seeded, so results are reproducible
for the same library versions).

## 1. Pipeline overview

```
raw CSV ──► loaders.py (deterministic cleaning) ──► drop exact duplicate rows
        ──► integrity checks ──► stratified 80/20 split (seed 42)
        ──► model selection: 5-fold × 3-repeat stratified CV on the TRAIN split only
        ──► final model = selected Pipeline inside CalibratedClassifierCV(sigmoid, cv=5), fit on TRAIN
        ──► single evaluation on the held-out TEST split
        ──► eligibility rules ──► model.joblib + metadata.json + plots
```

Training is a separate command; the web application only loads saved artifacts.

## 2. Preprocessing (leak-free)

* **Deterministic cleaning** in `ml/preprocessing/loaders.py` touches one row at a time:
  * Heart: binary target `num > 0`.
  * Diabetes: zeros in glucose, blood pressure, skin thickness, insulin and BMI are documented missing-value codes → NaN.
  * Kidney: strip stray tabs/spaces (`"\tyes"`, `"ckd\t"`), `?` → NaN, text categories → 0/1; physically impossible sodium (< 100 mEq/L) and potassium (> 10 mEq/L) entries → NaN (recording errors such as Na 4.5, K 47).
  * Liver: gender → 0/1, selector 1 → positive, 2 → negative.
* **Learned steps live inside the scikit-learn `Pipeline`** (`ml/preprocessing/pipeline.py`): median imputation + standard scaling for numeric/ordinal/binary columns; most-frequent imputation + one-hot encoding for nominal columns (heart `cp`, `restecg`, `slope`, `thal`). Because they are inside the pipeline, cross-validation and the final fit learn medians, means and categories from training rows only. A unit test asserts the fitted scaler's means equal those of the training rows.
* **Duplicates**: exact duplicate rows are removed *before* splitting so a record cannot appear in both train and test (13 duplicates removed from ILPD; none elsewhere).
* **Class imbalance**: no resampling is used. The goal is calibrated probabilities, and oversampling (e.g. SMOTE) distorts the base rate the calibrated probability depends on. Imbalanced-learn was therefore judged not methodologically justified.

## 3. Model selection

Candidates (fixed, modest hyper-parameters, listed in increasing complexity):
Logistic Regression, Decision Tree (depth 4), K-Nearest Neighbours (k = 15), SVM (RBF),
Random Forest (300 trees), Gradient Boosting (150 shallow trees).

Each is scored by repeated stratified 5-fold CV ROC-AUC on the training split.
The rule: highest mean CV ROC-AUC, but prefer the simplest model whose mean is
within 0.01 of the best. The held-out test set is **not** used for selection; test
scores for every candidate are recorded as information only.

| Module | CV ROC-AUC of selected model (mean ± sd) | Selected |
|---|---|---|
| Heart | 0.892 ± 0.043 (Random Forest best at 0.894) | Logistic Regression |
| Diabetes | 0.842 ± 0.026 | Logistic Regression |
| Kidney | 1.000 ± 0.000 | Logistic Regression |
| Liver | 0.721 ± 0.048 (tie with Random Forest 0.721) | Logistic Regression |

## 4. Probability calibration

The selected pipeline is wrapped in `CalibratedClassifierCV(method="sigmoid", cv=5)`:
five pipelines are trained on four-fifths of the training split and a Platt
(sigmoid) mapping is fitted on the held-out fifth each time, so calibration is
learned on data the underlying model did not see. Sigmoid rather than isotonic
was chosen because the training sets are small (242–614 rows) and isotonic
regression over-fits at that size.

Calibration is then evaluated once on the held-out test split with:

* **Brier score** and **Brier skill score** (BSS = 1 − Brier / Brier of always predicting the training prevalence).
* **Expected calibration error** (ECE), 5 equal-width bins — few bins because test sets have 61–154 patients.
* A calibration curve (`calibration_curve.png`).

## 5. Held-out results

| Module | Test n | ROC-AUC (95% bootstrap CI) | Accuracy | Majority baseline | Sensitivity | Specificity | F1 | Brier | BSS | ECE |
|---|---|---|---|---|---|---|---|---|---|---|
| Heart | 61 | 0.958 (0.898–0.996) | 0.869 | 0.541 | 0.929 | 0.818 | 0.867 | 0.090 | 0.639 | 0.097 |
| Diabetes | 154 | 0.812 (0.740–0.872) | 0.701 | 0.649 | 0.481 | 0.820 | 0.531 | 0.173 | 0.239 | 0.056 |
| Kidney | 80 | 1.000 (1.000–1.000) | 0.975 | 0.625 | 0.960 | 1.000 | 0.980 | 0.019 | 0.919 | 0.078 |
| Liver | 114 | 0.805 (0.726–0.879) | 0.711 | 0.711 | 0.938 | 0.152 | 0.822 | 0.160 | 0.220 | 0.081 |

Confusion matrices (TN, FP, FN, TP): heart 27/6/2/26, diabetes 82/18/28/26,
kidney 30/0/2/48, liver 5/28/5/76.

How to read these honestly:

* **Heart**: the test ROC-AUC (0.958) is higher than the CV estimate (0.892); with 61 test patients the CV figure is the more reliable estimate of future discrimination. ECE 0.097 only just meets the 0.10 criterion.
* **Diabetes**: decent ranking (AUC 0.81) but sensitivity at the 0.5 threshold is only 0.48 — many diabetic patients receive probabilities below 50%. This is why the app shows the probability and band rather than only the class.
* **Liver**: at the 0.5 threshold the model calls almost everyone positive (specificity 0.15); accuracy equals the majority-class baseline. The probabilities still rank patients better than chance (CV AUC 0.72) and are calibrated, so the module meets the pre-set rules, but the predicted class alone is close to uninformative. The ILPD dataset is known for weak separability and uncertain labels.
* **Kidney**: see §7.

## 6. Eligibility rules (fixed before training)

| Rule | Value |
|---|---|
| `available` requires CV **and** test ROC-AUC ≥ | 0.70 |
| below this on either → `unavailable` | 0.60 |
| integrity findings | reported as **data caveats** (shown in the app and docs); they do not change status |
| probability + risk band shown only if `available`, Brier skill score > 0 and ECE ≤ | 0.10 |

When probability is withheld the API returns `probability: null`, `risk_category: null`
and a `risk_unavailable_reason`. The class label is never converted into a
percentage, and a positive class is never mapped to HIGH.

**To enable probabilities for a withheld module** one would need: a dataset without
the integrity problems (or independent external data), a test set large enough for
a stable calibration estimate (several hundred patients), and ECE ≤ 0.10 with a
positive Brier skill score on that data.

## 7. Kidney dataset integrity

The integrity checks (`ml/evaluation/integrity.py`) found:

1. **Near-deterministic single features** — haemoglobin alone separates the classes with AUC 0.969 and packed cell volume with 0.952.
2. **Missingness predicts the label** — CKD records have on average 3.6 missing values versus 0.7 for non-CKD records; the count of missing values alone gives AUC 0.82. The two classes were evidently recorded differently, so a model can learn the collection process rather than the disease. (Imputation without missing-indicator columns was used to reduce, not remove, this effect.)
3. **Near-perfect separation** — every candidate reached CV ROC-AUC ≥ 0.977 and the held-out AUC is 1.000. On 400 records this is not a credible estimate of real-world performance.

No exact duplicates or conflicting labels were found, and the class labels match
UCI's published counts. The model meets the calibration criteria on held-out data
(ECE 0.078, Brier skill score 0.919), so it is served as an **available** module with
probability and risk band, like the others. The findings above are shown to users
as data caveats on the Model performance page: the near-perfect score reflects this
dataset and should be expected to drop substantially on patients from other sources.

(An earlier version of the project downgraded the module to "experimental" on these
findings; the project owner chose to present them as caveats instead. The
experimental code path is retained and tested.)

## 8. Risk bands

Applied by the shared service `app/services/risk.py` to calibrated probabilities only:

| Band | Probability |
|---|---|
| LOW | below 30% |
| MODERATE | 30% to below 70% |
| HIGH | 70% and above |

These cut-offs are **application-defined educational categories**, configurable via
`RISK_LOW_MAX` / `RISK_MODERATE_MAX`. They are not derived from clinical
guidelines and are not clinically approved. The predicted class uses a separate
0.5 decision threshold, so a MODERATE band can coincide with either class.

## 9. Explanations

For linear models the result lists up to five inputs with the largest
contribution to the log-odds relative to an average training patient
(coefficient × standardised value, averaged over the five calibration folds;
one-hot groups are centred). These are statistical associations inside the
model, not causes. Fields the user marked "not available" are excluded.

## 10. Limitations

* Small, old, single-centre datasets; populations are narrow (e.g. Pima: women of Pima heritage aged 21+; Cleveland: 1980s US cardiology referrals).
* No external validation; no fairness analysis across sex/age/ethnicity.
* Optional fields that the user marks unavailable are filled with training medians, which reduces reliability (the result says so).
* Not clinically validated. Do not use for diagnosis or treatment.
