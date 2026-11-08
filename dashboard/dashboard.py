# """Student Performance DW dashboard + Data Assistant (Streamlit).

# Used inside app.py, or standalone:  streamlit run dashboard/dashboard.py
# """
# import sys
# from pathlib import Path

# ROOT = Path(__file__).resolve().parent.parent
# if str(ROOT) not in sys.path:               # allow standalone execution
#     sys.path.insert(0, str(ROOT))

# import pandas as pd
# import plotly.express as px
# import streamlit as st

# from analytics.analytics import (get_filter_options, get_kpis, get_student_report,
#                                  run_query)
# from analytics.data_chatbot import ask_warehouse
# from compat import stretch
# from etl.load import run_etl
# from warehouse.database import table_counts, warehouse_is_loaded

# GREEN = ["#267653", "#4B9873", "#174B36", "#8CC9A8", "#BFE3CE"]

# STAR_SCHEMA = """
#                     dim_department              dim_semester
#                           |                          |
#  dim_student ---- fact_student_performance ---- dim_course
#                           |
#                      dim_teacher
# Grain: one row = one student x one course x one semester
# Measures: attendance_pct, study_hours, assignment/midterm/final marks,
#           total_marks, grade, grade_point, is_pass
# """


# def ensure_warehouse():
#     """Build the warehouse automatically the first time."""
#     if not warehouse_is_loaded():
#         with st.spinner("Building the data warehouse (first run)..."):
#             run_etl()


# def _fig(fig, height=340):
#     fig.update_layout(height=height, margin=dict(l=10, r=10, t=40, b=10))
#     st.plotly_chart(fig, **stretch())


# def _table(df):
#     st.dataframe(df, hide_index=True, **stretch())


# def render_dashboard():
#     st.header("📊 Student Performance Data Warehouse")
#     try:
#         ensure_warehouse()
#     except Exception as err:
#         st.error(f"Could not build the warehouse: {err}")
#         return

#     depts, sems = get_filter_options()
#     f1, f2 = st.columns(2)
#     dept = f1.selectbox("Department", ["All"] + depts)
#     sem = f2.selectbox("Semester", ["All"] + sems)

#     k = get_kpis(dept, sem)
#     if not k:
#         st.warning("No data for the selected filters.")
#         return
#     c = st.columns(5)
#     c[0].metric("Students", f"{k['total_students']:,}")
#     c[1].metric("Enrollments", f"{k['total_enrollments']:,}")
#     c[2].metric("Avg Marks", k["avg_marks"])
#     c[3].metric("Avg CGPA", k["avg_cgpa"])
#     c[4].metric("Pass Rate", f"{k['pass_rate']}%")

#     tab_over, tab_students, tab_tc, tab_dw = st.tabs(
#         ["Overview", "Students", "Teachers & Courses", "Warehouse / ETL"])

#     with tab_over:
#         a, b = st.columns(2)
#         with a:
#             df = run_query("dept_performance", dept, sem)
#             _fig(px.bar(df, x="department", y="avg_marks", text="avg_marks",
#                         title="Average marks by department",
#                         color_discrete_sequence=GREEN))
#         with b:
#             df = run_query("semester_trend", dept, sem)
#             _fig(px.line(df, x="semester", y=["avg_marks", "pass_rate"], markers=True,
#                          title="Semester trend (marks & pass rate)",
#                          color_discrete_sequence=GREEN))
#         a, b = st.columns(2)
#         with a:
#             df = run_query("grade_distribution", dept, sem)
#             _fig(px.bar(df, x="grade", y="count", text="count", title="Grade distribution",
#                         color_discrete_sequence=GREEN))
#         with b:
#             df = run_query("attendance_impact", dept, sem)
#             _fig(px.bar(df, x="attendance_band", y="avg_marks", text="avg_marks",
#                         title="Attendance vs average marks",
#                         color_discrete_sequence=GREEN))
#         a, b = st.columns(2)
#         with a:
#             df = run_query("study_hours_impact", dept, sem)
#             _fig(px.bar(df, x="study_band", y="avg_marks", text="avg_marks",
#                         title="Weekly study hours vs average marks",
#                         color_discrete_sequence=GREEN))
#         with b:
#             df = run_query("gender_comparison", dept, sem)
#             _fig(px.bar(df, x="gender", y=["avg_marks", "pass_rate"], barmode="group",
#                         title="Gender comparison", color_discrete_sequence=GREEN))

