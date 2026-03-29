import os
import json
import sqlite3
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path
from datetime import datetime

import cv2
import numpy as np
import pandas as pd
from ultralytics import YOLO
from PIL import Image

USERS_FILE = "users.json"
DB_PATH = "fabric_inspections.db"
SAVE_DIR = Path("saved_inspections")
SAVE_DIR.mkdir(exist_ok=True)

# ---------- USERS ----------
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_users(users_dict):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users_dict, f, indent=2)

# ---------- MODEL ----------
_model = None
def get_model():
    global _model
    if _model is None:
        _model = YOLO("best.pt")  # keep best.pt in main folder
    return _model

# ---------- DB HELPERS ----------
def _column_exists(cur, table: str, col: str) -> bool:
    cur.execute(f"PRAGMA table_info({table})")
    cols = [r[1] for r in cur.fetchall()]
    return col in cols

def init_db():
    """
    Creates DB if not exists and safely upgrades schema by adding missing columns.
    This avoids needing to delete DB when you add new features.
    """
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    # base table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS inspections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dt TEXT,
        user TEXT,
        source TEXT,
        total_defects INTEGER,
        high_severity INTEGER,
        quality_status TEXT,
        orig_path TEXT,
        ann_path TEXT,
        defects_json TEXT
    )
    """)

    # schema upgrades (safe add if old DB)
    if not _column_exists(cur, "inspections", "source"):
        cur.execute("ALTER TABLE inspections ADD COLUMN source TEXT")
    if not _column_exists(cur, "inspections", "defects_json"):
        cur.execute("ALTER TABLE inspections ADD COLUMN defects_json TEXT")

    con.commit()
    con.close()

def insert_inspection(dt, user, source, total, high, status, orig_path, ann_path, defects_json):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
    INSERT INTO inspections (dt, user, source, total_defects, high_severity, quality_status, orig_path, ann_path, defects_json)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (dt, user, source, total, high, status, orig_path, ann_path, defects_json))
    con.commit()
    con.close()

def read_inspections(limit=300):
    con = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        f"SELECT * FROM inspections ORDER BY id DESC LIMIT {limit}", con
    )
    con.close()
    return df

def delete_inspection(row_id: int):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("DELETE FROM inspections WHERE id=?", (row_id,))
    con.commit()
    con.close()

# ---------- SAVE IMAGES ----------
def save_images(original_pil: Image.Image, annotated_bgr: np.ndarray, prefix: str):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = f"{prefix}_{ts}"
    original_path = SAVE_DIR / f"{base}_original.jpg"
    annotated_path = SAVE_DIR / f"{base}_annotated.jpg"
    original_pil.save(original_path)
    cv2.imwrite(str(annotated_path), annotated_bgr)
    return str(original_path), str(annotated_path)

# ---------- HEATMAP ----------
def build_heatmap(img_shape, boxes_xyxy):
    h, w = img_shape[:2]
    heat = np.zeros((h, w), dtype=np.float32)

    for (x1, y1, x2, y2) in boxes_xyxy:
        x1, y1, x2, y2 = map(int, [x1, y1, x2, y2])
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w - 1, x2), min(h - 1, y2)
        heat[y1:y2, x1:x2] += 1.0

    heat = cv2.GaussianBlur(heat, (0, 0), sigmaX=25, sigmaY=25)
    heat_norm = cv2.normalize(heat, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    heat_color = cv2.applyColorMap(heat_norm, cv2.COLORMAP_JET)
    return heat_color

# ---------- EMAIL ----------
def send_email_with_pdf(sender_email: str, app_password: str, receiver_email: str,
                        subject: str, body: str, pdf_path: str):
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    msg = EmailMessage()
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg["Subject"] = subject
    msg.set_content(body)

    with open(pdf_path, "rb") as f:
        pdf_data = f.read()

    msg.add_attachment(
        pdf_data,
        maintype="application",
        subtype="pdf",
        filename=os.path.basename(pdf_path)
    )

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(sender_email, app_password)
        server.send_message(msg)