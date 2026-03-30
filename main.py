import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st

from theme import apply_theme
from auth import ensure_session, init_user_db

# Always-safe pages
from app_pages.login_page import show_login_page
from app_pages.homepage_page import show_homepage_page

# Optional page imports
IMAGE_AVAILABLE = True
IMAGE_IMPORT_ERROR = ""

VIDEO_AVAILABLE = True
VIDEO_IMPORT_ERROR = ""

WEBCAM_AVAILABLE = True
WEBCAM_IMPORT_ERROR = ""

ADMIN_DASHBOARD_AVAILABLE = True
ADMIN_DASHBOARD_IMPORT_ERROR = ""

LIVE_ADMIN_AVAILABLE = True
LIVE_ADMIN_IMPORT_ERROR = ""

MODEL_METRICS_AVAILABLE = True
MODEL_METRICS_IMPORT_ERROR = ""

try:
    from app_pages.image_upload_page import show_image_upload_page
except Exception as e:
    IMAGE_AVAILABLE = False
    IMAGE_IMPORT_ERROR = str(e)

try:
    from app_pages.video_upload_page import show_video_upload_page
except Exception as e:
    VIDEO_AVAILABLE = False
    VIDEO_IMPORT_ERROR = str(e)

try:
    from app_pages.webcam_realtime_page import show_webcam_realtime_page
except Exception as e:
    WEBCAM_AVAILABLE = False
    WEBCAM_IMPORT_ERROR = str(e)

try:
    from app_pages.admin_dashboard_page import show_admin_dashboard_page
except Exception as e:
    ADMIN_DASHBOARD_AVAILABLE = False
    ADMIN_DASHBOARD_IMPORT_ERROR = str(e)

try:
    from app_pages.live_admin_page import show_live_admin_page
except Exception as e:
    LIVE_ADMIN_AVAILABLE = False
    LIVE_ADMIN_IMPORT_ERROR = str(e)

try:
    from app_pages.model_metrics_page import show_model_metrics_page
except Exception as e:
    MODEL_METRICS_AVAILABLE = False
    MODEL_METRICS_IMPORT_ERROR = str(e)

st.set_page_config(
    page_title="Fabric Defect System",
    layout="wide"
)

apply_theme()
ensure_session()
init_user_db()

if st.session_state.get("logged_in"):
    role = st.session_state.get("role")

    pages = ["Homepage"]

    if IMAGE_AVAILABLE:
        pages.append("Image Upload")

    if VIDEO_AVAILABLE:
        pages.append("Video Upload")

    if WEBCAM_AVAILABLE:
        pages.append("Webcam Realtime")

    if MODEL_METRICS_AVAILABLE:
        pages.append("Model Metrics")

    if role == "admin":
        if ADMIN_DASHBOARD_AVAILABLE:
            pages.append("Admin Dashboard")
        if LIVE_ADMIN_AVAILABLE:
            pages.append("Live Admin")

    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.user}")
        st.caption(f"Role: {st.session_state.role}")

        if st.session_state.get("email"):
            st.caption(f"Email: {st.session_state.email}")

        page = st.radio("Navigation", pages)

        # Optional page warnings
        if not IMAGE_AVAILABLE:
            st.warning("Image Upload page is disabled in this deployment.")

        if not VIDEO_AVAILABLE:
            st.warning("Video Upload page is disabled in this deployment.")

        if not WEBCAM_AVAILABLE:
            st.warning("Webcam Realtime page is disabled in this deployment.")

        if not MODEL_METRICS_AVAILABLE:
            st.warning("Model Metrics page is disabled in this deployment.")

        if role == "admin":
            if not ADMIN_DASHBOARD_AVAILABLE:
                st.warning("Admin Dashboard page is disabled in this deployment.")
            if not LIVE_ADMIN_AVAILABLE:
                st.warning("Live Admin page is disabled in this deployment.")

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

elif page == "Image Upload":
    if not IMAGE_AVAILABLE:
        st.error("❌ Image Upload page is not available in this deployment.")
        if IMAGE_IMPORT_ERROR:
            st.caption(f"Import error: {IMAGE_IMPORT_ERROR}")
        st.stop()
    show_image_upload_page()

elif page == "Video Upload":
    if not VIDEO_AVAILABLE:
        st.error("❌ Video Upload page is not available in this deployment.")
        if VIDEO_IMPORT_ERROR:
            st.caption(f"Import error: {VIDEO_IMPORT_ERROR}")
        st.stop()
    show_video_upload_page()

elif page == "Webcam Realtime":
    if not WEBCAM_AVAILABLE:
        st.error("❌ Webcam Realtime page is not available in this deployment.")
        if WEBCAM_IMPORT_ERROR:
            st.caption(f"Import error: {WEBCAM_IMPORT_ERROR}")
        st.stop()
    show_webcam_realtime_page()

elif page == "Admin Dashboard":
    if st.session_state.get("role") != "admin":
        st.error("❌ Only Admin can access this page.")
        st.stop()
    if not ADMIN_DASHBOARD_AVAILABLE:
        st.error("❌ Admin Dashboard page is not available in this deployment.")
        if ADMIN_DASHBOARD_IMPORT_ERROR:
            st.caption(f"Import error: {ADMIN_DASHBOARD_IMPORT_ERROR}")
        st.stop()
    show_admin_dashboard_page()

elif page == "Live Admin":
    if st.session_state.get("role") != "admin":
        st.error("❌ Only Admin can access this page.")
        st.stop()
    if not LIVE_ADMIN_AVAILABLE:
        st.error("❌ Live Admin page is not available in this deployment.")
        if LIVE_ADMIN_IMPORT_ERROR:
            st.caption(f"Import error: {LIVE_ADMIN_IMPORT_ERROR}")
        st.stop()
    show_live_admin_page()

elif page == "Model Metrics":
    if not MODEL_METRICS_AVAILABLE:
        st.error("❌ Model Metrics page is not available in this deployment.")
        if MODEL_METRICS_IMPORT_ERROR:
            st.caption(f"Import error: {MODEL_METRICS_IMPORT_ERROR}")
        st.stop()
    show_model_metrics_page()
