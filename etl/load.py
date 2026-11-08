"""LOAD - build dimensions, then the fact table.

Run from the project root:   python -m etl.load
"""
from etl.extract import extract_csv, DEFAULT_CSV
from etl.transform import transform
from warehouse.database import get_connection, init_warehouse, table_counts
from warehouse.dimensions import (
    dim_department, dim_teacher, dim_course, dim_semester, dim_student,
)
from warehouse import fact_student_performance as fact


def run_etl(csv_path=DEFAULT_CSV):
    """Full refresh: extract -> transform -> rebuild warehouse -> load."""
    raw = extract_csv(csv_path)
    clean, report = transform(raw)

    init_warehouse(reset=True)
    with get_connection() as conn:
        dept_map = dim_department.load(conn, clean)
        maps = {
            "department": dept_map,
            "teacher": dim_teacher.load(conn, clean, dept_map),
            "course": dim_course.load(conn, clean, dept_map),
            "semester": dim_semester.load(conn, clean),
            "student": dim_student.load(conn, clean, dept_map),
        }
        report["fact_rows"] = fact.load(conn, clean, maps)

    report["table_counts"] = table_counts()
    return report


def _print_report(report):
    print("ETL finished")
    for key, value in report.items():
        if key != "table_counts":
            print(f"  {key:26}: {value}")
    print("  table row counts:")
    for table, count in report["table_counts"].items():
        print(f"    {table:26}: {count}")


if __name__ == "__main__":
    _print_report(run_etl())
