def show_live_admin_page():
    import math
    import pandas as pd
    import streamlit as st
    from streamlit_autorefresh import st_autorefresh

    from auth import require_admin, sidebar_user_panel
    from theme import apply_theme
    from live_sync import fetch_live_status

    apply_theme()
    require_admin()
    sidebar_user_panel()

    st.markdown("""
    <div class="hero-card">
        <div class="hero-title">📺 Live Admin Monitor</div>
        <div class="hero-subtitle">
            Monitor operator activity, latest live snapshots, quality status, and defect counts.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # auto refresh every 2 sec
    st_autorefresh(interval=2000, key="live_admin_refresh")

    # fetch latest live rows from supabase
    res = fetch_live_status()
    rows = res.data if (res is not None and hasattr(res, "data") and res.data) else []

    if not rows:
        st.info("No live operator data available.")
        return

    df = pd.DataFrame(rows)

    # safe columns
    for col in [
        "operator_name", "machine_id", "batch_no", "camera_mode",
        "quality_status", "source", "snapshot_path", "last_updated"
    ]:
        if col not in df.columns:
            df[col] = ""

    for col in ["total_defects", "high_severity", "avg_confidence", "max_confidence"]:
        if col not in df.columns:
            df[col] = 0

    if "is_online" not in df.columns:
        df["is_online"] = False

    if "defects_json" not in df.columns:
        df["defects_json"] = [{} for _ in range(len(df))]

    online_df = df[df["is_online"] == True].copy()
    offline_df = df[df["is_online"] == False].copy()

    # top metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("🟢 Online Operators", len(online_df))
    m2.metric("⚪ Offline Operators", len(offline_df))
    m3.metric(
        "🔴 Current Rejects",
        int((online_df["quality_status"].astype(str).str.upper() == "REJECT").sum()) if not online_df.empty else 0
    )
    m4.metric(
        "📦 Total Live Defects",
        int(online_df["total_defects"].fillna(0).sum()) if not online_df.empty else 0
    )

    if not online_df.empty and (online_df["quality_status"].astype(str).str.upper() == "REJECT").any():
        st.error("🚨 ALERT: One or more operators currently have REJECT status!")

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📡 Live Snapshot Grid")

    if online_df.empty:
        st.info("No operators are live right now.")
    else:
        online_df = online_df.sort_values(by="last_updated", ascending=False)

        cols_per_row = 3
        total_cards = len(online_df)
        total_rows = math.ceil(total_cards / cols_per_row)

        card_index = 0
        for _ in range(total_rows):
            cols = st.columns(cols_per_row)
            for col in cols:
                if card_index >= total_cards:
                    break

                row = online_df.iloc[card_index]
                card_index += 1

                operator_name = str(row.get("operator_name", "-"))
                machine_id = str(row.get("machine_id", "-"))
                batch_no = str(row.get("batch_no", "-"))
                camera_mode = str(row.get("camera_mode", "-"))
                source = str(row.get("source", "-"))
                status = str(row.get("quality_status", "PASS")).upper()
                total_defects = int(row.get("total_defects", 0) or 0)
                high_severity = int(row.get("high_severity", 0) or 0)
                avg_conf = float(row.get("avg_confidence", 0) or 0)
                max_conf = float(row.get("max_confidence", 0) or 0)
                snapshot_url = str(row.get("snapshot_path", "") or "")
                last_updated = str(row.get("last_updated", "-"))
                defects = row.get("defects_json", {})

                with col:
                    with st.container(border=True):
                        st.markdown(f"### 👤 {operator_name}")
                        st.caption(f"Machine: {machine_id} | Batch: {batch_no}")

                        if snapshot_url:
                            st.image(
                                snapshot_url,
                                caption=f"{camera_mode} Live Snapshot",
                                use_container_width=True
                            )
                        else:
                            st.info("No live snapshot yet.")

                        c1, c2 = st.columns(2)
                        c1.metric("Defects", total_defects)
                        c2.metric("High Severity", high_severity)

                        c3, c4 = st.columns(2)
                        c3.metric("Avg Conf", f"{avg_conf * 100:.1f}%")
                        c4.metric("Max Conf", f"{max_conf * 100:.1f}%")

                        if status == "REJECT":
                            st.markdown('<span class="badge-reject">REJECT</span>', unsafe_allow_html=True)
                        else:
                            st.markdown('<span class="badge-pass">PASS</span>', unsafe_allow_html=True)

                        st.write(f"**Camera Mode:** {camera_mode}")
                        st.write(f"**Source:** {source}")
                        st.write(f"**Updated:** {last_updated}")

                        if isinstance(defects, dict) and defects:
                            defect_df = pd.DataFrame(
                                [{"Defect": k, "Count": v} for k, v in defects.items()]
                            )
                            st.dataframe(defect_df, use_container_width=True, hide_index=True)
                        else:
                            st.caption("No defect breakdown available.")

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("⚪ Offline Operators")

    if offline_df.empty:
        st.caption("No offline operators.")
    else:
        show_cols = [
            "operator_name", "machine_id", "batch_no",
            "quality_status", "total_defects", "last_updated"
        ]
        show_cols = [c for c in show_cols if c in offline_df.columns]

        st.dataframe(
            offline_df[show_cols].sort_values(by="last_updated", ascending=False),
            use_container_width=True,
            hide_index=True
        )

    st.markdown("</div>", unsafe_allow_html=True)