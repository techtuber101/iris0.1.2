FROM ghcr.io/astral-sh/uv:python3.11-alpine

# Set environment mode
ENV ENV_MODE=production

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apk add --no-cache curl git

# Copy dependency files and install
COPY pyproject.toml uv.lock ./
ENV UV_LINK_MODE=copy
RUN uv sync --locked --quiet

# Copy application code
COPY . .

# Optional: expose a default port for local dev
# (ignored by Railway since it injects its own PORT at runtime)
EXPOSE 8000

# Start command — uses Railway's $PORT if set, otherwise defaults to 8000
CMD ["sh", "-c", "uv run python -m uvicorn core.run:app --host 0.0.0.0 --port ${PORT:-8000}"]
