import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st


from theme import apply_theme
from auth import ensure_session, init_user_db

from app_pages.login_page import show_login_page
from app_pages.homepage_page import show_homepage_page
from app_pages.webcam_realtime_page import show_webcam_realtime_page
from app_pages.image_upload_page import show_image_upload_page
from app_pages.video_upload_page import show_video_upload_page
from app_pages.admin_dashboard_page import show_admin_dashboard_page
from app_pages.live_admin_page import show_live_admin_page
from app_pages.model_metrics_page import show_model_metrics_page

st.set_page_config(
    page_title="Fabric Defect System",
    layout="wide"
)

apply_theme()
ensure_session()
init_user_db()

if st.session_state.get("logged_in"):
    role = st.session_state.get("role")

    if role == "admin":
        pages = [
            "Homepage",
            "Webcam Realtime",
            "Image Upload",
            "Video Upload",
            "Admin Dashboard",
            "Live Admin",
            "Model Metrics",
        ]
    else:
        pages = [
            "Homepage",
            "Webcam Realtime",
            "Image Upload",
            "Video Upload",
            "Model Metrics",
        ]

    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.user}")
        st.caption(f"Role: {st.session_state.role}")

        if st.session_state.get("email"):
            st.caption(f"Email: {st.session_state.email}")

        page = st.radio("Navigation", pages)

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
elif page == "Webcam Realtime":
    show_webcam_realtime_page()
elif page == "Image Upload":
    show_image_upload_page()
elif page == "Video Upload":
    show_video_upload_page()
elif page == "Admin Dashboard":
    if st.session_state.get("role") != "admin":
        st.error("❌ Only Admin can access this page.")
        st.stop()
    show_admin_dashboard_page()
elif page == "Live Admin":
    if st.session_state.get("role") != "admin":
        st.error("❌ Only Admin can access this page.")
        st.stop()
    show_live_admin_page()
elif page == "Model Metrics":
    show_model_metrics_page()