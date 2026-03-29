import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

import sys
import json
import traceback
import numpy as np
from PIL import Image
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from tensorflow.keras.applications import EfficientNetB0

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEIGHTS_PATH = os.path.join(BASE_DIR, "fabric_fixed.weights.h5")

CLASS_NAMES = [
    "Cotton",
    "Denim",
    "Leather",
    "Linen",
    "Polyester",
    "Satin",
    "Silk",
    "Velvet",
    "Wool"
]

_model = None


def build_model():
    inputs = keras.Input(shape=(224, 224, 3))

    x = tf.keras.applications.efficientnet.preprocess_input(inputs)

    base_model = EfficientNetB0(
        include_top=False,
        weights="imagenet",
        input_shape=(224, 224, 3)
    )
    base_model.trainable = False

    x = base_model(x, training=False)
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dropout(0.3)(x)
    outputs = layers.Dense(len(CLASS_NAMES), activation="softmax")(x)

    model = keras.Model(inputs, outputs)
    return model


def get_model():
    global _model

    if _model is None:
        if not os.path.exists(WEIGHTS_PATH):
            raise FileNotFoundError(f"Weights file not found: {WEIGHTS_PATH}")

        _model = build_model()
        _model.load_weights(WEIGHTS_PATH)

    return _model


def preprocess_image(image_path):
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")

    image = Image.open(image_path).convert("RGB")
    image = image.resize((224, 224))

    img = np.array(image).astype("float32")
    img = np.expand_dims(img, axis=0)

    return img


def predict(image_path):
    model = get_model()
    img = preprocess_image(image_path)

    pred = model.predict(img, verbose=0)[0]
    class_id = int(np.argmax(pred))
    confidence = float(np.max(pred))

    return {
        "fabric_type": CLASS_NAMES[class_id],
        "confidence": confidence
    }


if __name__ == "__main__":
    try:
        if len(sys.argv) < 2:
            raise ValueError("No image path provided to classifier_runner.py")

        image_path = sys.argv[1]
        result = predict(image_path)

        # Print only JSON
        print(json.dumps(result), flush=True)

    except Exception as e:
        error_info = {
            "error": str(e),
            "traceback": traceback.format_exc()
        }
        print(json.dumps(error_info), file=sys.stderr, flush=True)
        sys.exit(1)