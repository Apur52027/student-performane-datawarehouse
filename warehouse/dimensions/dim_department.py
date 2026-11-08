"""dim_department - one row per academic department."""

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS dim_department (
    dept_key  INTEGER PRIMARY KEY AUTOINCREMENT,
    dept_name TEXT NOT NULL UNIQUE
)
"""


def load(conn, df):
    names = sorted(df["department"].dropna().unique())
    conn.executemany(
        "INSERT OR IGNORE INTO dim_department (dept_name) VALUES (?)",
        [(n,) for n in names],
    )
    rows = conn.execute("SELECT dept_name, dept_key FROM dim_department").fetchall()
    return {r[0]: r[1] for r in rows}
