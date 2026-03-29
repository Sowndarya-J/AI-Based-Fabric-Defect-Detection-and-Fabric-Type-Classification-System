import json
import time
from datetime import datetime, timezone

import av
import cv2
import pandas as pd
import streamlit as st
from PIL import Image
from streamlit_webrtc import VideoProcessorBase, WebRtcMode, webrtc_streamer

from auth import require_login
from live_sync import push_live_status, set_operator_offline, upload_live_frame
from operator_form import require_operator_info
from utils import get_model, insert_inspection, save_images
from fabric_classifier import predict_fabric_type, render_fabric_info


def show_webcam_realtime_page():
    require_login()

    st.markdown("""
    <div class="hero-card">
        <div class="hero-title">📷 Webcam Realtime</div>
        <div class="hero-subtitle">
            Real-time fabric defect detection using webcam
        </div>
    </div>
    """, unsafe_allow_html=True)

    model = get_model()

    if "last_snapshot_upload_ts" not in st.session_state:
        st.session_state.last_snapshot_upload_ts = 0.0
    if "last_status_push_ts" not in st.session_state:
        st.session_state.last_status_push_ts = 0.0
    if "last_live_snapshot_url" not in st.session_state:
        st.session_state.last_live_snapshot_url = ""

    def send_live_update(
        operator_name,
        machine_id,
        batch_no,
        camera_mode,
        quality_status,
        total_defects,
        high_severity,
        avg_confidence,
        max_confidence,
        defects_json,
        is_online=True,
        snapshot_path="",
        force=False,
    ):
        now_ts = time.time()

        if not force and (now_ts - st.session_state.last_status_push_ts < 2):
            return

        payload = {
            "operator_id": operator_name,
            "operator_name": operator_name,
            "machine_id": machine_id or "",
            "batch_no": batch_no or "",
            "camera_mode": camera_mode or "",
            "quality_status": quality_status or "PASS",
            "total_defects": int(total_defects or 0),
            "high_severity": int(high_severity or 0),
            "avg_confidence": float(avg_confidence or 0.0),
            "max_confidence": float(max_confidence or 0.0),
            "defects_json": defects_json if isinstance(defects_json, dict) else {},
            "snapshot_path": snapshot_path or "",
            "source": f"webcam-{camera_mode.lower().replace(' ', '-')}",
            "is_online": bool(is_online),
            "last_updated": datetime.now(timezone.utc).isoformat()
        }

        push_live_status(payload)
        st.session_state.last_status_push_ts = now_ts

    def analyze_result(res):
        r0 = res[0]
        boxes = r0.boxes
        names = r0.names

        counts = {}
        total = 0
        high = 0
        confs = []

        if boxes is not None and len(boxes) > 0:
            for b in boxes:
                cls_id = int(b.cls[0])
                conf = float(b.conf[0])
                name = names[cls_id]

                counts[name] = counts.get(name, 0) + 1
                total += 1
                confs.append(conf)

                if conf > 0.80:
                    high += 1

        if high > 0:
            status = "REJECT"
        elif total <= 2:
            status = "PASS"
        else:
            status = "REJECT"

        avg_conf = round(sum(confs) / len(confs), 4) if confs else 0.0
        max_conf = round(max(confs), 4) if confs else 0.0
        annotated = r0.plot()

        return counts, total, high, status, avg_conf, max_conf, annotated

    st.markdown('<div class="card">', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        run_webcam = st.toggle("Start Camera", value=False, key="webcam_toggle")
    with c2:
        confidence_threshold = st.slider("Confidence Threshold", 0.0, 1.0, 0.25, 0.05, key="webcam_conf")
    with c3:
        webcam_imgsz = st.selectbox("Image Size", [320, 416, 512, 640], index=0, key="webcam_imgsz")
    with c4:
        webcam_every_n = st.selectbox("Run YOLO Every N Frames", [1, 2, 3, 4, 5], index=2, key="webcam_every_n")

    cam_mode = st.selectbox("Camera", ["Back Camera", "Front Camera"], index=0, key="webcam_camera")
    fabric_every_n = st.selectbox("Run Fabric Classification Every N Frames", [5, 10, 15, 20, 30], index=2, key="fabric_every_n")
    st.markdown("</div>", unsafe_allow_html=True)

    require_operator_info()

    facing_mode = "environment" if cam_mode == "Back Camera" else "user"

    live_status_placeholder = st.empty()
    live_fabric_placeholder = st.empty()

    class YOLOVideoProcessor(VideoProcessorBase):
        def __init__(self):
            self.frame_count = 0
            self.last_original = None
            self.last_annotated = None
            self.last_counts = {}
            self.last_total = 0
            self.last_high = 0
            self.last_status = "PASS"
            self.last_avg_conf = 0.0
            self.last_max_conf = 0.0
            self.last_fabric_type = "Unknown"
            self.last_fabric_conf = None

        def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
            img = frame.to_ndarray(format="bgr24")
            self.last_original = img.copy()
            self.frame_count += 1

            out = self.last_annotated if self.last_annotated is not None else img

            # Defect detection
            if self.frame_count % int(webcam_every_n) == 0:
                res = model.predict(
                    source=img,
                    conf=float(confidence_threshold),
                    imgsz=int(webcam_imgsz),
                    verbose=False
                )

                counts, total, high, status, avg_conf, max_conf, annotated = analyze_result(res)

                self.last_counts = counts
                self.last_total = total
                self.last_high = high
                self.last_status = status
                self.last_avg_conf = avg_conf
                self.last_max_conf = max_conf
                self.last_annotated = annotated
                out = annotated

            # Fabric classification
            if self.frame_count % int(fabric_every_n) == 0:
                try:
                    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    pil_img = Image.fromarray(rgb)
                    fabric_type, fabric_conf = predict_fabric_type(pil_img)
                    self.last_fabric_type = fabric_type
                    self.last_fabric_conf = fabric_conf
                except Exception:
                    self.last_fabric_type = "Unknown"
                    self.last_fabric_conf = None

            return av.VideoFrame.from_ndarray(out, format="bgr24")

    ctx = None

    if run_webcam:
        send_live_update(
            st.session_state.user,
            st.session_state.machine_id,
            st.session_state.batch_no,
            cam_mode,
            "PASS",
            0,
            0,
            0.0,
            0.0,
            {},
            is_online=True,
            force=True,
        )

        ctx = webrtc_streamer(
            key=f"fabric-webcam-{facing_mode}",
            mode=WebRtcMode.SENDRECV,
            video_processor_factory=YOLOVideoProcessor,
            media_stream_constraints={
                "video": {
                    "facingMode": {"ideal": facing_mode},
                    "width": {"ideal": 1280},
                    "height": {"ideal": 720},
                },
                "audio": False,
            },
            async_processing=True,
        )
    else:
        set_operator_offline(st.session_state.user)
        st.info("Turn ON Start Camera to begin live detection.")

    if ctx and ctx.video_processor:
        vp = ctx.video_processor

        counts = vp.last_counts
        total = vp.last_total
        status = vp.last_status
        avg_conf = vp.last_avg_conf
        max_conf = vp.last_max_conf

        live_snapshot_url = st.session_state.get("last_live_snapshot_url", "")
        now_ts = time.time()

        if vp.last_annotated is not None and (now_ts - st.session_state.last_snapshot_upload_ts >= 3):
            annotated_rgb = cv2.cvtColor(vp.last_annotated, cv2.COLOR_BGR2RGB)
            annotated_pil = Image.fromarray(annotated_rgb)

            snapshot_url = upload_live_frame(annotated_pil, st.session_state.user)
            if snapshot_url:
                st.session_state.last_live_snapshot_url = snapshot_url
                live_snapshot_url = snapshot_url
                st.session_state.last_snapshot_upload_ts = now_ts

        send_live_update(
            st.session_state.user,
            st.session_state.machine_id,
            st.session_state.batch_no,
            cam_mode,
            status,
            total,
            vp.last_high,
            avg_conf,
            max_conf,
            counts,
            is_online=True,
            snapshot_path=live_snapshot_url,
        )

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Defects", total)
        m2.metric("High Severity", vp.last_high)
        m3.metric("Avg Confidence", f"{avg_conf * 100:.1f}%")
        m4.metric("Max Confidence", f"{max_conf * 100:.1f}%")

        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Live Fabric Type")
        if vp.last_fabric_type != "Unknown":
            st.success(f"Detected Fabric Type: {vp.last_fabric_type}")
            render_fabric_info(st, vp.last_fabric_type, vp.last_fabric_conf)
        else:
            st.info("Fabric type not detected yet.")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Defect Summary")
        if counts:
            st.table(pd.DataFrame(counts.items(), columns=["Defect", "Count"]))
        else:
            st.info("No defects detected.")
        st.markdown("</div>", unsafe_allow_html=True)

        if status == "PASS":
            live_status_placeholder.markdown('<span class="badge-pass">PASS</span>', unsafe_allow_html=True)
        else:
            live_status_placeholder.markdown('<span class="badge-reject">REJECT</span>', unsafe_allow_html=True)

        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Save Current Webcam Frame")

        if st.button("Save Current Frame", use_container_width=True, key="save_webcam_frame"):
            if vp.last_original is None or vp.last_annotated is None:
                st.warning("No frame available yet.")
            else:
                original_rgb = cv2.cvtColor(vp.last_original, cv2.COLOR_BGR2RGB)
                original_pil = Image.fromarray(original_rgb)

                orig_path, ann_path = save_images(
                    original_pil,
                    vp.last_annotated,
                    prefix=f"{facing_mode}_{st.session_state.user}"
                )

                defects_json_str = json.dumps(vp.last_counts, ensure_ascii=False)

                dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                insert_inspection(
                    dt,
                    st.session_state.user,
                    f"webcam-{facing_mode}",
                    vp.last_total,
                    vp.last_high,
                    vp.last_status,
                    orig_path,
                    ann_path,
                    defects_json_str
                )

                st.success("Saved successfully")
                st.write(orig_path)
                st.write(ann_path)
        st.markdown("</div>", unsafe_allow_html=True)