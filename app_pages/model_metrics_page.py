def show_model_metrics_page():
    import os
    import pandas as pd
    import streamlit as st

    from theme import apply_theme
    from auth import require_login, sidebar_user_panel

    apply_theme()
    require_login()
    sidebar_user_panel()

    st.markdown("""
    <div class="hero-card">
        <div class="hero-title">📊 Model Metrics</div>
        <div class="hero-subtitle">
            View YOLO training metrics, curves, and final model performance from results.csv
        </div>
    </div>
    """, unsafe_allow_html=True)

    results_path = "results.csv"

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📁 File Status")

    if not os.path.exists(results_path):
        st.error("results.csv not found.")
        st.info("📌 Put your training results.csv inside Fabric_Defect_App folder.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    st.success("✅ results.csv loaded successfully")
    st.markdown("</div>", unsafe_allow_html=True)

    metrics_df = pd.read_csv(results_path)

    if metrics_df.empty:
        st.error("results.csv is empty.")
        return

    last_row = metrics_df.iloc[-1]

    def pick(cols, default=0.0):
        for c in cols:
            if c in metrics_df.columns:
                try:
                    return float(last_row[c])
                except Exception:
                    return float(default)
        return float(default)

    precision = pick(["metrics/precision(B)", "metrics/precision", "precision"])
    recall = pick(["metrics/recall(B)", "metrics/recall", "recall"])
    map50 = pick(["metrics/mAP50(B)", "metrics/mAP50", "mAP50"])
    map5095 = pick(["metrics/mAP50-95(B)", "metrics/mAP50-95", "mAP50-95"])

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("✅ Last Epoch Metrics")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Precision", f"{precision:.3f}")
    c2.metric("Recall", f"{recall:.3f}")
    c3.metric("mAP@50", f"{map50:.3f}")
    c4.metric("mAP@50-95", f"{map5095:.3f}")

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📈 Training Curves")

    def try_line_chart(label, candidates):
        for col in candidates:
            if col in metrics_df.columns:
                st.write(f"**{label}**")
                st.line_chart(metrics_df[col])
                return True
        return False

    found_any = False
    found_any |= try_line_chart("Precision", ["metrics/precision(B)", "metrics/precision", "precision"])
    found_any |= try_line_chart("Recall", ["metrics/recall(B)", "metrics/recall", "recall"])
    found_any |= try_line_chart("mAP@50", ["metrics/mAP50(B)", "metrics/mAP50", "mAP50"])
    found_any |= try_line_chart("mAP@50-95", ["metrics/mAP50-95(B)", "metrics/mAP50-95", "mAP50-95"])
    found_any |= try_line_chart("Train Box Loss", ["train/box_loss", "box_loss"])
    found_any |= try_line_chart("Train Class Loss", ["train/cls_loss", "cls_loss"])
    found_any |= try_line_chart("Train DFL Loss", ["train/dfl_loss", "dfl_loss"])

    if not found_any:
        st.warning("No known metric columns found in results.csv")

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("🧠 Performance Summary")

    if map50 >= 0.85:
        st.success("Excellent model performance")
    elif map50 >= 0.70:
        st.info("Good model performance")
    elif map50 >= 0.50:
        st.warning("Moderate model performance")
    else:
        st.error("Low model performance")

    st.write(f"**Precision:** {precision:.3f}")
    st.write(f"**Recall:** {recall:.3f}")
    st.write(f"**mAP@50:** {map50:.3f}")
    st.write(f"**mAP@50-95:** {map5095:.3f}")

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📄 Full Results")

    with st.expander("Show results.csv"):
        st.dataframe(metrics_df, use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)