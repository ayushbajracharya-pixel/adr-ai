# ADR AI Server

A FastAPI-based backend that ingests ADRs (Architecture Decision Records), extracts key data with OpenAI, stores vectors in ChromaDB, uploads files to AWS S3 (via LocalStack for local development), manages conversations in PostgreSQL, and integrates with LangSmith for observability.

---

## Prerequisites

- Docker and Docker Compose
  - On Windows with WSL2: Docker Desktop with WSL integration enabled
- Python 3.12 (for local dev)
  - Recommended via pyenv or install from Deadsnakes PPA
- UV (for local dev) - Fast Python package installer and resolver

---

## Migration from Poetry to UV

This project has been migrated from Poetry to UV. If you're setting up the project for the first time or migrating:

1. **Remove old Poetry files** (optional, for cleanup):
   ```bash
   rm poetry.lock
   rm -rf .venv  # if you had a Poetry-managed venv
   ```

2. **Install UV** (see installation instructions below)

3. **Sync dependencies** - This will create `uv.lock` and set up the virtual environment:
   ```bash
   uv sync
   ```

4. **Run the application**:
   ```bash
   uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

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
  uv.lock
  README.md
```

---

## Environment Variables

Create a `.env` file under `server/`:

```bash
OPENAI_API_KEY=sk-your-openai-key

# Database (PostgreSQL)
DATABASE_URL=postgresql+asyncpg://adr_user:adr_password@postgres:5432/adr_db

# ChromaDB (Vector Database)
# When running locally: CHROMADB_HOST=localhost CHROMADB_PORT=8001
# When running in Docker: CHROMADB_HOST=chromadb CHROMADB_PORT=8000 (defaults)
CHROMADB_HOST=chromadb
CHROMADB_PORT=8000

# AWS / LocalStack (for local development)
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
S3_BUCKET_NAME=adr-bucket
S3_BUCKET_REGION=us-east-1
AWS_ENDPOINT_URL=http://localstack:4566  # LocalStack endpoint

# Google OAuth 2.0
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
SECRET_KEY=your-random-secret-key-for-jwt-signing
FRONTEND_URL=http://localhost:3000

# LangSmith (Optional - for observability)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
LANGCHAIN_API_KEY=your-langsmith-api-key
LANGCHAIN_PROJECT=adr-ai
```

Notes:
- `.env` is loaded by `docker-compose.yml` and `app/config/settings.py`.
- **ChromaDB Configuration:**
  - When running locally (outside Docker): Set `CHROMADB_HOST=localhost` and `CHROMADB_PORT=8001` to connect to the ChromaDB container running on the host port.
  - When running in Docker: Use defaults (`CHROMADB_HOST=chromadb` and `CHROMADB_PORT=8000`) to connect via Docker service name.
- For local development, LocalStack emulates AWS S3. The bucket will be created automatically.
- For production, remove `AWS_ENDPOINT_URL` and use real AWS credentials.
- LangSmith integration is optional but recommended for monitoring LLM calls and debugging.
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

