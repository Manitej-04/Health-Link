# Model Evaluation Report

Generated automatically by `python -m ml.training.train`. All figures are real outputs of the training run on the stated public datasets. They are **not** evidence of clinical validity.

| Module | Status | Algorithm | Test n | ROC-AUC (95% CI) | Accuracy | Precision | Recall | F1 | Brier | ECE | Probability shown |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Heart Disease | available | Logistic Regression | 61 | 0.958 (0.898–0.996) | 0.869 | 0.812 | 0.929 | 0.867 | 0.090 | 0.097 | yes |
| Diabetes | available | Logistic Regression | 154 | 0.812 (0.740–0.872) | 0.701 | 0.591 | 0.481 | 0.531 | 0.173 | 0.056 | yes |
| Chronic Kidney Disease | available | Logistic Regression | 80 | 1.000 (1.000–1.000) | 0.975 | 1.000 | 0.960 | 0.980 | 0.019 | 0.078 | yes |
| Liver Disease | available | Logistic Regression | 114 | 0.805 (0.726–0.879) | 0.711 | 0.731 | 0.938 | 0.822 | 0.160 | 0.081 | yes |

## Heart Disease

- Dataset: UCI Heart Disease (Cleveland subset, 303 patients) — 303 rows, 303 after de-duplication; train 242 / test 61
- Status: **available**
- Probability: Sigmoid-calibrated probabilities met the criteria on held-out data (ECE 0.097 <= 0.1, Brier skill score 0.639 > 0)
- Selected model: Logistic Regression + sigmoid calibration
- Held-out confusion matrix: TN 27, FP 6, FN 2, TP 26; specificity 0.818; Brier skill score 0.639; majority-class baseline accuracy 0.541

Cross-validation on the training split (mean ± sd):

| Algorithm | ROC-AUC | Accuracy | F1 | Recall | Precision |
|---|---|---|---|---|---|
| Logistic Regression **(selected)** | 0.892 ± 0.043 | 0.821 | 0.797 | 0.768 | 0.837 |
| Decision Tree | 0.811 ± 0.071 | 0.759 | 0.729 | 0.705 | 0.766 |
| K-Nearest Neighbors | 0.884 ± 0.045 | 0.800 | 0.768 | 0.729 | 0.818 |
| Support Vector Machine (RBF) | 0.884 ± 0.044 | 0.803 | 0.777 | 0.756 | 0.810 |
| Random Forest | 0.894 ± 0.042 | 0.813 | 0.789 | 0.771 | 0.816 |
| Gradient Boosting | 0.867 ± 0.044 | 0.780 | 0.758 | 0.759 | 0.761 |

Held-out test scores of every candidate (informational only — not used for selection):

| Algorithm | ROC-AUC | Accuracy | Precision | Recall | F1 |
|---|---|---|---|---|---|
| Logistic Regression | 0.958 | 0.869 | 0.812 | 0.929 | 0.867 |
| Decision Tree | 0.873 | 0.770 | 0.719 | 0.821 | 0.767 |
| K-Nearest Neighbors | 0.966 | 0.902 | 0.867 | 0.929 | 0.897 |
| Support Vector Machine (RBF) | 0.957 | 0.918 | 0.871 | 0.964 | 0.915 |
| Random Forest | 0.944 | 0.885 | 0.839 | 0.929 | 0.881 |
| Gradient Boosting | 0.963 | 0.902 | 0.867 | 0.929 | 0.897 |

Integrity checks: exact duplicates 0 (removed before split), conflicting-label duplicates 0, missingness AUC 0.505, strongest single-feature AUC ('thal', 0.766).

## Diabetes

- Dataset: Pima Indians Diabetes (768 female patients, age 21+) — 768 rows, 768 after de-duplication; train 614 / test 154
- Status: **available**
- Probability: Sigmoid-calibrated probabilities met the criteria on held-out data (ECE 0.056 <= 0.1, Brier skill score 0.239 > 0)
- Selected model: Logistic Regression + sigmoid calibration
- Held-out confusion matrix: TN 82, FP 18, FN 28, TP 26; specificity 0.820; Brier skill score 0.239; majority-class baseline accuracy 0.649

Cross-validation on the training split (mean ± sd):

| Algorithm | ROC-AUC | Accuracy | F1 | Recall | Precision |
|---|---|---|---|---|---|
| Logistic Regression **(selected)** | 0.842 ± 0.026 | 0.783 | 0.646 | 0.573 | 0.752 |
| Decision Tree | 0.778 ± 0.042 | 0.728 | 0.592 | 0.575 | 0.634 |
| K-Nearest Neighbors | 0.832 ± 0.040 | 0.757 | 0.618 | 0.564 | 0.696 |
| Support Vector Machine (RBF) | 0.832 ± 0.030 | 0.763 | 0.622 | 0.561 | 0.712 |
| Random Forest | 0.829 ± 0.039 | 0.756 | 0.620 | 0.572 | 0.686 |
| Gradient Boosting | 0.829 ± 0.028 | 0.757 | 0.617 | 0.567 | 0.690 |

Held-out test scores of every candidate (informational only — not used for selection):

| Algorithm | ROC-AUC | Accuracy | Precision | Recall | F1 |
|---|---|---|---|---|---|
| Logistic Regression | 0.813 | 0.708 | 0.600 | 0.500 | 0.545 |
| Decision Tree | 0.825 | 0.799 | 0.709 | 0.722 | 0.716 |
| K-Nearest Neighbors | 0.807 | 0.734 | 0.644 | 0.537 | 0.586 |
| Support Vector Machine (RBF) | 0.796 | 0.740 | 0.652 | 0.556 | 0.600 |
| Random Forest | 0.816 | 0.747 | 0.667 | 0.556 | 0.606 |
| Gradient Boosting | 0.813 | 0.721 | 0.622 | 0.519 | 0.566 |

