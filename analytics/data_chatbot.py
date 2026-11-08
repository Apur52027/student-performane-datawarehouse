"""Data Assistant - ask questions about the warehouse in Bangla / Banglish / English.

Pipeline:  question -> LLM writes SQL -> validated + run READ-ONLY -> LLM explains.
If the LLM is unavailable (no API key / offline) a rule-based fallback answers
common questions using the pre-written queries in performance_queries.sql.
"""
import json
import re
import sqlite3

import pandas as pd

from analytics.analytics import run_query
from warehouse.database import ALLOWED_OBJECTS, get_connection

MAX_ROWS = 200

SCHEMA_DESCRIPTION = """
SQLite star schema (student performance warehouse).

VIEW vw_student_performance  -- flat, PREFER THIS for most questions
  student_id, student_name, gender, department, course_code, course_name,
  credit_hours, teacher_name, semester (e.g. 'Spring 2024'), academic_year,
  term ('Spring'|'Summer'|'Fall'), attendance_pct (0-100), study_hours (per week),
  assignment_marks (/20), midterm_marks (/30), final_marks (/50),
  total_marks (/100), grade ('A+','A','A-','B+','B','B-','C+','C','D','F'),
  grade_point (0-4), is_pass (1 pass, 0 fail)

TABLES: fact_student_performance(student_key, course_key, teacher_key, dept_key,
  semester_key, attendance_pct, study_hours, assignment_marks, midterm_marks,
  final_marks, total_marks, grade, grade_point, is_pass)
  dim_student(student_key, student_id, student_name, gender, dept_key)
  dim_course(course_key, course_code, course_name, credit_hours, dept_key)
  dim_teacher(teacher_key, teacher_name, dept_key)
  dim_department(dept_key, dept_name)   -- 'CSE','EEE','BBA','English','Mathematics'
  dim_semester(semester_key, semester_name, academic_year, term, semester_order)

Notes: CGPA = SUM(grade_point*credit_hours)/SUM(credit_hours).
Pass rate % = 100.0*SUM(is_pass)/COUNT(*).
"""

SQL_SYSTEM_PROMPT = f"""You are a careful SQL analyst for a university student performance warehouse.
{SCHEMA_DESCRIPTION}
RULES:
- Write ONE read-only SQLite SELECT (or WITH ... SELECT). Never modify data.
- Use only the tables/view above. Do not invent columns.
- Use ROUND(..., 2) for averages. Add ORDER BY and LIMIT (max {MAX_ROWS}) where sensible.
- Text filters: use exact values from the schema notes; prefer LIKE for names.
- If the question cannot be answered from this data, return {{"sql": "", "reason": "<short reason>"}}.
Return ONLY JSON: {{"sql": "SELECT ...", "reason": ""}}"""

ANSWER_SYSTEM_PROMPT = """You are a friendly data assistant for a university dashboard.
You are given the user's question, the SQL that was run and its result rows.
- Answer in the SAME language/script as the question (Bangla script -> Bangla,
  Banglish -> Banglish, English -> English).
- Be concise (2-5 sentences). Mention the key numbers. Never invent numbers
  that are not in the result. If the result is empty, say no matching data was found."""

FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|replace|attach|detach|pragma|"
    r"vacuum|reindex|truncate|grant|revoke|load_extension)\b", re.I)


# --------------------------------------------------------------------------
# SQL safety
# --------------------------------------------------------------------------
def validate_sql(sql):
    """Return cleaned SQL or raise ValueError."""
    sql = (sql or "").strip().rstrip(";").strip()
    if not sql:
        raise ValueError("Empty SQL.")
    if ";" in sql:
        raise ValueError("Only a single statement is allowed.")
    if "--" in sql or "/*" in sql:
        raise ValueError("SQL comments are not allowed.")
    if not re.match(r"^(select|with)\b", sql, re.I):
        raise ValueError("Only SELECT queries are allowed.")
    if FORBIDDEN.search(sql):
        raise ValueError("Query contains a forbidden keyword.")
    return sql


def _authorizer(action, arg1, arg2, dbname, source):
    allowed_actions = {
        sqlite3.SQLITE_SELECT,
        sqlite3.SQLITE_FUNCTION,
        getattr(sqlite3, "SQLITE_RECURSIVE", 33),
    }
    if action in allowed_actions:
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_READ and arg1 in ALLOWED_OBJECTS:
        return sqlite3.SQLITE_OK
    return sqlite3.SQLITE_DENY


def execute_readonly(sql):
    """Validate and run SQL on a read-only connection with an authorizer."""
    sql = validate_sql(sql)
    wrapped = f"SELECT * FROM ({sql}) LIMIT {MAX_ROWS}"
    with get_connection(readonly=True) as conn:
        conn.set_authorizer(_authorizer)
        try:
            return sql, pd.read_sql_query(wrapped, conn)
        finally:
            conn.set_authorizer(None)


