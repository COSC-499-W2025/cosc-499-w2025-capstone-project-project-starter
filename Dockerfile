# Step 1: Start from a lightweight Python image
FROM python:3.12-slim

# Step 2: Set a working directory inside the container
WORKDIR /app

# Step 3: Copy all the project files into that directory
COPY . /app

# Step 4: Install dependencies from requirements.txt if it exists
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt || true

# Step 5: Default command when container runs
CMD ["python", "docker_test_entry.py"]
