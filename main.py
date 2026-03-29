import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st

from theme import apply_theme
from auth import ensure_session, init_user_db

from app_pages.login_page import show_login_page
from app_pages.homepage_page import show_homepage_page

st.set_page_config(
    page_title="Fabric Defect System",
    layout="wide"
)

apply_theme()
ensure_session()
init_user_db()

if st.session_state.get("logged_in"):
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.user}")
        st.caption(f"Role: {st.session_state.role}")

        if st.session_state.get("email"):
            st.caption(f"Email: {st.session_state.email}")

        page = st.radio("Navigation", ["Homepage"])

        if st.button("Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.user = None
            st.session_state.role = None
            st.session_state.email = None
            st.rerun()
else:
    page = "Login"

if page == "Login":
    show_login_page()
elif page == "Homepage":
    show_homepage_page()
