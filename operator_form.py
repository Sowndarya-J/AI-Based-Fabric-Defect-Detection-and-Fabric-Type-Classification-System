import streamlit as st

def require_operator_info():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Operator Info")

    c1, c2 = st.columns(2)
    with c1:
        machine_id = st.text_input(
            "Machine ID",
            value=st.session_state.get("machine_id", "")
        )
    with c2:
        batch_no = st.text_input(
            "Batch No",
            value=st.session_state.get("batch_no", "")
        )

    st.session_state.machine_id = machine_id.strip()
    st.session_state.batch_no = batch_no.strip()

    if not st.session_state.machine_id or not st.session_state.batch_no:
        st.warning("Please enter Machine ID and Batch No before continuing.")
        st.markdown("</div>", unsafe_allow_html=True)
        st.stop()

    st.markdown("</div>", unsafe_allow_html=True)