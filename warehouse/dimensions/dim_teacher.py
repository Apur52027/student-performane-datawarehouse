"""dim_teacher - one row per teacher (home department attached)."""

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS dim_teacher (
    teacher_key  INTEGER PRIMARY KEY AUTOINCREMENT,
    teacher_name TEXT NOT NULL UNIQUE,
    dept_key     INTEGER NOT NULL REFERENCES dim_department(dept_key)
)
"""


def load(conn, df, dept_map):
    uniq = df.drop_duplicates(subset=["teacher_name"])[["teacher_name", "department"]]
    conn.executemany(
        "INSERT OR IGNORE INTO dim_teacher (teacher_name, dept_key) VALUES (?, ?)",
        [(r.teacher_name, dept_map[r.department]) for r in uniq.itertuples()],
    )
    rows = conn.execute("SELECT teacher_name, teacher_key FROM dim_teacher").fetchall()
    return {r[0]: r[1] for r in rows}
