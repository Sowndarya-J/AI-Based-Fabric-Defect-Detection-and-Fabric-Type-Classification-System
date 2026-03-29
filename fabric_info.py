import cv2
import numpy as np
from tensorflow.keras.models import load_model

MODEL_PATH = "fabric_classifier.h5"

CLASS_NAMES = ['Blended', 'Cotton', 'Denim', 'Linen', 'Nylon', 'Polyester', 'Rayon', 'Silk', 'Wool']

FABRIC_INFO = {
    "Cotton": {
        "desc": "This is Cotton cloth.",
        "season": "Best for summer season.",
        "uses": "Soft, breathable, comfortable, and good for daily wear."
    },
    "Rayon": {
        "desc": "This is Rayon cloth.",
        "season": "Suitable for summer and mild weather.",
        "uses": "Lightweight, smooth, and often used for dresses and shirts."
    },
    "Silk": {
        "desc": "This is Silk cloth.",
        "season": "Best for special occasions and moderate climate.",
        "uses": "Smooth, shiny, elegant, and used for sarees and party wear."
    },
    "Denim": {
        "desc": "This is Denim cloth.",
        "season": "Suitable for all seasons, especially casual wear.",
        "uses": "Strong, durable, and used for jeans and jackets."
    },
    "Wool": {
        "desc": "This is Wool cloth.",
        "season": "Best for winter season.",
        "uses": "Warm, soft, and used for sweaters and blankets."
    },
    "Polyester": {
        "desc": "This is Polyester cloth.",
        "season": "Suitable for all seasons.",
        "uses": "Durable, wrinkle-resistant, and easy to maintain."
    },
    "Nylon": {
        "desc": "This is Nylon cloth.",
        "season": "Suitable for rainy and active use.",
        "uses": "Strong, stretchable, and used for sportswear and bags."
    },
    "Linen": {
        "desc": "This is Linen cloth.",
        "season": "Best for hot summer season.",
        "uses": "Cool, breathable, and comfortable for summer clothing."
    },
    "Blended": {
        "desc": "This is Blended Fabric cloth.",
        "season": "Suitable for multiple seasons depending on blend.",
        "uses": "Made by combining fibers for better comfort, durability, and flexibility."
    }
}

_model = None


def get_fabric_model():
    global _model
    if _model is None:
        _model = load_model(MODEL_PATH)
    return _model


def predict_fabric_type(pil_image):
    model = get_fabric_model()

    img = np.array(pil_image.convert("RGB"))
    img = cv2.resize(img, (224, 224))
    img = img.astype("float32") / 255.0
    img = np.expand_dims(img, axis=0)

    pred = model.predict(img, verbose=0)
    class_id = int(np.argmax(pred))
    confidence = float(np.max(pred))

    fabric_type = CLASS_NAMES[class_id]
    return fabric_type, confidence


def render_fabric_info(st, fabric_type, confidence=None):
    info = FABRIC_INFO.get(fabric_type, {
        "desc": f"This is {fabric_type} cloth.",
        "season": "Suitable for general use.",
        "uses": "Used in various clothing applications."
    })

    st.subheader("🧵 Fabric Information")

    c1, c2, c3 = st.columns(3)
    c1.metric("Fabric Type", fabric_type)
    c2.metric("Best Season", info["season"])
    if confidence is not None:
        c3.metric("Model Confidence", f"{confidence * 100:.2f}%")
    else:
        c3.metric("Main Use", info["uses"])

    st.info(
        f"**Description:** {info['desc']}\n\n"
        f"**Best Season:** {info['season']}\n\n"
        f"**Uses:** {info['uses']}"
    )