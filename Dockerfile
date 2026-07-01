FROM python:3.10-slim

WORKDIR /app

# 安裝 OpenCV 所需的 Linux 基本影像套件
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main.py:app", "--host", "0.0.0.0", "--port", "10000"]
