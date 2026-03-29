import json
import time
from datetime import datetime, timezone

import cv2
import pandas as pd
import streamlit as st
from PIL import Image

from auth import require_login
from live_sync import push_live_status, set_operator_offline, upload_live_frame
from utils import get_model, insert_inspection, save_images
from fabric_classifier import predict_fabric_type, render_fabric_info


def show_video_upload_page():
    require_login()

    st.markdown("""
    <div class="hero-card">
        <div class="hero-title">🎞 Video Upload</div>
        <div class="hero-subtitle">
            Upload a fabric video and detect defects
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.session_state.machine_id = "VIDEO_TEST"
    st.session_state.batch_no = "SIMULATION"

    model = get_model()

    defaults = {
        "video_last_original": None,
        "video_last_annotated": None,
        "video_last_counts": {},
        "video_last_total": 0,
        "video_last_high": 0,
        "video_last_status": "PASS",
        "video_last_avg_conf": 0.0,
        "video_last_max_conf": 0.0,
        "video_last_snapshot_upload_ts": 0.0,
        "video_last_status_push_ts": 0.0,
        "video_last_live_snapshot_url": "",
        "video_processed_once": False,
        "video_last_saved_orig": "",
        "video_last_saved_ann": "",
        "video_last_fabric_type": "Unknown",
        "video_last_fabric_conf": None,
        "video_last_fabric_error": "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    def send_live_update(
        operator_name,
        machine_id,
        batch_no,
        input_mode,
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

        if not force and (now_ts - st.session_state.video_last_status_push_ts < 2):
            return

        payload = {
            "operator_id": operator_name,
            "operator_name": operator_name,
            "machine_id": machine_id or "",
            "batch_no": batch_no or "",
            "camera_mode": input_mode,
            "quality_status": quality_status or "PASS",
            "total_defects": int(total_defects or 0),
            "high_severity": int(high_severity or 0),
            "avg_confidence": float(avg_confidence or 0.0),
            "max_confidence": float(max_confidence or 0.0),
            "defects_json": defects_json if isinstance(defects_json, dict) else {},
            "snapshot_path": snapshot_path or "",
            "source": "video-file",
            "is_online": bool(is_online),
            "last_updated": datetime.now(timezone.utc).isoformat()
        }

        push_live_status(payload)
        st.session_state.video_last_status_push_ts = now_ts

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

    def upload_snapshot_if_needed(image_bgr, operator_id):
        now_ts = time.time()
        current_url = st.session_state.get("video_last_live_snapshot_url", "")

        if image_bgr is not None and (now_ts - st.session_state.video_last_snapshot_upload_ts >= 3):
            rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb)
            snapshot_url = upload_live_frame(pil_img, operator_id)

            if snapshot_url:
                st.session_state.video_last_live_snapshot_url = snapshot_url
                st.session_state.video_last_snapshot_upload_ts = now_ts
                current_url = snapshot_url

        return current_url

    def draw_fabric_overlay(frame_bgr, fabric_type, fabric_conf):
        output = frame_bgr.copy()

        if fabric_type and fabric_type != "Unknown":
            label = f"Fabric: {fabric_type}"
            if fabric_conf is not None:
                label += f" ({fabric_conf * 100:.1f}%)"
        else:
            label = "Fabric: Unknown"

        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.8
        thickness = 2

        (text_w, text_h), baseline = cv2.getTextSize(label, font, font_scale, thickness)

        x1, y1 = 10, 15
        x2 = x1 + text_w + 20
        y2 = y1 + text_h + baseline + 20

        cv2.rectangle(output, (x1, y1), (x2, y2), (0, 0, 0), -1)
        cv2.putText(
            output,
            label,
            (x1 + 10, y1 + text_h + 8),
            font,
            font_scale,
            (0, 255, 0),
            thickness,
            cv2.LINE_AA
        )

        return output

    def save_current_detected_video_frame():
        if st.session_state.video_last_original is None or st.session_state.video_last_annotated is None:
            st.warning("No detected video frame available to save.")
            return

        original_rgb = cv2.cvtColor(st.session_state.video_last_original, cv2.COLOR_BGR2RGB)
        original_pil = Image.fromarray(original_rgb)

        display_frame = draw_fabric_overlay(
            st.session_state.video_last_annotated,
            st.session_state.video_last_fabric_type,
            st.session_state.video_last_fabric_conf
        )

        orig_path, ann_path = save_images(
            original_pil,
            display_frame,
            prefix=f"video_{st.session_state.user}"
        )

        defects_json_str = json.dumps(st.session_state.video_last_counts, ensure_ascii=False)

        dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        insert_inspection(
            dt,
            st.session_state.user,
            "video-file",
            st.session_state.video_last_total,
            st.session_state.video_last_high,
            st.session_state.video_last_status,
            orig_path,
            ann_path,
            defects_json_str
        )

        st.session_state.video_last_saved_orig = orig_path
        st.session_state.video_last_saved_ann = ann_path
        st.success("Saved successfully")
        st.write(orig_path)
        st.write(ann_path)

        st.markdown("### Saved Frame Details")
        st.write(f"**Fabric Type:** {st.session_state.video_last_fabric_type}")
        if st.session_state.video_last_fabric_conf is not None:
            st.write(f"**Fabric Confidence:** {st.session_state.video_last_fabric_conf * 100:.2f}%")

    st.markdown('<div class="card">', unsafe_allow_html=True)
    confidence_threshold = st.slider("Confidence Threshold", 0.0, 1.0, 0.25, 0.05, key="video_conf")
    uploaded_video = st.file_uploader(
        "Upload Fabric Video",
        type=["mp4", "avi", "mov", "mkv"],
        key="video_uploader"
    )
    st.markdown("</div>", unsafe_allow_html=True)

    frame_placeholder = st.empty()
    live_status_placeholder = st.empty()
    live_metrics_placeholder = st.empty()
    live_defects_placeholder = st.empty()
    final_fabric_placeholder = st.empty()

    if uploaded_video is None:
        set_operator_offline(st.session_state.user)
        st.session_state.video_processed_once = False
        st.info("Upload a video file to start detection.")
        return

    temp_video_path = f"temp_{uploaded_video.name}"

    with open(temp_video_path, "wb") as f:
        f.write(uploaded_video.read())

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Uploaded Video")
    st.video(temp_video_path)
    st.markdown("</div>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    process_video = c1.button("Process Video", use_container_width=True, key="process_video_btn")
    auto_save_latest = c2.button("Save Latest Detected Frame", use_container_width=True, key="save_video_latest_btn")

    if process_video:
        send_live_update(
            st.session_state.user,
            st.session_state.machine_id,
            st.session_state.batch_no,
            "Video File",
            "PASS",
            0,
            0,
            0.0,
            0.0,
            {},
            is_online=True,
            force=True,
        )

        cap = cv2.VideoCapture(temp_video_path)
        frame_count = 0
        st.session_state.video_processed_once = False
        st.session_state.video_last_fabric_type = "Unknown"
        st.session_state.video_last_fabric_conf = None
        st.session_state.video_last_fabric_error = ""

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1
            st.session_state.video_last_original = frame.copy()

            # Run defect detection every 3 frames
            if frame_count % 3 != 0:
                continue

            res = model.predict(
                source=frame,
                conf=float(confidence_threshold),
                imgsz=640,
                verbose=False
            )

            counts, total, high, status, avg_conf, max_conf, annotated = analyze_result(res)

            st.session_state.video_last_counts = counts
            st.session_state.video_last_total = total
            st.session_state.video_last_high = high
            st.session_state.video_last_status = status
            st.session_state.video_last_avg_conf = avg_conf
            st.session_state.video_last_max_conf = max_conf
            st.session_state.video_last_annotated = annotated
            st.session_state.video_processed_once = True

            # Show current annotated frame during processing
            display_rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
            frame_placeholder.image(
                display_rgb,
                caption="Detected Video Frame",
                use_container_width=True
            )

            live_snapshot_url = upload_snapshot_if_needed(annotated, st.session_state.user)

            send_live_update(
                st.session_state.user,
                st.session_state.machine_id,
                st.session_state.batch_no,
                "Video File",
                status,
                total,
                high,
                avg_conf,
                max_conf,
                counts,
                is_online=True,
                snapshot_path=live_snapshot_url,
            )

            with live_metrics_placeholder.container():
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Total Defects", total)
                m2.metric("High Severity", high)
                m3.metric("Avg Confidence", f"{avg_conf * 100:.1f}%")
                m4.metric("Max Confidence", f"{max_conf * 100:.1f}%")

            with live_defects_placeholder.container():
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.subheader("Defect Summary")
                if counts:
                    st.table(pd.DataFrame(counts.items(), columns=["Defect", "Count"]))
                else:
                    st.info("No defects detected.")
                st.markdown("</div>", unsafe_allow_html=True)

            if status == "PASS":
                live_status_placeholder.markdown(
                    '<span class="badge-pass">PASS</span>',
                    unsafe_allow_html=True
                )
            else:
                live_status_placeholder.markdown(
                    '<span class="badge-reject">REJECT</span>',
                    unsafe_allow_html=True
                )

            time.sleep(0.03)

        cap.release()

        # ==========================================
        # FABRIC TYPE DETECTION AFTER VIDEO PROCESSING
        # ==========================================
        if st.session_state.video_last_original is not None:
            try:
                last_rgb = cv2.cvtColor(st.session_state.video_last_original, cv2.COLOR_BGR2RGB)
                last_pil = Image.fromarray(last_rgb)

                fabric_type, fabric_conf = predict_fabric_type(last_pil)

                st.session_state.video_last_fabric_type = fabric_type
                st.session_state.video_last_fabric_conf = fabric_conf
                st.session_state.video_last_fabric_error = ""

                # Add fabric overlay to final annotated frame
                if st.session_state.video_last_annotated is not None:
                    final_display = draw_fabric_overlay(
                        st.session_state.video_last_annotated,
                        fabric_type,
                        fabric_conf
                    )
                    st.session_state.video_last_annotated = final_display

                    final_rgb = cv2.cvtColor(final_display, cv2.COLOR_BGR2RGB)
                    frame_placeholder.image(
                        final_rgb,
                        caption="Final Frame with Fabric Type",
                        use_container_width=True
                    )

                with final_fabric_placeholder.container():
                    st.markdown('<div class="card">', unsafe_allow_html=True)
                    st.subheader("Final Fabric Type Result")
                    st.success(f"Detected Fabric Type: {fabric_type}")
                    render_fabric_info(st, fabric_type, fabric_conf)
                    st.markdown("</div>", unsafe_allow_html=True)

            except Exception as e:
                st.session_state.video_last_fabric_type = "Unknown"
                st.session_state.video_last_fabric_conf = None
                st.session_state.video_last_fabric_error = str(e)

                with final_fabric_placeholder.container():
                    st.markdown('<div class="card">', unsafe_allow_html=True)
                    st.subheader("Final Fabric Type Result")
                    st.error("Fabric classification failed after video processing.")
                    st.exception(e)
                    st.markdown("</div>", unsafe_allow_html=True)

        st.success("Video processing completed")

    if auto_save_latest:
        if not st.session_state.video_processed_once:
            st.warning("Please process the video first.")
        else:
            save_current_detected_video_frame()

    if st.session_state.video_last_annotated is not None:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Save Current Video Frame")
        if st.button("Save Current Video Frame", use_container_width=True, key="save_video_current_btn"):
            if not st.session_state.video_processed_once:
                st.warning("Please process the video first.")
            else:
                save_current_detected_video_frame()
        st.markdown("</div>", unsafe_allow_html=True)