FROM python:3.12.10

# システムパッケージの更新
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN groupadd -r app && useradd -r -g app app
USER app

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]