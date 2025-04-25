# 使用官方 Python 镜像
FROM python:3.10-alpine

# 工作目录
WORKDIR /app

# 复制项目文件
COPY . .

# 安装依赖
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# 设置环境变量（防止 Streamlit 或 Google 报错）
ENV PYTHONUNBUFFERED=1

# 默认运行 main.py
CMD ["python", "main.py"]
