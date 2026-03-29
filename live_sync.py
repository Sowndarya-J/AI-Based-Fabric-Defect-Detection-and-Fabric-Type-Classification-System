from datetime import datetime, timezone
from io import BytesIO
import streamlit as st
from supabase import create_client


@st.cache_resource
def get_supabase():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"]
    )


def push_live_status(data):
    supabase = get_supabase()
    return supabase.table("live_operator_status").upsert(
        data,
        on_conflict="operator_id"
    ).execute()


def set_operator_offline(operator_id):
    supabase = get_supabase()
    return supabase.table("live_operator_status").update({
        "is_online": False,
        "last_updated": datetime.now(timezone.utc).isoformat()
    }).eq("operator_id", operator_id).execute()


def fetch_live_status():
    supabase = get_supabase()
    return supabase.table("live_operator_status") \
        .select("*") \
        .order("last_updated", desc=True) \
        .execute()


def upload_live_frame(pil_image, operator_id):
    supabase = get_supabase()

    buffer = BytesIO()
    pil_image.save(buffer, format="JPEG", quality=85)
    buffer.seek(0)

    file_path = f"{operator_id}/latest.jpg"

    supabase.storage.from_("live-frames").upload(
        path=file_path,
        file=buffer.getvalue(),
        file_options={"content-type": "image/jpeg", "upsert": "true"}
    )

    return supabase.storage.from_("live-frames").get_public_url(file_path)
