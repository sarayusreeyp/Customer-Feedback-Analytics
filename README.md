# Customer Feedback Analytics (CFA)

End-to-end feedback analytics workflow that integrates survey responses, product reviews, and customer support text to uncover recurring themes, detect sentiment shifts, and compute service action priorities.

---

## Architecture & Module Sequence

```
Module 1: Generators ──> Module 2: DB ──> Module 3: Validation ──> Module 4: Processing ──> Module 5: Analytics ──> Module 6: Evaluation
```

1. **`cfa.generators` (Module 1)**: Deterministic synthetic generation of Master Data (`Customer`, `Product`, `Channel`, `Survey`, `Theme`), Event Data (`Review`, `SurveyResponse`, `SupportTicket`, `SupportMessage`, `ActionItem`), and labelled anomalies with strict separation from clean data.
2. **`cfa.db` (Module 2)**: Relational SQLite schema managed with SQLAlchemy (primary keys, foreign keys, bridge tables, and composite indexes).
3. **`cfa.validation` (Module 3)**: Data quality gate asserting PK uniqueness, FK referential integrity, enum/pattern conformance, and fixed-seed reproducibility.
4. **`cfa.processing` (Module 4)**: NLP pipeline for batched sentiment inference and multi-class theme classification.
5. **`cfa.analytics` (Module 5)**: Time-series sentiment trend aggregation, Net Sentiment Score (NSS), inflection point detection, theme frequency distribution, and service priority scoring.
6. **`cfa.evaluation` (Module 6)**: Performance benchmarking (Precision, Recall, F1, Accuracy) evaluating predictions against isolated ground truth data.

---

## Directory Structure

```
Customer-Feedback-Analytics/
├── configs/
│   └── config.yaml              # Volume presets, seeds, and model configs
├── data/
│   ├── raw/                     # Raw incoming data (normal + injected anomalies without issue_type)
│   ├── validated/               # Validated clean datasets loaded into SQLite DB
│   ├── excluded_anomalies/      # Excluded anomaly records for validation verification
│   ├── ground_truth/            # Ground truth index and separate anomaly files with issue_type
│   ├── evaluation/              # Synthetic human-reviewed labeled benchmark dataset
│   ├── db/                      # SQLite database (feedback.db)
│   ├── schema.sql               # Standalone DDL schema
│   └── manifest.json            # Provenance manifest & SHA-256 checksums
├── reports/
│   ├── model_evaluation_report.csv # Precision/Recall/F1 metrics vs ground truth
│   ├── data_evaluation_report.csv  # Synthetic data evaluation audit (criteria a-g)
│   └── data_evaluation_report.md   # Markdown summary of data evaluation audit
├── final_outcomes/
│   ├── recurring_themes.csv        # Theme frequencies, counts & percentage share
│   ├── sentiment_shifts.csv        # Weekly sentiment breakdown & Net Sentiment Scores
│   ├── sentiment_shifts_lineage.csv# Traceability drilldown mapping trends to source records
│   └── service_priorities.csv      # Ranked action priorities by customer friction & urgency
├── docs/
│   ├── DATA_DICTIONARY.md          # Full data dictionary for all entities and fields
│   └── PROVENANCE.md               # Synthetic data provenance, licensing & lawful use statement
├── src/cfa/
│   ├── generators/              # Module 1: Data generators & raw validation gate
│   ├── db/                      # Module 2: DB schema, loader, queries
│   ├── validation/              # Module 3: Data quality audit checks
│   ├── processing/              # Module 4: Sentiment & theme pipelines
│   ├── analytics/               # Module 5: Trends & service priority scoring
│   └── evaluation/              # Module 6: Ground truth metrics & evaluation
├── tests/                       # Unit and integration test suite (28 tests)
├── pyproject.toml               # Package configuration
├── requirements.txt             # Project dependencies
└── README.md
```

---

## Data Folder Reference (`data/`)

All runtime data is written under `data/` by the pipeline. The directory is **never committed to version control** — it is regenerated on every run from the configured seed.

