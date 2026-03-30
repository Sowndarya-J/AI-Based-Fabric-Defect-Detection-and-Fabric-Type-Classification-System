def show_image_upload_page():
    import os
    import sys
    import streamlit as st

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    try:
        import cv2
    except Exception as e:
        st.error("Image Upload page is not available in this deployment because OpenCV failed to load.")
        st.caption(str(e))
        st.stop()

    import json
    import pandas as pd
    import matplotlib.pyplot as plt
    from PIL import Image
    from datetime import datetime

    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, Image as RLImage
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.lib.pagesizes import A4

    from theme import apply_theme
    from utils import (
        get_model,
        save_images,
        build_heatmap,
        insert_inspection,
        send_email_with_pdf
    )
    from fabric_classifier import predict_fabric_type, render_fabric_info

    apply_theme()

    st.title("🖼 Image Upload Detection")

    if not st.session_state.get("logged_in", False):
        st.warning("Please Login first (Go to Login page).")
        st.stop()

    model = get_model()
    confidence_threshold = st.slider("Confidence Threshold", 0.0, 1.0, 0.25, 0.05)

    uploaded_file = st.file_uploader("Upload Fabric Image", type=["jpg", "jpeg", "png"])

    if uploaded_file is None:
        st.info("Upload an image first.")
        return

    image = Image.open(uploaded_file).convert("RGB")
    st.image(image, caption="Uploaded Image", width=500)

    if st.button("Detect Defects (Image)"):
        fabric_type = "Unknown"
        fabric_conf = None

        try:
            fabric_type, fabric_conf = predict_fabric_type(image)
            st.success(f"Detected Fabric Type: {fabric_type}")
            render_fabric_info(st, fabric_type, fabric_conf)
        except Exception as e:
            st.error("Fabric classification failed.")
            st.exception(e)

        try:
            results = model(image, conf=confidence_threshold)
            result = results[0]
            result_image = result.plot()

            st.image(result_image, caption="Detected Defects", width=500)

            boxes = result.boxes
            names = result.names

            defect_data = []
            defect_count = {}
            total_defects = 0
            quality_status = "PASS"
            high_defects = 0

            if boxes is not None and len(boxes) > 0:
                for box in boxes:
                    cls_id = int(box.cls[0])
                    conf = float(box.conf[0])
                    defect_name = names[cls_id]

                    if conf > 0.80:
                        severity = "High"
                    elif conf > 0.50:
                        severity = "Medium"
                    else:
                        severity = "Low"

                    total_defects += 1
                    defect_count[defect_name] = defect_count.get(defect_name, 0) + 1
                    defect_data.append([defect_name, round(conf * 100, 2), severity])

                st.subheader("📋 Defect Details")
                df = pd.DataFrame(defect_data, columns=["Defect Type", "Confidence (%)", "Severity"])
                st.table(df)

                st.subheader("📊 Defect Distribution Chart")
                fig = plt.figure(figsize=(4, 4))
                plt.pie(defect_count.values(), labels=defect_count.keys(), autopct="%1.1f%%")
                plt.title("Defect Distribution")
                st.pyplot(fig)
                plt.close(fig)

                st.subheader("🏭 Quality Decision")
                high_defects = sum(1 for d in defect_data if d[2] == "High")

                if high_defects > 0:
                    quality_status = "REJECT"
                    st.error("❌ QUALITY STATUS: REJECT (High Severity Defect Found)")
                elif total_defects <= 2:
                    quality_status = "PASS"
                    st.success("✅ QUALITY STATUS: PASS")
                else:
                    quality_status = "REJECT"
                    st.warning("⚠️ QUALITY STATUS: REJECT (Too Many Defects)")

                st.subheader("🔥 Defect Heatmap")
                xyxy = boxes.xyxy.cpu().numpy()
                heat_color = build_heatmap(result_image.shape, xyxy)
                overlay = cv2.addWeighted(result_image, 0.7, heat_color, 0.3, 0)
                st.image(overlay, caption="Heatmap Overlay", width=500)

            else:
                defect_data = []
                st.success("🎉 No Defects Found — PERFECT FABRIC")
                quality_status = "PASS"
                total_defects = 0
                high_defects = 0
                defect_count = {}

            defects_json = json.dumps(defect_count, ensure_ascii=False)

            orig_path, ann_path = save_images(image, result_image, prefix=st.session_state.user)

            st.success("✅ Saved images:")
            st.write(orig_path)
            st.write(ann_path)

            dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            insert_inspection(
                dt,
                st.session_state.user,
                "image",
                total_defects,
                high_defects,
                quality_status,
                orig_path,
                ann_path,
                defects_json
            )

            st.subheader("📄 Generate PDF Report")

            pdf_file = f"report_{st.session_state.user}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            pdf_path = os.path.join(project_root, pdf_file)

            if st.button("Generate PDF Report"):
                styles = getSampleStyleSheet()
                doc = SimpleDocTemplate(pdf_path, pagesize=A4)
                elements = []

                elements.append(Paragraph("Fabric Defect Inspection Report", styles["Title"]))
                elements.append(Spacer(1, 12))

                elements.append(Paragraph(f"<b>Date & Time:</b> {dt}", styles["Normal"]))
                elements.append(Paragraph(f"<b>Inspector:</b> {st.session_state.user}", styles["Normal"]))
                elements.append(Paragraph(f"<b>Fabric Type:</b> {fabric_type}", styles["Normal"]))

                if fabric_conf is not None:
                    elements.append(Paragraph(f"<b>Fabric Confidence:</b> {fabric_conf * 100:.2f}%", styles["Normal"]))

                elements.append(Paragraph(f"<b>Quality Status:</b> {quality_status}", styles["Normal"]))
                elements.append(Paragraph(f"<b>Total Defects:</b> {total_defects}", styles["Normal"]))
                elements.append(Spacer(1, 12))

                if os.path.exists(orig_path):
                    elements.append(Paragraph("<b>Original Image:</b>", styles["Heading3"]))
                    elements.append(RLImage(orig_path, width=4 * inch, height=3 * inch))
                    elements.append(Spacer(1, 12))

                if os.path.exists(ann_path):
                    elements.append(Paragraph("<b>Annotated Image:</b>", styles["Heading3"]))
                    elements.append(RLImage(ann_path, width=4 * inch, height=3 * inch))
                    elements.append(Spacer(1, 12))

                table_data = [["Defect Type", "Confidence (%)", "Severity"]]
                if len(defect_data) > 0:
                    table_data.extend(defect_data)
                else:
                    table_data.append(["No Defects", "0", "-"])

                table = Table(table_data)
                table.setStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ])
                elements.append(table)

                doc.build(elements)

                st.success(f"PDF report generated: {pdf_path}")

                with open(pdf_path, "rb") as f:
                    st.download_button(
                        label="⬇ Download PDF Report",
                        data=f,
                        file_name=os.path.basename(pdf_path),
                        mime="application/pdf"
                    )

        except Exception as e:
            st.error("Defect detection failed.")
            st.exception(e)
