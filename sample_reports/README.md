# Sample lab reports for Health-Link

16 demo documents, 4 per module, each as **PNG** and **PDF**. All patient names,
IDs and the laboratory are fictitious. Values come from real, de-identified
records of the public training datasets (record number printed at the bottom of
each report); two kidney reports have haemoglobin and packed cell volume adjusted
to land in the moderate band.

How to use: sign in → **Read a report** → choose the matching module → upload a
file → **Extract values** → **Continue** → **Get assessment**.

| Module | 01 | 02 | 03 | 04 |
|---|---|---|---|---|
| Heart | Low 7.0% | Moderate 44.6% | High 92.8% | Moderate 62.1% |
| Diabetes | Low 7.0% | Moderate 44.9% | High 92.2% | Moderate 62.1% |
| Kidney | Low 7.0% | Moderate 45.4% | High 93.8% | Moderate 63.0% |
| Liver | Moderate 37.7% | Moderate 45.0% | Moderate 62.1% | High 93.0% |

The liver model's lowest possible estimate is about 35%, so no liver report can
show LOW; report 01 is the lowest-scoring liver record in the dataset.

Percentages are from the models shipped with the project (scikit-learn 1.9.1).
After retraining on another library version they may move by a point or two;
`answer_key.csv` can be regenerated with `python scripts/generate_sample_reports.py`.

SAMPLE TEST DOCUMENTS — not real medical reports.
