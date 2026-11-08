# DialectMood AI + Student Performance Data Warehouse

One Streamlit project with two parts:

1. **DialectMood AI** – Bangla dialect (Dinajpur / Rangpur) + sentiment analysis, a dialect-aware **Mood Companion chatbot** with memory and a safety layer, and a personal journal.
2. **Student Performance Data Warehouse** – ETL → star schema (SQLite) → SQL analytics → dashboard → **Data Assistant chatbot** (ask questions in Bangla / Banglish / English).

## Run

```bash
python -m venv venv && source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                  # put your GROQ_API_KEY inside
streamlit run app.py
```

The warehouse is built automatically on first visit to **DW Dashboard**. Manual build:

```bash
python data/generate_data.py    # (optional) regenerate synthetic CSV
python -m etl.load              # extract -> transform -> load
```

No API key? Everything still works: sentiment falls back to a lexicon, the Data Assistant to
built-in queries. Only the Mood Chat and LLM dialect fallback need the key.

## Structure

```
app.py  auth.py  database.py  chat_memory.py  chatbot_service.py  sentiment_service.py  compat.py
data/        student_performance.csv, generate_data.py
etl/         extract.py  transform.py  load.py
warehouse/   database.py  fact_student_performance.py  dimensions/dim_*.py
analytics/   performance_queries.sql  analytics.py  data_chatbot.py
dashboard/   dashboard.py
dialect/     dialect_service.py  llm.py
vocabulary/  north_bengal_shared.txt  rangpur.txt  dinajpur.txt
```

## Warehouse design

```
 dim_department   dim_semester
        \            /
 dim_student - fact_student_performance - dim_course
                    |
               dim_teacher
```
Grain: one student × one course × one semester. Grading: Bangladesh 4.0 scale (A+ ≥ 80 … D ≥ 40, F < 40).
Marks: assignment 20 + midterm 30 + final 50 = 100. CGPA is credit-weighted.

ETL cleaning: trims text, standardises gender/department/semester, drops rows with missing keys or marks,
removes duplicates, clips values to valid ranges, imputes missing attendance/study hours with the course median.

## Data Assistant safety

LLM-written SQL is validated (single `SELECT`/`WITH`, no comments, no write keywords), executed on a
**read-only** connection with a SQLite authorizer that only allows the warehouse tables, and capped at 200 rows.

## Bugs fixed in the original code

| Problem | Fix |
|---|---|
| `sentiment_service.py` was imported but missing → app crashed | Written (LLM + lexicon fallback, 4 classes) |
| Flat imports (`from llm import …`) vs the folder layout; `chart_memory`/`Chartbot_service` naming | Proper packages; files named `chat_memory.py`, `chatbot_service.py` |
| Broken Bangla strings (`মইু`, `দঃুখিত`, `ত োমার`, `বেচেঁ`) | Re-typed with correct Unicode |
| `has_recent_crisis_context()` never used | Now adds a safety directive for follow-ups like “yes” |
| Substring keyword matching (`মা` matched `মাস`, `want to die` matched `want to diet`) | Word-boundary matching |
| Chatbot dialect detection used a separate hard-coded list | Uses the shared vocabulary files |
| Summaries re-generated on almost every message | Only complete chunks are summarised (cached) |
| SQLite connections never closed | Context managers that commit/rollback/close |
| English text sent to the dialect LLM | Returns “Other/Uncertain” without an LLM call |
| `use_container_width` removed in new Streamlit | `compat.stretch()` works on old and new versions |
| Crisis text could be labelled Neutral in sentiment | Forced to Negative + safety suggestion |

## Notes
- The vocabulary files are **starter lists** – extend/validate them with native speakers; detection quality depends on them.
- Mood-related outputs are not clinical assessments. Bangladesh emergency number used in safety replies: **999**.
- The CSV is synthetic demo data; replace it with real data using the same column names (see `etl/transform.py`).
