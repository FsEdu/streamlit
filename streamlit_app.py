import os
import subprocess
import streamlit as st
import threading
import time # 导入 time 模块用于延时

# 设置页面
st.set_page_config(page_title="Honey-Girl", layout="wide")

# UI 控制状态
if "running" not in st.session_state:
    st.session_state.running = False
    st.session_state.logs = ""
    st.session_state.process = None # 用于存储子进程对象

st.title("🌐 Honey-Girl")

# 环境变量 (保持不变)
envs = {
    "BOT_TOKEN": st.secrets.get("BOT_TOKEN", ""),
    "CHAT_ID": st.secrets.get("CHAT_ID", ""),
    "ARGO_AUTH": st.secrets.get("ARGO_AUTH", ""),
    "ARGO_DOMAIN": st.secrets.get("ARGO_DOMAIN", ""),
    "NEZHA_KEY": st.secrets.get("NEZHA_KEY", ""),
    "NEZHA_PORT": st.secrets.get("NEZHA_PORT", ""),
    "NEZHA_SERVER": st.secrets.get("NEZHA_SERVER", ""),
}

# 写出 .env 文件 (保持不变)
with open("./env.sh", "w") as shell_file:
    shell_file.write("#!/bin/bash\n")
    for k, v in envs.items():
        os.environ[k] = v
        shell_file.write(f"export {k}='{v}'\n")

# 构造命令（自动启动逻辑）
def run_backend_and_install_deps():
    if st.session_state.process and st.session_state.process.poll() is None:
        st.session_state.logs += "\n后端服务已在运行中，无需重复启动。\n"
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

        # **重要：在 Docker 环境中，依赖通常在 Dockerfile 构建阶段安装，所以这里可以移除或仅作为本地调试的备用**
        # 但为了你目前的需求，我们暂时保留，但知道它可能在生产环境中是冗余的。
        st.session_state.logs += "pip install -r requirements.txt ...\n"
        install_result = subprocess.run("pip install -r requirements.txt", shell=True, check=True, capture_output=True, text=True)
        st.session_state.logs += install_result.stdout
        st.session_state.logs += "✅ 依赖安装完成\n"

        # 启动 app.py 后台运行
        st.session_state.logs += "启动 python app.py ...\n"
        process = subprocess.Popen(["python", "app.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
        st.session_state.process = process
        st.session_state.logs += "✅ 后端服务已成功启动！\n"

        # 持续读取子进程输出（非阻塞方式）
        def read_output(proc):
            while True: # 循环读取，直到进程结束
                line = proc.stdout.readline()
                if not line: # 如果没有更多输出，检查进程是否还活着
                    if proc.poll() is not None: # 进程已结束
                        break
                    time.sleep(0.1) # 短暂等待
                    continue
                st.session_state.logs += line
                st.rerun() # 实时更新日志
                time.sleep(0.01) # 避免更新过快

            # 进程结束后，读取剩余的错误输出
            for line in proc.stderr:
                st.session_state.logs += f"ERROR: {line}"
                st.rerun()
                time.sleep(0.01)

            st.session_state.logs += f"\nBackend process exited with code {proc.returncode}\n"
            st.session_state.running = False
            st.rerun() # 最后更新一次状态

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

# --- Streamlit 应用启动时的自动触发逻辑 ---
# 检查是否已在运行，如果未运行则自动启动
if not st.session_state.running:
    st.warning("🔄 正在初始化和启动后端服务，请稍候...")
    threading.Thread(target=run_backend_and_install_deps, daemon=True).start()
else:
    st.success("✅ 后端服务已在运行中。")

# 显示日志
st.subheader("部署日志")
st.code(st.session_state.logs, language="bash", height=300) # 增加高度方便查看

# 展示视频和图片 (保持不变)
video_paths = ["./meinv.mp4", "./mv2.mp4"]
for path in video_paths:
    if os.path.exists(path):
        st.video(path)

image_path = "./mv.jpg"
if os.path.exists(image_path):
    st.image(image_path, caption="南音", use_container_width=True)

