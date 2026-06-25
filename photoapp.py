import streamlit as st
import cloudinary
import cloudinary.uploader
import io
import datetime
import traceback
from PIL import Image

st.set_page_config(
    page_title="อัพโหลดใบเสร็จ",
    page_icon="🧾",
    layout="centered",
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; }
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        min-height: 100vh;
    }
    .block-container {
        background: white;
        border-radius: 20px;
        padding: 2.5rem 2rem !important;
        margin-top: 2rem;
        box-shadow: 0 20px 60px rgba(0,0,0,0.15);
        max-width: 680px;
    }
    h1 { color: #1a1a2e !important; font-weight: 700 !important; text-align: center; }
    .subtitle {
        text-align: center; color: #6b7280;
        margin-top: -0.5rem; margin-bottom: 1.5rem; font-size: 1rem;
    }
    .stButton > button {
        background: linear-gradient(135deg, #667eea, #764ba2) !important;
        color: white !important; border: none !important;
        border-radius: 12px !important; padding: 0.75rem 2rem !important;
        font-size: 1.1rem !important; font-weight: 600 !important;
        width: 100%;
    }
    .success-box {
        background: #f0fdf4; border: 2px solid #86efac;
        border-radius: 14px; padding: 1.2rem 1.5rem;
        color: #166534; margin-top: 1rem;
    }
    .error-box {
        background: #fef2f2; border: 2px solid #fca5a5;
        border-radius: 14px; padding: 1.2rem 1.5rem;
        color: #991b1b; margin-top: 1rem;
    }
    .info-box {
        background: #eff6ff; border: 2px solid #93c5fd;
        border-radius: 14px; padding: 1rem 1.5rem;
        color: #1e40af; margin-top: 0.5rem; font-size: 0.95rem;
    }
    .divider { border: none; border-top: 1.5px solid #f3f4f6; margin: 1.5rem 0; }
    .image-card {
        border: 1.5px solid #e5e7eb;
        border-radius: 12px;
        padding: 0.75rem;
        margin-bottom: 0.75rem;
        background: #f9fafb;
    }
</style>
""", unsafe_allow_html=True)

# ── Cloudinary setup ──────────────────────────────────────────────────────────
@st.cache_resource
def setup_cloudinary():
    cloudinary.config(
        cloud_name=st.secrets["cloudinary"]["cloud_name"],
        api_key=st.secrets["cloudinary"]["api_key"],
        api_secret=st.secrets["cloudinary"]["api_secret"],
        secure=True
    )
    return True

def upload_to_cloudinary(image_bytes: bytes, filename: str, num_receipts: int) -> str:
    folder_map = {1: "1_ใบเสร็จ", 2: "2_ใบเสร็จ", 3: "3_ใบเสร็จ"}
    folder = f"ใบเสร็จ/{folder_map[num_receipts]}"
    result = cloudinary.uploader.upload(
        image_bytes,
        folder=folder,
        public_id=filename,
        resource_type="image",
        overwrite=False,
    )
    return result.get("secure_url", "")

setup_cloudinary()

# ── Session state init ────────────────────────────────────────────────────────
if "queued_images" not in st.session_state:
    st.session_state.queued_images = []   # list of {"pil": Image, "name": str}
if "upload_results" not in st.session_state:
    st.session_state.upload_results = []  # list of {"filename": str, "url": str, "ok": bool}
if "file_uploader_key" not in st.session_state:
    st.session_state.file_uploader_key = 0  # bump to reset the uploader widget

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("# 🧾 อัพโหลดใบเสร็จ")
st.markdown(
    '<p class="subtitle">รูปจะถูกส่งเข้า Cloudinary โดยตรง · ปลอดภัย · ไม่มีการเก็บข้อมูล</p>',
    unsafe_allow_html=True,
)
st.markdown('<hr class="divider">', unsafe_allow_html=True)

# ── Mode & sender ─────────────────────────────────────────────────────────────
st.markdown("#### 📋 เลือกจำนวนใบเสร็จในรูป")
mode = st.radio(
    label="โหมด",
    options=["1 ใบเสร็จ (ทั้งรูป)", "2 ใบเสร็จ (ทั้งรูป)", "3 ใบเสร็จ (ทั้งรูป)"],
    label_visibility="collapsed",
)
num_receipts = {"1 ใบเสร็จ (ทั้งรูป)": 1, "2 ใบเสร็จ (ทั้งรูป)": 2, "3 ใบเสร็จ (ทั้งรูป)": 3}[mode]

st.markdown('<hr class="divider">', unsafe_allow_html=True)
st.markdown("#### 👤 ชื่อผู้ส่ง")
sender_name = st.text_input(
    "ชื่อผู้ส่ง",
    placeholder="เช่น สมชาย, ฝ่ายบัญชี, สาขา 01 ...",
    label_visibility="collapsed",
)

# ── File uploader (reset key ทุกครั้งที่เพิ่มรูปสำเร็จ) ──────────────────────
st.markdown('<hr class="divider">', unsafe_allow_html=True)
st.markdown("#### 📷 เพิ่มรูปภาพ")

uploaded_file = st.file_uploader(
    "วางหรือเลือกไฟล์รูปภาพ (เพิ่มทีละรูปได้เรื่อย ๆ)",
    type=["jpg", "jpeg", "png", "webp"],
    label_visibility="collapsed",
    key=f"uploader_{st.session_state.file_uploader_key}",
)

# ── "เพิ่มรูปนี้" button ──────────────────────────────────────────────────────
if uploaded_file is not None:
    image = Image.open(uploaded_file)
    if image.mode in ("RGBA", "P"):
        image = image.convert("RGB")

    st.image(image, caption=f"ตัวอย่าง: {uploaded_file.name}", use_container_width=True)

    if st.button("➕ เพิ่มรูปนี้เข้าคิว"):
        st.session_state.queued_images.append(
            {"pil": image, "name": uploaded_file.name}
        )
        # bump key → รีเซ็ต uploader widget ให้เลือกรูปใหม่ได้ทันที
        st.session_state.file_uploader_key += 1
        st.rerun()

# ── แสดงคิวรูปที่รอ upload ───────────────────────────────────────────────────
if st.session_state.queued_images:
    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    st.markdown(f"#### 🗂️ รูปในคิว ({len(st.session_state.queued_images)} รูป)")

    cols_per_row = 3
    images = st.session_state.queued_images
    for row_start in range(0, len(images), cols_per_row):
        cols = st.columns(cols_per_row)
        for col_idx, img_data in enumerate(images[row_start: row_start + cols_per_row]):
            global_idx = row_start + col_idx
            with cols[col_idx]:
                st.image(img_data["pil"], use_container_width=True)
                st.caption(img_data["name"])
                if st.button("🗑️ ลบ", key=f"del_{global_idx}"):
                    st.session_state.queued_images.pop(global_idx)
                    st.rerun()

    st.info(f"พร้อมอัพโหลด {len(st.session_state.queued_images)} รูป → โฟลเดอร์ {num_receipts}_ใบเสร็จ")

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    if st.button(f"☁️ อัพโหลดทั้งหมด ({len(st.session_state.queued_images)} รูป)"):
        if not sender_name.strip():
            st.markdown(
                '<div class="error-box">⚠️ กรุณากรอกชื่อผู้ส่งก่อนอัพโหลด</div>',
                unsafe_allow_html=True,
            )
        else:
            safe_sender = sender_name.strip().replace("/", "-").replace("\\", "-")
            results = []
            progress = st.progress(0, text="กำลังอัพโหลด...")

            for idx, img_data in enumerate(st.session_state.queued_images):
                try:
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:19]
                    filename = f"{safe_sender}_{timestamp}_{idx+1}"

                    buf = io.BytesIO()
                    img_data["pil"].save(buf, format="JPEG", quality=92)

                    url = upload_to_cloudinary(buf.getvalue(), filename, num_receipts)
                    results.append({"filename": filename, "url": url, "ok": True})
                except Exception as e:
                    results.append({"filename": img_data["name"], "url": "", "ok": False, "err": str(e)})

                progress.progress((idx + 1) / len(st.session_state.queued_images),
                                   text=f"อัพโหลด {idx+1}/{len(st.session_state.queued_images)}...")

            progress.empty()
            st.session_state.upload_results = results
            st.session_state.queued_images = []   # ล้างคิว
            st.session_state.file_uploader_key += 1
            st.rerun()

# ── แสดงผลลัพธ์ ───────────────────────────────────────────────────────────────
if st.session_state.upload_results:
    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    st.markdown("#### ✅ ผลการอัพโหลด")

    success_count = sum(1 for r in st.session_state.upload_results if r["ok"])
    fail_count = len(st.session_state.upload_results) - success_count

    if success_count:
        lines = [f"<strong>✅ อัพโหลดสำเร็จ {success_count} รูป!</strong>"]
        for r in st.session_state.upload_results:
            if r["ok"]:
                lines.append(f"📄 {r['filename']}.jpg")
        st.markdown(
            f'<div class="success-box">{"<br>".join(lines)}</div>',
            unsafe_allow_html=True,
        )

    if fail_count:
        lines = [f"<strong>❌ อัพโหลดไม่สำเร็จ {fail_count} รูป</strong>"]
        for r in st.session_state.upload_results:
            if not r["ok"]:
                lines.append(f"• {r['filename']}: {r.get('err','unknown error')}")
        st.markdown(
            f'<div class="error-box">{"<br>".join(lines)}</div>',
            unsafe_allow_html=True,
        )

    if st.button("🔄 เริ่มใหม่"):
        st.session_state.upload_results = []
        st.rerun()

st.markdown('<hr class="divider">', unsafe_allow_html=True)
st.markdown(
    '<p style="text-align:center;color:#d1d5db;font-size:0.8rem;">รูปทั้งหมดจะถูกส่งเข้าบัญชี Cloudinary ของเจ้าของระบบเท่านั้น</p>',
    unsafe_allow_html=True,
)
