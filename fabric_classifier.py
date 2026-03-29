import json
import subprocess
import tempfile
import os

FABRIC_INFO = {
    "Cotton": {
        "desc": "This is Cotton cloth.",
        "season": "Best for summer season.",
        "uses": "Soft, breathable, comfortable, and good for daily wear."
    },
    "Denim": {
        "desc": "This is Denim cloth.",
        "season": "Suitable for all seasons, especially casual wear.",
        "uses": "Strong, durable, and used for jeans and jackets."
    },
    "Leather": {
        "desc": "This is Leather material.",
        "season": "Suitable for cool and moderate weather.",
        "uses": "Durable, stylish, and used for jackets, bags, shoes, and accessories."
    },
    "Linen": {
        "desc": "This is Linen cloth.",
        "season": "Best for hot summer season.",
        "uses": "Cool, breathable, and comfortable for summer clothing."
    },
    "Polyester": {
        "desc": "This is Polyester cloth.",
        "season": "Suitable for all seasons.",
        "uses": "Durable, wrinkle-resistant, and easy to maintain."
    },
    "Satin": {
        "desc": "This is Satin cloth.",
        "season": "Suitable for special occasions and mild weather.",
        "uses": "Smooth, glossy, and used for dresses, sarees, and decorative clothing."
    },
    "Silk": {
        "desc": "This is Silk cloth.",
        "season": "Best for special occasions and moderate climate.",
        "uses": "Smooth, shiny, elegant, and used for sarees and party wear."
    },
    "Velvet": {
        "desc": "This is Velvet cloth.",
        "season": "Best for winter and festive wear.",
        "uses": "Soft, rich, and used for party wear, blouses, and decorative garments."
    },
    "Wool": {
        "desc": "This is Wool cloth.",
        "season": "Best for winter season.",
        "uses": "Warm, soft, and used for sweaters and blankets."
    }
}

CLASSIFIER_PYTHON = r"C:\Users\Lenovo\Desktop\Fabric_Defect_App\venv_classifier\Scripts\python.exe"
CLASSIFIER_SCRIPT = r"C:\Users\Lenovo\Desktop\Fabric_Defect_App\classifier_runner.py"


def _extract_json_from_stdout(stdout_text: str):
    """
    TensorFlow may print logs to stdout.
    So we try to parse the last valid JSON object line.
    """
    lines = [line.strip() for line in stdout_text.splitlines() if line.strip()]

    # Try whole output first
    try:
        return json.loads(stdout_text.strip())
    except Exception:
        pass

    # Then try line by line from bottom
    for line in reversed(lines):
        try:
            return json.loads(line)
        except Exception:
            continue

    raise json.JSONDecodeError("No valid JSON found in classifier output", stdout_text, 0)


def predict_fabric_type(pil_image):
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        temp_path = tmp.name
        pil_image.save(temp_path)

    try:
        proc = subprocess.run(
            [CLASSIFIER_PYTHON, CLASSIFIER_SCRIPT, temp_path],
            capture_output=True,
            text=True
        )

        stdout = (proc.stdout or "").strip()
        stderr = (proc.stderr or "").strip()

        if proc.returncode != 0:
            error_msg = (
                f"Classifier failed.\n\n"
                f"STDOUT:\n{stdout}\n\n"
                f"STDERR:\n{stderr}"
            )
            raise RuntimeError(error_msg)

        if not stdout:
            raise RuntimeError(
                f"Classifier returned empty output.\nSTDERR:\n{stderr}"
            )

        result = _extract_json_from_stdout(stdout)

        if "fabric_type" not in result or "confidence" not in result:
            raise RuntimeError(
                f"Unexpected classifier output: {result}\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"
            )

        return result["fabric_type"], result["confidence"]

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def render_fabric_info(st, fabric_type, confidence=None):
    info = FABRIC_INFO.get(
        fabric_type,
        {
            "desc": f"This is {fabric_type} cloth.",
            "season": "Suitable for general use.",
            "uses": "Used in various clothing applications."
        }
    )

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