#     with tab_students:
#         st.subheader("🏆 Top 10 students (by CGPA)")
#         top = run_query("top_students", dept, sem)
#         _table(top)
#         st.subheader("⚠️ At-risk students")
#         st.caption("CGPA below 2.5, attendance below 75%, or 2+ failed courses.")
#         risk = run_query("at_risk_students", dept, sem)
#         _table(risk)
#         if not risk.empty:
#             st.download_button("Download at-risk list (CSV)",
#                                risk.to_csv(index=False).encode("utf-8"),
#                                "at_risk_students.csv", "text/csv")
#         st.subheader("🔎 Student report")
#         sid = st.text_input("Enter Student ID (e.g. S1001)")
#         if sid.strip():
#             rep = get_student_report(sid.strip().upper())
#             if rep.empty:
#                 st.info("No student found with that ID.")
#             else:
#                 _table(rep)

#     with tab_tc:
#         a, b = st.columns(2)
#         with a:
#             st.subheader("Teacher performance")
#             tdf = run_query("teacher_performance", dept, sem)
#             _table(tdf)
#         with b:
#             if not tdf.empty:
#                 _fig(px.bar(tdf, x="teacher", y="avg_marks", color="department",
#                             title="Average marks by teacher"))
#         st.subheader("Hardest courses (highest fail rate)")
#         cdf = run_query("course_difficulty", dept, sem)
#         _table(cdf)
#         if not cdf.empty:
#             _fig(px.bar(cdf, x="course_name", y="fail_rate", text="fail_rate",
#                         title="Fail rate by course", color_discrete_sequence=GREEN))

#     with tab_dw:
#         st.subheader("Star schema")
#         st.code(STAR_SCHEMA, language="text")
#         st.subheader("Row counts")
#         counts = table_counts()
#         _table(pd.DataFrame({"table": list(counts), "rows": list(counts.values())}))
#         if st.button("🔄 Re-run ETL from CSV"):
#             try:
#                 with st.spinner("Running ETL..."):
#                     report = run_etl()
#                 st.success("ETL completed.")
#                 st.json({k: v for k, v in report.items() if k != "table_counts"})
#             except Exception as err:
#                 st.error(f"ETL failed: {err}")


# def _auto_chart(df):
#     if df is None or df.empty or df.shape[1] < 2 or len(df) > 30:
#         return
#     cols = list(df.columns)
#     if not pd.api.types.is_numeric_dtype(df[cols[0]]) and pd.api.types.is_numeric_dtype(df[cols[1]]):
#         _fig(px.bar(df, x=cols[0], y=cols[1], color_discrete_sequence=GREEN), height=300)


# def render_data_assistant():
#     st.header("🤖 Data Assistant")
#     st.caption("Ask about the student performance data in Bangla, Banglish or English. "
#                "Examples: “কোন বিভাগের পাস রেট সবচেয়ে বেশি?”, “top 5 students in CSE”, "
#                "“which course has the highest fail rate?”")
#     try:
#         ensure_warehouse()
#     except Exception as err:
#         st.error(f"Could not build the warehouse: {err}")
#         return

#     st.session_state.setdefault("dw_chat", [])
#     if st.button("Clear chat", key="dw_clear"):
#         st.session_state.dw_chat = []
#         st.rerun()

