import os
import subprocess
import streamlit as st
import threading
import time
import sys # 用于捕获标准输出和标准错误
import io  # 用于捕获标准输出和标准错误

# --- 1. 确保依赖安装 (在Streamlit应用启动时执行，避免重复安装) ---
# 这是一个临时的解决方案，因为你没有使用 Dockerfile。
# 在生产环境中，更推荐在部署前通过 Dockerfile 或 CI/CD 脚本来完成依赖安装。
# 这里我们尝试在每次应用启动时执行一次，但会检查是否已成功安装。

# 使用一个会话状态来标记是否已经尝试过安装依赖
if "dependencies_installed" not in st.session_state:
    st.session_state.dependencies_installed = False

if not st.session_state.dependencies_installed:
    st.info("⚙️ 首次启动：正在安装或检查Python依赖 (requirements.txt)...")
    try:
        # 尝试安装依赖，捕获其输出
        # 注意：这里捕获的输出不会直接显示在 Streamlit UI 上，但可以在后台日志中查看
        install_result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
            capture_output=True, text=True, check=True, encoding='utf-8'
        )
        st.session_state.logs += "✅ 依赖安装成功:\n" + install_result.stdout
        if install_result.stderr:
            st.session_state.logs += "⚠️ 依赖安装警告/错误:\n" + install_result.stderr
        st.session_state.dependencies_installed = True
        st.success("✅ Python依赖安装/检查完成。")
    except subprocess.CalledProcessError as e:
        st.session_state.logs += f"\n❌ 依赖安装失败:\n{e.stdout}\n{e.stderr}"
        st.error("❌ 依赖安装失败，请检查 requirements.txt 和日志。")
        st.stop() # 依赖安装失败，停止应用加载
    except Exception as e:
        st.session_state.logs += f"\n❌ 依赖安装过程中发生未知错误: {e}"
        st.error("❌ 依赖安装过程中发生未知错误，停止应用加载。")
        st.stop()
    # 强制刷新一次，显示依赖安装结果
    st.rerun()

# --- 2. Streamlit 应用页面配置和初始化 ---
st.set_page_config(page_title="Honey-Girl", layout="wide")

# UI 控制状态
if "running" not in st.session_state:
    st.session_state.running = False
    st.session_state.logs = "" # 用于显示所有日志
    st.session_state.backend_process_pid = None # 存储 app.py 进程的 PID
    # 如果你的 app.py 仍然使用这些变量，请保留
    st.session_state.sub = ""
    st.session_state.argo = ""
    # 用于捕获 app.py 实时输出的缓冲区和线程
    st.session_state.stdout_buffer = io.StringIO()
    st.session_state.stderr_buffer = io.StringIO()
    st.session_state.stdout_reader_thread = None
    st.session_state.stderr_reader_thread = None

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
# 注意：在 Streamlit Cloud 等生产环境中，st.secrets 更推荐用于敏感信息
with open("./env.sh", "w") as shell_file:
    shell_file.write("#!/bin/bash\n")
    for k, v in envs.items():
        os.environ[k] = v # 设置系统环境变量
        shell_file.write(f"export {k}='{v}'\n")

# --- 3. 后端服务启动和监控逻辑 ---