# --------------------------------------------------------------------------
# LLM helpers (imported lazily so the app still works without LangChain)
# --------------------------------------------------------------------------
def _llm_text(system, human, temperature=0.1):
    from langchain_core.messages import SystemMessage, HumanMessage
    from dialect.llm import get_llm
    response = get_llm(temperature=temperature).invoke(
        [SystemMessage(content=system), HumanMessage(content=human)])
    content = response.content
    if isinstance(content, list):
        content = "".join(i.get("text", "") if isinstance(i, dict) else str(i)
                          for i in content)
    return str(content).strip()


def _parse_json(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("LLM did not return JSON.")
    return json.loads(text[start:end + 1])


def _history_text(history, limit=4):
    lines = []
    for m in (history or [])[-limit * 2:]:
        if m.get("role") == "user":
            lines.append(f"User: {m.get('content', '')}")
    return "\n".join(lines)


def generate_sql(question, history=None, error_hint=""):
    prompt = f"Earlier user questions (context):\n{_history_text(history)}\n\n"
    prompt += f"Question: {question}"
    if error_hint:
        prompt += f"\n\nYour previous SQL failed with: {error_hint}\nFix it."
    data = _parse_json(_llm_text(SQL_SYSTEM_PROMPT, prompt))
    return (data.get("sql") or "").strip(), data.get("reason", "")


def explain_result(question, sql, df):
    preview = df.head(25).to_csv(index=False)
    return _llm_text(
        ANSWER_SYSTEM_PROMPT,
        f"Question: {question}\n\nSQL:\n{sql}\n\nResult ({len(df)} rows, first 25):\n{preview}",
        temperature=0.3,
    )


# --------------------------------------------------------------------------
# Rule-based fallback
# --------------------------------------------------------------------------
INTENTS = [
    ("at_risk_students", ["risk", "weak", "struggl", "ঝুঁকি", "দুর্বল", "ফেল করছে"]),
    ("teacher_performance", ["teacher", "faculty", "শিক্ষক", "স্যার", "ম্যাডাম"]),
    ("course_difficulty", ["course", "subject", "difficult", "hard", "কোর্স", "বিষয়", "কঠিন"]),
    ("top_students", ["top", "best", "topper", "cgpa", "সেরা", "টপ", "ভালো ছাত্র", "merit"]),
    ("attendance_impact", ["attendance", "উপস্থিতি", "হাজিরা"]),
    ("study_hours_impact", ["study", "hours", "পড়াশোনা", "পড়ার সময়"]),
    ("gender_comparison", ["gender", "male", "female", "ছেলে", "মেয়ে", "boy", "girl"]),
    ("grade_distribution", ["grade", "গ্রেড", "distribution"]),
    ("semester_trend", ["trend", "semester", "সেমিস্টার", "progress", "improv"]),
    ("dept_performance", ["department", "dept", "বিভাগ", "cse", "eee", "bba"]),
]


def rule_based_answer(question):
    q = question.lower()
    name = "kpi_summary"
    for intent, words in INTENTS:
        if any(w in q for w in words):
            name = intent
            break
    dept = next((d for d in ("CSE", "EEE", "BBA", "English", "Mathematics")
                 if d.lower() in q), None)
    df = run_query(name, dept=dept)
    is_bn = bool(re.search(r"[\u0980-\u09FF]", question))
    if is_bn:
        text = f"এখানে '{name}' বিশ্লেষণের ফলাফল দেওয়া হলো ({len(df)}টি সারি)। " \
               "(AI মডেল বন্ধ থাকায় সাধারণ নিয়মভিত্তিক উত্তর দেওয়া হয়েছে।)"
    else:
        text = f"Here is the '{name}' result ({len(df)} rows). " \
               "(Rule-based answer - the AI model is not available right now.)"
    return text, f"-- predefined query: {name}", df


# --------------------------------------------------------------------------
# Public entry point
# --------------------------------------------------------------------------
def ask_warehouse(question, history=None):
    """Return dict(answer, sql, data, method, error)."""
    question = (question or "").strip()
    if not question:
        return {"answer": "Please ask a question.", "sql": "", "data": None,
                "method": "none", "error": None}

    error_hint, last_error = "", None
    for _attempt in range(2):
        try:
            sql, reason = generate_sql(question, history, error_hint)
            if not sql:
                return {"answer": reason or "This question cannot be answered from the data.",
                        "sql": "", "data": None, "method": "llm", "error": None}
            sql, df = execute_readonly(sql)
            try:
                answer = explain_result(question, sql, df)
            except Exception:
                answer = f"Query returned {len(df)} rows."
            return {"answer": answer, "sql": sql, "data": df,
                    "method": "llm", "error": None}
        except (ValueError, sqlite3.Error, pd.errors.DatabaseError) as err:
            error_hint, last_error = str(err), str(err)       # let the LLM retry once
        except Exception as err:                              # no key / network / import
            last_error = str(err)
            break

    try:
        answer, sql, df = rule_based_answer(question)
        return {"answer": answer, "sql": sql, "data": df,
                "method": "rule-based", "error": last_error}
    except Exception as err:
        return {"answer": "Sorry, I could not answer that right now.",
                "sql": "", "data": None, "method": "none", "error": str(err)}