#     for msg in st.session_state.dw_chat:
#         with st.chat_message(msg["role"]):
#             st.markdown(msg["content"])
#             if msg.get("sql"):
#                 with st.expander("SQL used"):
#                     st.code(msg["sql"], language="sql")
#             if msg.get("data") is not None:
#                 _table(msg["data"])
#                 _auto_chart(msg["data"])

#     question = st.chat_input("Ask a question about student performance...")
#     if question:
#         with st.chat_message("user"):
#             st.markdown(question)
#         with st.chat_message("assistant"):
#             with st.spinner("Analyzing..."):
#                 res = ask_warehouse(question, st.session_state.dw_chat)
#             st.markdown(res["answer"])
#             if res["sql"]:
#                 with st.expander("SQL used"):
#                     st.code(res["sql"], language="sql")
#             if res["data"] is not None:
#                 _table(res["data"])
#                 _auto_chart(res["data"])
#             if res["method"] == "rule-based" and res["error"]:
#                 st.caption(f"AI model unavailable ({res['error'][:80]}). Using built-in answers.")
#         st.session_state.dw_chat.append({"role": "user", "content": question})
#         st.session_state.dw_chat.append({"role": "assistant", "content": res["answer"],
#                                          "sql": res["sql"], "data": res["data"]})


# if __name__ == "__main__":
#     st.set_page_config(page_title="Student Performance DW", page_icon="📊", layout="wide")
#     choice = st.sidebar.radio("Page", ["Dashboard", "Data Assistant"])
#     render_dashboard() if choice == "Dashboard" else render_data_assistant()

"""Student Performance DW Dashboard + Gemini Data Assistant.

Run through:
    streamlit run app.py

Or standalone:
    streamlit run dashboard/dashboard.py
"""

import sys
from pathlib import Path

# ============================================================
# PROJECT PATH
# ============================================================

ROOT = Path(__file__).resolve().parent.parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ============================================================
# IMPORTS
# ============================================================

import pandas as pd
import plotly.express as px
import streamlit as st

from analytics.analytics import (
    get_filter_options,
    get_kpis,
    get_student_report,
    run_query
)

from analytics.data_chatbot import ask_warehouse

from compat import stretch
from etl.load import run_etl
from warehouse.database import (
    table_counts,
    warehouse_is_loaded
)


# ============================================================
# PAGE CONFIGURATION
# ============================================================

# Only configure here when running this file directly.
if __name__ == "__main__":
    st.set_page_config(
        page_title="Student Performance DW",
        page_icon="📊",
        layout="wide"
    )


# ============================================================
# COLORS
# ============================================================

GREEN = [
    "#267653",
    "#4B9873",
    "#174B36",
    "#8CC9A8",
    "#BFE3CE"
]


# ============================================================
# STAR SCHEMA
# ============================================================

STAR_SCHEMA = """
                 dim_department       dim_semester
                       |                   |
 dim_student ---- fact_student_performance ---- dim_course
                       |
                  dim_teacher

Grain:
One row = One student x One course x One semester

Measures:
Attendance, Study Hours, Assignment Marks,
Midterm Marks, Final Marks, Total Marks,
Grade, Grade Point and Pass Status.
"""


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def ensure_warehouse():

    """Build warehouse automatically on first run."""

    if not warehouse_is_loaded():

        with st.spinner(
            "Building Student Performance Data Warehouse..."
        ):

            run_etl()


# ============================================================
# CHART HELPER
# ============================================================

def _fig(fig, height=340):

    fig.update_layout(
        height=height,
        margin=dict(
            l=10,
            r=10,
            t=40,
            b=10
        ),
        template="plotly_white"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )


# ============================================================
# TABLE HELPER
# ============================================================

def _table(df):

    if df is not None and not df.empty:

        st.dataframe(
            df,
            hide_index=True,
            use_container_width=True
        )

    else:

        st.info("No data available.")


# ============================================================
# AUTOMATIC CHART
# ============================================================

