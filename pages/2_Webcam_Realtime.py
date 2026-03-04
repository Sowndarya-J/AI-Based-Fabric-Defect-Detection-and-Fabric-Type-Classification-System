import json
import streamlit as st
import av
import cv2
import pandas as pd
from datetime import datetime
from PIL import Image
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase, WebRtcMode

from utils import get_model, save_images, insert_inspection

st.title("📷 Real-time Webcam Detection (Mobile Front/Back)")

if not st.session_state.get("logged_in", False):
    st.warning("Please Login first (Go to Login page).")
    st.stop()

model = get_model()

# ---------- Controls ----------
confidence_threshold = st.slider("Confidence Threshold", 0.0, 1.0, 0.25, 0.05)

colA, colB, colC, colD = st.columns(4)
with colA:
    run_webcam = st.toggle("Start Camera", value=False)

with colB:
    webcam_imgsz = st.selectbox("img size (CPU friendly)", [320, 416, 512, 640], index=0)

with colC:
    webcam_every_n = st.selectbox("Run YOLO every N frames", [1, 2, 3, 4, 5], index=2)

with colD:
    # ✅ Camera selector (front/back)
    cam_mode = st.selectbox("Camera", ["Back Camera", "Front Camera"], index=0)

# Map to WebRTC facingMode
facing_mode = "environment" if cam_mode == "Back Camera" else "user"

st.caption("📌 Mobile tip: For back camera, select 'Back Camera' and restart camera if needed.")

# Live placeholders
live_counts_placeholder = st.empty()
live_status_placeholder = st.empty()

class YOLOVideoProcessor(VideoProcessorBase):
    def __init__(self):
        self.frame_count = 0
        self.last_original = None     # last raw frame (BGR)
        self.last_annotated = None    # last annotated frame (BGR)
        self.last_counts = {}
        self.last_total = 0
        self.last_high = 0
        self.last_status = "PASS"

    def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
        img = frame.to_ndarray(format="bgr24")  # BGR
        self.last_original = img.copy()
        self.frame_count += 1

        out = self.last_annotated if self.last_annotated is not None else img

        # Run YOLO every N frames (CPU optimization)
        if self.frame_count % int(webcam_every_n) == 0:
            res = model.predict(
                source=img,
                conf=float(confidence_threshold),
                imgsz=int(webcam_imgsz),
                verbose=False
            )
            r0 = res[0]
            boxes = r0.boxes
            names = r0.names

            counts = {}
            total = 0
            high = 0

            if boxes is not None and len(boxes) > 0:
                for b in boxes:
                    cls_id = int(b.cls[0])
                    conf = float(b.conf[0])
                    name = names[cls_id]

                    counts[name] = counts.get(name, 0) + 1
                    total += 1
                    if conf > 0.80:
                        high += 1

            # Quality logic
            if high > 0:
                status = "REJECT"
            elif total <= 2:
                status = "PASS"
            else:
                status = "REJECT"

            self.last_counts = counts
            self.last_total = total
            self.last_high = high
            self.last_status = status

            annotated = r0.plot()  # BGR
            self.last_annotated = annotated
            out = annotated

        return av.VideoFrame.from_ndarray(out, format="bgr24")


ctx = None

if run_webcam:
    ctx = webrtc_streamer(
        key=f"fabric-webcam-{facing_mode}",  # ✅ key changes when camera changes
        mode=WebRtcMode.SENDRECV,
        video_processor_factory=YOLOVideoProcessor,
        media_stream_constraints={
            "video": {
                "facingMode": {"ideal": facing_mode},  # ✅ front/back request
                "width": {"ideal": 1280},
                "height": {"ideal": 720},
            },
            "audio": False,
        },
        async_processing=True,
    )
else:
    st.info("Turn ON **Start Camera** to begin real-time detection.")

# ---- Show live stats + save snapshot ----
if ctx and ctx.video_processor:
    vp = ctx.video_processor

    counts = vp.last_counts
    total = vp.last_total
    status = vp.last_status

    live_counts_placeholder.subheader("🧾 Live Defect Count")
    if counts:
        live_counts_placeholder.table(pd.DataFrame(counts.items(), columns=["Defect", "Count"]))
    else:
        live_counts_placeholder.info("No defects detected in current frames.")

    if status == "PASS":
        live_status_placeholder.success(f"✅ LIVE QUALITY: PASS (Total defects: {total})")
    else:
        live_status_placeholder.error(f"❌ LIVE QUALITY: REJECT (Total defects: {total})")

    st.divider()
    st.subheader("💾 Save Camera Snapshot to History")

    if st.button("📌 Save Current Frame"):
        if vp.last_original is None or vp.last_annotated is None:
            st.warning("No frame available yet. Wait a few seconds after starting camera.")
        else:
            # Convert original BGR -> PIL RGB
            original_rgb = cv2.cvtColor(vp.last_original, cv2.COLOR_BGR2RGB)
            original_pil = Image.fromarray(original_rgb)

            # Save both images
            orig_path, ann_path = save_images(
                original_pil,
                vp.last_annotated,
                prefix=f"{facing_mode}_{st.session_state.user}"
            )

            defects_json = json.dumps(vp.last_counts, ensure_ascii=False)

            # Insert to DB with source showing camera type
            dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            insert_inspection(
                dt,
                st.session_state.user,
                f"webcam-{facing_mode}",   # ✅ source = webcam-user / webcam-environment
                vp.last_total,
                vp.last_high,
                vp.last_status,
                orig_path,
                ann_path,
                defects_json
            )

            st.success("✅ Saved snapshot to history!")
            st.write(orig_path)
            st.write(ann_path)

st.warning("⚠️ Mobile camera works best on HTTPS (Streamlit Cloud / ngrok). If camera doesn’t open on phone, use HTTPS.")