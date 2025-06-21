import os
import subprocess
import streamlit as st
import threading
import asyncio
import time # 导入 time 模块用于延时，如果需要日志刷新

# 设置页面
st.set_page_config(page_title="girl-show", layout="wide")

# UI 控制状态
if "running" not in st.session_state:
    st.session_state.running = False
    st.session_state.logs = ""
    st.session_state.sub = ""
    st.session_state.argo = ""
    st.session_state.backend_process = None # <--- **新增：初始化用于存储进程的变量**

st.title("🌐 girl-show")

# 环境变量
envs = {
    "BOT_TOKEN": st.secrets.get("BOT_TOKEN", ""),
    "CHAT_ID": st.secrets.get("CHAT_ID", ""),
    "ARGO_AUTH": st.secrets.get("ARGO_AUTH", ""),
    "ARGO_DOMAIN": st.secrets.get("ARGO_DOMAIN", ""),
    "NEZHA_KEY": st.secrets.get("NEZHA_KEY", ""),
    "NEZHA_PORT": st.secrets.get("NEZHA_PORT", ""),
    "NEZHA_SERVER": st.secrets.get("NEZHA_SERVER", ""),
    "UPLOAD_URL": st.secrets.get("UPLOAD_URL", "")
}

# 写出 .env 文件
with open("./env.sh", "w") as shell_file:
    shell_file.write("#!/bin/bash\n")
    for k, v in envs.items():
        os.environ[k] = v  # 设置系统环境变量
        shell_file.write(f"export {k}='{v}'\n")

# 构造命令（去掉 screen，使用 subprocess.Popen 兼容 streamlit 平台）
def run_backend():
    try:
        # 检查后端服务是否已经在运行
        # 注意：这里假设 st.session_state.backend_process 存储的是 Popen 对象
        if st.session_state.backend_process and st.session_state.backend_process.poll() is None:
            st.session_state.logs += "\n⚠️ 后端服务已在运行中，无需重复启动。"
            st.session_state.running = True # 确保状态是运行中
            return

        st.session_state.logs += "⚙️ 正在安装依赖并启动后端服务...\n"
        st.session_state.running = True # 标记为正在尝试启动
        st.rerun() # 强制 Streamlit 刷新以显示最新日志

        # 赋予执行权限
        st.session_state.logs += "chmod +x app.py ...\n"
        subprocess.run("chmod +x app.py", shell=True, check=True, capture_output=True, text=True)
        st.session_state.logs += "✅ chmod +x app.py 完成\n"

        # 安装依赖
        st.session_state.logs += "pip install -r requirements.txt ...\n"
        install_result = subprocess.run("pip install -r requirements.txt", shell=True, check=True, capture_output=True, text=True)
        st.session_state.logs += install_result.stdout
        st.session_state.logs += "✅ 依赖安装完成\n"

        # 启动 app.py 后台运行，并将 Popen 对象存储到 session_state
        # 注意：为了让 Streamlit 捕获到 app.py 的输出，通常需要将其重定向
        # 但你之前的代码没有重定向，如果它能工作，说明你的部署环境有特殊处理
        # 否则，可能需要像我之前那样用 PIPE 捕获。我们这里先保持原样。
        process = subprocess.Popen(["python", "app.py"])
        st.session_state.backend_process = process # <--- **存储 Popen 对象**
        st.session_state.logs += f"✅ 后端服务已成功启动 (PID: {process.pid})！\n"
        # st.session_state.running = False # <--- **这里应该保持 True，表示运行中**
        st.session_state.running = True # 启动成功，设为 True
        st.rerun() # 再次刷新以显示最终状态

    except Exception as e:
        st.session_state.logs += f"\n❌ 出错: {e}"
        st.session_state.running = False # 启动失败，设为 False
        st.session_state.backend_process = None # 清空进程对象
        st.rerun() # 刷新显示错误

# 定义异步主函数 (用于包装 run_backend，以便在线程中运行 asyncio.run)
async def main():
    run_backend() # 直接调用同步函数

# --- 自动启动部署逻辑 (替换了原来的按钮) ---
# 每次 Streamlit 脚本运行时，检查并启动/监控后端服务
if not st.session_state.running:
    st.warning("🔄 正在初始化和启动后端服务，请稍候...")
    # 在新的线程中启动 main，daemon=True 确保线程随主程序退出而退出
    threading.Thread(target=lambda: asyncio.run(main()), daemon=True).start()
    # 立即强制刷新，显示“正在初始化”信息
    st.rerun()
else:
    # 检查进程是否仍然存活
    if st.session_state.backend_process and st.session_state.backend_process.poll() is None:
        st.success("✅ 后端服务已在运行中。")
    else:
        # 如果 session_state.running 是 True 但进程已退出，则重置状态
        st.session_state.running = False
        st.session_state.backend_process = None
        st.error("❌ 后端服务已停止，尝试刷新页面重新启动。")
        # 强制刷新一次，触发重新启动尝试
        st.rerun()

# --- 日志显示 ---
st.subheader("部署日志")
# 注意：如果 app.py 的输出没有显示在这里，需要考虑重定向其输出到文件，然后这里读取
# 或者在 subprocess.Popen 中使用 stdout=subprocess.PIPE 来捕获
st.code(st.session_state.logs, language="bash", height=300)

# --- 展示视频和图片 ---
video_paths = ["./meinv.mp4", "./mv2.mp4"]
for path in video_paths:
    if os.path.exists(path):
        st.video(path)

image_path = "./mv.jpg"
if os.path.exists(image_path):
    st.image(image_path, caption="林熳", use_container_width=True)

