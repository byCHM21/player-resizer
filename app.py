import io
from pathlib import Path
from PIL import Image
from rembg import new_session, remove
import streamlit as st

# กำหนดค่าหน้าเว็บ
st.set_page_config(
    page_title="Player Image Cutter & Resizer",
    page_icon="⚽",
    layout="centered",
)

st.title("⚽ Player Image Dicut & Auto-Resize")
st.write("อัปโหลดรูปนักเตะ เลือกลีก และขนาดที่ต้องการเพื่อประมวลผลอัตโนมัติ")

# ค่าคอนฟิกขนาดตาม Requirement
CONFIG = {
    "T1": {
        "LINE UP (467x650)": {"size": (467, 650), "mode": "full"},
        "SUBSTITUTION (105x95)": {"size": (105, 95), "mode": "upper"},
        "PLAYER STATS (130x115)": {"size": (130, 115), "mode": "upper"},
    },
    "T2": {
        "LINE UP (145x105)": {"size": (145, 105), "mode": "upper"},
    },
}


# แคชโมเดล AI ไว้ในหน่วยความจำ ไม่ต้องโหลดซ้ำทุกครั้งที่กด
@st.cache_resource
def load_dicut_model():
    return new_session("birefnet-general")


session = load_dicut_model()


def process_player_image(
    image: Image.Image, target_w: int, target_h: int, mode: str
) -> Image.Image:
    # ตัดพื้นหลัง
    cutout = remove(image.convert("RGBA"), session=session)

    # ตัดขอบว่างโปร่งใสรอบตัวนักเตะ
    bbox = cutout.getbbox()
    if bbox:
        cutout = cutout.crop(bbox)

    src_w, src_h = cutout.size

    # กรณีภาพขนาดเล็ก ให้ครอปเน้นช่วงครึ่งตัวบน 60%
    if mode == "upper":
        crop_bottom = int(src_h * 0.60)
        cutout = cutout.crop((0, 0, src_w, crop_bottom))
        src_w, src_h = cutout.size

    # รักษาสัดส่วนภาพ (Aspect Ratio)
    scale = min(target_w / src_w, target_h / src_h)
    new_w = int(src_w * scale)
    new_h = int(src_h * scale)
    resized_img = cutout.resize((new_w, new_h), Image.Resampling.LANCZOS)

    # วางลงบน Canvas โปร่งใส จัดกึ่งกลางและชิดล่าง
    canvas = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
    offset_x = (target_w - new_w) // 2
    offset_y = target_h - new_h
    canvas.paste(resized_img, (offset_x, offset_y), resized_img)

    return canvas


# --- ส่วนติดต่อผู้ใช้ (UI Layout) ---
col1, col2 = st.columns(2)
with col1:
    selected_tier = st.selectbox("เลือกลีก (Tier)", options=["T1", "T2"])

with col2:
    available_presets = list(CONFIG[selected_tier].keys())
    selected_preset = st.selectbox("ประเภทกราฟิก", options=available_presets)

uploaded_file = st.file_uploader(
    "เลือกไฟล์รูปภาพนักเตะ (JPG / PNG)", type=["jpg", "jpeg", "png"]
)

if uploaded_file is not None:
    # แสดงรูปต้นฉบับ
    orig_image = Image.open(uploaded_file)
    st.image(
        orig_image,
        caption="รูปภาพต้นฉบับ",
        use_container_width=False,
        width=250,
    )

    if st.button("🚀 เริ่มตัดพื้นหลังและปรับขนาด", type="primary"):
        preset_info = CONFIG[selected_tier][selected_preset]
        target_w, target_h = preset_info["size"]
        mode = preset_info["mode"]

        with st.spinner("AI กำลังตัดขอบและจัดวางภาพ..."):
            result_img = process_player_image(
                orig_image, target_w, target_h, mode
            )

        st.success("ประมวลผลสำเร็จ!")

        # แสดงภาพผลลัพธ์
        st.image(
            result_img,
            caption=f"ผลลัพธ์: {selected_tier} - {selected_preset}",
            use_container_width=False,
        )

        # เตรียมปุ่มดาวน์โหลดไฟล์ PNG
        buf = io.BytesIO()
        result_img.save(buf, format="PNG")
        byte_im = buf.getvalue()

        clean_name = Path(uploaded_file.name).stem
        download_filename = (
            f"{clean_name}_{selected_tier}_{target_w}x{target_h}.png"
        )

        st.download_button(
            label="💾 ดาวน์โหลดรูปภาพ PNG",
            data=byte_im,
            file_name=download_filename,
            mime="image/png",
        )