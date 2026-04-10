# ============================================================================
# AI Knowledge Agent - Production Dockerfile
# Multi-stage build for a smaller final image and better layer caching.
# ============================================================================

# ---- Stage 1: Builder ----
# Install dependencies in a builder stage so we don't ship build tools
# in the final image.
FROM python:3.11-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create a virtual environment to isolate dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements first for better Docker layer caching
# Dependencies only re-install when requirements.txt changes
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ---- Stage 2: Runtime ----
# Final image contains only what's needed to run the application.
FROM python:3.11-slim

# Create a non-root user for security
# Running as root inside containers is a common security mistake
RUN groupadd -r agent && useradd -r -g agent -m -d /home/agent agent

# Install only runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the virtual environment from the builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set the working directory
WORKDIR /app

# Copy application code
# .dockerignore controls what gets included
COPY --chown=agent:agent . .

# Create directories that need to be writable
RUN mkdir -p /app/chroma_db /app/docs /app/generated_images && \
    chown -R agent:agent /app

# Switch to the non-root user
USER agent

# Expose the Streamlit port
EXPOSE 8501

# Health check — Kubernetes, ECS, and docker-compose all use this
# to determine if the container is ready to receive traffic
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Environment variables with sensible defaults
# These can be overridden at runtime via docker-compose, Kubernetes secrets,
# or ECS task definitions
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Run Streamlit
CMD ["streamlit", "run", "app.py"]