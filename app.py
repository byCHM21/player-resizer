import streamlit as st
from PIL import Image, ImageOps
from rembg import new_session, remove
import io
import zipfile
from pathlib import Path

st.set_page_config(page_title="Player Image Cutter (Batch)", page_icon="⚽")
st.title("⚽ Player Image Dicut & Batch Resize")
st.write("อัปโหลดรูปนักเตะพร้อมกันหลายคน เลือกลีก และดาวน์โหลดไฟล์ผลลัพธ์ทั้งหมดเป็น ZIP")

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

@st.cache_resource
def load_session():
    return new_session("u2net")

session = load_session()

def process_player(image: Image.Image, target_w: int, target_h: int, mode: str):
    image = ImageOps.exif_transpose(image)
    
    # ป้องกันแรมเต็ม
    max_dim = 2000
    if max(image.size) > max_dim:
        image.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
        
    cutout = remove(image.convert("RGBA"), session=session)
    
    bbox = cutout.getbbox()
    if bbox:
        cutout = cutout.crop(bbox)
        
    src_w, src_h = cutout.size
    
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

# แผงตั้งค่า
col1, col2 = st.columns(2)
with col1:
    tier = st.selectbox("เลือกลีก", ["T1", "T2"])
with col2:
    preset = st.selectbox("ประเภทกราฟิก", list(CONFIG[tier].keys()))

# เปิดให้อัปโหลดพร้อมกันได้หลายไฟล์ (accept_multiple_files=True)
uploaded_files = st.file_uploader(
    "เลือกรูปภาพนักเตะ (เลือกพร้อมกันหลายไฟล์ได้)", 
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True
)

if uploaded_files:
    st.info(f"เลือกไว้ทั้งหมด {len(uploaded_files)} ไฟล์")
    
    if st.button("🚀 เริ่มประมวลผลทั้งหมด", type="primary"):
        w, h = CONFIG[tier][preset]["size"]
        m = CONFIG[tier][preset]["mode"]
        clean_preset_name = preset.split(" ")[0].lower()
        
        # Buffer สำหรับสร้างไฟล์ ZIP ในหน่วยความจำ
        zip_buffer = io.BytesIO()
        
        # แถบแสดงความคืบหน้า (Progress Bar)
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for idx, uploaded_file in enumerate(uploaded_files):
                status_text.text(f"กำลังประมวลผล [{idx + 1}/{len(uploaded_files)}]: {uploaded_file.name}")
                
                img = Image.open(uploaded_file)
                result_img = process_player(img, w, h, m)
                
                # แปลงเป็น PNG และเก็บลงใน ZIP
                img_byte_arr = io.BytesIO()
                result_img.save(img_byte_arr, format="PNG")
                
                file_stem = Path(uploaded_file.name).stem
                out_name = f"{file_stem}_{tier}_{clean_preset_name}_{w}x{h}.png"
                zip_file.writestr(out_name, img_byte_arr.getvalue())
                
                # อัปเดตสถานะ Progress Bar
                progress_bar.progress((idx + 1) / len(uploaded_files))
                
        status_text.text("✅ ประมวลผลเสร็จสิ้นทุกไฟล์แล้ว!")
        st.success(f"แปลงรูปภาพสำเร็จครบทั้ง {len(uploaded_files)} รูป")
        
        # ปุ่มดาวน์โหลดไฟล์ ZIP รวม
        st.download_button(
            label="📦 ดาวน์โหลดรูปทั้งหมด (.ZIP)",
            data=zip_buffer.getvalue(),
            file_name=f"players_{tier}_{clean_preset_name}_{w}x{h}.zip",
            mime="application/zip"
        )
