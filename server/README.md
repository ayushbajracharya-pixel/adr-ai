# ADR AI Server

A FastAPI-based backend that ingests ADRs (Architecture Decision Records), extracts key data with OpenAI, stores vectors in ChromaDB, and uploads files to AWS S3.

---

## Prerequisites

- Docker and Docker Compose
  - On Windows with WSL2: Docker Desktop with WSL integration enabled
- Python 3.13 (for local dev)
  - Recommended via pyenv or install from Deadsnakes PPA
- Poetry (for local dev)

---

## Project Structure

```text
server/
  app/
    chains/
    config/
    constants/
    models/
    services/
    utils/
    main.py
  docker-compose.yml
  docker-compose.debug.yml
  Dockerfile
  pyproject.toml
  poetry.lock
  README.md
```

---

## Environment Variables

Create a `.env` file under `server/`:

```bash
OPENAI_API_KEY=sk-your-openai-key
AWS_ACCESS_KEY_ID=your-access-key-id
AWS_SECRET_ACCESS_KEY=your-secret-access-key
S3_BUCKET_NAME=your-bucket-name
S3_BUCKET_REGION=us-east-1

# Google OAuth 2.0
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
SECRET_KEY=your-random-secret-key-for-jwt-signing
FRONTEND_URL=http://localhost:3000
```

Notes:
- `.env` is loaded by `docker-compose.yml` and `app/config/settings.py`.
- Ensure the AWS credentials have permission to put/get/list objects in `S3_BUCKET_NAME`.
- **Google OAuth 2.0 Setup:**
  1. Go to [Google Cloud Console](https://console.cloud.google.com/)
  2. Create a new project or select an existing one
  3. Configure the OAuth consent screen:
     - Go to "APIs & Services" → "OAuth consent screen"
     - Choose "External" (unless using Google Workspace)
     - Fill in app name, user support email, and developer contact
     - Add scopes: `openid`, `email`, `profile`
     - Save and continue
  4. Create OAuth 2.0 credentials:
     - Go to "APIs & Services" → "Credentials"
     - Click "Create Credentials" → "OAuth 2.0 Client ID"
     - Choose "Web application" as the application type
     - Add authorized redirect URI: `http://localhost:8000/api/auth/google/callback` (or your server URL)
     - Click "Create"
  5. Copy the Client ID and Client Secret to your `.env` file
  6. Generate a random secret key for `SECRET_KEY` (e.g., using `openssl rand -hex 32`)
  
  Note: This uses the modern Google Identity Services (OAuth 2.0 / OpenID Connect) - no deprecated APIs required.

---

## Run with Docker Compose (recommended)

```bash
cd server
# Build and start FastAPI and ChromaDB
docker compose up --build
```

Services:
- FastAPI: http://localhost:8000
- ChromaDB: http://localhost:8001 (proxied to container 8000)

Hot reload is enabled via `--reload` (mounted `./app` volume).

### Debug Mode

```bash
docker compose -f docker-compose.debug.yml up --build
```
- Opens debugpy on port 5678 and waits for client attach.

---

## Run locally (without Docker)

1) Install Python 3.13

- Using pyenv (recommended):
```bash
pyenv install 3.13.0
pyenv virtualenv 3.13.0 adr-ai-server
pyenv activate adr-ai-server
```

- Or via apt (Deadsnakes):
```bash
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install -y python3.13 python3.13-venv python3.13-dev
python3.13 -m venv .venv
source .venv/bin/activate
```

2) Install Poetry and deps
```bash
pip install poetry
poetry install
```

3) Set env vars
```bash
cp .env.example .env  # if you create one, otherwise ensure required keys are present
```

4) Run API
```bash
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

5) Start ChromaDB (if running locally)
- Option A: Run via Docker only for ChromaDB
```bash
docker run -p 8001:8000 -v $(pwd)/data/chroma_db:/data --name chromadb_server -d chromadb/chroma
```
- Option B: Use full Docker Compose (recommended above)

---

## API

- Health: `GET /api/health` → `{ "status": "healthy" }`
- Upload ADR: `POST /api/upload` (multipart/form-data, file field: `file`)

---

## Common Issues (WSL2/Docker)

- Permission denied on Docker socket:
```bash
sudo usermod -aG docker $USER
newgrp docker
# or temporarily: sudo chmod 666 /var/run/docker.sock
```

- `systemctl restart docker` fails on WSL2:
  - Restart Docker Desktop from Windows instead. WSL2 does not manage the docker service via systemd.

- `Unit docker.service not found`:
  - Same as above; use Docker Desktop controls.

- Ensure WSL integration is enabled for your distro in Docker Desktop Settings → Resources → WSL Integration.

---

## Development Tips

- Code style/typing managed via Poetry dependencies; run linters/formatters as configured.
- Hot reload active in Docker Compose; modify files in `server/app/` to see changes.
- S3 bucket policy is set to public-read for object access in `UploaderService`.

---

## Cleaning up

```bash
# Stop and remove containers
cd server
docker compose down

# Remove chroma data (if needed)
rm -rf data/chroma_db
```