def _auto_chart(df):

    """Automatically create chart from query results."""

    if df is None or df.empty:
        return

    if df.shape[1] < 2 or len(df) > 30:
        return

    try:

        categorical = [
            col for col in df.columns
            if not pd.api.types.is_numeric_dtype(df[col])
        ]

        numeric = [
            col for col in df.columns
            if pd.api.types.is_numeric_dtype(df[col])
        ]

        if not categorical or not numeric:
            return

        x_col = categorical[0]
        y_col = numeric[0]

        chart_df = df[[x_col, y_col]].dropna()

        if chart_df.empty:
            return

        st.subheader("📊 Visual Analysis")

        _fig(
            px.bar(
                chart_df,
                x=x_col,
                y=y_col,
                text=y_col,
                title=f"{y_col} by {x_col}",
                color_discrete_sequence=GREEN
            ),
            height=300
        )

    except Exception as err:

        st.caption(f"Chart unavailable: {err}")


# ============================================================
# AI STATUS HELPER
# ============================================================

def _show_ai_status(method, error=None):

    """Display whether Gemini or fallback mode was used."""

    if method == "llm":

        st.success(
            "🟢 AI Mode Active — Gemini generated the SQL and processed the request."
        )

    elif method == "rule-based":

        st.warning(
            "🟡 Rule-based Mode Active — Gemini AI is unavailable."
        )

        if error:

            with st.expander("View Gemini API Error"):

                st.code(str(error))

    else:

        st.error(
            "🔴 Assistant could not process the request."
        )

        if error:

            st.code(str(error))


# ============================================================
# DASHBOARD PAGE
# ============================================================