# 启动 app.py 并实时捕获其输出的函数
def run_and_monitor_backend():
    # 检查进程是否已在运行
    if st.session_state.backend_process_pid:
        try:
            os.kill(st.session_state.backend_process_pid, 0)
            # 进程仍在运行，不重复启动
            # st.session_state.logs += "\n后端服务已经在运行中 (PID: {}).".format(st.session_state.backend_process_pid)
            st.session_state.running = True
            return # 已在运行，直接返回
        except OSError:
            # 进程不存在或已终止，需要重新启动
            st.session_state.logs += "\n检测到后端服务 (PID: {}) 已停止或不存在，尝试重新启动。".format(st.session_state.backend_process_pid)
            st.session_state.backend_process_pid = None
            st.session_state.running = False

    st.session_state.logs += "\n⚙️ 正在尝试启动后端服务 (app.py)...\n"
    try:
        # 赋予 app.py 执行权限 (这行也可以移除，如果 app.py 不需要执行权限)
        subprocess.run("chmod +x app.py", shell=True, check=True, capture_output=True, text=True)
        st.session_state.logs += "✅ chmod +x app.py 完成\n"

        # 使用 Popen 后台启动 app.py
        # IMPORTANT: 我们在这里捕获 stdout/stderr，并使用线程读取
        process = subprocess.Popen(
            [sys.executable, "app.py"], # 使用当前 Streamlit 进程的 Python 解释器
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1 # 行缓冲
        )
        st.session_state.backend_process_pid = process.pid
        st.session_state.logs += f"✅ 后端服务已成功启动 (PID: {process.pid})！\n"
        st.session_state.running = True

        # 启动线程来实时读取 app.py 的 stdout 和 stderr
        def reader(pipe, buffer):
            for line in iter(pipe.readline, ''): # 持续读取直到 EOF
                buffer.write(line)
            pipe.close()

        st.session_state.stdout_reader_thread = threading.Thread(
            target=reader, args=(process.stdout, st.session_state.stdout_buffer), daemon=True
        )
        st.session_state.stderr_reader_thread = threading.Thread(
            target=reader, args=(process.stderr, st.session_state.stderr_buffer), daemon=True
        )

        st.session_state.stdout_reader_thread.start()
        st.session_state.stderr_reader_thread.start()

    except subprocess.CalledProcessError as e:
        st.session_state.logs += f"\n❌ 命令执行出错: {e}\n"
        st.session_state.logs += f"stdout:\n{e.stdout}\n"
        st.session_state.logs += f"stderr:\n{e.stderr}\n"
        st.session_state.running = False
        st.session_state.backend_process_pid = None
    except Exception as e:
        st.session_state.logs += f"\n❌ 启动过程中出现未知错误: {e}\n"
        st.session_state.logs += f"\n请确保 app.py 路径正确且可执行，或检查其内部是否有语法错误。"
        st.session_state.running = False
        st.session_state.backend_process_pid = None

# --- 4. Streamlit 应用主循环和 UI 更新 ---

# 每次 Streamlit 脚本运行时，检查并启动/监控后端服务
if not st.session_state.running:
    # 只有在依赖安装完成后才尝试启动后端服务
    if st.session_state.dependencies_installed:
        run_and_monitor_backend()
    else:
        # 如果依赖还没安装好，就等待下一次 rerun
        pass # 上面已经通过 st.rerun() 强制刷新了

# 实时更新日志显示
# 从缓冲区获取新日志
st.session_state.logs += st.session_state.stdout_buffer.getvalue()
st.session_state.stdout_buffer.truncate(0) # 清空已读取部分
st.session_state.stdout_buffer.seek(0)    # 重置文件指针

st.session_state.logs += st.session_state.stderr_buffer.getvalue()
st.session_state.stderr_buffer.truncate(0)
st.session_state.stderr_buffer.seek(0)

# 检查后端进程状态
if st.session_state.backend_process_pid:
    try:
        # 尝试发送信号0，检查进程是否存在
        os.kill(st.session_state.backend_process_pid, 0)
        st.session_state.running = True
        st.success(f"✅ 后端服务正在运行中 (PID: {st.session_state.backend_process_pid}).")
    except OSError:
        # 进程已终止
        st.session_state.logs += f"\n后端服务 (PID: {st.session_state.backend_process_pid}) 已终止。"
        st.session_state.backend_process_pid = None
        st.session_state.running = False
        st.error("❌ 后端服务已停止。")
else:
    if st.session_state.dependencies_installed: # 只有在依赖安装成功后才显示停止状态
        st.error("❌ 后端服务未运行。")

# 为了让日志实时更新，每隔一段时间自动刷新 Streamlit 应用
# 确保在运行中才刷新，避免不必要的循环
if st.session_state.running:
    time.sleep(1) # 每秒刷新一次，以获取新日志和检查进程状态
    st.rerun()

# --- 5. UI 内容显示 (保持不变) ---
st.subheader("部署日志")
st.code(st.session_state.logs, language="bash", height=300)

# 展示视频
# 检查是否存在，假设文件名是 meinv.mp4
video_paths = ["./meinv.mp4", "./mv2.mp4"]
for path in video_paths:
    if os.path.exists(path):
        st.video(path)

# 展示图片
image_path = "./mv.jpg"
if os.path.exists(image_path):
    st.image(image_path, caption="南音", use_container_width=True)

