import streamlit as st
from streamlit_option_menu import option_menu
from utils import init_db

st.set_page_config(page_title="Fabric QC System", layout="wide")

init_db()

# ---------- Hide default Streamlit navigation ----------
st.markdown("""
<style>
section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] {display:none;}
</style>
""", unsafe_allow_html=True)

# ---------- SIDEBAR ----------
with st.sidebar:

    st.markdown("## 🧵 Fabric QC System")
    st.caption("Real-time Fabric Defect Detection")

    st.markdown("---")

    st.markdown("### MODULES")

    selected = option_menu(
        menu_title=None,
        options=[
            "Home",
            "Login",
            "Image Upload",
            "Live Webcam",
            "Model Metrics",
            "Admin Dashboard"
        ],
        icons=[
            "house",
            "key",
            "image",
            "camera-video",
            "bar-chart",
            "gear"
        ],
        default_index=0,
        styles={
            "container": {"padding": "0!important"},
            "icon": {"font-size": "18px"},
            "nav-link": {
                "font-size": "15px",
                "text-align": "left",
                "margin": "5px",
            },
            "nav-link-selected": {
                "background-color": "#262730",
            },
        }
    )

    st.markdown("---")

    st.markdown("### USER")

    if st.session_state.get("logged_in", False):

        user = st.session_state.get("user")
        role = st.session_state.get("role")

        st.info(f"👤 {user} ({role})")

        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.user = None
            st.session_state.role = None
            st.rerun()

    else:
        st.warning("Not logged in")

# ---------- PAGE LOADER ----------
def run_page(path):
    with open(path, "r", encoding="utf-8") as f:
        code = f.read()
    exec(compile(code, path, "exec"), globals(), globals())


# ---------- ROUTING ----------
if selected == "Home":

    st.title("🏠 Fabric Defect Detection System")

    st.write("Use the sidebar to navigate between modules.")

    st.markdown("""
### Modules

- 🔐 Login (Admin / Operator)
- 🖼 Image Upload Detection
- 📷 Live Webcam Detection
- 📊 Model Metrics
- 🛠 Admin Dashboard

### Features

- YOLO Fabric Defect Detection  
- Real-time Camera Inspection  
- PDF Report Generation  
- Email Report Sending  
- SQLite Inspection Database  
- Admin Analytics Dashboard  
""")


elif selected == "Login":
    run_page("pages/1_Login.py")

elif selected == "Image Upload":
    run_page("pages/3_Image_Upload.py")

elif selected == "Live Webcam":
    run_page("pages/2_Webcam_Realtime.py")

elif selected == "Model Metrics":
    run_page("pages/5_Model_Metrics.py")

elif selected == "Admin Dashboard":
    run_page("pages/4_Admin_Dashboard.py")