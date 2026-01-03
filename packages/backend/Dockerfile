FROM python:3.10-slim

WORKDIR /app

# Install build dependencies for some packages (if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download UniDic
# This downloads to site-packages, which is fine in Docker
RUN python -m unidic download

COPY . .

# Cloud Run expects port 8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
