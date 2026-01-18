# Use official Python image
# Multi-stage build for optimized production image
FROM python:3.11-slim as builder

# Set environment variables for build stage
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy and install requirements
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Production stage
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/opt/venv/bin:$PATH"

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Create application directory
WORKDIR /app

# Cache-busting arg to force fresh copy of application code
ARG CACHEBUST=1

# Copy application code
COPY . .

# Ensure migration helper script is executable
RUN chmod +x run_migrations.sh || true

# Copy entrypoint and make executable (must be done before switching user)
COPY entrypoint.sh /entrypoint.sh
RUN chmod 755 /entrypoint.sh && chown appuser:appuser /entrypoint.sh

# Create logs and secrets directories and set permissions
RUN mkdir -p logs /secrets && \
    chown -R appuser:appuser /app /secrets

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Use entrypoint which fetches secrets and starts the app
ENTRYPOINT ["/entrypoint.sh"]
