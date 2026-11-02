import streamlit as st
import PIL.Image
from PIL import ImageDraw, ImageFont, ImageStat
import tempfile
import os
import glob

if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip

st.set_page_config(page_title="Hệ Thống Video Template", layout="centered")
st.title("Tạo Video Đạo Lý - Tự Động Hóa Thông Minh")

os.makedirs("templates", exist_ok=True)
template_files = glob.glob("templates/*.jpg") + glob.glob("templates/*.png") + glob.glob("templates/*.jpeg")

# THUẬT TOÁN 1: QUÉT MÀU NỀN TỰ ĐỘNG
def get_optimal_colors(image, box):
    # Cắt lấy vùng ảnh chứa chữ để phân tích
    region = image.crop(box)
    stat = ImageStat.Stat(region)
    r, g, b = stat.mean[:3]
    
    # Tính độ sáng (Luminance) theo công thức chuẩn
    luminance = 0.299 * r + 0.587 * g + 0.114 * b
    
    if luminance > 135:
        # Nền sáng: Chữ đỏ đô, viền trắng mỏng để cắt nét
        return "#8C2131", "white" 
    else:
        # Nền tối: Chữ vàng nổi bật, viền đen
        return "#FACC15", "black"

# THUẬT TOÁN 2: TÔN TRỌNG ENTER & BẢO VỆ TRÀN VIỀN
def process_text_lines(text, font, max_width_px=980):
    # Tôn trọng dấu Enter (xuống dòng thủ công) của người dùng
    manual_lines = text.split('\n')
    final_lines = []
    
    for line in manual_lines:
        if not line.strip():
            final_lines.append("") # Hỗ trợ Enter 2 lần tạo khoảng trống
            continue
            
        # Nếu dòng quá dài, chia nhỏ nó ra theo pixel
        words = line.split()
        current_line = ""
        for word in words:
            test_line = current_line + " " + word if current_line else word
            if font.getlength(test_line) <= max_width_px:
                current_line = test_line
            else:
                final_lines.append(current_line)
                current_line = word
        if current_line:
            final_lines.append(current_line)
            
    return final_lines

if not template_files:
    st.info("💡 Thư mục 'templates' đang trống. Hãy thêm ảnh nền vào!")
else:
    selected_template = st.selectbox("1. Chọn mẫu nền", template_files, format_func=lambda x: os.path.basename(x))
    st.image(selected_template, caption="Ảnh xem trước", width=250)
        
    st.markdown("---")
    vid_file = st.file_uploader("2. Tải video (Tỷ lệ 16:9)", type=["mp4", "mov"])
    
    # Bỏ tiêu đề phụ, đổi thành nhập liệu Enter thoải mái
    main_title = st.text_area("3. Tiêu đề chính (Bấm Enter để chủ động xuống dòng tự do)")
    
    if st.button("Tạo Video Ngay", use_container_width=True):
        if vid_file and main_title:
            with st.spinner("Đang phân tích màu sắc và kết xuất video..."):
                tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') 
                tfile.write(vid_file.read())
                tfile.close()
                
                img = PIL.Image.open(selected_template).convert("RGB")
                img = img.resize((1080, 1920))
                draw = ImageDraw.Draw(img)
                
                try:
                    font_main = ImageFont.truetype("font_serif.ttf", 90)
                except IOError:
                    font_main = ImageFont.load_default()
                
                # --- AUTO MÀU CHỮ CHUYÊN NGHIỆP ---
                # Chỉ xét màu của khu vực nửa dưới (từ pixel 1200 đến 1920)
                text_box_region = (0, 1200, 1080, 1920)
                text_color, stroke_color = get_optimal_colors(img, text_box_region)
                
                # --- CHÈN CHỮ CHỦ ĐỘNG XUỐNG DÒNG ---
                lines = process_text_lines(main_title, font_main, max_width_px=980)
                total_height = len(lines) * 120
                
                # Tọa độ vùng dưới đẩy lên một chút vì video đã đẩy lên
                start_y = 1450 - (total_height / 2)
                
                for line in lines:
                    if line: 
                        draw.text((540, start_y), line, font=font_main, fill=text_color, anchor="mm", stroke_width=3, stroke_fill=stroke_color)
                    start_y += 120
                    
                img.save("temp_bg.jpg")
                
                # --- CHÈN VIDEO (ĐẨY LÊN 3CM) ---
                video = VideoFileClip(tfile.name).resize(width=1080)
                background = ImageClip("temp_bg.jpg").set_duration(video.duration)
                
                # Tham số y=400 đẩy video lên trên (Thay vì center là 656)
                final = CompositeVideoClip([background, video.set_position(("center", 400))])
                
                output_path = "output_video.mp4"
                final.write_videofile(output_path, fps=30, codec="libx264", audio_codec="aac")
                
                st.success("Tuyệt vời! Video của bạn đã sẵn sàng.")
                st.video(output_path)
                with open(output_path, "rb") as file:
                    st.download_button("⬇️ Tải Video Về Máy", data=file, file_name="video_hoan_thanh.mp4", mime="video/mp4")
                    
                video.close()
                background.close()
                final.close()
                if os.path.exists(tfile.name): os.remove(tfile.name)
                if os.path.exists("temp_bg.jpg"): os.remove("temp_bg.jpg")
        else:
            st.error("Vui lòng tải lên video và nhập tiêu đề chính!")