### `data/raw/`
Contains every CSV produced by **Module 1 (generators)**, including both normal records and injected anomaly records (without the `issue_type` label, so anomalies are indistinguishable from clean data at this stage). This represents the **unvalidated intake** layer.

| File | Description |
|:---|:---|
| `customers.csv` | Master customer records: ID, name, email, region, segment, lifecycle state |
| `products.csv` | Fixed 20-product catalogue: product ID, name, category |
| `channels.csv` | Fixed 6-channel list: channel ID, name, type (digital/voice/physical) |
| `themes.csv` | Fixed 15-theme feedback taxonomy: theme ID, name, description |
| `sentiment_labels.csv` | Sentiment label master: SENT-01/02/03, polarity (−1/0/+1) |
| `surveys.csv` | Survey definitions: survey ID, title, type (NPS/CSAT/CES/…), product, channel, date range |
| `reviews.csv` | Product reviews (normal + unlabelled anomalies): star rating 1–5, sentiment, language, ambiguity flag |
| `survey_responses.csv` | Survey responses (normal + unlabelled anomalies): rating 1–10, response text, language |
| `support_tickets.csv` | Support tickets: ticket ID, customer, channel, status, creation & resolution timestamps |
| `support_messages.csv` | Support conversation messages (normal + unlabelled anomalies): sender type, text, language |
| `review_themes.csv` | Bridge: review ↔ theme assignments (1 primary + 0–2 secondary themes per review) |
| `response_themes.csv` | Bridge: survey response ↔ theme assignments |
| `message_themes.csv` | Bridge: support message ↔ theme assignments |
| `action_items.csv` | Derived action items: one per theme whose mention count ≥ threshold, with priority |

### `data/validated/`
Contains the **same file set as `raw/`** but with anomaly records stripped out by the Module 1 validation gate. These CSVs are the direct source for SQLite ingestion (Module 2). Only records that pass all four validation rules (no PII, no TEST marker, no label contradiction, no duplicate) are present here.

| File | Description |
|:---|:---|
| *(same filenames as `raw/`)* | Clean records only — anomaly records removed by `validate_reviews()`, `validate_survey_responses()`, `validate_support_messages()`, and `validate_theme_bridge()` |

### `data/excluded_anomalies/`
Contains every record **rejected** by the validation gate, with an explicit `exclusion_reason` column explaining why each record was quarantined. Used to verify the gate's detection recall in Module 6.

| File | Description |
|:---|:---|
| `excluded_reviews.csv` | Rejected review records with `exclusion_reason` column |
| `excluded_responses.csv` | Rejected survey response records with `exclusion_reason` |
| `excluded_messages.csv` | Rejected support message records with `exclusion_reason` |
| `all_excluded_anomalies.csv` | Union of all three exclusion sets, with a common `entity_type` and `record_id` column for cross-entity analysis |

Possible `exclusion_reason` values: `pii_leak`, `test_label_in_input`, `label_contradiction`, `duplicate_submission`, `out_of_taxonomy_theme`.

### `data/ground_truth/`
Isolated reference files that contain the **true labels** for every injected anomaly. These files are **never loaded into the SQLite database** and serve exclusively as the evaluation benchmark for anomaly detection recall (Module 6). The separation guarantees zero feature leakage.

| File | Description |
|:---|:---|
| `reviews_anomalies.csv` | Anomalous review records **with** `issue_type` column (ground truth label) |
| `responses_anomalies.csv` | Anomalous survey response records with `issue_type` |
| `messages_anomalies.csv` | Anomalous support message records with `issue_type` |
| `ground_truth.csv` | Combined index: `record_id`, `entity_type`, `issue_type`, `correct_sentiment_label`, `correct_theme_id`, `notes` — one row per injected anomaly |

Injected anomaly types (`issue_type` values): `label_contradiction`, `duplicate_response`, `pii_leak`, `out_of_taxonomy_theme`, `test_label_in_input`.

### `data/evaluation/`
A synthetic **human-reviewed labeled benchmark** dataset sampled from validated reviews, used by Module 6 to compute model performance metrics (accuracy, precision, recall, F1) against predictions written by Module 4.

