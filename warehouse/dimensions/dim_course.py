"""dim_course - one row per course."""

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS dim_course (
    course_key   INTEGER PRIMARY KEY AUTOINCREMENT,
    course_code  TEXT NOT NULL UNIQUE,
    course_name  TEXT NOT NULL,
    credit_hours REAL NOT NULL DEFAULT 3,
    dept_key     INTEGER NOT NULL REFERENCES dim_department(dept_key)
)
"""


def load(conn, df, dept_map):
    uniq = df.drop_duplicates(subset=["course_code"])[
        ["course_code", "course_name", "credit_hours", "department"]]
    conn.executemany(
        "INSERT OR IGNORE INTO dim_course "
        "(course_code, course_name, credit_hours, dept_key) VALUES (?, ?, ?, ?)",
        [(r.course_code, r.course_name, float(r.credit_hours), dept_map[r.department])
         for r in uniq.itertuples()],
    )
    rows = conn.execute("SELECT course_code, course_key FROM dim_course").fetchall()
    return {r[0]: r[1] for r in rows}
