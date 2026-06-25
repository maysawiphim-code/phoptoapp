import streamlit as st
import cloudinary
import cloudinary.uploader
import io
import datetime
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
    .stApp { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }
    .block-container {
        background: white; border-radius: 20px;
        padding: 2.5rem 2rem !important; margin-top: 2rem;
        box-shadow: 0 20px 60px rgba(0,0,0,0.15); max-width: 680px;
    }
    h1 { color: #1a1a2e !important; font-weight: 700 !important; text-align: center; }
    .subtitle { text-align: center; color: #6b7280; margin-top: -0.5rem; margin-bottom: 1.5rem; font-size: 1rem; }
    .stButton > button {
        background: linear-gradient(135deg, #667eea, #764ba2) !important;
        color: white !important; border: none !important;
        border-radius: 12px !important; padding: 0.75rem 2rem !important;
        font-size: 1.1rem !important; font-weight: 600 !important; width: 100%;
    }
    .success-box { background: #f0fdf4; border: 2px solid #86efac; border-radius: 14px; padding: 1.2rem 1.5rem; color: #166534; margin-top: 1rem; }
    .error-box { background: #fef2f2; border: 2px solid #fca5a5; border-radius: 14px; padding: 1.2rem 1.5rem; color: #991b1b; margin-top: 1rem; }
    .divider { border: none; border-top: 1.5px solid #f3f4f6; margin: 1.5rem 0; }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def setup_cloudinary():
    cloudinary.config(
        cloud_name=st.secrets["cloudinary"]["cloud_name"],
        api_key=st.secrets["cloudinary"]["api_key"],
        api_secret=st.secrets["cloudinary"]["api_secret"],
        secure=True
    )
    return True

def upload_to_cloudinary(image_bytes, filename, num_receipts):
    folder_map = {1: "1_ใบเสร็จ", 2: "2_ใบเสร็จ", 3: "3_ใบเสร็จ"}
    folder = f"ใบเสร็จ/{folder_map[num_receipts]}"
    result = cloudinary.uploader.upload(
        image_bytes, folder=folder, public_id=filename,
        resource_type="image", overwrite=False,
    )
    return result.get("secure_url", "")

setup_cloudinary()

# session state
for key, val in [("queue", []), ("results", []), ("uploader_key", 0)]:
    if key not in st.session_state:
        st.session_state[key] = val

# ── UI ──
st.markdown("# 🧾 อัพโหลดใบเสร็จ")
st.markdown('<p class="subtitle">รูปจะถูกส่งเข้า Cloudinary โดยตรง · ปลอดภัย</p>', unsafe_allow_html=True)
st.markdown('<hr class="divider">', unsafe_allow_html=True)

st.markdown("#### 📋 จำนวนใบเสร็จในรูป")
mode = st.radio("โหมด", ["1 ใบเสร็จ", "2 ใบเสร็จ", "3 ใบเสร็จ"], label_visibility="collapsed")
num_receipts = int(mode[0])

st.markdown('<hr class="divider">', unsafe_allow_html=True)
st.markdown("#### 👤 ชื่อผู้ส่ง")
sender_name = st.text_input("ชื่อผู้ส่ง", placeholder="เช่น สมชาย, ฝ่ายบัญชี ...", label_visibility="collapsed")

st.markdown('<hr class="divider">', unsafe_allow_html=True)
st.markdown("#### 📷 เลือกรูป")

# uploader key เปลี่ยนทุกครั้ง → widget รีเซ็ต → เลือกรูปใหม่ได้
uploaded = st.file_uploader(
    "เลือกไฟล์",
    type=["jpg", "jpeg", "png", "webp"],
    label_visibility="collapsed",
    key=f"up_{st.session_state.uploader_key}",
)

if uploaded:
    img = Image.open(uploaded)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    st.image(img, caption=uploaded.name, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("➕ เพิ่มรูปนี้"):
            # บันทึก bytes แทน PIL object เพื่อหลีกเลี่ยง pickling issue
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=92)
            st.session_state.queue.append({
                "bytes": buf.getvalue(),
                "name": uploaded.name,
            })
            st.session_state.uploader_key += 1  # รีเซ็ต uploader
            st.rerun()

# ── แสดงคิว ──
if st.session_state.queue:
    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    st.markdown(f"#### 🗂️ รูปในคิว ({len(st.session_state.queue)} รูป)")

    for i, item in enumerate(st.session_state.queue):
        c1, c2 = st.columns([4, 1])
        with c1:
            st.image(item["bytes"], caption=f"{i+1}. {item['name']}", use_container_width=True)
        with c2:
            st.write("")
            st.write("")
            if st.button("🗑️", key=f"del_{i}"):
                st.session_state.queue.pop(i)
                st.rerun()

    st.info(f"พร้อมอัพโหลด {len(st.session_state.queue)} รูป → โฟลเดอร์ {num_receipts}_ใบเสร็จ")
    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    if st.button(f"☁️ อัพโหลดทั้งหมด ({len(st.session_state.queue)} รูป)"):
        if not sender_name.strip():
            st.markdown('<div class="error-box">⚠️ กรุณากรอกชื่อผู้ส่งก่อนอัพโหลด</div>', unsafe_allow_html=True)
        else:
            safe_sender = sender_name.strip().replace("/", "-").replace("\\", "-")
            results = []
            prog = st.progress(0, text="กำลังอัพโหลด...")

            for idx, item in enumerate(st.session_state.queue):
                try:
                    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    fname = f"{safe_sender}_{ts}_{idx+1}"
                    url = upload_to_cloudinary(item["bytes"], fname, num_receipts)
                    results.append({"filename": fname, "ok": True})
                except Exception as e:
                    results.append({"filename": item["name"], "ok": False, "err": str(e)})

                prog.progress((idx+1)/len(st.session_state.queue), text=f"อัพโหลด {idx+1}/{len(st.session_state.queue)}...")

            prog.empty()
            st.session_state.results = results
            st.session_state.queue = []
            st.session_state.uploader_key += 1
            st.rerun()

# ── ผลลัพธ์ ──
if st.session_state.results:
    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    ok = [r for r in st.session_state.results if r["ok"]]
    fail = [r for r in st.session_state.results if not r["ok"]]

    if ok:
        lines = [f"<strong>✅ อัพโหลดสำเร็จ {len(ok)} รูป!</strong>"] + [f"📄 {r['filename']}.jpg" for r in ok]
        st.markdown(f'<div class="success-box">{"<br>".join(lines)}</div>', unsafe_allow_html=True)
    if fail:
        lines = [f"<strong>❌ ไม่สำเร็จ {len(fail)} รูป</strong>"] + [f"• {r['filename']}: {r.get('err','')}" for r in fail]
        st.markdown(f'<div class="error-box">{"<br>".join(lines)}</div>', unsafe_allow_html=True)

    if st.button("🔄 เริ่มใหม่"):
        st.session_state.results = []
        st.rerun()

st.markdown('<hr class="divider">', unsafe_allow_html=True)
st.markdown('<p style="text-align:center;color:#d1d5db;font-size:0.8rem;">รูปทั้งหมดจะถูกส่งเข้าบัญชี Cloudinary ของเจ้าของระบบเท่านั้น</p>', unsafe_allow_html=True)
