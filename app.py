import streamlit as st
import cv2
import numpy as np
import tempfile
import os

# 适配 MoviePy 2.0 的导入
from moviepy import VideoFileClip, AudioFileClip

# ================= 页面配置 =================
st.set_page_config(page_title="视频无损去水印", page_icon="🎬", layout="wide")

# ================= 🔐 密码保护逻辑 (新加的部分) =================

# 1. 这里设置你的密码！
MY_PASSWORD = "666" 

# 初始化 Session State (用来记住登录状态)
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

def check_password():
    """检查密码是否正确"""
    user_input = st.session_state['input_password']
    if user_input == MY_PASSWORD:
        st.session_state['logged_in'] = True
        st.session_state['input_password'] = ""  # 清空输入框
    else:
        st.error("❌ 密码错误，请联系管理员获取权限")

# 如果没登录，显示登录框
if not st.session_state['logged_in']:
    st.title("🔒 访问受限")
    st.markdown("该工具仅限内部使用，请输入访问密码。")
    st.text_input("请输入密码", type="password", key="input_password", on_change=check_password)
    st.stop()  # ⛔️ 停止运行下面的代码

# ================= 🎉 登录成功后显示的主程序 =================

st.title("🎬 视频无损去水印工具")
st.markdown("上传视频 -> 调整红框遮住水印 -> 一键去除 -> 保持原画质")

# ... (下面是之前的核心功能代码，不用动) ...

def process_video(input_path, output_path, mask_x, mask_y, mask_w, mask_h):
    cap = cv2.VideoCapture(input_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    temp_out_path = "temp_video_no_audio.mp4"
    fourcc = cv2.VideoWriter_fourcc(*'mp4v') 
    out = cv2.VideoWriter(temp_out_path, fourcc, fps, (width, height))

    progress_bar = st.progress(0)
    status_text = st.empty()
    frame_count = 0
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break

        mask = np.zeros((height, width), dtype=np.uint8)
        mask[mask_y:mask_y+mask_h, mask_x:mask_x+mask_w] = 255
        inpainted_frame = cv2.inpaint(frame, mask, 3, cv2.INPAINT_TELEA)
        out.write(inpainted_frame)

        frame_count += 1
        if frame_count % 10 == 0 and total_frames > 0:
            progress_bar.progress(min(frame_count / total_frames, 1.0))
            status_text.text(f"正在处理第 {frame_count}/{total_frames} 帧...")

    cap.release()
    out.release()
    progress_bar.progress(1.0)
    status_text.text("视频画面修复完成，正在合成音频...")

    try:
        new_video_clip = VideoFileClip(temp_out_path)
        original_video_clip = VideoFileClip(input_path)
        audio = original_video_clip.audio
        
        if audio:
            final_clip = new_video_clip.with_audio(audio)
        else:
            final_clip = new_video_clip

        final_clip.write_videofile(
            output_path, 
            codec='libx264', 
            audio_codec='aac', 
            bitrate='8000k', 
            logger=None
        )
        
        new_video_clip.close()
        original_video_clip.close()
        if os.path.exists(temp_out_path): os.remove(temp_out_path)
        return True
    except Exception as e:
        st.error(f"音频合成失败: {e}")
        return False

uploaded_file = st.file_uploader("第一步：上传视频文件 (.mp4)", type=["mp4", "mov", "avi"])

if uploaded_file is not None:
    tfile = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") 
    tfile.write(uploaded_file.read())
    video_path = tfile.name

    cap = cv2.VideoCapture(video_path)
    ret, first_frame = cap.read()
    cap.release()

    if ret:
        first_frame_rgb = cv2.cvtColor(first_frame, cv2.COLOR_BGR2RGB)
        height, width, _ = first_frame_rgb.shape

        st.subheader("🛠️ 设置水印区域")
        col1, col2 = st.columns([1, 1])

        with col1:
            st.image(first_frame_rgb, caption="原始画面", use_container_width=True)
            
        with col2:
            st.info(f"视频分辨率: {width} x {height}")
            
            x_val = st.slider("左边距 (X)", 0, width, 20)
            y_val = st.slider("上边距 (Y)", 0, height, 20)
            w_val = st.slider("宽度 (Width)", 10, width, 200)
            h_val = st.slider("高度 (Height)", 10, height, 80)

            preview_img = first_frame_rgb.copy()
            cv2.rectangle(preview_img, (x_val, y_val), (x_val + w_val, y_val + h_val), (255, 0, 0), 3)
            st.image(preview_img, caption="🔴 红色区域将被修复 (预览)", use_container_width=True)

        st.markdown("---")

        if st.button("🚀 开始去水印 (保持原画质)", type="primary"):
            output_video_path = f"cleaned_{uploaded_file.name}"
            with st.spinner("正在逐帧修复... 请耐心等待"):
                success = process_video(video_path, output_video_path, x_val, y_val, w_val, h_val)
            
            if success:
                st.success("✅ 处理完成！")
                with open(output_video_path, "rb") as f:
                    st.download_button(
                        label="📥 下载处理后的视频",
                        data=f,
                        file_name=output_video_path,
                        mime="video/mp4"
                    )
                try:
                    os.remove(output_video_path)
                    os.remove(video_path)
                except: pass
