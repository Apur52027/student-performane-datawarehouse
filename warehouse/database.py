"""Warehouse connection helpers (SQLite star schema)."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from warehouse.dimensions import (
    dim_department, dim_teacher, dim_course, dim_semester, dim_student,
)
from warehouse import fact_student_performance as fact

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "student_dw.db"

ALL_TABLES = [
    "dim_department", "dim_teacher", "dim_course",
    "dim_semester", "dim_student", "fact_student_performance",
]
ALLOWED_OBJECTS = ALL_TABLES + ["vw_student_performance"]


@contextmanager
def get_connection(readonly=False):
    """Yield a connection. Commits on success and always closes."""
    if readonly:
        conn = sqlite3.connect(f"{DB_PATH.as_uri()}?mode=ro", uri=True)
    else:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_warehouse(reset=False):
    """Create all dimension + fact tables (and the flat view)."""
    with get_connection() as conn:
        if reset:
            conn.execute(f"DROP VIEW IF EXISTS {fact.VIEW_NAME}")
            for table in reversed(ALL_TABLES):
                conn.execute(f"DROP TABLE IF EXISTS {table}")
        for module in (dim_department, dim_teacher, dim_course,
                       dim_semester, dim_student):
            conn.execute(module.CREATE_SQL)
        conn.execute(fact.CREATE_SQL)
        for stmt in fact.INDEX_SQL:
            conn.execute(stmt)
        conn.execute(fact.CREATE_VIEW_SQL)


def table_counts():
    counts = {}
    with get_connection() as conn:
        for table in ALL_TABLES:
            try:
                counts[table] = conn.execute(
                    f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            except sqlite3.OperationalError:
                counts[table] = 0
    return counts


def warehouse_is_loaded():
    if not DB_PATH.exists():
        return False
    return table_counts().get("fact_student_performance", 0) > 0
