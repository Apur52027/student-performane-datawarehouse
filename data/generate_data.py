"""Generate a realistic *synthetic* data/student_performance.csv.

Run:  python data/generate_data.py
The file deliberately contains a few dirty rows (missing values, duplicates,
inconsistent gender labels, extra spaces) so the ETL cleaning step has real work.
"""
import random
from pathlib import Path

import pandas as pd

OUT = Path(__file__).with_name("student_performance.csv")
SEMESTERS = ["Spring 2023", "Fall 2023", "Spring 2024",
             "Fall 2024", "Spring 2025", "Fall 2025"]
N_STUDENTS = 150

DEPARTMENTS = {
    "CSE": {
        "courses": ["Programming Fundamentals", "Discrete Mathematics", "Digital Logic Design",
                    "Data Structures", "Object Oriented Programming", "Computer Architecture",
                    "Algorithms", "Database Systems", "Operating Systems",
                    "Computer Networks", "Software Engineering", "Artificial Intelligence"],
        "teachers": ["Dr. Rahim Uddin", "Ms. Nusrat Jahan", "Mr. Tanvir Hasan"],
    },
    "EEE": {
        "courses": ["Basic Electrical Engineering", "Physics for Engineers", "Calculus",
                    "Circuit Analysis", "Electronics I", "Engineering Mathematics",
                    "Signals and Systems", "Digital Electronics", "Electrical Machines",
                    "Power Systems", "Control Systems", "Communication Engineering"],
        "teachers": ["Dr. Kamal Hossain", "Ms. Farzana Akter", "Mr. Shahidul Islam"],
    },
    "BBA": {
        "courses": ["Principles of Management", "Microeconomics", "Business Mathematics",
                    "Financial Accounting", "Marketing Management", "Business Statistics",
                    "Macroeconomics", "Organizational Behavior", "Corporate Finance",
                    "Human Resource Management", "Operations Management", "Business Law"],
        "teachers": ["Dr. Mahmudul Karim", "Ms. Sabrina Sultana", "Mr. Arif Chowdhury"],
    },
    "English": {
        "courses": ["Introduction to Literature", "English Phonetics", "Grammar and Composition",
                    "Poetry", "Linguistics", "Drama", "Fiction", "Literary Criticism",
                    "Sociolinguistics", "Translation Studies", "Postcolonial Literature",
                    "Research Methodology"],
        "teachers": ["Dr. Rubina Haque", "Mr. Imran Khan", "Ms. Tahmina Begum"],
    },
    "Mathematics": {
        "courses": ["Calculus I", "Linear Algebra", "Mathematical Logic", "Calculus II",
                    "Differential Equations", "Probability Theory", "Real Analysis",
                    "Abstract Algebra", "Numerical Methods", "Complex Analysis",
                    "Statistics", "Mathematical Modelling"],
        "teachers": ["Dr. Abdul Malek", "Ms. Shirin Parvin", "Mr. Zahid Hasan"],
    },
}

MALE = ["Rahim", "Karim", "Tanvir", "Sajib", "Hasan", "Imran", "Rakib", "Arif",
        "Mehedi", "Nayeem", "Fahim", "Shakil", "Jubayer", "Sourav", "Asif"]
FEMALE = ["Nusrat", "Farzana", "Sabrina", "Tasnim", "Rumana", "Mim", "Sumaiya",
          "Jannat", "Tania", "Ayesha", "Lamia", "Nabila", "Priya", "Shirin", "Rina"]
LAST = ["Ahmed", "Hossain", "Islam", "Rahman", "Khan", "Chowdhury", "Uddin",
        "Akter", "Sarker", "Mondal", "Roy", "Das", "Begum", "Mia", "Siddique"]


def clip(x, lo, hi):
    return max(lo, min(hi, x))


def build_rows(seed=42):
    rng = random.Random(seed)
    teacher_effect = {t: rng.uniform(-3, 3)
                      for info in DEPARTMENTS.values() for t in info["teachers"]}
    course_effect = {}
    rows = []
    for i in range(N_STUDENTS):
        dept = rng.choice(list(DEPARTMENTS))
        info = DEPARTMENTS[dept]
        gender = rng.choice(["Male", "Female"])
        name = f"{rng.choice(MALE if gender == 'Male' else FEMALE)} {rng.choice(LAST)}"
        ability = rng.gauss(0, 1)
        start = rng.randint(0, 2)
        for n in range(4):                       # 4 semesters per student
            for j in range(3):                   # 3 courses per semester
                idx = 3 * n + j
                code = f"{dept[:3].upper()}{n + 1}{j + 1:02d}"
                cname = info["courses"][idx]
                credit = 2.0 if j == 2 else 3.0
                teacher = info["teachers"][idx % 3]
                course_effect.setdefault(code, rng.uniform(-6, 6))
                attendance = clip(rng.gauss(80 + 5 * ability, 10), 40, 100)
                study = clip(rng.gauss(12 + 3 * ability, 4), 1, 40)
                score = (60 + 10 * ability + 0.25 * (attendance - 80)
                         + 0.30 * (study - 12) + course_effect[code]
                         + teacher_effect[teacher] + rng.gauss(0, 6))
                score = clip(score, 5, 98)
                rows.append({
                    "student_id": f"S{1001 + i}",
                    "student_name": name,
                    "gender": gender,
                    "department": dept,
                    "course_code": code,
                    "course_name": cname,
                    "credit_hours": credit,
                    "teacher_name": teacher,
                    "semester": SEMESTERS[start + n],
                    "attendance_pct": round(attendance, 1),
                    "study_hours": round(study, 1),
                    "assignment_marks": round(clip(score / 100 * 20 + rng.gauss(0, 1), 0, 20), 1),
                    "midterm_marks": round(clip(score / 100 * 30 + rng.gauss(0, 2), 0, 30), 1),
                    "final_marks": round(clip(score / 100 * 50 + rng.gauss(0, 3), 0, 50), 1),
                })
    return rows, rng


def make_dirty(rows, rng):
    """Inject a small amount of realistic noise."""
    for r in rows:
        x = rng.random()
        if x < 0.015:
            r["attendance_pct"] = None
        elif x < 0.025:
            r["study_hours"] = None
        if rng.random() < 0.03:
            r["student_name"] = f"  {r['student_name'].upper()} "
        if rng.random() < 0.05:
            r["gender"] = {"Male": rng.choice(["M", "male"]),
                           "Female": rng.choice(["F", "female"])}[r["gender"]]
    rows += [dict(r) for r in rng.sample(rows, 8)]           # duplicates
    for r in rng.sample(rows, 2):
        r["student_id"] = ""                                 # missing key
    for r in rng.sample(rows, 2):
        r["final_marks"] = None                              # missing marks
    rng.shuffle(rows)
    return rows


def main():
    rows, rng = build_rows()
    rows = make_dirty(rows, rng)
    df = pd.DataFrame(rows)
    df.to_csv(OUT, index=False, encoding="utf-8")
    print(f"Wrote {len(df)} rows -> {OUT}")


if __name__ == "__main__":
    main()
