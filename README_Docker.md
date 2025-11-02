# 🐳 Docker Setup for Artifact Miner

This document explains how to build and run the Docker environment for the project.
The Docker setup ensures that everyone on the team runs the same Python environment, regardless of their local system.

---

## 📦 Prerequisites

Make sure you have the following installed on your machine:

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

Verify installation:

```bash
docker --version
docker compose version
Build and Run the Container
From the root of the repository (where the Dockerfile is located), run:

bash
Copy code
docker compose up --build
This command:

Builds the image using the Dockerfile

Starts the container defined in docker-compose.yml

Runs the test script docker_test_entry.py

✅ Verify It’s Working
If everything is set up correctly, you should see this message:

csharp
Copy code
✅ Docker environment is working correctly!
This confirms that:

The Docker image built successfully

Python is installed and running inside the container

Your project files were copied correctly

🧱 File Overview
File	Purpose
Dockerfile	Defines the container’s environment and dependencies
.dockerignore	Excludes unnecessary files from the image (caches, logs, etc.)
requirements.txt	Lists Python dependencies to install in the container
docker-compose.yml	Defines how to build and run the container
docker_test_entry.py	Temporary test script to verify Docker setup

🔄 Common Commands
Rebuild the image after making changes
bash
Copy code
docker compose build
Run the container without rebuilding
bash
Copy code
docker compose up
Stop and remove containers
bash
Copy code
docker compose down
Run a one-off command inside the container
bash
Copy code
docker compose run app python --version

🚀 Next Steps
Once the full project code is ready, update the Dockerfile’s final line:

dockerfile
Copy code
CMD ["python", "src/main.py"]
This will make the container run our actual application instead of the test file.