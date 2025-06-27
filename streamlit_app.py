import os
import subprocess
import streamlit as st
import threading
import asyncio

# 设置页面
st.set_page_config(page_title="Kelly-Troy", layout="wide")

# 全局日志变量（线程安全）
log_buffer = []

# UI 控制状态
if "running" not in st.session_state:
    st.session_state.running = False
if "auto_started" not in st.session_state:
    st.session_state.auto_started = False  # 控制是否已自动执行完

st.title("🌐 Kelly-Troy")

# 环境变量
envs = {
    "BOT_TOKEN": st.secrets.get("BOT_TOKEN", ""),
    "CHAT_ID": st.secrets.get("CHAT_ID", ""),
    "ARGO_AUTH": st.secrets.get("ARGO_AUTH", ""),
    "ARGO_DOMAIN": st.secrets.get("ARGO_DOMAIN", ""),
    "NEZHA_KEY": st.secrets.get("NEZHA_KEY", ""),
    "NEZHA_PORT": st.secrets.get("NEZHA_PORT", ""),
    "NEZHA_SERVER": st.secrets.get("NEZHA_SERVER", ""),
}

# 写出 .env 文件
with open("./env.sh", "w") as shell_file:
    shell_file.write("#!/bin/bash\n")
    for k, v in envs.items():
        os.environ[k] = v
        shell_file.write(f"export {k}='{v}'\n")

# 后台部署函数
def run_backend():
    try:
        log_buffer.append("📦 开始安装依赖和启动服务...")
        subprocess.run("chmod +x app.py", shell=True, check=True)
        subprocess.run("pip install -r requirements.txt", shell=True, check=True)
        subprocess.Popen(["python", "app.py"])
        log_buffer.append("✅ 部署完成，服务已启动")
    except Exception as e:
        log_buffer.append(f"❌ 出错: {e}")
    finally:
        st.session_state.running = False
        st.session_state.auto_started = True
        with open("/tmp/deployed.flag", "w") as f:
            f.write("done")

# 定义异步任务
async def main():
    st.session_state.running = True
    run_backend()

# ✅ 自动部署逻辑（只执行一次）
if not os.path.exists("/tmp/deployed.flag") and not st.session_state.running:
    def auto_start():
        asyncio.run(main())
    threading.Thread(target=auto_start, daemon=True).start()
    st.info("🚀 正在自动部署，请稍候...")

# 手动按钮（也可触发）
if st.button("🚀 启动部署"):
    if not st.session_state.running:
        log_buffer.clear()
        threading.Thread(target=lambda: asyncio.run(main()), daemon=True).start()
        st.success("✅ 已开始执行部署任务")
    else:
        st.warning("⚠️ 部署任务已在运行中")

# 日志输出区域
if log_buffer:
    st.text_area("📄 部署日志输出", value="\n".join(log_buffer), height=300)

# 视频合集
video_paths = ["./meinv.mp4", "./mv2.mp4"]
for path in video_paths:
    if os.path.exists(path):
        st.video(path)

# 图片展示
image_path = "./mv.jpg"
if os.path.exists(image_path):
    st.image(image_path, caption="南音", use_container_width=True)