| File | Description |
|:---|:---|
| `human_reviewed_eval.csv` | Up to 300 sampled records with fields: `sample_id`, `source_record_id`, `entity_type`, `text`, `language`, `is_ambiguous`, `ground_truth_sentiment`, `ground_truth_theme_id`, `review_status`, `verified_by`, `confidence` |

### `data/db/`

| File | Description |
|:---|:---|
| `feedback.db` | SQLite relational database created and seeded by Module 2. Contains all 11 entity tables, 3 bridge tables, and a `status_history` table. Module 4 adds `predicted_sentiment` and `predicted_theme` columns in-place. Module 5 syncs `action_items` and `status_history` after analytics. |

### `data/schema.sql`
A standalone **DDL script** exported by Module 2 (`export_schema_sql()`). Contains `CREATE TABLE` statements for every table in `feedback.db`, including primary keys, foreign keys, and composite indexes. Can be used to inspect or recreate the schema without a running Python environment.

### `data/manifest.json`
A **provenance manifest** written at the end of Module 1. Records:
- `generated_at`: ISO 8601 timestamp of the generation run
- `seed`: the random seed used
- `scale`: `starter` or `full`
- `files`: for every output CSV — `rows` (row count), `sha256` (first 16 hex chars of SHA-256), `relative_path`

Used by Module 6 criterion **(g)** to verify reproducibility documentation.

---

## Quickstart & Execution Guide

### 1. Installation
```powershell
pip install -r requirements.txt
pip install -e .
```

### 2. Run the Entire End-to-End Workflow in One Command

To run with the complete submission benchmark volume (**50,000 reviews/responses and 20,000 support messages** as specified in the problem statement):
```powershell
python main.py --scale full --seed 20261022
```

For fast local testing and rapid CI verification, you can run the lighter starter preset:
```powershell
python main.py --scale starter --seed 20261022
```

This automatically runs all 6 steps in sequence:
1. `cfa.generators`: Produces synthetic datasets (`data/raw/`), defect datasets (`data/anomalies/`), and `data/ground_truth/ground_truth.csv`, generating `data/manifest.json`.
2. `cfa.db`: Loads all tables into SQLite (`data/db/feedback.db`) with foreign key constraints, and exports `data/schema.sql`.
3. `cfa.validation`: Audits primary key uniqueness, foreign key integrity, allowed enums, derived rules reconciliation, and deterministic reproducibility.
4. `cfa.processing`: Executes batched sentiment analysis and theme classification inference.
5. `cfa.analytics`: Computes Net Sentiment Scores, sentiment trends, inflection points, and priority scores, exporting to `reports/`.
6. `cfa.evaluation`: Evaluates accuracy, precision, recall, and F1 across clean and anomaly subsets, exporting to `reports/evaluation_results.csv`.

---

### 3. Generated Deliverables & Reports

#### Quality & Evaluation Reports (`reports/`)
- `reports/model_evaluation_report.csv`: Performance metrics (Accuracy, Precision, Recall, F1) across clean baseline and all anomaly subsets.
- `reports/data_evaluation_report.csv` & `.md`: Verification of data against project rubric criteria (a) through (g).

#### Business Outcomes (`final_outcomes/`)
- `final_outcomes/recurring_themes.csv`: Mentions per theme across reviews, surveys, and messages, with percentage shares.
- `final_outcomes/sentiment_shifts.csv`: Weekly and monthly sentiment distributions, Net Sentiment Scores, inflection points, and sample source record IDs.
- `final_outcomes/sentiment_shifts_lineage.csv`: Full record-level lineage mapping every time window directly to constituent review, survey response, and support message IDs.
- `final_outcomes/service_priorities.csv`: Ranked service priorities by customer friction, negative sentiment ratio, and urgency.
- `final_outcomes/analytics_summary.md`: Executive summary and prioritized action recommendations report.

---

### [Link to the Prompt History Log, AI Usage, Reviewer Guide](https://drive.google.com/file/d/1Z-hBxamMWKmj7ai7SFNCa9jxR2SznmPH/view?usp=sharing)

### 4. Run Test Suite
```powershell
python -m pytest tests/ -v
```
Output: **34 passed in ~13s**.
