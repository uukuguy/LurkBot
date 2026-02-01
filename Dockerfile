# =============================================================================
# LurkBot Production Dockerfile
# Multi-stage build for optimized image size
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Builder - Install dependencies and build the application
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS builder

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set environment variables for uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Copy dependency files first for better layer caching
COPY pyproject.toml uv.lock ./

# Install production dependencies only
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# Copy source code
COPY src/ ./src/
COPY README.md ./

# Install the project itself
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# -----------------------------------------------------------------------------
# Stage 2: Runtime - Minimal production image
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

# Install runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        tini \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

# Create non-root user for security
RUN groupadd --gid 1000 lurkbot && \
    useradd --uid 1000 --gid 1000 --create-home --shell /bin/bash lurkbot

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder --chown=lurkbot:lurkbot /app/.venv /app/.venv

# Copy source code
COPY --from=builder --chown=lurkbot:lurkbot /app/src /app/src

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    # LurkBot configuration
    LURKBOT_GATEWAY_HOST=0.0.0.0 \
    LURKBOT_GATEWAY_PORT=18789 \
    # Home directory for config
    HOME=/home/lurkbot

# Create directories for config and workspace
RUN mkdir -p /home/lurkbot/.lurkbot /home/lurkbot/workspace && \
    chown -R lurkbot:lurkbot /home/lurkbot

# Switch to non-root user
USER lurkbot

# Expose gateway port
EXPOSE 18789

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${LURKBOT_GATEWAY_PORT}/health || exit 1

# Use tini as init system for proper signal handling
ENTRYPOINT ["/usr/bin/tini", "--"]

# Default command: start gateway server
CMD ["lurkbot", "gateway", "start"]

# -----------------------------------------------------------------------------
# Stage 3: Development - Include dev dependencies
# -----------------------------------------------------------------------------
FROM runtime AS development

USER root

# Install development dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
        vim \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

USER lurkbot

# Override for development
CMD ["lurkbot", "gateway", "start", "--reload"]

# -----------------------------------------------------------------------------
# Stage 4: Browser - Include Playwright for browser automation
# -----------------------------------------------------------------------------
FROM runtime AS browser

USER root

# Install Playwright dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libnss3 \
        libnspr4 \
        libatk1.0-0 \
        libatk-bridge2.0-0 \
        libcups2 \
        libdrm2 \
        libdbus-1-3 \
        libxkbcommon0 \
        libatspi2.0-0 \
        libxcomposite1 \
        libxdamage1 \
        libxfixes3 \
        libxrandr2 \
        libgbm1 \
        libasound2 \
        libpango-1.0-0 \
        libcairo2 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

# Install Playwright browsers
RUN pip install playwright && \
    playwright install chromium

USER lurkbot

CMD ["lurkbot", "gateway", "start"]
