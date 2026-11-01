# System & Model Evaluation Report

**Evaluated on Human-Reviewed Benchmark:** `human_reviewed_eval.csv` (300 verified records)

### 1. Model Performance (Sentiment & Multi-Label Theme Classification)

| Evaluation Subset | Samples | Sentiment Accuracy | Sentiment Precision (macro) | Sentiment Recall (macro) | Sentiment Macro-F1 | Theme Precision (multi-label) | Theme Recall (multi-label) | Theme Macro-F1 | Theme Micro-F1 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **all_human_reviewed** | 300 | 0.6533 | 0.7017 | 0.6551 | 0.6617 | 0.9111 | 0.3540 | 0.4624 | 0.5028 |
| **clear_records** | 289 | 0.6609 | 0.7258 | 0.6622 | 0.6725 | 0.9278 | 0.3677 | 0.4776 | 0.5183 |
| **ambiguous_or_sarcastic** | 11 | 0.4545 | 0.1515 | 0.3333 | 0.2083 | 0.0667 | 0.0389 | 0.0489 | 0.1176 |
| **english_language** | 288 | 0.6562 | 0.7013 | 0.6576 | 0.6649 | 0.9115 | 0.3680 | 0.4772 | 0.5160 |
| **multilingual** | 12 | 0.5833 | 0.7619 | 0.6667 | 0.5926 | 0.0222 | 0.0667 | 0.0333 | 0.2105 |

---

### 2. Validation Gate Anomaly Detection & Quarantine Recall

| Injected Anomaly Type | Injected Volume | Quarantined By Gate | Detection Recall |
| :--- | :---: | :---: | :---: |
| duplicate_response | 300 | 300 | 100.0% |
| label_contradiction | 300 | 300 | 100.0% |
| out_of_taxonomy_theme | 300 | 300 | 100.0% |
| pii_leak | 300 | 300 | 100.0% |
| test_label_in_input | 300 | 300 | 100.0% |
| **OVERALL** | 1,500 | 1,500 | **100.0%** |
