FROM python:3.9-slim

WORKDIR /app

# Install build dependencies
# Install build dependencies
# libgomp1 and openblas are required for ML libraries on Linux
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    libopenblas-dev \
    mecab \
    libmecab-dev \
    mecab-ipadic-utf8 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# Pin setuptools<60 because newer versions break distutils compatibility required by older libraries (chainer/numpy)
RUN pip install --no-cache-dir "setuptools<60" wheel && \
    pip install --no-cache-dir -r requirements.txt

# Download UniDic
RUN python -m unidic download

COPY . .

# Cloud Run injects the PORT environment variable (default 8080)
ENV PORT=8080
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
