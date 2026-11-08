"""dim_student - one row per student (Type-1: latest values win)."""

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS dim_student (
    student_key  INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id   TEXT NOT NULL UNIQUE,
    student_name TEXT NOT NULL,
    gender       TEXT NOT NULL,
    dept_key     INTEGER NOT NULL REFERENCES dim_department(dept_key)
)
"""


def load(conn, df, dept_map):
    uniq = df.drop_duplicates(subset=["student_id"], keep="last")[
        ["student_id", "student_name", "gender", "department"]]
    conn.executemany(
        "INSERT OR IGNORE INTO dim_student "
        "(student_id, student_name, gender, dept_key) VALUES (?, ?, ?, ?)",
        [(r.student_id, r.student_name, r.gender, dept_map[r.department])
         for r in uniq.itertuples()],
    )
    rows = conn.execute("SELECT student_id, student_key FROM dim_student").fetchall()
    return {r[0]: r[1] for r in rows}
