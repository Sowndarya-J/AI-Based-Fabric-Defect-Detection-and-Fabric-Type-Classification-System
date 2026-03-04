import os
import json
import cv2
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
from PIL import Image
from datetime import datetime

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, Image as RLImage
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import A4

from utils import (
    get_model,
    save_images,
    build_heatmap,
    insert_inspection,
    send_email_with_pdf
)

st.title("🖼 Image Upload Detection")

if not st.session_state.get("logged_in", False):
    st.warning("Please Login first (Go to Login page).")
    st.stop()

model = get_model()

confidence_threshold = st.slider("Confidence Threshold", 0.0, 1.0, 0.25, 0.05)

uploaded_file = st.file_uploader("Upload Fabric Image", type=["jpg", "png", "jpeg"])

if uploaded_file is not None:
    image = Image.open(uploaded_file).convert("RGB")
    st.image(image, caption="Uploaded Image", width=500)

    if st.button("Detect Defects (Image)"):

        results = model(image, conf=confidence_threshold)
        result = results[0]
        result_image = result.plot()  # BGR numpy array

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
            df = pd.DataFrame([["No Defects", 0, "-"]], columns=["Defect Type", "Confidence (%)", "Severity"])
            st.success("🎉 No Defects Found — PERFECT FABRIC")
            quality_status = "PASS"
            total_defects = 0
            high_defects = 0
            defect_count = {}

        # ✅ NEW: defect types saved as JSON
        defects_json = json.dumps(defect_count, ensure_ascii=False)

        # Save images
        orig_path, ann_path = save_images(image, result_image, prefix=st.session_state.user)
        st.success("✅ Saved images:")
        st.write(orig_path)
        st.write(ann_path)

        # ✅ Insert to DB (source=image + defects_json)
        dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        insert_inspection(
            dt, st.session_state.user, "image",
            total_defects, high_defects, quality_status,
            orig_path, ann_path,
            defects_json
        )

        # ---------------- PDF GENERATION ----------------
        pdf_path = "Fabric_Report.pdf"
        doc = SimpleDocTemplate(pdf_path, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()

        elements.append(Paragraph("Fabric Defect Detection Report", styles["Heading1"]))
        elements.append(Spacer(1, 0.3 * inch))
        elements.append(Paragraph(f"Date: {dt}", styles["Normal"]))
        elements.append(Spacer(1, 0.15 * inch))
        elements.append(Paragraph(f"Inspector: {st.session_state.user}", styles["Normal"]))
        elements.append(Spacer(1, 0.15 * inch))
        elements.append(Paragraph("Source: Image Upload", styles["Normal"]))
        elements.append(Spacer(1, 0.15 * inch))
        elements.append(Paragraph(f"Confidence Threshold: {confidence_threshold}", styles["Normal"]))
        elements.append(Spacer(1, 0.15 * inch))
        elements.append(Paragraph(f"Quality Status: {quality_status}", styles["Normal"]))
        elements.append(Spacer(1, 0.3 * inch))

        data = [["Defect Type", "Confidence (%)", "Severity"]] + df.values.tolist()
        table = Table(data)
        table.setStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ])
        elements.append(table)
        elements.append(Spacer(1, 0.4 * inch))

        temp_image_path = "detected_image.jpg"
        Image.fromarray(result_image).save(temp_image_path)
        elements.append(RLImage(temp_image_path, width=4 * inch, height=3 * inch))

        doc.build(elements)

        with open(pdf_path, "rb") as f:
            st.download_button(
                "📄 Download PDF Report",
                data=f,
                file_name="Fabric_Report.pdf",
                mime="application/pdf",
            )

        # ---------------- EMAIL ----------------
        st.subheader("📧 Email PDF Report (Gmail)")
        with st.expander("Send report via Email", expanded=False):
            sender_email = st.text_input(
                "Sender Gmail",
                value=st.secrets.get("SENDER_EMAIL", ""),
                placeholder="yourgmail@gmail.com"
            )
            app_password = st.text_input(
                "Gmail App Password",
                value=st.secrets.get("APP_PASSWORD", ""),
                type="password",
                placeholder="16-character app password"
            )
            receiver_email = st.text_input("Receiver Email", placeholder="receiver@gmail.com")

            email_subject = st.text_input("Email Subject", value="Fabric Defect Detection Report")
            email_body = st.text_area(
                "Email Message",
                value=f"Hi,\n\nPlease find attached the Fabric Defect Detection Report.\n\nInspector: {st.session_state.user}\nDate: {dt}\nQuality Status: {quality_status}\n\nThanks."
            )

            if st.button("📨 Send Email"):
                try:
                    if not sender_email or not app_password or not receiver_email:
                        st.warning("Please fill Receiver Email (Sender from secrets).")
                    else:
                        send_email_with_pdf(
                            sender_email=sender_email.strip(),
                            app_password=app_password.strip(),
                            receiver_email=receiver_email.strip(),
                            subject=email_subject.strip(),
                            body=email_body,
                            pdf_path=pdf_path
                        )
                        st.success("✅ Email sent successfully!")
                except Exception as e:
                    st.error(f"❌ Email failed: {e}")