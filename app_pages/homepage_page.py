def show_homepage_page():
    import streamlit as st

    st.markdown("""
    <style>
    .hero {
        background: linear-gradient(135deg, #ffdde1, #ee9ca7);
        padding: 30px;
        border-radius: 20px;
        text-align: center;
        color: #000;
        box-shadow: 0 10px 25px rgba(0,0,0,0.2);
    }
    .card {
        background: rgba(255,255,255,0.85);
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 5px 15px rgba(0,0,0,0.15);
    }
    </style>
    """, unsafe_allow_html=True)

    # HERO SECTION
    st.markdown("""
    <div class="hero">
        <h1>🧵 AI-Based Fabric Defect Detection and Fabric Type Classification System</h1>
        <p><b>Smart Quality Control using Deep Learning (YOLO)</b></p>
        <p>Real-time defect detection</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("## 🚀 Project Overview")

    st.markdown("""
    This system uses **Artificial Intelligence** to automatically detect defects in fabric materials.
    
    Traditional manual inspection:
    ❌ Time consuming  
    ❌ Human errors  
    ❌ Not scalable  
    
    Our system:
    ✅ Fast detection  
  
    ✅ Real-time monitoring    
    """)

    st.markdown("---")

    # FEATURES
    st.markdown("## 🔥 Key Features")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        <div class="card">
        <h4>📷 Image Detection</h4>
        Upload fabric image and detect defects instantly.
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="card">
        <h4>🎥 Video Analysis</h4>
        Detect defects from recorded video frames.
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="card">
        <h4>📊 Model Metrics</h4>
        Track precision, recall, and mAP performance.
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="card">
        <h4>📡 Live Detection</h4>
        Real-time webcam monitoring for defects.
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="card">
        <h4>🧠 YOLO AI Model</h4>
        Deep learning model trained for fabric defects.
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="card">
        <h4>👨‍💼 Admin Dashboard</h4>
        Monitor operator performance and defect logs.
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # WORKFLOW
    st.markdown("## ⚙️ How It Works")

    st.markdown("""
    1️⃣ Capture image / video / live stream  
    2️⃣ YOLO model processes input  
    3️⃣ Detects defects with bounding boxes  
    4️⃣ Calculates confidence score  
    5️⃣ Generates quality report  
    """)

    st.markdown("---")

    # DEFECT TYPES
    st.markdown("## 🧩 Detectable Defects")

    st.markdown("""
    - 🕳️ Hole  
    - 🧵 Broken Thread  
    - 🛢️ Oil Stain  
    - ✂️ Cutting Defect  
    - ⚡ Crack / Damage  
    - 🎨 Color Variation  
    """)

    st.markdown("---")

    # BENEFITS
    st.markdown("## 💡 Benefits")

    col1, col2, col3 = st.columns(3)

    col1.metric("⚡ Speed", "Fast Detection")
    col2.metric("🎯 Accuracy", "High Precision")
    col3.metric("🏭 Industry", "Automation Ready")

    st.markdown("---")

    # FINAL SECTION
    st.success("🚀 Ready to detect fabric defects using AI!")

    st.info("👉 Use sidebar to navigate through features")