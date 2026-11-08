import re

import streamlit as st

from compat import stretch
from database import register_user, authenticate_user

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def auth_page():
    st.markdown("<h1 style='text-align:center;color:#267653'>🌿 DialectMood AI</h1>",
                unsafe_allow_html=True)
    st.markdown("<p style='text-align:center'>Your Bangla Dialect Intelligence & Mood Companion</p>",
                unsafe_allow_html=True)
    st.write("")

    left, right = st.columns([1, 1])

    with left:
        st.markdown("## Welcome!")
        st.write("Understand your regional dialect, discover emotional expressions, "
                 "explore student-performance analytics and talk with your AI mood companion.")
        st.markdown("**Supported varieties**")
        st.markdown("- Dinajpur Bangla\n- Rangpur Bangla\n- Standard Bangla\n- Bangla-English mixed text")

    with right:
        login_tab, signup_tab = st.tabs(["Sign In", "Sign Up"])

        with login_tab:
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            if st.button("Sign In", key="login_btn", **stretch()):
                user = authenticate_user(email, password)
                if user:
                    st.session_state.user = user
                    st.session_state.page = "Home"
                    st.rerun()
                else:
                    st.error("Invalid email or password.")

        with signup_tab:
            name = st.text_input("Full Name", key="signup_name")
            email = st.text_input("Email Address", key="signup_email")
            password = st.text_input("Password", type="password", key="signup_password")
            confirm = st.text_input("Confirm Password", type="password", key="signup_confirm")
            if st.button("Create Account", key="signup_btn", **stretch()):
                if not name.strip() or not email.strip():
                    st.warning("Please enter your name and email.")
                elif not EMAIL_RE.match(email.strip()):
                    st.warning("Please enter a valid email address.")
                elif len(password) < 8:
                    st.warning("Password must be at least 8 characters.")
                elif password != confirm:
                    st.error("Passwords do not match.")
                else:
                    success, message = register_user(name, email, password)
                    (st.success if success else st.error)(message)
