import streamlit as st
from PIL import Image, ImageOps
from rembg import new_session, remove
import io
from pathlib import Path

st.set_page_config(page_title="Player Image Cutter", page_icon="⚽")
st.title("⚽ Player Image Dicut & Auto-Resize")

CONFIG = {
    "T1": {
        "LINE UP (467x650)": {"size": (467, 650), "mode": "full"},
        "SUBSTITUTION (105x95)": {"size": (105, 95), "mode": "upper"},
        "PLAYER STATS (130x115)": {"size": (130, 115), "mode": "upper"}
    },
    "T2": {
        "LINE UP (145x105)": {"size": (145, 105), "mode": "upper"}
    }
}

# ใช้โมเดล u2net เพื่อความเสถียรและไม่กินแรมจนเครื่องค้าง
@st.cache_resource
def load_session():
    return new_session("u2net")

session = load_session()

def process_player(image: Image.Image, target_w: int, target_h: int, mode: str):
    # ปรับแนวภาพตามกล้อง
    image = ImageOps.exif_transpose(image)
    
    # ป้องกันแรมเต็ม: ลดขนาดภาพต้นฉบับถ้าใหญ่เกิน 2000px
    max_dim = 2000
    if max(image.size) > max_dim:
        image.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
        
    # ตัดพื้นหลัง
    cutout = remove(image.convert("RGBA"), session=session)
    
    # ลบขอบโปร่งใสส่วนเกิน
    bbox = cutout.getbbox()
    if bbox:
        cutout = cutout.crop(bbox)
        
    src_w, src_h = cutout.size
    
    # กรณีภาพขนาดเล็ก ให้ตัดเน้นเฉพาะ 60% ตัวบน (หน้า/อก)
    if mode == "upper":
        cutout = cutout.crop((0, 0, src_w, int(src_h * 0.60)))
        src_w, src_h = cutout.size
        
    scale = min(target_w / src_w, target_h / src_h)
    new_w = max(1, int(src_w * scale))
    new_h = max(1, int(src_h * scale))
    resized_img = cutout.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    canvas = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
    canvas.paste(resized_img, ((target_w - new_w) // 2, target_h - new_h), resized_img)
    return canvas

col1, col2 = st.columns(2)
with col1:
    tier = st.selectbox("เลือกลีก", ["T1", "T2"])
with col2:
    preset = st.selectbox("ประเภทกราฟิก", list(CONFIG[tier].keys()))

uploaded = st.file_uploader("เลือกรูปภาพนักเตะ", type=["jpg", "jpeg", "png"])

if uploaded:
    img = Image.open(uploaded)
    st.image(img, width=250, caption="รูปต้นฉบับ")
    
    if st.button("เริ่มประมวลผล", type="primary"):
        w, h = CONFIG[tier][preset]["size"]
        m = CONFIG[tier][preset]["mode"]
        
        with st.spinner("กำลังตัดขอบและจัดขนาด..."):
            res = process_player(img, w, h, m)
            
        st.image(res, caption=f"ผลลัพธ์ ({w}x{h} px)")
        
        buf = io.BytesIO()
        res.save(buf, format="PNG")
        st.download_button(
            label="💾 ดาวน์โหลด PNG",
            data=buf.getvalue(),
            file_name=f"{Path(uploaded.name).stem}_{tier}_{w}x{h}.png",
            mime="image/png"
        )
