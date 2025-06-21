# 使用官方 Python 运行时作为父镜像
FROM python:3.9-slim-buster

# 设置工作目录
WORKDIR /app

# 复制 requirements.txt 到工作目录
COPY requirements.txt ./

# 安装所有依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制你的应用代码到工作目录
COPY . .

# 设置 Streamlit 端口
EXPOSE 8501

# 当容器启动时运行 Streamlit 应用
# 确保 streamlit_app.py 内部包含了启动 app.py 的逻辑
CMD ["streamlit", "run", "streamlit_app.py", "--server.port", "8501", "--server.enableCORS", "false", "--server.enableXsrfProtection", "false"]
