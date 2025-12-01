# 🐳 Docker Setup for Artifact Miner

This guide explains how to **build and run the Docker environment** for the project.  
Docker ensures that everyone on the team runs the same Python environment — regardless of their local setup.

---

## 📦 Prerequisites

Make sure you have the following installed:

- **Docker**
- **Docker Compose**

Verify installation:

```bash
docker --version
docker compose version
```

---

## ⚙️ Build & Run the Container

From the **root of the repository** (where the `Dockerfile` is located), run:

```bash
docker compose up --build
```

This command will:

1. **Build** the Docker image using the `Dockerfile`
2. **Start** the container defined in `docker-compose.yml`
3. **Run** the test script `docker_test_entry.py` to verify that everything works

---

## ✅ Verifying the Setup

If everything is configured correctly, you should see this message:

```bash
✅ Docker environment is working correctly!
```

This confirms that:

- The Docker image built successfully  
- Python is installed and running inside the container  
- Your project files were copied correctly  

---

## 🧱 File Overview

| File | Purpose |
|------|----------|
| `Dockerfile` | Defines the container’s environment and dependencies |
| `.dockerignore` | Excludes unnecessary files (logs, caches, etc.) |
| `requirements.txt` | Lists Python dependencies to install |
| `docker-compose.yml` | Defines how to build and run the container |
| `docker_test_entry.py` | Temporary test script used to verify setup |

---

## 🔄 Common Docker Commands

**Rebuild the image after making changes:**
```bash
docker compose build
```

**Run the container without rebuilding:**
```bash
docker compose up
```

**Stop and remove containers:**
```bash
docker compose down
```

**Run a one-off command inside the container:**
```bash
docker compose run app python --version
```

---

**To build the containers and see tables added to the DB, do the following:**
```bash
docker compose build
docker compose up -d
docker compose exec db psql -U postgres -d postgres

\dt
```