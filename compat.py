"""Streamlit version compatibility.
`use_container_width=True` was replaced by `width="stretch"` in newer Streamlit.
Usage:  st.button("x", **stretch())
"""
import streamlit as st
from packaging.version import Version, InvalidVersion


def stretch():
    try:
        new_api = Version(st.__version__) >= Version("1.50.0")
    except InvalidVersion:
        new_api = True
    return {"width": "stretch"} if new_api else {"use_container_width": True}
