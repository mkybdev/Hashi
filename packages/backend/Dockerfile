FROM python:3.9-slim

WORKDIR /app

# Install build dependencies including Rust for sudachipy
# libgomp1 and openblas are required for ML libraries on Linux
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    libopenblas-dev \
    mecab \
    libmecab-dev \
    mecab-ipadic-utf8 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Rust (required for building sudachipy)
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

COPY requirements.txt .
# Upgrade pip to prefer prebuilt wheels, then install setuptools<60 and dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir "setuptools<60" wheel && \
    pip install --no-cache-dir -r requirements.txt

# Download UniDic
RUN python -m unidic download

COPY . .

# Cloud Run injects the PORT environment variable (default 8080)
ENV PORT=8080
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
