import streamlit as st
import cloudinary
import cloudinary.uploader
import io
import datetime
from PIL import Image
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="อัพโหลดใบเสร็จ", page_icon="🧾", layout="centered")

# ── ชีตรายชื่อผู้ส่ง (autocomplete) ──
# ต้องแชร์ชีตนี้ให้ service account (client_email) ด้วย อย่างน้อยสิทธิ์ Editor
NAME_SHEET_ID = "1P1RVAJy-1tqHGMR2MyhM-DmAlTUDyrI8f71Qaf0Moko"

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; }
    .stApp { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }
    .block-container { background: white; border-radius: 20px; padding: 2.5rem 2rem !important; margin-top: 2rem; box-shadow: 0 20px 60px rgba(0,0,0,0.15); max-width: 680px; }
    h1 { color: #1a1a2e !important; font-weight: 700 !important; text-align: center; }
    .subtitle { text-align: center; color: #6b7280; margin-top: -0.5rem; margin-bottom: 1.5rem; font-size: 1rem; }
    .stButton > button { background: linear-gradient(135deg, #667eea, #764ba2) !important; color: white !important; border: none !important; border-radius: 12px !important; padding: 0.75rem 2rem !important; font-size: 1.1rem !important; font-weight: 600 !important; width: 100%; }
    .success-box { background: #f0fdf4; border: 2px solid #86efac; border-radius: 14px; padding: 1.2rem 1.5rem; color: #166534; margin-top: 1rem; }
    .error-box { background: #fef2f2; border: 2px solid #fca5a5; border-radius: 14px; padding: 1.2rem 1.5rem; color: #991b1b; margin-top: 1rem; }
    .divider { border: none; border-top: 1.5px solid #f3f4f6; margin: 1.5rem 0; }
    .rotate-btn button { padding: 0.35rem 0.5rem !important; font-size: 0.85rem !important; }
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

@st.cache_resource
def get_gspread_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=scopes
    )
    return gspread.authorize(creds)

@st.cache_resource
def setup_gsheet():
    """
    เชื่อมต่อ Google Sheets (Log) ผ่าน Service Account
    ต้องตั้งค่าใน .streamlit/secrets.toml แบบนี้:

    [gcp_service_account]
    type = "service_account"
    project_id = "..."
    private_key_id = "..."
    private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
    client_email = "...@....iam.gserviceaccount.com"
    client_id = "..."
    token_uri = "https://oauth2.googleapis.com/token"

    [gsheet]
    sheet_id = "GOOGLE_SHEET_ID_ตรงนี้"
    worksheet_name = "Log"

    และอย่าลืม "แชร์" Google Sheet ให้กับอีเมลใน client_email (สิทธิ์ Editor)
    """
    client = get_gspread_client()
    sh = client.open_by_key(st.secrets["gsheet"]["sheet_id"])
    ws_name = st.secrets["gsheet"].get("worksheet_name", "Log")
    try:
        ws = sh.worksheet(ws_name)
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title=ws_name, rows=1000, cols=10)
        ws.append_row(["วันที่-เวลา", "ผู้ส่ง", "ชื่อไฟล์", "จำนวนใบเสร็จ", "ขนาด (KB)", "ขนาดภาพ (px)", "ลิงก์รูป"])
    return ws

# ─────────────────────────────────────────────
#  รายชื่อผู้ส่ง (ดึงจากชีตรายชื่อ → ใช้ autocomplete)
# ─────────────────────────────────────────────
@st.cache_data(ttl=120, show_spinner=False)
def load_sender_names() -> list[str]:
    """
    ดึงรายชื่อจากชีตรายชื่อ (NAME_SHEET_ID) แท็บแรก
    - ถ้ามีหัวคอลัมน์ชื่อ "ผู้ส่ง" หรือ "ชื่อ" จะใช้คอลัมน์นั้น
    - ถ้าไม่มี จะใช้คอลัมน์แรก (ข้ามหัวตารางถ้าดูเหมือนหัวตาราง)
    cache 2 นาที — ชื่อที่เพิ่มใหม่ในชีตจะโผล่มาเองภายใน 2 นาที
    """
    try:
        client = get_gspread_client()
        ws = client.open_by_key(NAME_SHEET_ID).get_worksheet(0)
        rows = ws.get_all_values()
        if not rows:
            return []

        header = [c.strip() for c in rows[0]]
        col_idx = None
        for key in ("ผู้ส่ง", "ชื่อผู้ส่ง", "ชื่อ", "name", "Name"):
            if key in header:
                col_idx = header.index(key)
                break

        if col_idx is not None:
            values = [r[col_idx] for r in rows[1:] if len(r) > col_idx]
        else:
            # ใช้คอลัมน์แรก; ถ้าแถวแรกดูเป็นหัวตาราง (มีคำว่า ชื่อ/ผู้ส่ง) ให้ข้าม
            start = 1 if any(k in header[0] for k in ("ชื่อ", "ผู้ส่ง", "name", "Name")) else 0
            values = [r[0] for r in rows[start:] if r and r[0]]

        # ตัดช่องว่าง + ตัดค่าซ้ำ (คงลำดับเดิม)
        seen, names = set(), []
        for v in values:
            v = v.strip()
            if v and v not in seen:
                seen.add(v)
                names.append(v)
        return names
    except Exception:
        return []

def add_sender_name_to_sheet(name: str):
    """ถ้าเป็นชื่อใหม่ (พิมพ์เอง ไม่ได้เลือกจากรายการ) ให้บันทึกเพิ่มลงชีตรายชื่อ"""
    try:
        client = get_gspread_client()
        ws = client.open_by_key(NAME_SHEET_ID).get_worksheet(0)
        ws.append_row([name])
        load_sender_names.clear()  # ล้าง cache ให้รายชื่อล่าสุดโผล่ทันที
    except Exception:
        pass  # เพิ่มชื่อไม่สำเร็จ ไม่ต้อง block การอัพโหลด

def log_to_gsheet(sender_name, filename, num_receipts, size_kb, dim, url):
    try:
        ws = setup_gsheet()
        ws.append_row([
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            sender_name,
            filename,
            num_receipts,
            size_kb,
            dim,
            url,
        ])
        return True, ""
    except Exception as e:
        return False, str(e)

def compress_image(file, max_side: int = 1600, quality: int = 82, rotation: int = 0) -> tuple[bytes, int, int]:
    """
    ลดขนาดรูปให้ด้านยาวไม่เกิน max_side px แล้ว compress เป็น JPEG
    คืน (bytes, new_width, new_height)
    rotation: องศาที่ต้องการหมุน (ตามเข็มนาฬิกา) เช่น 90, 180, 270
    """
    img = Image.open(file)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    if rotation:
        # PIL rotate หมุนทวนเข็ม ดังนั้นใส่ค่าลบเพื่อให้หมุนตามเข็ม
        img = img.rotate(-rotation, expand=True)
    w, h = img.size
    if max(w, h) > max_side:
        scale = max_side / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=True)
    return buf.getvalue(), img.width, img.height

def upload_to_cloudinary(image_bytes, filename, num_receipts):
    folder_map = {1: "1_ใบเสร็จ", 2: "2_ใบเสร็จ", 3: "3_ใบเสร็จ"}
    result = cloudinary.uploader.upload(
        image_bytes,
        folder=f"ใบเสร็จ/{folder_map[num_receipts]}",
        public_id=filename,
        resource_type="image",
        overwrite=False,
    )
    return result.get("secure_url", "")

setup_cloudinary()

st.markdown("# 🧾 อัพโหลดใบเสร็จ")
st.markdown('<p class="subtitle">รูปจะถูกส่งเข้า Cloudinary โดยตรง · ปลอดภัย</p>', unsafe_allow_html=True)
st.markdown('<hr class="divider">', unsafe_allow_html=True)

st.markdown("#### 📋 จำนวนใบเสร็จในรูป")
mode = st.radio("โหมด", ["1 ใบเสร็จ", "2 ใบเสร็จ", "3 ใบเสร็จ"], label_visibility="collapsed")
num_receipts = int(mode[0])

st.markdown('<hr class="divider">', unsafe_allow_html=True)
st.markdown("#### 👤 ชื่อผู้ส่ง")

sender_options = load_sender_names()

# selectbox แบบพิมพ์ค้นหาได้: พิมพ์ขึ้นต้นแล้วรายชื่อจากชีตจะโผล่ให้เลือกทันที
# accept_new_options=True = ถ้าไม่มีชื่อในรายการ ก็พิมพ์ชื่อใหม่ได้เลย (ต้องใช้ Streamlit >= 1.45)
sender_name = st.selectbox(
    "ชื่อผู้ส่ง",
    options=sender_options,
    index=None,
    placeholder="พิมพ์ชื่อเพื่อค้นหา หรือพิมพ์ชื่อใหม่... เช่น สมชาย, ฝ่ายบัญชี",
    accept_new_options=True,
    label_visibility="collapsed",
)
sender_name = (sender_name or "").strip()

if not sender_options:
    st.caption("⚠️ ยังโหลดรายชื่อจากชีตไม่ได้ — เช็คว่าแชร์ชีตรายชื่อให้ service account แล้ว (ยังพิมพ์ชื่อเองได้ตามปกติ)")

st.markdown('<hr class="divider">', unsafe_allow_html=True)
st.markdown("#### 📷 เลือกรูปภาพ (เลือกได้หลายรูปพร้อมกัน)")
st.caption("💡 กด Ctrl ค้างไว้แล้วคลิกเลือกหลายรูปพร้อมกัน")

uploaded_files = st.file_uploader(
    "เลือกไฟล์",
    type=["jpg", "jpeg", "png", "webp"],
    accept_multiple_files=True,
    label_visibility="collapsed",
)

# เก็บองศาที่หมุนของแต่ละรูป (key = ชื่อไฟล์ + ขนาดไฟล์ เพื่อกันชนกันเวลาไฟล์ชื่อซ้ำ)
if "rotations" not in st.session_state:
    st.session_state.rotations = {}

if uploaded_files:
    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    st.markdown(f"#### 🔍 รูปที่เลือก ({len(uploaded_files)} รูป)")

    cols = st.columns(3)
    for i, f in enumerate(uploaded_files):
        file_key = f"{f.name}_{f.size}"
        if file_key not in st.session_state.rotations:
            st.session_state.rotations[file_key] = 0

        with cols[i % 3]:
            rotation = st.session_state.rotations[file_key]

            # แสดงภาพ preview ที่หมุนแล้ว (ไม่ยุ่งกับไฟล์ต้นฉบับ)
            img_preview = Image.open(f)
            if img_preview.mode in ("RGBA", "P"):
                img_preview = img_preview.convert("RGB")
            if rotation:
                img_preview = img_preview.rotate(-rotation, expand=True)

            st.image(img_preview, caption=f.name, use_container_width=True)

            st.markdown('<div class="rotate-btn">', unsafe_allow_html=True)
            if st.button("🔄 หมุน 90°", key=f"rotate_{file_key}_{i}"):
                st.session_state.rotations[file_key] = (rotation + 90) % 360
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    st.info(f"จะบันทึกในโฟลเดอร์ {num_receipts}_ใบเสร็จ ทั้ง {len(uploaded_files)} รูป")
    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    if st.button(f"☁️ อัพโหลดทั้งหมด ({len(uploaded_files)} รูป)"):
        if not sender_name:
            st.markdown('<div class="error-box">⚠️ กรุณาเลือกหรือกรอกชื่อผู้ส่งก่อนอัพโหลด</div>', unsafe_allow_html=True)
        else:
            safe_sender = sender_name.replace("/", "-").replace("\\", "-")
            results = []
            log_errors = []
            prog = st.progress(0, text="กำลังอัพโหลด...")

            for idx, f in enumerate(uploaded_files):
                try:
                    file_key = f"{f.name}_{f.size}"
                    rotation = st.session_state.rotations.get(file_key, 0)

                    # ── compress: max 1600px ด้านยาว, quality 82, หมุนตามที่ตั้งค่า ──
                    img_bytes, new_w, new_h = compress_image(f, max_side=1600, quality=82, rotation=rotation)

                    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    fname = f"{safe_sender}_{ts}_{idx+1}"
                    url = upload_to_cloudinary(img_bytes, fname, num_receipts)
                    size_kb = round(len(img_bytes) / 1024)
                    dim = f"{new_w}×{new_h}"

                    results.append({
                        "filename": fname,
                        "ok": True,
                        "size_kb": size_kb,
                        "dim": dim,
                    })

                    # ── บันทึกลง Google Sheet ──
                    log_ok, log_err = log_to_gsheet(
                        sender_name, fname, num_receipts, size_kb, dim, url
                    )
                    if not log_ok:
                        log_errors.append(f"{fname}: {log_err}")

                except Exception as e:
                    results.append({"filename": f.name, "ok": False, "err": str(e)})

                prog.progress((idx+1)/len(uploaded_files), text=f"อัพโหลด {idx+1}/{len(uploaded_files)}...")

            prog.empty()

            # ── ถ้าเป็นชื่อใหม่ที่ไม่อยู่ในชีตรายชื่อ ให้เพิ่มเข้าไปอัตโนมัติ ──
            if sender_name and sender_name not in sender_options:
                add_sender_name_to_sheet(sender_name)

            ok   = [r for r in results if r["ok"]]
            fail = [r for r in results if not r["ok"]]

            if ok:
                lines = [f"<strong>✅ อัพโหลดสำเร็จ {len(ok)} รูป!</strong>"]
                for r in ok:
                    lines.append(f"📄 {r['filename']}.jpg &nbsp;·&nbsp; {r['dim']} px &nbsp;·&nbsp; {r['size_kb']} KB")
                st.markdown(f'<div class="success-box">{"<br>".join(lines)}</div>', unsafe_allow_html=True)
            if fail:
                lines = [f"<strong>❌ ไม่สำเร็จ {len(fail)} รูป</strong>"]
                lines += [f"• {r['filename']}: {r.get('err','')}" for r in fail]
                st.markdown(f'<div class="error-box">{"<br>".join(lines)}</div>', unsafe_allow_html=True)
            if log_errors:
                st.warning("⚠️ อัพโหลดรูปสำเร็จ แต่บันทึกลง Google Sheet ไม่สำเร็จบางรายการ:\n" + "\n".join(log_errors))

st.markdown('<hr class="divider">', unsafe_allow_html=True)
st.markdown('<p style="text-align:center;color:#d1d5db;font-size:0.8rem;">รูปทั้งหมดจะถูกส่งเข้าบัญชี Cloudinary ของเจ้าของระบบเท่านั้น</p>', unsafe_allow_html=True)