- **LangSmith Setup (Optional):**
  1. Sign up at [LangSmith](https://smith.langchain.com/)
  2. Create an API key from your account settings
  3. Create a project (or use the default)
  4. Add the API key and project name to your `.env` file
  5. Set `LANGCHAIN_TRACING_V2=true` to enable tracing

---

## Features

- **Conversation Management**: Users can create, view, update, and delete conversations
- **Message History**: All messages are stored in PostgreSQL with conversation context
- **Context-Aware Responses**: AI responses use conversation history for better context
- **LocalStack Integration**: Local AWS S3 emulation for development
- **LangSmith Observability**: Monitor and debug LLM calls in real-time
- **PostgreSQL Storage**: Persistent storage for conversations and messages

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
- PostgreSQL: localhost:5433 (mapped from container port 5432)
- LocalStack: http://localhost:4566 (S3 emulation)

Hot reload is enabled via `--reload` (mounted `./app` volume).

### Setup LocalStack Resources

After starting LocalStack, run the setup script to create the S3 bucket and configure policies:

```bash
# From the host machine
./scripts/localstack_setup.sh

# Or from inside the web container
docker compose exec web bash -c "cd /app && ./scripts/localstack_setup.sh"
```

The script will:
- Create the S3 bucket (if it doesn't exist)
- Set up public read access policy
- Configure CORS for web access

You can customize the bucket name by setting the `S3_BUCKET_NAME` environment variable.

### Debug Mode

```bash
docker compose -f docker-compose.debug.yml up --build
```
- Opens debugpy on port 5678 and waits for client attach.

---

## Run locally (without Docker)

### Installing UV on Ubuntu

UV is a fast Python package installer and resolver written in Rust. Install it using one of these methods:

**Option 1: Using the official installer (Recommended)**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

After installation, add UV to your PATH (if not already added):
```bash
source $HOME/.cargo/env
# Or add to your ~/.bashrc or ~/.zshrc:
echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

**Option 2: Using pip**
```bash
pip install uv
```

**Option 3: Using pipx**
```bash
pipx install uv
```

Verify installation:
```bash
uv --version
```

### Setting up the project

1) Install Python 3.12

- Using pyenv (recommended):
```bash
pyenv install 3.12.0
pyenv local 3.12.0
```

- Or via apt (Deadsnakes):
```bash
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3.12-dev
```

2) Install dependencies with UV
```bash
# UV will automatically create a virtual environment and install dependencies
uv sync

# Or if you want to use an existing virtual environment:
# source .venv/bin/activate  # if you have one
# uv pip install -e .
```

3) Set env vars
```bash
cp .env.example .env  # if you create one, otherwise ensure required keys are present
```

4) Run API
```bash
# Using UV (recommended - automatically uses the project's virtual environment)
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Or activate the virtual environment manually and run:
source .venv/bin/activate  # UV creates .venv by default
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

5) Start ChromaDB (if running locally)
- Option A: Run via Docker only for ChromaDB
```bash
docker run -p 8001:8000 -v $(pwd)/data/chroma_db:/data --name chromadb_server -d chromadb/chroma
```
- Option B: Use full Docker Compose (recommended above)

### Common UV Commands

```bash
# Install/update dependencies
uv sync

# Add a new dependency
uv add package-name

# Add a dev dependency
uv add --dev package-name

# Remove a dependency
uv remove package-name

# Run a command in the project environment
uv run <command>

# Activate the virtual environment
source .venv/bin/activate

# Update all dependencies
uv sync --upgrade
```

---

## API

### Core Endpoints
- Health: `GET /api/health` → `{ "status": "healthy" }`
- Upload ADR: `POST /api/upload` (multipart/form-data, file field: `file`)
- Query ADRs: `POST /api/query` → `{ "query": "...", "response": "...", "references": [...] }`
- List Files: `GET /api/files` → `[{ "object_key": "...", "filename": "...", ... }]`
- Delete File: `DELETE /api/files/{object_key}`

### Conversation Endpoints
- List Conversations: `GET /api/conversations` → `[{ "id": "...", "title": "...", ... }]`
- Create Conversation: `POST /api/conversations` → `{ "id": "...", "title": "...", ... }`
- Get Conversation: `GET /api/conversations/{id}` → `{ "id": "...", "messages": [...] }`
- Update Conversation: `PATCH /api/conversations/{id}` → `{ "id": "...", "title": "...", ... }`
- Delete Conversation: `DELETE /api/conversations/{id}` → `204 No Content`
- Send Message: `POST /api/conversations/{id}/messages` → `{ "query": "...", "response": "...", "references": [...] }`

### Auth Endpoints
- Google Login: `GET /api/auth/google/login`
- Get Current User: `GET /api/auth/me`
- Logout: `POST /api/auth/logout`

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

- Code style/typing managed via UV dependencies; run linters/formatters as configured.
- Hot reload active in Docker Compose; modify files in `server/app/` to see changes.
- S3 bucket policy is set to public-read for object access in `UploaderService`.
- UV automatically manages virtual environments - no need to manually create or activate them when using `uv run`.

---

## Cleaning up

```bash
# Stop and remove containers
cd server
docker compose down

# Remove chroma data (if needed)
rm -rf data/chroma_db
```
