import os
import subprocess
import streamlit as st
import threading
import asyncio
import time # 导入 time 模块用于延时

# 设置页面
st.set_page_config(page_title="Honey-Girl", layout="wide")

# UI 控制状态
if "running" not in st.session_state:
    st.session_state.running = False
    st.session_state.logs = ""
    st.session_state.sub = ""
    st.session_state.argo = ""
    st.session_state.process = None # 用于存储子进程对象

st.title("🌐 Honey-Girl")

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
        os.environ[k] = v  # 设置系统环境变量
        shell_file.write(f"export {k}='{v}'\n")

# 构造命令（去掉 screen，使用 subprocess.Popen 兼容 streamlit 平台）
def run_backend():
    if st.session_state.process and st.session_state.process.poll() is None:
        # 如果进程已经在运行，则不重复启动
        st.session_state.logs += "\n后端服务已在运行中，无需重复启动。"
        st.session_state.running = True
        return

    st.session_state.running = True
    st.session_state.logs = "⚙️ 正在安装依赖并启动后端服务...\n"
    st.rerun() # 强制 Streamlit 刷新以显示最新日志

    try:
        # 赋予执行权限
        st.session_state.logs += "chmod +x app.py ...\n"
        subprocess.run("chmod +x app.py", shell=True, check=True, capture_output=True, text=True)
        st.session_state.logs += "✅ chmod +x app.py 完成\n"

        # 安装依赖
        st.session_state.logs += "pip install -r requirements.txt ...\n"
        # 捕获依赖安装的输出
        install_result = subprocess.run("pip install -r requirements.txt", shell=True, check=True, capture_output=True, text=True)
        st.session_state.logs += install_result.stdout
        st.session_state.logs += "✅ 依赖安装完成\n"

        # 启动 app.py 后台运行，并将输出重定向
        st.session_state.logs += "启动 python app.py ...\n"
        # 使用 preexec_fn=os.setsid 来创建一个新的会话，防止父进程退出时子进程也退出
        # 注意：在某些部署环境中，这种方式可能不适用，需要根据实际平台调整
        process = subprocess.Popen(["python", "app.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
        st.session_state.process = process
        st.session_state.logs += "✅ 后端服务已成功启动！\n"

        # 持续读取子进程输出（非阻塞方式）
        def read_output(proc):
            for line in proc.stdout:
                st.session_state.logs += line
                time.sleep(0.01) # 避免更新过快
            for line in proc.stderr:
                st.session_state.logs += f"ERROR: {line}"
                time.sleep(0.01)

        # 在新线程中读取输出，以免阻塞主线程
        threading.Thread(target=read_output, args=(process,), daemon=True).start()

    except subprocess.CalledProcessError as e:
        st.session_state.logs += f"\n❌ 命令执行出错: {e}\n"
        st.session_state.logs += f"stdout:\n{e.stdout}\n"
        st.session_state.logs += f"stderr:\n{e.stderr}\n"
        st.session_state.running = False
    except Exception as e:
        st.session_state.logs += f"\n❌ 启动过程中出现未知错误: {e}\n"
        st.session_state.running = False

    st.rerun() # 再次刷新以显示最终状态

# 检查是否已在运行，如果未运行则自动启动
if not st.session_state.running:
    # 使用线程来运行后端启动逻辑，避免阻塞 Streamlit UI
    # 注意：在某些部署环境（如 Streamlit Cloud），直接在主线程中长时间运行 subprocess 可能导致应用超时。
    # 使用 threading.Thread 是一个好的实践。
    threading.Thread(target=run_backend, daemon=True).start()
    st.warning("🔄 正在初始化和启动后端服务，请稍候...")
else:
    st.success("✅ 后端服务已在运行中。")

# 显示日志
st.subheader("部署日志")
st.code(st.session_state.logs, language="bash")

# 展示视频
video_paths = ["./meinv.mp4", "./mv2.mp4"]
for path in video_paths:
    if os.path.exists(path):
        st.video(path)

# 展示图片
image_path = "./mv.jpg"
if os.path.exists(image_path):
    st.image(image_path, caption="南音", use_container_width=True)
