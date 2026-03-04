import os
import pandas as pd
import streamlit as st

st.title("📊 Model Performance Metrics (Training)")

# Must login first
if not st.session_state.get("logged_in", False):
    st.warning("Please Login first (Go to Login page).")
    st.stop()

# ---- File check ----
st.write("results.csv found:", os.path.exists("results.csv"))

if not os.path.exists("results.csv"):
    st.info("📌 Put your training results.csv inside Fabric_Defect_App folder (same folder as Home.py).")
    st.stop()

# ---- Load ----
metrics_df = pd.read_csv("results.csv")

if metrics_df.empty:
    st.error("results.csv is empty.")
    st.stop()

last_row = metrics_df.iloc[-1]

# ---- Column picker (supports different YOLO formats) ----
def pick(cols, default=0.0):
    for c in cols:
        if c in metrics_df.columns:
            try:
                return float(last_row[c])
            except:
                return float(default)
    return float(default)

precision = pick(["metrics/precision(B)", "metrics/precision", "precision"])
recall = pick(["metrics/recall(B)", "metrics/recall", "recall"])
map50 = pick(["metrics/mAP50(B)", "metrics/mAP50", "mAP50"])
map5095 = pick(["metrics/mAP50-95(B)", "metrics/mAP50-95", "mAP50-95"])

# ---- Show last-epoch metrics ----
st.subheader("✅ Last Epoch Metrics")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Precision", f"{precision:.3f}")
c2.metric("Recall", f"{recall:.3f}")
c3.metric("mAP@50", f"{map50:.3f}")
c4.metric("mAP@50-95", f"{map5095:.3f}")

# ---- Charts (if columns exist) ----
st.subheader("📈 Training Curves")

def try_line_chart(label, candidates):
    for col in candidates:
        if col in metrics_df.columns:
            st.write(f"**{label}** → `{col}`")
            st.line_chart(metrics_df[col])
            return True
    return False

found_any = False
found_any |= try_line_chart("Precision", ["metrics/precision(B)", "metrics/precision", "precision"])
found_any |= try_line_chart("Recall", ["metrics/recall(B)", "metrics/recall", "recall"])
found_any |= try_line_chart("mAP@50", ["metrics/mAP50(B)", "metrics/mAP50", "mAP50"])
found_any |= try_line_chart("mAP@50-95", ["metrics/mAP50-95(B)", "metrics/mAP50-95", "mAP50-95"])

# also show loss curves if present
found_any |= try_line_chart("Train Box Loss", ["train/box_loss", "box_loss"])
found_any |= try_line_chart("Train Class Loss", ["train/cls_loss", "cls_loss"])
found_any |= try_line_chart("Train DFL Loss", ["train/dfl_loss", "dfl_loss"])

if not found_any:
    st.warning("No known metric columns found. Open results.csv below and check column names.")

# ---- Full table ----
with st.expander("📄 Show full results.csv"):
    st.dataframe(metrics_df)