FROM python:3.10-slim

WORKDIR /app

# Install system dependencies for OCR and image processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies with pip cache mount for faster rebuilds
# Using --mount=type=cache allows pip to reuse downloaded packages between builds
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements.txt

# Copy application code (this layer only invalidates when code changes)
COPY src/ ./src/
COPY utils/ ./utils/
COPY frontend/ ./frontend/

# Set Python path to include src directory
ENV PYTHONPATH=/app/src

# Expose API port
EXPOSE 8000

# Run the API server
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
