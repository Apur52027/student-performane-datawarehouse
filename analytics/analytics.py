"""Run the named SQL queries from performance_queries.sql."""
import re
from functools import lru_cache
from pathlib import Path

import pandas as pd

from warehouse.database import get_connection

SQL_FILE = Path(__file__).with_name("performance_queries.sql")


@lru_cache(maxsize=1)
def load_queries():
    text = SQL_FILE.read_text(encoding="utf-8")
    parts = re.split(r"^--\s*name:\s*(\w+)\s*$", text, flags=re.M)
    queries = {}
    for name, body in zip(parts[1::2], parts[2::2]):
        sql = "\n".join(l for l in body.splitlines() if not l.strip().startswith("--"))
        queries[name] = sql.strip().rstrip(";")
    return queries


def _norm(value):
    return None if value in (None, "", "All") else value


def run_query(name, dept=None, semester=None):
    queries = load_queries()
    if name not in queries:
        raise KeyError(f"Unknown query '{name}'. Available: {sorted(queries)}")
    params = {"dept": _norm(dept), "semester": _norm(semester)}
    with get_connection(readonly=True) as conn:
        return pd.read_sql_query(queries[name], conn, params=params)


def get_kpis(dept=None, semester=None):
    df = run_query("kpi_summary", dept, semester)
    if df.empty or pd.isna(df.iloc[0]["total_enrollments"]):
        return {}
    row = df.iloc[0].to_dict()
    row["total_students"] = int(row["total_students"])
    row["total_enrollments"] = int(row["total_enrollments"])
    return row


def get_filter_options():
    with get_connection(readonly=True) as conn:
        depts = [r[0] for r in conn.execute(
            "SELECT dept_name FROM dim_department ORDER BY dept_name")]
        sems = [r[0] for r in conn.execute(
            "SELECT semester_name FROM dim_semester ORDER BY semester_order")]
    return depts, sems


def get_student_report(student_id):
    """All course results of one student (used for drill-down)."""
    with get_connection(readonly=True) as conn:
        return pd.read_sql_query(
            "SELECT semester, course_code, course_name, teacher_name, attendance_pct, "
            "total_marks, grade, grade_point FROM vw_student_performance "
            "WHERE student_id = ? ORDER BY academic_year, term",
            conn, params=(student_id,))
