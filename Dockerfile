FROM python:3.10-slim

WORKDIR /app

# 修正：加上 --allow-releaseinfo-change 與清潔指令，保證 Linux 套件順利安裝不崩潰
RUN apt-get clean && \
    apt-get update --allow-releaseinfo-change && \
    apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main.py:app", "--host", "0.0.0.0", "--port", "10000"]
