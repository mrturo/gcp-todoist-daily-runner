# Use Alpine Linux for minimal attack surface and fewer CVEs
# Alpine uses musl libc instead of glibc, reducing vulnerability exposure
FROM python:3.11-alpine

WORKDIR /app

# Create non-root user first (better layer caching)
RUN adduser -D -u 1000 appuser


# Instala versiones seguras de paquetes críticos antes de requirements.txt
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip>=25.3 && \
    pip install --no-cache-dir --upgrade wheel>=0.46.2 jaraco.context>=6.1.0 'protobuf<6' && \
    pip cache purge && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code and set ownership
COPY --chown=appuser:appuser src/ ./src/

# Switch to non-root user
USER appuser

# Health check for container orchestration
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT:-8080}/').read()" || exit 1

# Use exec form for proper signal handling (SIGTERM for graceful shutdown)
# Cloud Run provides $PORT, defaults to 8080 if not set
CMD ["sh", "-c", "uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1 --log-level warning --access-log --no-server-header"]

