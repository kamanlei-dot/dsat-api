# ================== Builder Stage ==================
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    libnss3 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxkbcommon0 \
    libgbm1 \
    libasound2 \
    libatspi2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 下載 Playwright 瀏覽器
RUN playwright install --with-deps chromium

# ================== Production Stage ==================
FROM python:3.11-slim

WORKDIR /app

# 複製系統依賴
RUN apt-get update && apt-get install -y \
    libnss3 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxkbcommon0 \
    libgbm1 \
    libasound2 \
    libatspi2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 複製 Python 套件和 Playwright 瀏覽器
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /root/.cache/ms-playwright /root/.cache/ms-playwright

COPY . .

EXPOSE 8000

# 使用 uvicorn 啟動（較穩定）
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
