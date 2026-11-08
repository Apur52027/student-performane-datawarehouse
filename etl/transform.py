"""TRANSFORM - clean, validate and enrich the raw data."""
import re

import pandas as pd

REQUIRED_COLUMNS = [
    "student_id", "student_name", "gender", "department", "course_code",
    "course_name", "credit_hours", "teacher_name", "semester", "attendance_pct",
    "study_hours", "assignment_marks", "midterm_marks", "final_marks",
]
TEXT_COLUMNS = ["student_id", "student_name", "gender", "department",
                "course_code", "course_name", "teacher_name", "semester"]
NUMERIC_COLUMNS = ["credit_hours", "attendance_pct", "study_hours",
                   "assignment_marks", "midterm_marks", "final_marks"]
MARK_LIMITS = {"assignment_marks": 20, "midterm_marks": 30, "final_marks": 50}
SEMESTER_RE = re.compile(r"^(Spring|Summer|Fall)\s+(\d{4})$", re.I)

# Bangladesh 4.0 grading scale
GRADE_SCALE = [(80, "A+", 4.00), (75, "A", 3.75), (70, "A-", 3.50),
               (65, "B+", 3.25), (60, "B", 3.00), (55, "B-", 2.75),
               (50, "C+", 2.50), (45, "C", 2.25), (40, "D", 2.00)]
GENDER_MAP = {"m": "Male", "male": "Male", "f": "Female", "female": "Female"}


def grade_for(total):
    for threshold, letter, point in GRADE_SCALE:
        if total >= threshold:
            return letter, point
    return "F", 0.0


def _clean_text(s):
    return s.astype("string").str.replace(r"\s+", " ", regex=True).str.strip()


def _standard_semester(value):
    m = SEMESTER_RE.match(str(value).strip()) if pd.notna(value) else None
    return f"{m.group(1).title()} {m.group(2)}" if m else None


def _standard_department(value):
    value = str(value).strip()
    return value.upper() if len(value) <= 4 else value.title()


def transform(raw):
    report = {"rows_in": int(len(raw))}
    df = raw.copy()
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"CSV is missing required columns: {missing}")
    df = df[REQUIRED_COLUMNS]

    for col in TEXT_COLUMNS:
        df[col] = _clean_text(df[col])
    for col in NUMERIC_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # 1. rows without key fields are unusable
    key_cols = ["student_id", "student_name", "department", "course_code",
                "course_name", "teacher_name", "semester"]
    before = len(df)
    df = df.dropna(subset=key_cols)
    df = df[(df[key_cols] != "").all(axis=1)]
    report["dropped_missing_keys"] = int(before - len(df))

    # 2. standardise categorical values
    df["semester"] = df["semester"].map(_standard_semester)
    before = len(df)
    df = df.dropna(subset=["semester"])
    report["dropped_invalid_semester"] = int(before - len(df))

    df["department"] = df["department"].map(_standard_department)
    df["gender"] = (df["gender"].str.lower().map(GENDER_MAP)
                    .fillna("Other").astype(str))
    df["student_id"] = df["student_id"].str.upper()
    df["course_code"] = df["course_code"].str.upper()
    df["student_name"] = df["student_name"].str.title()
    for col in TEXT_COLUMNS:
        df[col] = df[col].astype(str)

    # 3. marks are required for grading
    mark_cols = list(MARK_LIMITS)
    before = len(df)
    df = df.dropna(subset=mark_cols)
    report["dropped_missing_marks"] = int(before - len(df))

    # 4. duplicates (grain = student x course x semester)
    before = len(df)
    df = df.drop_duplicates(subset=["student_id", "course_code", "semester"], keep="first")
    report["duplicates_removed"] = int(before - len(df))

    # 5. range validation
    for col, limit in MARK_LIMITS.items():
        df[col] = df[col].clip(0, limit)
    df["attendance_pct"] = df["attendance_pct"].clip(0, 100)
    df["study_hours"] = df["study_hours"].clip(0, 60)
    df["credit_hours"] = df["credit_hours"].fillna(3.0).clip(0.5, 6)

    # 6. impute missing attendance / study hours with the course median
    for col, key in (("attendance_pct", "filled_attendance"),
                     ("study_hours", "filled_study_hours")):
        n_missing = int(df[col].isna().sum())
        df[col] = df[col].fillna(df.groupby("course_code")[col].transform("median"))
        df[col] = df[col].fillna(df[col].median())
        report[key] = n_missing

    # 7. derived measures
    df["total_marks"] = (df[mark_cols].sum(axis=1)).round(1)
    grades = df["total_marks"].map(grade_for)
    df["grade"] = grades.map(lambda g: g[0])
    df["grade_point"] = grades.map(lambda g: g[1])
    df["is_pass"] = (df["grade"] != "F").astype(int)

    df = df.reset_index(drop=True)
    report["rows_out"] = int(len(df))
    return df, report
