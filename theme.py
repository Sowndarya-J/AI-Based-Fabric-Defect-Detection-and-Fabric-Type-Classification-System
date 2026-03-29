import streamlit as st

def apply_theme():
    st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(135deg, #fff1f2 0%, #ffe4e6 40%, #fff7f7 100%);
        color: #4a1d2d;
    }

    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 2rem;
        padding-left: 2rem;
        padding-right: 2rem;
        max-width: 1400px;
    }

    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #be185d 0%, #9d174d 100%);
        border-right: 2px solid #f9a8d4;
    }

    section[data-testid="stSidebar"] * {
        color: #fff7fb !important;
        font-weight: 600;
    }

    .hero-card {
        background: linear-gradient(135deg, #f472b6 0%, #ec4899 50%, #db2777 100%);
        border: 2px solid #fbcfe8;
        border-radius: 24px;
        padding: 26px;
        margin-bottom: 22px;
        box-shadow: 0 10px 28px rgba(190, 24, 93, 0.18);
    }

    .hero-title {
        font-size: 2rem;
        font-weight: 800;
        color: #fffafc;
        margin-bottom: 0.35rem;
    }

    .hero-subtitle {
        font-size: 1rem;
        font-weight: 500;
        color: #fff1f7;
        line-height: 1.5;
    }

    .card {
        background: #fffafb;
        border: 2px solid #fbcfe8;
        border-radius: 20px;
        padding: 18px;
        margin-bottom: 18px;
        box-shadow: 0 6px 18px rgba(244, 114, 182, 0.10);
    }

    h1, h2, h3, h4, h5, h6 {
        color: #831843 !important;
        font-weight: 800 !important;
    }

    p, label, div, span {
        color: #4a1d2d;
    }

    .stButton > button,
    .stDownloadButton > button {
        width: 100%;
        border: none !important;
        border-radius: 14px !important;
        padding: 0.75rem 1rem !important;
        font-weight: 800 !important;
        font-size: 15px !important;
        color: white !important;
        background: linear-gradient(135deg, #ec4899 0%, #db2777 100%) !important;
        box-shadow: 0 6px 16px rgba(219, 39, 119, 0.22) !important;
    }

    .stButton > button:hover,
    .stDownloadButton > button:hover {
        background: linear-gradient(135deg, #db2777 0%, #be185d 100%) !important;
    }

    [data-testid="stMetric"] {
        background: #fffafb;
        border: 2px solid #fbcfe8;
        border-radius: 16px;
        padding: 12px;
        box-shadow: 0 4px 12px rgba(244, 114, 182, 0.08);
    }

    [data-testid="stMetricLabel"] {
        color: #9d174d !important;
        font-weight: 700 !important;
    }

    [data-testid="stMetricValue"] {
        color: #be185d !important;
        font-weight: 800 !important;
    }

    .badge-pass {
        display: inline-block;
        padding: 8px 14px;
        border-radius: 999px;
        background: #16a34a;
        color: white;
        font-weight: 800;
    }

    .badge-reject {
        display: inline-block;
        padding: 8px 14px;
        border-radius: 999px;
        background: #e11d48;
        color: white;
        font-weight: 800;
    }
    </style>
    """, unsafe_allow_html=True)