def render_dashboard():

    st.header("📊 Student Performance Data Warehouse")

    # Initialize warehouse
    try:

        ensure_warehouse()

    except Exception as err:

        st.error(
            f"Could not build the warehouse: {err}"
        )

        return

    # --------------------------------------------------------
    # FILTERS
    # --------------------------------------------------------

    depts, sems = get_filter_options()

    f1, f2 = st.columns(2)

    dept = f1.selectbox(
        "Department",
        ["All"] + depts
    )

    sem = f2.selectbox(
        "Semester",
        ["All"] + sems
    )

    # --------------------------------------------------------
    # KPIs
    # --------------------------------------------------------

    k = get_kpis(dept, sem)

    if not k:

        st.warning(
            "No data for the selected filters."
        )

        return

    c = st.columns(5)

    c[0].metric(
        "Students",
        f"{k['total_students']:,}"
    )

    c[1].metric(
        "Enrollments",
        f"{k['total_enrollments']:,}"
    )

    c[2].metric(
        "Average Marks",
        k["avg_marks"]
    )

    c[3].metric(
        "Average CGPA",
        k["avg_cgpa"]
    )

    c[4].metric(
        "Pass Rate",
        f"{k['pass_rate']}%"
    )

    # --------------------------------------------------------
    # DASHBOARD TABS
    # --------------------------------------------------------

    tab_over, tab_students, tab_tc, tab_dw = st.tabs(
        [
            "Overview",
            "Students",
            "Teachers & Courses",
            "Warehouse / ETL"
        ]
    )

    # ========================================================
    # OVERVIEW
    # ========================================================

    with tab_over:

        a, b = st.columns(2)

        with a:

            df = run_query(
                "dept_performance",
                dept,
                sem
            )

            if not df.empty:

                _fig(
                    px.bar(
                        df,
                        x="department",
                        y="avg_marks",
                        text="avg_marks",
                        title="Average Marks by Department",
                        color_discrete_sequence=GREEN
                    )
                )

            else:
                st.info("No department performance data.")

        with b:

            df = run_query(
                "semester_trend",
                dept,
                sem
            )

            if not df.empty:

                _fig(
                    px.line(
                        df,
                        x="semester",
                        y=["avg_marks", "pass_rate"],
                        markers=True,
                        title="Semester Trend",
                        color_discrete_sequence=GREEN
                    )
                )

            else:
                st.info("No semester trend data.")

        a, b = st.columns(2)

        with a:

            df = run_query(
                "grade_distribution",
                dept,
                sem
            )

            if not df.empty:

                _fig(
                    px.bar(
                        df,
                        x="grade",
                        y="count",
                        text="count",
                        title="Grade Distribution",
                        color_discrete_sequence=GREEN
                    )
                )

            else:
                st.info("No grade distribution data.")

        with b:

            df = run_query(
                "attendance_impact",
                dept,
                sem
            )

            if not df.empty:

                _fig(
                    px.bar(
                        df,
                        x="attendance_band",
                        y="avg_marks",
                        text="avg_marks",
                        title="Attendance vs Average Marks",
                        color_discrete_sequence=GREEN
                    )
                )

            else:
                st.info("No attendance data.")

        a, b = st.columns(2)

        with a:

            df = run_query(
                "study_hours_impact",
                dept,
                sem
            )

            if not df.empty:

                _fig(
                    px.bar(
                        df,
                        x="study_band",
                        y="avg_marks",
                        text="avg_marks",
                        title="Weekly Study Hours vs Average Marks",
                        color_discrete_sequence=GREEN
                    )
                )

            else:
                st.info("No study hours data.")

        with b:

            df = run_query(
                "gender_comparison",
                dept,
                sem
            )

            if not df.empty:

                _fig(
                    px.bar(
                        df,
                        x="gender",
                        y=["avg_marks", "pass_rate"],
                        barmode="group",
                        title="Gender Comparison",
                        color_discrete_sequence=GREEN
                    )
                )

            else:
                st.info("No gender comparison data.")

    # ========================================================
    # STUDENTS
    # ========================================================

    with tab_students:

        st.subheader("🏆 Top 10 Students by CGPA")

        top = run_query(
            "top_students",
            dept,
            sem
        )

        _table(top)

        st.subheader("⚠️ At-Risk Students")

        st.caption(
            "CGPA below 2.5, attendance below 75%, "
            "or 2+ failed courses."
        )

        risk = run_query(
            "at_risk_students",
            dept,
            sem
        )

        _table(risk)

        if not risk.empty:

            st.download_button(
                "Download At-Risk List (CSV)",
                risk.to_csv(index=False).encode("utf-8"),
                "at_risk_students.csv",
                "text/csv"
            )

        st.subheader("🔎 Student Report")

        sid = st.text_input(
            "Enter Student ID (e.g. S1001)"
        )

        if sid.strip():

            rep = get_student_report(
                sid.strip().upper()
            )

            if rep.empty:

                st.info(
                    "No student found with that ID."
                )

            else:

                _table(rep)

    # ========================================================
    # TEACHERS AND COURSES
    # ========================================================

    with tab_tc:

        a, b = st.columns(2)

        with a:

            st.subheader("Teacher Performance")

            tdf = run_query(
                "teacher_performance",
                dept,
                sem
            )

            _table(tdf)

        with b:

            if not tdf.empty:

                _fig(
                    px.bar(
                        tdf,
                        x="teacher",
                        y="avg_marks",
                        color="department",
                        title="Average Marks by Teacher"
                    )
                )

        st.subheader("Hardest Courses")

        st.caption(
            "Courses with the highest failure rates."
        )

        cdf = run_query(
            "course_difficulty",
            dept,
            sem
        )

        _table(cdf)

        if not cdf.empty:

            _fig(
                px.bar(
                    cdf,
                    x="course_name",
                    y="fail_rate",
                    text="fail_rate",
                    title="Course Failure Rate",
                    color_discrete_sequence=GREEN
                )
            )

    # ========================================================
    # DATA WAREHOUSE / ETL
    # ========================================================

    with tab_dw:

        st.subheader("Star Schema")

        st.code(
            STAR_SCHEMA,
            language="text"
        )

        st.subheader("Warehouse Table Counts")

        counts = table_counts()

        _table(
            pd.DataFrame({
                "table": list(counts),
                "rows": list(counts.values())
            })
        )

        if st.button(
            "🔄 Re-run ETL from CSV"
        ):

            try:

                with st.spinner("Running ETL..."):

                    report = run_etl()

                st.success("ETL completed successfully.")

                st.json({
                    k: v
                    for k, v in report.items()
                    if k != "table_counts"
                })

            except Exception as err:

                st.error(f"ETL failed: {err}")


