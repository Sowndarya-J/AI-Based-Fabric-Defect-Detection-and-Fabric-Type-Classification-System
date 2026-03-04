import streamlit as st
from utils import load_users

st.title("🔐 Login")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None
    st.session_state.role = None

USERS = load_users()

u = st.text_input("Username")
p = st.text_input("Password", type="password")

if st.button("Login"):
    if u in USERS and USERS[u]["password"] == p:
        st.session_state.logged_in = True
        st.session_state.user = u
        st.session_state.role = USERS[u]["role"]
        st.success(f"Logged in as {u} ({st.session_state.role})")
    else:
        st.error("Invalid username/password")

if st.session_state.logged_in:
    st.info(f"✅ User: {st.session_state.user} | Role: {st.session_state.role}")
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.user = None
        st.session_state.role = None
        st.rerun()