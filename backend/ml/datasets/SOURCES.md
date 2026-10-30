# Dataset sources and verification

All four datasets are public and widely used for research and teaching. The
official UCI Machine Learning Repository host (`archive.ics.uci.edu`) was not
reachable from the build environment, so the files were obtained from public
mirrors and **verified against the statistics UCI publishes** for each
dataset. The automated test `tests/test_ml.py::test_dataset_matches_published_statistics`
re-checks row counts and class counts on every test run.

If you prefer to use the official files, download them from the links below,
convert them to the formats described, and retrain (`python -m ml.training.train`).

| File (in `raw/`) | Dataset | Official source | Mirror used | Verification |
|---|---|---|---|---|
| `heart_cleveland.csv` | UCI Heart Disease — Cleveland subset (Detrano et al., 1989) | https://archive.ics.uci.edu/dataset/45/heart+disease | `heart_disease_cl` from the CRAN R package **ucidata** (J. Balamuta), github.com/coatless/ucidata, which reads `processed.cleveland.data` verbatim; factor labels mapped back to the original UCI integer codes | 303 rows; `num` distribution 164/55/36/35/13 and 4 missing `ca` + 2 missing `thal`, identical to UCI |
| `pima_diabetes.csv` | Pima Indians Diabetes (Smith et al., 1988; NIDDK) | Originally UCI; https://www.kaggle.com/datasets/uciml/pima-indians-diabetes-database | github.com/jbrownlee/Datasets `pima-indians-diabetes.data.csv` | 768 rows, 500 negative / 268 positive |
| `kidney_disease.csv` | UCI Chronic Kidney Disease (Rubini, Soundarapandian & Eswaran, 2015) | https://archive.ics.uci.edu/dataset/336/chronic+kidney+disease | github.com/ArjunAnil2000/Chronic-Kidney-Disease-dataset (`kidney_disease.csv`, the common CSV export of the UCI ARFF) | 400 rows, 250 ckd / 150 notckd; cross-checked cell-by-cell against a second independent mirror (github.com/Livruen/chronic-kidney-disease) — identical values |
| `ilpd.csv` | ILPD — Indian Liver Patient Dataset (Ramana, Babu & Venkateswarlu, 2012) | https://archive.ics.uci.edu/dataset/225/ilpd+indian+liver+patient+dataset | github.com/mikeizbicki/datasets `csv/uci/Indian Liver Patient Dataset (ILPD).csv` | 583 rows, 416 liver / 167 non-liver patients, 441 male / 142 female, 4 missing A/G ratio — identical to UCI; matches a second mirror byte-for-byte in values |

SHA-256 of the files used to train the shipped models:

```
68b13ff5bc336b0b60bd026879a8e6fb716b2bd008f3b1ea6ada30a5549c54de  heart_cleveland.csv
6bfe5d0f379d17a0e0819b996407e3c09bf80febd4287f2ed212190dfff154af  pima_diabetes.csv
aaeb0712557ec913a61400c216b45b02cc3d0ff0ad89d3ce3112960c7271f3bf  kidney_disease.csv
84feac16488de5cf89bd22bd802c77f25841fe93e9ddd32355683e94d46c3425  ilpd.csv
```

## Licences / usage

* UCI datasets added since 2023 carry CC BY 4.0; older UCI datasets are provided
  for research and education with a request to cite the donors. Cite the
  original papers above in your project report.
* The Pima dataset originates from the US National Institute of Diabetes and
  Digestive and Kidney Diseases and is distributed for research use.
* None of these datasets may be used to make clinical decisions.

## Expected formats (if you replace a file)

* `heart_cleveland.csv` — header row; columns `age,sex,cp,trestbps,chol,fbs,restecg,thalach,exang,oldpeak,slope,ca,thal,num`; UCI integer codes; empty cells for missing.
* `pima_diabetes.csv` — no header; 9 columns in UCI order (pregnancies … age, outcome).
* `kidney_disease.csv` — header row with `id` and the 24 UCI attribute abbreviations plus `classification`; text values as in UCI (`yes/no`, `normal/abnormal`, …).
* `ilpd.csv` — no header; 11 columns in UCI order; gender as `Male`/`Female`; selector 1 = liver patient, 2 = not.
