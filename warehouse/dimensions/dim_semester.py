"""dim_semester - one row per academic term, e.g. 'Spring 2024'."""

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS dim_semester (
    semester_key   INTEGER PRIMARY KEY AUTOINCREMENT,
    semester_name  TEXT NOT NULL UNIQUE,
    academic_year  INTEGER NOT NULL,
    term           TEXT NOT NULL,
    semester_order INTEGER NOT NULL
)
"""

TERM_ORDER = {"Spring": 1, "Summer": 2, "Fall": 3}


def load(conn, df):
    rows = []
    for name in sorted(df["semester"].dropna().unique()):
        term, year = name.split()
        rows.append((name, int(year), term, int(year) * 10 + TERM_ORDER[term]))
    conn.executemany(
        "INSERT OR IGNORE INTO dim_semester "
        "(semester_name, academic_year, term, semester_order) VALUES (?, ?, ?, ?)",
        rows,
    )
    res = conn.execute("SELECT semester_name, semester_key FROM dim_semester").fetchall()
    return {r[0]: r[1] for r in res}