# ============================================================
# DATA ASSISTANT PAGE
# ============================================================

def render_data_assistant():

    st.header("🤖 Student Performance Data Assistant")

    st.caption(
        "Ask questions about student performance in "
        "Bangla, Banglish or English."
    )

    st.info(
        "Examples: কোন বিভাগের পাস রেট সবচেয়ে বেশি? | "
        "Top 5 students in CSE | "
        "Which course has the highest fail rate?"
    )

    # --------------------------------------------------------
    # ENSURE WAREHOUSE
    # --------------------------------------------------------

    try:

        ensure_warehouse()

    except Exception as err:

        st.error(
            f"Could not build the warehouse: {err}"
        )

        return

    # --------------------------------------------------------
    # CHAT HISTORY
    # --------------------------------------------------------

    st.session_state.setdefault(
        "dw_chat",
        []
    )

    # --------------------------------------------------------
    # CLEAR CHAT
    # --------------------------------------------------------

    if st.button(
        "🗑️ Clear Chat",
        key="dw_clear"
    ):

        st.session_state.dw_chat = []

        st.rerun()

    # --------------------------------------------------------
    # DISPLAY PREVIOUS MESSAGES
    # --------------------------------------------------------

    for msg in st.session_state.dw_chat:

        with st.chat_message(msg["role"]):

            st.markdown(
                msg["content"]
            )

            if msg.get("method"):

                _show_ai_status(
                    msg["method"],
                    msg.get("error")
                )

            if msg.get("sql"):

                with st.expander("View SQL Query"):

                    st.code(
                        msg["sql"],
                        language="sql"
                    )

            if msg.get("data") is not None:

                _table(msg["data"])

                _auto_chart(msg["data"])

    # --------------------------------------------------------
    # USER QUESTION
    # --------------------------------------------------------

    question = st.chat_input(
        "Ask a question about student performance..."
    )

    if question:

        # Display user message
        with st.chat_message("user"):

            st.markdown(question)

        # Process assistant response
        with st.chat_message("assistant"):

            with st.spinner(
                "Analyzing your question..."
            ):

                res = ask_warehouse(
                    question,
                    st.session_state.dw_chat
                )

            # Answer
            st.markdown(
                res["answer"]
            )

            # AI status
            _show_ai_status(
                res.get("method", "none"),
                res.get("error")
            )

            # SQL
            if res.get("sql"):

                with st.expander("View SQL Query"):

                    st.code(
                        res["sql"],
                        language="sql"
                    )

            # Data result
            if res.get("data") is not None:

                _table(res["data"])

                _auto_chart(res["data"])

        # ----------------------------------------------------
        # SAVE CHAT HISTORY
        # ----------------------------------------------------

        st.session_state.dw_chat.append({
            "role": "user",
            "content": question
        })

        st.session_state.dw_chat.append({
            "role": "assistant",
            "content": res["answer"],
            "sql": res.get("sql", ""),
            "data": res.get("data"),
            "method": res.get("method", "none"),
            "error": res.get("error")
        })


# ============================================================
# STANDALONE EXECUTION
# ============================================================

if __name__ == "__main__":

    st.sidebar.title(
        "🎓 Student Performance DW"
    )

    choice = st.sidebar.radio(
        "Navigation",
        [
            "Dashboard",
            "Data Assistant"
        ]
    )

    if choice == "Dashboard":

        render_dashboard()

    else:

        render_data_assistant()
