
import streamlit as st

# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Student Performance Data Warehouse",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown("""
<style>

@import url('https://fonts.googleapis.com/css2?family=Hind+Siliguri:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Hind Siliguri', sans-serif;
}

.stApp {
    background-color: #F5F7FA;
}

/* Header */

.main-title {
    color: #1F4E79;
    font-size: 30px;
    font-weight: 800;
    margin-bottom: 5px;
}

/* Hero Section */

.hero {
    background: linear-gradient(120deg, #163A5F 0%, #3478B8 100%);
    padding: 45px;
    border-radius: 20px;
    color: white;
    width: 100%;
    box-sizing: border-box;
    margin: 15px 0 25px 0;
    box-shadow: 0 8px 25px rgba(22, 58, 95, 0.15);
}

.hero h1 {
    color: #FFFFFF !important;
    font-size: clamp(26px, 4vw, 42px);
    font-weight: 800;
    line-height: 1.3;
    margin: 0;
    padding: 0;
}

.hero p {
    color: #EAF3FA !important;
    font-size: 17px;
    line-height: 1.8;
    margin-top: 18px;
    max-width: 750px;
}

/* Navigation Buttons */

.stButton > button {
    border-radius: 10px;
    font-weight: 600;
    min-height: 45px;
}

/* Responsive */

@media screen and (max-width: 768px) {

    .hero {
        padding: 25px 20px;
        border-radius: 15px;
    }

    .hero p {
        font-size: 15px;
    }

    .main-title {
        font-size: 25px;
    }

}

</style>
""", unsafe_allow_html=True)


# ============================================================
# SESSION STATE
# ============================================================

if "page" not in st.session_state:
    st.session_state.page = "Dashboard"


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="main-title">🎓 Student Performance Data Warehouse</div>',
    unsafe_allow_html=True
)

st.caption(
    "Student Performance Analysis, Data Warehouse & Decision Support System"
)


# ============================================================
# NAVIGATION
# ============================================================

pages = ["Dashboard", "Data Assistant"]

cols = st.columns(len(pages))

for col, page in zip(cols, pages):

    with col:

        if st.button(
            page,
            key=f"nav_{page}",
            type=(
                "primary"
                if st.session_state.page == page
                else "secondary"
            ),
            use_container_width=True
        ):

            st.session_state.page = page
            st.rerun()


st.divider()


# ============================================================
# DASHBOARD PAGE
# ============================================================

if st.session_state.page == "Dashboard":

    # st.markdown("""
    # <div class="hero">

    #     <h1>Student Performance Analytics</h1>

    #     <p>
    #     Analyze student academic performance using a
    #     Data Warehouse, dimensional data model, KPIs,
    #     interactive dashboards and analytical queries.
    #     </p>

    # </div>
    # """, unsafe_allow_html=True)

    # Load dashboard module
    try:
        from dashboard.dashboard import render_dashboard

        render_dashboard()

    except Exception as e:
        st.error("Dashboard could not be loaded.")
        st.exception(e)


# ============================================================
# DATA ASSISTANT PAGE
# ============================================================

elif st.session_state.page == "Data Assistant":

    # st.markdown("""
    # <div class="hero">

    #     <h1>📊 Student Performance Data Assistant</h1>

    #     <p>
    #     Ask questions about student performance,
    #     academic results, attendance, subjects and
    #     other data warehouse information.
    #     </p>

    # </div>
    # """, unsafe_allow_html=True)

    # Load Data Assistant module
    try:
        from dashboard.dashboard import render_data_assistant

        render_data_assistant()

    except Exception as e:
        st.error("Data Assistant could not be loaded.")
        st.exception(e)


# ============================================================
# FOOTER
# ============================================================

st.divider()

# st.caption(
#     "Student Performance Data Warehouse | Streamlit + SQLite"
# )
