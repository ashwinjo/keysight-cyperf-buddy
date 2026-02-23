FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python package manager and dependencies
RUN pip install --no-cache-dir uv

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies using uv
RUN uv pip install --system -r requirements.txt

# Copy application code
COPY . .

# Health check: API responds to /health
HEALTHCHECK --interval=5s --timeout=10s --retries=5 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
