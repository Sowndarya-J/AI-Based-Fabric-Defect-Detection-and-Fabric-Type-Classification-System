def show_login_page():
    import streamlit as st
    from auth import check_login, register_user

    st.title("🔐 Secure Login")

    st.info(
        "Use Gmail + strong password. "
        "Password must be at least 8 characters with uppercase, lowercase, number, and special character."
    )

    tab1, tab2 = st.tabs(["Login", "Register"])

    with tab1:
        st.markdown("### Login")
        st.markdown('<div class="card">', unsafe_allow_html=True)

        email = st.text_input(
            "Gmail",
            placeholder="example@gmail.com",
            key="login_email"
        )
        password = st.text_input(
            "Password",
            type="password",
            key="login_password"
        )

        if st.button("Login", use_container_width=True, key="login_btn"):
            ok, username, role = check_login(email, password)
            if ok:
                st.session_state.logged_in = True
                st.session_state.user = username
                st.session_state.role = role
                st.session_state.email = email.strip().lower()
                st.success("✅ Login successful")
                st.rerun()
            else:
                st.error("❌ Invalid email or password")

        st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        st.markdown("### Register")
        st.markdown('<div class="card">', unsafe_allow_html=True)

        username = st.text_input(
            "Username",
            placeholder="Enter username",
            key="reg_username"
        )
        email = st.text_input(
            "Gmail",
            placeholder="example@gmail.com",
            key="reg_email"
        )
        password = st.text_input(
            "Password",
            type="password",
            key="reg_password"
        )
        confirm_password = st.text_input(
            "Confirm Password",
            type="password",
            key="reg_confirm_password"
        )

        st.caption(
            "Rules: 8+ characters, at least 1 uppercase, 1 lowercase, 1 number, and 1 special character."
        )

        if st.button("Register", use_container_width=True, key="register_btn"):
            if not username or not email or not password or not confirm_password:
                st.warning("⚠️ All fields are required")
            elif password != confirm_password:
                st.error("❌ Passwords do not match")
            else:
                ok, msg = register_user(username, email, password, role="operator")
                if ok:
                    st.success(f"✅ {msg}")
                else:
                    st.error(f"❌ {msg}")

        st.markdown('</div>', unsafe_allow_html=True)