Integrity checks: exact duplicates 0 (removed before split), conflicting-label duplicates 0, missingness AUC 0.528, strongest single-feature AUC ('glucose', 0.793).

## Chronic Kidney Disease

- Dataset: UCI Chronic Kidney Disease (400 patients) — 400 rows, 400 after de-duplication; train 320 / test 80
- Status: **available**
- Probability: Sigmoid-calibrated probabilities met the criteria on held-out data (ECE 0.078 <= 0.1, Brier skill score 0.919 > 0)
- Selected model: Logistic Regression + sigmoid calibration
- Held-out confusion matrix: TN 30, FP 0, FN 2, TP 48; specificity 1.000; Brier skill score 0.919; majority-class baseline accuracy 0.625

Cross-validation on the training split (mean ± sd):

| Algorithm | ROC-AUC | Accuracy | F1 | Recall | Precision |
|---|---|---|---|---|---|
| Logistic Regression **(selected)** | 1.000 ± 0.000 | 0.995 | 0.996 | 0.993 | 0.998 |
| Decision Tree | 0.977 ± 0.021 | 0.960 | 0.968 | 0.963 | 0.974 |
| K-Nearest Neighbors | 1.000 ± 0.001 | 0.953 | 0.960 | 0.925 | 1.000 |
| Support Vector Machine (RBF) | 1.000 ± 0.000 | 0.993 | 0.994 | 0.988 | 1.000 |
| Random Forest | 0.999 ± 0.002 | 0.991 | 0.993 | 0.995 | 0.990 |
| Gradient Boosting | 0.999 ± 0.002 | 0.985 | 0.988 | 0.992 | 0.985 |

Held-out test scores of every candidate (informational only — not used for selection):

| Algorithm | ROC-AUC | Accuracy | Precision | Recall | F1 |
|---|---|---|---|---|---|
| Logistic Regression | 1.000 | 0.988 | 1.000 | 0.980 | 0.990 |
| Decision Tree | 0.988 | 0.975 | 0.980 | 0.980 | 0.980 |
| K-Nearest Neighbors | 1.000 | 0.975 | 1.000 | 0.960 | 0.980 |
| Support Vector Machine (RBF) | 1.000 | 0.988 | 1.000 | 0.980 | 0.990 |
| Random Forest | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| Gradient Boosting | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |

Integrity checks: exact duplicates 0 (removed before split), conflicting-label duplicates 0, missingness AUC 0.824, strongest single-feature AUC ('hemo', 0.969).

Data caveats (integrity findings, reported but not used to downgrade the module):
- Single raw features separate the classes almost perfectly: hemo, pcv (AUC >= 0.95)
- The number of missing values per record predicts the label (AUC 0.824); records were likely collected differently for each class
- Held-out ROC-AUC 1.000 indicates near-perfect separation

## Liver Disease

- Dataset: Indian Liver Patient Dataset (583 patients) — 583 rows, 570 after de-duplication; train 456 / test 114
- Status: **available**
- Probability: Sigmoid-calibrated probabilities met the criteria on held-out data (ECE 0.081 <= 0.1, Brier skill score 0.220 > 0)
- Selected model: Logistic Regression + sigmoid calibration
- Held-out confusion matrix: TN 5, FP 28, FN 5, TP 76; specificity 0.152; Brier skill score 0.220; majority-class baseline accuracy 0.711

Cross-validation on the training split (mean ± sd):

| Algorithm | ROC-AUC | Accuracy | F1 | Recall | Precision |
|---|---|---|---|---|---|
| Logistic Regression **(selected)** | 0.721 ± 0.048 | 0.709 | 0.819 | 0.924 | 0.736 |
| Decision Tree | 0.649 ± 0.054 | 0.651 | 0.768 | 0.821 | 0.731 |
| K-Nearest Neighbors | 0.678 ± 0.054 | 0.691 | 0.802 | 0.878 | 0.739 |
| Support Vector Machine (RBF) | 0.630 ± 0.050 | 0.713 | 0.832 | 0.999 | 0.713 |
| Random Forest | 0.721 ± 0.044 | 0.695 | 0.803 | 0.875 | 0.743 |
| Gradient Boosting | 0.701 ± 0.048 | 0.702 | 0.807 | 0.878 | 0.748 |

Held-out test scores of every candidate (informational only — not used for selection):

| Algorithm | ROC-AUC | Accuracy | Precision | Recall | F1 |
|---|---|---|---|---|---|
| Logistic Regression | 0.803 | 0.711 | 0.745 | 0.901 | 0.816 |
| Decision Tree | 0.767 | 0.711 | 0.735 | 0.926 | 0.820 |
| K-Nearest Neighbors | 0.746 | 0.728 | 0.745 | 0.938 | 0.831 |
| Support Vector Machine (RBF) | 0.654 | 0.711 | 0.711 | 1.000 | 0.831 |
| Random Forest | 0.765 | 0.728 | 0.740 | 0.951 | 0.832 |
| Gradient Boosting | 0.781 | 0.711 | 0.731 | 0.938 | 0.822 |

Integrity checks: exact duplicates 0 (removed before split), conflicting-label duplicates 0, missingness AUC 0.504, strongest single-feature AUC ('total_bilirubin', 0.701).
