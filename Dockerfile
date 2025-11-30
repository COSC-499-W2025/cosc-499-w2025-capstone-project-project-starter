# Step 1: Start from Python 3.9 slim
FROM python:3.9-slim

# Step 2: Set working directory
WORKDIR /app

# Step 3: Install system dependencies for psycopg2
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Step 4: Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Step 5: Copy project files
COPY . /app

# Step 6: Default command
CMD ["python", "docker_test_entry.py"]