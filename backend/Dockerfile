FROM ghcr.io/astral-sh/uv:python3.11-alpine

ENV ENV_MODE production
WORKDIR /app

RUN apk add --no-cache curl git

# Install Python dependencies
COPY pyproject.toml uv.lock ./
ENV UV_LINK_MODE=copy
RUN uv sync --locked --quiet

# Copy application code
COPY . .

# Calculate optimal worker count based on 16 vCPUs
# Using (2*CPU)+1 formula for CPU-bound applications
ENV WORKERS=7
ENV THREADS=2
ENV WORKER_CONNECTIONS=2000

ENV PYTHONPATH=/app
ENV PORT=8000
EXPOSE $PORT

# Start command for Railway
CMD ["sh", "-c", "uv run python -m uvicorn core.run:app --host 0.0.0.0 --port $PORT"]
