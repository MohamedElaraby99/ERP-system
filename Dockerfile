# Multi-stage build for production optimization
FROM python:3.9-slim as builder

# Set work directory
WORKDIR /app

# Install build dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        python3-dev \
        libpq-dev \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# Production stage
FROM python:3.9-slim

# Set environment variables for production
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production \
    FLASK_DEBUG=False

# Create app user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Install runtime dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client \
        libpq5 \
        curl \
        nginx \
        supervisor \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy wheels from builder stage and install
COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache /wheels/*

# Create necessary directories
RUN mkdir -p /app/logs \
    && mkdir -p /app/uploads \
    && mkdir -p /app/backups \
    && mkdir -p /app/static \
    && mkdir -p /app/templates

# Copy application code
COPY . /app/

# Copy nginx configuration
COPY nginx/nginx.conf /etc/nginx/sites-available/default

# Copy supervisor configuration
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Set proper permissions
RUN chown -R appuser:appuser /app \
    && chown -R appuser:appuser /var/log/nginx \
    && chown -R appuser:appuser /var/lib/nginx

# Create startup script
COPY docker/start.sh /start.sh
RUN chmod +x /start.sh

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8005/health || exit 1

# Expose port
EXPOSE 8005

# Start application
CMD ["/start.sh"] 