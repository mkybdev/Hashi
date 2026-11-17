FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:0.9.16 /uv /uvx /bin/

WORKDIR /app

# バインドマウントで仮想環境や辞書が隠れない場所に配置する
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:${PATH}" \
    UV_PYTHON_DOWNLOADS=never

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

COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --locked --no-dev --no-cache

# Download UniDic
RUN uv run --no-sync python -m unidic download

COPY . .

# Cloud Run injects the PORT environment variable (default 8080)
ENV PORT=8080
CMD ["sh", "-c", "uv run --no-sync uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
