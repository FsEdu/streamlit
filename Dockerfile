# 使用官方 Python 运行时作为父镜像，选择一个轻量级版本
FROM python:3.9-slim-buster

# 设置工作目录
WORKDIR /app

# 复制 requirements.txt 到工作目录
# 这一步很重要，可以利用 Docker 缓存，如果 requirements.txt 不变，则无需重新安装依赖
COPY requirements.txt ./

# 安装所有依赖
# --no-cache-dir: 不缓存 pip 包，减少镜像大小
# --upgrade pip: 升级 pip 到最新版本
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 复制你的所有应用代码到工作目录
# '.' 表示当前目录（Dockerfile 所在的目录）
# '.': 表示复制到容器的 /app 目录
COPY . .

# 如果 app.py 需要执行权限，可以提前在这里给
RUN chmod +x app.py

# 设置 Streamlit 监听的端口
EXPOSE 8501

# 当容器启动时运行 Streamlit 应用
# --server.port 8501: 告诉 Streamlit 监听 8501 端口
# --server.enableCORS false: 禁用 CORS 检查，可能在某些部署场景下有用
# --server.enableXsrfProtection false: 禁用 CSRF 保护，同上
# 替换你的 Streamlit 应用文件名
CMD ["streamlit", "run", "streamlit_app.py", "--server.port", "8501", "--server.enableCORS", "false", "--server.enableXsrfProtection", "false"]
