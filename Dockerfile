# Step 1: Start from Alpine Linux
FROM alpine:3.18

# Step 2: Install system dependencies for Python build, pyenv, and PostgreSQL
RUN apk add --no-cache \
    bash \
    curl \
    git \
    build-base \
    zlib-dev \
    bzip2-dev \
    readline-dev \
    sqlite-dev \
    openssl-dev \
    libffi-dev \
    postgresql postgresql-contrib postgresql-client postgresql-dev \
    ca-certificates \
    && update-ca-certificates

# Step 3: Set environment variables for pyenv
ENV PYENV_ROOT="/root/.pyenv"
ENV PATH="$PYENV_ROOT/bin:$PYENV_ROOT/shims:$PATH"

# Step 4: Install pyenv
RUN git clone https://github.com/pyenv/pyenv.git $PYENV_ROOT \
    && git clone https://github.com/pyenv/pyenv-virtualenv.git $PYENV_ROOT/plugins/pyenv-virtualenv

# Step 5: Copy project files into container
WORKDIR /app
COPY . /app

# Step 6: Ensure install script is executable
RUN chmod +x /app/src/ml/setup.sh

# Step 7: Run install script (which installs Python 3.6.15 and dependencies)
RUN bash /app/src/ml/setup.sh

# Step 8: Default command to run your Python app
# CMD ["python", "main.py"]
