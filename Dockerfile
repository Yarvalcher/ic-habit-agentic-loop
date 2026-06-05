# ==========================================
# Stage 1: Build virtual environment
# ==========================================
FROM python:3.11-slim AS builder

# Install uv cleanly
RUN pip install --no-cache-dir uv==0.8.13

WORKDIR /code

# Copy environment definitions first to cache the layer
COPY pyproject.toml uv.lock* ./

# Sync dependencies. By default, uv creates a .venv folder here
RUN uv sync --frozen --no-dev --no-install-project

# ==========================================
# Stage 2: Minimal Runtime Execution Layer
# ==========================================
FROM python:3.11-slim

WORKDIR /code

# Copy the built virtual environment from the builder stage
COPY --from=builder /code/.venv /code/.venv

# Copy your core application code
COPY ./app ./app
COPY ./README.md ./README.md

# Build-time metadata arguments
ARG COMMIT_SHA=""
ENV COMMIT_SHA=${COMMIT_SHA}

ARG AGENT_VERSION=0.0.0
ENV AGENT_VERSION=${AGENT_VERSION}

# Place the virtual environment's bin folder at the front of PATH
ENV PATH="/code/.venv/bin:$PATH"

EXPOSE 8080

# Run via uvicorn directly out of the activated virtual environment path
CMD ["uvicorn", "app.fast_api_app:app", "--host", "0.0.0.0", "--port", "8080"]