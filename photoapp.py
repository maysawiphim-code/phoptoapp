import streamlit as st
import cloudinary
import cloudinary.uploader
import io
import datetime
import traceback
from PIL import Image

# ─────────────────────────────────────────
#  Page Config
# ─────────────────────────────────────────
st.set_page_config(
    page_title="อัพโหลดใบเสร็จ",
    page_icon="🧾",
    layout="centered",
)

# ─────────────────────────────────────────
#  Custom CSS
# ─────────────────────────────────────────
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
    .stRadio > div { gap: 0.5rem; }
    .stRadio label {
        background: #f9fafb; border: 2px solid #e5e7eb;
        border-radius: 12px; padding: 0.9rem 1.2rem !important;
        font-size: 1rem !important; color: #374151 !important;
        transition: all 0.2s; cursor: pointer; width: 100%;
    }
    .stRadio label:hover { border-color: #667eea; background: #f5f3ff; }
    div[data-testid="stFileUploader"] {
        border: 2.5px dashed #c4b5fd;
        border-radius: 16px; background: #faf5ff; padding: 1rem;
    }
    .stButton > button {
        background: linear-gradient(135deg, #667eea, #764ba2) !important;
        color: white !important; border: none !important;
        border-radius: 12px !important; padding: 0.75rem 2rem !important;
        font-size: 1.1rem !important; font-weight: 600 !important;
        width: 100%; transition: opacity 0.2s !important;
        font-family: 'Sarabun', sans-serif !important;
    }
    .stButton > button:hover { opacity: 0.9 !important; }
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
    .divider { border: none; border-top: 1.5px solid #f3f4f6; margin: 1.5rem 0; }
    .preview-label { font-size: 0.85rem; color: #9ca3af; margin-bottom: 0.3rem; text-align: center; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────
#  Cloudinary Setup
# ─────────────────────────────────────────
@st.cache_resource
def setup_cloudinary():
    cloudinary.config(
        cloud_name=st.secrets["cloudinary"]["cloud_name"],
        api_key=st.secrets["cloudinary"]["api_key"],
        api_secret=st.secrets["cloudinary"]["api_secret"],
        secure=True
    )
    return True


def upload_to_cloudinary(image_bytes: bytes, filename: str, folder: str) -> str:
    """อัพโหลดรูปขึ้น Cloudinary และคืน URL"""
    result = cloudinary.uploader.upload(
        image_bytes,
        folder=f"ใบเสร็จ/{folder}",
        public_id=filename,
        resource_type="image",
        type="private",  # private ดูได้เฉพาะเจ้าของ
    )
    return result.get("secure_url", "")


def crop_image(image: Image.Image, part: int, total: int) -> Image.Image:
    w, h = image.size
    section_h = h // total
    top = section_h * part
    bottom = h if part == total - 1 else section_h * (part + 1)
    return image.crop((0, top, w, bottom))


# ─────────────────────────────────────────
#  UI
# ─────────────────────────────────────────
setup_cloudinary()

st.markdown("# 🧾 อัพโหลดใบเสร็จ")
st.markdown('<p class="subtitle">รูปจะถูกส่งเข้า Cloudinary โดยตรง · ปลอดภัย · ไม่มีการเก็บข้อมูล</p>', unsafe_allow_html=True)
st.markdown('<hr class="divider">', unsafe_allow_html=True)

# ── เลือกโหมด ──
st.markdown("#### 📋 เลือกจำนวนใบเสร็จในรูป")
mode = st.radio(
    label="โหมด",
    options=["1 ใบเสร็จ (ทั้งรูป)", "2 ใบเสร็จ (แบ่งครึ่ง)", "3 ใบเสร็จ (แบ่งสาม)"],
    label_visibility="collapsed",
)
num_receipts = {"1 ใบเสร็จ (ทั้งรูป)": 1, "2 ใบเสร็จ (แบ่งครึ่ง)": 2, "3 ใบเสร็จ (แบ่งสาม)": 3}[mode]

st.markdown('<hr class="divider">', unsafe_allow_html=True)

# ── ชื่อผู้ส่ง ──
st.markdown("#### 👤 ชื่อผู้ส่ง")
sender_name = st.text_input(
    "ชื่อผู้ส่ง",
    placeholder="เช่น สมชาย, ฝ่ายบัญชี, สาขา 01 ...",
    label_visibility="collapsed",
)

st.markdown('<hr class="divider">', unsafe_allow_html=True)

# ── อัพโหลดรูป ──
st.markdown("#### 📷 เลือกรูปภาพ")
uploaded_file = st.file_uploader(
    "วางหรือเลือกไฟล์รูปภาพ",
    type=["jpg", "jpeg", "png", "webp"],
    label_visibility="collapsed",
)

# ── Preview ──
if uploaded_file:
    image = Image.open(uploaded_file)
    if image.mode in ("RGBA", "P"):
        image = image.convert("RGB")

    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    st.markdown("#### 🔍 ตัวอย่างก่อนอัพโหลด")

    if num_receipts == 1:
        st.markdown('<p class="preview-label">ใบเสร็จ 1 — ทั้งรูป</p>', unsafe_allow_html=True)
        st.image(image, use_container_width=True)
    else:
        cols = st.columns(num_receipts)
        for i in range(num_receipts):
            cropped = crop_image(image, i, num_receipts)
            with cols[i]:
                st.markdown(f'<p class="preview-label">ใบเสร็จ {i+1}</p>', unsafe_allow_html=True)
                st.image(cropped, use_container_width=True)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # ── ปุ่มอัพโหลด ──
    if st.button("☁️ อัพโหลดใบเสร็จ"):
        if not sender_name.strip():
            st.markdown('<div class="error-box">⚠️ กรุณากรอกชื่อผู้ส่งก่อนอัพโหลด</div>', unsafe_allow_html=True)
        else:
            try:
                with st.spinner("กำลังอัพโหลด..."):
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    safe_sender = sender_name.strip().replace("/", "-").replace("\\", "-")
                    sub_folder = f"{num_receipts} ใบเสร็จ"
                    links = []

                    if num_receipts == 1:
                        buf = io.BytesIO()
                        image.save(buf, format="JPEG", quality=92)
                        filename = f"{safe_sender}_{timestamp}"
                        url = upload_to_cloudinary(buf.getvalue(), filename, sub_folder)
                        links.append((f"{filename}.jpg", url))
                    else:
                        for i in range(num_receipts):
                            cropped = crop_image(image, i, num_receipts)
                            buf = io.BytesIO()
                            cropped.save(buf, format="JPEG", quality=92)
                            filename = f"{safe_sender}_{timestamp}_สวนที่{i+1}"
                            url = upload_to_cloudinary(buf.getvalue(), filename, sub_folder)
                            links.append((f"{filename}.jpg", url))

                result_html = f"""
                <div class="success-box">
                    <strong>✅ อัพโหลดสำเร็จ {len(links)} ไฟล์!</strong><br>
                    <span style="font-size:0.9rem">📁 บันทึกใน: ใบเสร็จ / {sub_folder}</span><br><br>
                """
                for name, url in links:
                    result_html += f'📄 {name}<br>'
                result_html += "</div>"
                st.markdown(result_html, unsafe_allow_html=True)

            except Exception as e:
                st.markdown(f'<div class="error-box">❌ เกิดข้อผิดพลาด: {e}</div>', unsafe_allow_html=True)
                st.code(traceback.format_exc())

# ── Footer ──
st.markdown('<hr class="divider">', unsafe_allow_html=True)
st.markdown('<p style="text-align:center;color:#d1d5db;font-size:0.8rem;">รูปทั้งหมดจะถูกส่งเข้าบัญชี Cloudinary ของเจ้าของระบบเท่านั้น</p>', unsafe_allow_html=True)
