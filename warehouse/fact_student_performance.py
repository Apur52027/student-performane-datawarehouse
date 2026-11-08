"""fact_student_performance - grain: one student x one course x one semester."""

VIEW_NAME = "vw_student_performance"

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS fact_student_performance (
    fact_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    student_key      INTEGER NOT NULL REFERENCES dim_student(student_key),
    course_key       INTEGER NOT NULL REFERENCES dim_course(course_key),
    teacher_key      INTEGER NOT NULL REFERENCES dim_teacher(teacher_key),
    dept_key         INTEGER NOT NULL REFERENCES dim_department(dept_key),
    semester_key     INTEGER NOT NULL REFERENCES dim_semester(semester_key),
    attendance_pct   REAL,
    study_hours      REAL,
    assignment_marks REAL,
    midterm_marks    REAL,
    final_marks      REAL,
    total_marks      REAL NOT NULL,
    grade            TEXT NOT NULL,
    grade_point      REAL NOT NULL,
    is_pass          INTEGER NOT NULL CHECK (is_pass IN (0, 1)),
    UNIQUE (student_key, course_key, semester_key)
)
"""

INDEX_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_fact_student  ON fact_student_performance(student_key)",
    "CREATE INDEX IF NOT EXISTS idx_fact_course   ON fact_student_performance(course_key)",
    "CREATE INDEX IF NOT EXISTS idx_fact_teacher  ON fact_student_performance(teacher_key)",
    "CREATE INDEX IF NOT EXISTS idx_fact_dept     ON fact_student_performance(dept_key)",
    "CREATE INDEX IF NOT EXISTS idx_fact_semester ON fact_student_performance(semester_key)",
]

CREATE_VIEW_SQL = f"""
CREATE VIEW IF NOT EXISTS {VIEW_NAME} AS
SELECT f.fact_id, st.student_id, st.student_name, st.gender,
       d.dept_name AS department, c.course_code, c.course_name, c.credit_hours,
       t.teacher_name, s.semester_name AS semester, s.academic_year, s.term,
       f.attendance_pct, f.study_hours, f.assignment_marks, f.midterm_marks,
       f.final_marks, f.total_marks, f.grade, f.grade_point, f.is_pass
FROM fact_student_performance f
JOIN dim_student    st ON st.student_key  = f.student_key
JOIN dim_course     c  ON c.course_key    = f.course_key
JOIN dim_teacher    t  ON t.teacher_key   = f.teacher_key
JOIN dim_department d  ON d.dept_key      = f.dept_key
JOIN dim_semester   s  ON s.semester_key  = f.semester_key
"""

_COLS = ("student_key", "course_key", "teacher_key", "dept_key", "semester_key",
         "attendance_pct", "study_hours", "assignment_marks", "midterm_marks",
         "final_marks", "total_marks", "grade", "grade_point", "is_pass")
_INT_COLS = {"student_key", "course_key", "teacher_key", "dept_key",
             "semester_key", "is_pass"}


def load(conn, df, maps):
    df = df.copy()
    df["student_key"] = df["student_id"].map(maps["student"])
    df["course_key"] = df["course_code"].map(maps["course"])
    df["teacher_key"] = df["teacher_name"].map(maps["teacher"])
    df["dept_key"] = df["department"].map(maps["department"])
    df["semester_key"] = df["semester"].map(maps["semester"])

    key_cols = ["student_key", "course_key", "teacher_key", "dept_key", "semester_key"]
    if df[key_cols].isna().any().any():
        raise ValueError("Surrogate key lookup failed - check dimension loading.")

    rows = []
    for rec in df.to_dict("records"):
        row = []
        for col in _COLS:
            val = rec[col]
            if val != val:            # NaN -> NULL
                val = None
            elif col in _INT_COLS:
                val = int(val)
            row.append(val)
        rows.append(tuple(row))

    conn.executemany(
        f"INSERT INTO fact_student_performance ({', '.join(_COLS)}) "
        f"VALUES ({', '.join('?' * len(_COLS))})",
        rows,
    )
    return len(rows)
