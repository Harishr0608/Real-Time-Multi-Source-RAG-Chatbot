FROM base AS app

WORKDIR /app

# Copy application code
COPY --chown=app_user:app_user . /app

# Set Python path
ENV PYTHONPATH=/app

# Expose ports
EXPOSE 8000 8501

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command (can be overridden in docker-compose)
CMD ["uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"]