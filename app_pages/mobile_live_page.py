def show_mobile_live_page():
    import streamlit as st
    import av
    import cv2
    from PIL import Image
    from streamlit_webrtc import webrtc_streamer, VideoProcessorBase, WebRtcMode

    from utils import get_model
    from fabric_classifier import predict_fabric_type

    st.title("📱 Mobile Live Detection")

    if not st.session_state.get("logged_in"):
        st.warning("Please login first.")
        st.stop()

    model = get_model()

    confidence_threshold = st.slider("Confidence Threshold", 0.0, 1.0, 0.25, 0.05)
    camera_mode = st.selectbox("Camera Mode", ["Back Camera", "Front Camera"], index=0)

    facing_mode = "environment" if camera_mode == "Back Camera" else "user"

    live_result = st.empty()
    fabric_result = st.empty()

    class MobileVideoProcessor(VideoProcessorBase):
        def __init__(self):
            self.frame_count = 0
            self.last_fabric_type = "Unknown"
            self.last_fabric_conf = None

        def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
            img = frame.to_ndarray(format="bgr24")
            self.frame_count += 1

            # YOLO defect detection
            results = model.predict(
                source=img,
                conf=float(confidence_threshold),
                imgsz=640,
                verbose=False
            )

            result = results[0]
            annotated = result.plot()

            boxes = result.boxes
            names = result.names

            defect_count = {}
            total_defects = 0
            high_defects = 0
            confs = []

            if boxes is not None and len(boxes) > 0:
                for box in boxes:
                    cls_id = int(box.cls[0])
                    conf = float(box.conf[0])
                    defect_name = names[cls_id]

                    defect_count[defect_name] = defect_count.get(defect_name, 0) + 1
                    total_defects += 1
                    confs.append(conf)

                    if conf > 0.80:
                        high_defects += 1

            avg_conf = round(sum(confs) / len(confs), 4) if confs else 0.0
            max_conf = round(max(confs), 4) if confs else 0.0

            # Fabric classification every 20 frames
            if self.frame_count % 20 == 0:
                try:
                    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    pil_img = Image.fromarray(rgb)
                    fabric_type, fabric_conf = predict_fabric_type(pil_img)
                    self.last_fabric_type = fabric_type
                    self.last_fabric_conf = fabric_conf
                except Exception:
                    self.last_fabric_type = "Unknown"
                    self.last_fabric_conf = None

            # Quality logic
            if high_defects > 0:
                status = "REJECT"
            elif total_defects <= 2:
                status = "PASS"
            else:
                status = "REJECT"

            # Draw fabric text overlay
            label = f"Fabric: {self.last_fabric_type}"
            if self.last_fabric_conf is not None:
                label += f" ({self.last_fabric_conf * 100:.1f}%)"

            cv2.rectangle(annotated, (10, 10), (420, 50), (0, 0, 0), -1)
            cv2.putText(
                annotated,
                label,
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2,
                cv2.LINE_AA
            )

            # Update UI
            live_result.markdown(
                f"""
                ### Live Result
                **Total Defects:** {total_defects}  
                **High Severity:** {high_defects}  
                **Avg Confidence:** {avg_conf * 100:.1f}%  
                **Max Confidence:** {max_conf * 100:.1f}%  
                **Quality Status:** {status}
                """
            )

            fabric_result.markdown(
                f"""
                ### Fabric Type
                **Fabric:** {self.last_fabric_type}  
                **Confidence:** {self.last_fabric_conf * 100:.1f}% if self.last_fabric_conf else 0
                """
            )

            return av.VideoFrame.from_ndarray(annotated, format="bgr24")

    webrtc_streamer(
        key="mobile-live-detection",
        mode=WebRtcMode.SENDRECV,
        video_processor_factory=MobileVideoProcessor,
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
