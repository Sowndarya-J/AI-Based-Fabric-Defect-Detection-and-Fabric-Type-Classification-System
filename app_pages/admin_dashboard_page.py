def show_admin_dashboard_page():
    import os
    import json
    import streamlit as st
    import pandas as pd

    from auth import require_admin, sidebar_user_panel
    from theme import apply_theme
    from utils import read_inspections, delete_inspection, load_users, save_users

    apply_theme()
    require_admin()
    sidebar_user_panel()

    st.markdown("""
    <div class="hero-card">
        <div class="hero-title">🛠 Admin Dashboard</div>
        <div class="hero-subtitle">
            Manage users, inspect saved records, preview images, analyze defects, and maintain the database.
        </div>
    </div>
    """, unsafe_allow_html=True)

    def safe_load_defects(s):
        try:
            if s is None or str(s).strip() == "":
                return {}
            return json.loads(s)
        except Exception:
            return {}

    # -----------------------------
    # USER MANAGEMENT
    # -----------------------------
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("👤 User Management")

    USERS = load_users()

    u1, u2 = st.columns([1.2, 1])

    with u1:
        with st.expander("➕ Create New User", expanded=False):
            new_user = st.text_input("New Username", key="admin_new_user")
            new_pass = st.text_input("New Password", type="password", key="admin_new_pass")
            new_role = st.selectbox("Role", ["operator", "admin"], index=0, key="admin_new_role")

            if st.button("Create User", use_container_width=True, key="admin_create_user_btn"):
                if not new_user or not new_pass:
                    st.warning("Username and password required.")
                elif new_user in USERS:
                    st.error("User already exists.")
                else:
                    USERS[new_user] = {"password": new_pass, "role": new_role}
                    save_users(USERS)
                    st.success(f"✅ Created user: {new_user} ({new_role})")
                    st.rerun()

    with u2:
        with st.expander("🗑 Delete User", expanded=False):
            del_user = st.selectbox("Select user to delete", list(USERS.keys()), key="admin_delete_user_select")
            if st.button("Delete Selected User", use_container_width=True, key="admin_delete_user_btn"):
                if del_user == "admin":
                    st.error("You cannot delete the main admin.")
                else:
                    USERS.pop(del_user, None)
                    save_users(USERS)
                    st.success(f"Deleted user: {del_user}")
                    st.rerun()

    with st.expander("📋 View All Users", expanded=False):
        user_table = [{"Username": k, "Role": v["role"]} for k, v in USERS.items()]
        st.dataframe(pd.DataFrame(user_table), use_container_width=True, hide_index=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # -----------------------------
    # LOAD DB
    # -----------------------------
    db_df = read_inspections(limit=800)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📦 Inspection Database")

    if db_df.empty:
        st.info("No inspection records yet.")
        st.markdown('</div>', unsafe_allow_html=True)
        return

    db_df["dt"] = pd.to_datetime(db_df["dt"], errors="coerce")
    db_df = db_df.dropna(subset=["dt"])
    db_df["date"] = db_df["dt"].dt.date

    if "source" not in db_df.columns:
        db_df["source"] = "unknown"
    if "defects_json" not in db_df.columns:
        db_df["defects_json"] = "{}"

    all_defects = set()
    for s in db_df["defects_json"].tolist():
        d = safe_load_defects(s)
        for k in d.keys():
            all_defects.add(k)

    all_defects = sorted(list(all_defects))

    # -----------------------------
    # FILTERS
    # -----------------------------
    st.subheader("🔎 Search & Filter")

    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        min_date = db_df["date"].min()
        max_date = db_df["date"].max()
        date_range = st.date_input("Date Range", value=(min_date, max_date), key="admin_date_range")

    with c2:
        users_list = ["All"] + sorted(db_df["user"].astype(str).unique().tolist())
        selected_user = st.selectbox("Operator", users_list, key="admin_filter_user")

    with c3:
        status_list = ["All"] + sorted(db_df["quality_status"].astype(str).unique().tolist())
        selected_status = st.selectbox("Pass / Reject", status_list, key="admin_filter_status")

    with c4:
        source_list = ["All"] + sorted(db_df["source"].astype(str).unique().tolist())
        selected_source = st.selectbox("Source", source_list, key="admin_filter_source")

    with c5:
        defect_list = ["All"] + all_defects
        selected_defect = st.selectbox("Defect Type", defect_list, key="admin_filter_defect")

    filtered = db_df.copy()

    if isinstance(date_range, tuple) and len(date_range) == 2:
        start, end = date_range
        filtered = filtered[(filtered["date"] >= start) & (filtered["date"] <= end)]
    else:
        filtered = filtered[filtered["date"] == date_range]

    if selected_user != "All":
        filtered = filtered[filtered["user"].astype(str) == selected_user]

    if selected_status != "All":
        filtered = filtered[filtered["quality_status"].astype(str) == selected_status]

    if selected_source != "All":
        filtered = filtered[filtered["source"].astype(str) == selected_source]

    if selected_defect != "All":
        def has_defect(x):
            d = safe_load_defects(x)
            return selected_defect in d and d[selected_defect] > 0
        filtered = filtered[filtered["defects_json"].apply(has_defect)]

    st.success(f"✅ Filtered records: {len(filtered)}")

    show_df = filtered.drop(columns=["date"], errors="ignore")
    st.dataframe(show_df, use_container_width=True)

    st.download_button(
        "⬇️ Download Filtered CSV",
        data=show_df.to_csv(index=False).encode("utf-8"),
        file_name="filtered_inspections.csv",
        mime="text/csv",
        use_container_width=True,
        key="admin_download_csv"
    )

    st.markdown('</div>', unsafe_allow_html=True)

    # -----------------------------
    # PREVIEW IMAGES
    # -----------------------------
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("🖼 Preview Saved Images")

    if len(filtered) > 0:
        ids = filtered["id"].tolist()
        selected_id = st.selectbox("Select Inspection ID", ids, key="admin_preview_id")

        row = filtered[filtered["id"] == selected_id].iloc[0]
        orig_path = str(row.get("orig_path", ""))
        ann_path = str(row.get("ann_path", ""))

        cp1, cp2 = st.columns(2)

        with cp1:
            st.subheader("Original Image")
            if orig_path and os.path.exists(orig_path):
                st.image(orig_path, use_container_width=True)
            else:
                st.warning("Original image file not found.")

        with cp2:
            st.subheader("Annotated Image")
            if ann_path and os.path.exists(ann_path):
                st.image(ann_path, use_container_width=True)
            else:
                st.warning("Annotated image file not found.")

        st.subheader("⬇️ Download Images")
        d1, d2 = st.columns(2)

        with d1:
            if orig_path and os.path.exists(orig_path):
                with open(orig_path, "rb") as f:
                    st.download_button(
                        "Download Original",
                        data=f,
                        file_name=os.path.basename(orig_path),
                        mime="image/jpeg",
                        use_container_width=True,
                        key="admin_download_original"
                    )

        with d2:
            if ann_path and os.path.exists(ann_path):
                with open(ann_path, "rb") as f:
                    st.download_button(
                        "Download Annotated",
                        data=f,
                        file_name=os.path.basename(ann_path),
                        mime="image/jpeg",
                        use_container_width=True,
                        key="admin_download_annotated"
                    )
    else:
        st.info("No rows after filter. Adjust filters to preview images.")

    st.markdown('</div>', unsafe_allow_html=True)

    # -----------------------------
    # ANALYTICS
    # -----------------------------
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📊 Analytics Dashboard")

    total_inspections = len(filtered)
    total_defects = int(filtered["total_defects"].sum()) if len(filtered) > 0 else 0
    avg_defects = float(filtered["total_defects"].mean()) if total_inspections > 0 else 0.0
    reject_count = int((filtered["quality_status"] == "REJECT").sum()) if len(filtered) > 0 else 0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Inspections", f"{total_inspections}")
    m2.metric("Total Defects", f"{total_defects}")
    m3.metric("Avg Defects / Fabric", f"{avg_defects:.2f}")
    m4.metric("Reject Count", f"{reject_count}")

    st.subheader("📅 Defects Per Day")
    per_day = (
        filtered.groupby("date")["total_defects"]
        .sum()
        .reset_index()
        .sort_values("date")
        .set_index("date")
    )
    if not per_day.empty:
        st.line_chart(per_day)
    else:
        st.info("No data available for daily chart.")

    st.subheader("✅ PASS vs ❌ REJECT")
    status_counts = (
        filtered["quality_status"]
        .value_counts()
        .rename_axis("status")
        .reset_index(name="count")
    )
    if not status_counts.empty:
        st.bar_chart(status_counts.set_index("status"))
    else:
        st.info("No status data available.")

    st.subheader("📸 Inspections by Source")
    by_source = filtered["source"].value_counts().to_frame("count")
    if not by_source.empty:
        st.bar_chart(by_source)
    else:
        st.info("No source data available.")

    st.subheader("⭐ Most Common Defect Type")

    agg = {}
    for s in filtered["defects_json"].tolist():
        d = safe_load_defects(s)
        for k, v in d.items():
            agg[k] = agg.get(k, 0) + int(v)

    if len(agg) == 0:
        st.info("No defect type data available yet.")
    else:
        most_common = max(agg.items(), key=lambda x: x[1])
        st.success(f"Most common defect: {most_common[0]} (Total: {most_common[1]})")

        st.subheader("📊 Top Defects (Count)")
        agg_df = pd.DataFrame(
            sorted(agg.items(), key=lambda x: x[1], reverse=True),
            columns=["Defect", "Count"]
        )
        st.bar_chart(agg_df.set_index("Defect"))

    st.markdown('</div>', unsafe_allow_html=True)

    # -----------------------------
    # DELETE RECORD
    # -----------------------------
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("🗑 Delete Inspection Record")

    del_id = st.number_input("Enter Inspection ID to delete", min_value=0, step=1, key="admin_delete_record_id")

    if st.button("Delete Record", use_container_width=True, key="admin_delete_record_btn"):
        if del_id > 0:
            delete_inspection(int(del_id))
            st.success(f"Deleted record ID {int(del_id)}")
            st.rerun()
        else:
            st.warning("Enter a valid ID")

    st.markdown('</div>', unsafe_allow_html=True)