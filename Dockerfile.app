FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Install system dependencies INCLUDING curl для healthcheck
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY agata_prompt_data/ ./agata_prompt_data/
COPY config/ ./config/
COPY run_server.py .
COPY run_telegram_bot.py .
COPY config.env .

# Create non-root user
RUN useradd --create-home --shell /bin/bash agatha
RUN chown -R agatha:agatha /app
USER agatha

# Expose port
EXPOSE 8000

# Health check - ТЕПЕРЬ curl УСТАНОВЛЕН
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1

# Run with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120", "app.api.main:create_app()"] 