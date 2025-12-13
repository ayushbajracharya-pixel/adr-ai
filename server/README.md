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
    api/              # API routes and dependencies
      v1/
        routes/       # Route handlers (auth, conversations, files, query, upload)
        schemas/      # API request/response schemas
    core/             # Core application components
      config.py       # Settings and configuration
      database.py     # Database session management
      security.py     # JWT and authentication utilities
      exceptions.py   # Custom exception classes
    domain/           # Domain models and schemas
      models/         # Database models (Conversation, Message)
      schemas/        # Domain schemas (QueryIntent, ADRMetadata)
    infrastructure/   # External service integrations
      llm/            # LLM chains (extraction, generation)
      retrieval/      # Hybrid retrieval system (vector + BM25)
      vector_db/      # Vector database integration
    middleware/       # Request middleware (auth, CORS)
    services/         # Business logic services
      adr/            # ADR processing and querying
      auth/           # Authentication services
      conversation/    # Conversation management
      storage/        # S3 storage operations
    utils/            # Utility functions
    main.py           # FastAPI application entry point
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

# LLM Configuration (Optional - defaults shown)
LLM_MODEL_NAME=gpt-4.1-nano
LLM_TEMPERATURE=0.1
EXTRACTION_MODEL_NAME=gpt-4.1-nano
EXTRACTION_TEMPERATURE=0.0

# Retrieval Configuration (Optional - defaults shown)
RETRIEVAL_K=5
HYBRID_SEARCH_ENABLED=true
BM25_K=10
VECTOR_K=10
RRF_K=60
LIST_QUERY_LIMIT=50

# Text Splitting Configuration (Optional - defaults shown)
CHUNK_SIZE=1000
CHUNK_OVERLAP=200

# Conversation History Configuration (Optional - defaults shown)
CONVERSATION_HISTORY_LIMIT=10
MESSAGE_TRUNCATE_LENGTH=500
```

Notes:
- `.env` is loaded by `docker-compose.yml` and `app/core/config.py`.
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

- **Configuration Options:**
  - LLM settings: Model names and temperatures for query generation and extraction
  - Retrieval settings: Hybrid search parameters, retrieval counts, RRF configuration
  - Text processing: Chunk size and overlap for document splitting
  - Conversation settings: History limits and message truncation lengths
  - All configuration options have sensible defaults and are optional

---

## Features

### Core Functionality
- **Document Processing**: Upload and process ADR documents (PDF, DOCX, TXT, MD) with automatic text extraction and metadata extraction using LLM
- **Intelligent Query System**: Natural language queries with intent extraction, hybrid retrieval (semantic + BM25 + metadata filtering), and contextual response generation
- **Conversation Management**: Multi-threaded conversations with persistent message history, context-aware responses, and full CRUD operations
- **Authentication**: Google OAuth 2.0 with domain restriction (@lftechnology.com) and JWT-based API authentication

### Technical Features
- **Hybrid Search**: Combines vector similarity search, BM25 keyword search, and metadata filtering with Reciprocal Rank Fusion (RRF)
- **Query Validation**: Intelligent query quality validation to filter out conversational fillers and non-searchable queries
- **Metadata Extraction**: LLM-powered extraction of ADR metadata (technologies, domain, status, author, dates, etc.)
- **Vector Storage**: ChromaDB for semantic search with intelligent document chunking
- **File Storage**: AWS S3 integration (LocalStack for local development) with public-read access
- **Observability**: Optional LangSmith integration for LLM call tracing and debugging

---

## RAG Pipeline Architecture

The system implements a complete RAG (Retrieval-Augmented Generation) pipeline from document ingestion to query response. Here's how the components are connected:

### Data Ingestion Pipeline

```
1. Document Upload (PDF/DOCX/TXT/MD)
   ↓
2. S3 Storage → File stored in S3 bucket (adr_uploads/)
   ↓
3. Text Extraction → DocumentProcessor extracts raw text
   ↓
4. Metadata Extraction → MetadataExtractor uses LLM to extract:
   - ADR number, title, status, author, date
   - Technologies, domain, compliance needs
   - Decision, rationale, consequences
   ↓
5. Text Chunking → VectorStoreService splits text intelligently:
   - Uses ADR section headings as separators (Context, Decision, Consequences, etc.)
   - Configurable chunk size (default: 1000 chars) with overlap (200 chars)
   ↓
6. Vector Embedding → OpenAI embeddings generated for each chunk
   ↓
7. ChromaDB Storage → Chunks stored with:
   - Vector embeddings (for semantic search)
   - Metadata (for filtering)
   - Original text (for context in responses)
```

### Query & Retrieval Pipeline

```
1. User Query → Natural language question
   ↓
2. Query Validation → QueryProcessor validates:
   - Filters conversational fillers ("thanks", "ok", etc.)
   - Identifies searchable vs. conversational queries
   ↓
3. Intent Extraction → LLM extracts query intent:
   - Technologies mentioned
   - Domain/industry context
   - Requirements and compliance needs
   - Metadata filters (author, status, date ranges)
   - Query type (list, filter, semantic, hybrid)
   ↓
4. Hybrid Retrieval → HybridRetriever performs:
   a) Vector Search (Semantic):
      - Embed query → Find similar chunks via cosine similarity
   b) BM25 Search (Keyword):
      - Tokenize query → Rank documents by keyword relevance
   c) Metadata Filtering:
      - Apply filters (technologies, status, author, dates, etc.)
   d) Reciprocal Rank Fusion (RRF):
      - Merge results from vector + BM25 searches
      - Apply metadata filters
      - Rank final results
   ↓
5. Response Generation → ResponseGenerator:
   - Combines retrieved chunks with query and conversation history
   - Generates contextual response using LLM
   - Formats response as HTML with proper structure
   ↓
6. Reference Creation → Extracts source information:
   - ADR titles, filenames, relevant sections
   - Links to original documents (S3 URLs)
   ↓
7. Return Response → JSON with:
   - Query, response text (HTML), references array
```

### Key Components

- **ADRService**: Main orchestrator coordinating all services
- **DocumentProcessor**: Handles file format parsing and text extraction
- **MetadataExtractor**: LLM-powered structured metadata extraction
- **VectorStoreService**: Manages ChromaDB operations and intelligent chunking
- **QueryProcessor**: Validates queries, extracts intent, performs retrieval
- **HybridRetriever**: Combines vector, BM25, and metadata filtering
- **ResponseGenerator**: Creates contextual, formatted responses

### Conversation Context

When queries include conversation history:
- Last 10 messages are included in the prompt (configurable)
- Messages are truncated to 500 chars each (configurable)
- Context helps generate more relevant, contextual responses
- Conversation history stored in PostgreSQL for persistence

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

#### 1. Start the Debug Compose File

```bash
docker compose -f docker-compose.debug.yml up --build
```

This will:
- Start all services (web, chromadb, postgres, localstack)
- Expose debugpy on port **5678**
- Wait for a debugger to attach (the app won't start processing requests until you attach)

#### 2. Attach Your Debugger

The debug compose file uses **debugpy** and waits for a client connection. Attach from your IDE:

**VS Code:**

1. Create or update `.vscode/launch.json` in the project root:
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Remote Attach",
      "type": "debugpy",
      "request": "attach",
      "connect": {
        "host": "localhost",
        "port": 5678
      },
      "pathMappings": [
        {
          "localRoot": "${workspaceFolder}/server/app",
          "remoteRoot": "/app/app"
        }
      ]
    }
  ]
}
```

2. Start the debug compose file (from step 1)

3. Press `F5` or go to **Run → Start Debugging**

4. Select **"Python: Remote Attach"**

**Notes:**
- The container waits for the debugger; attach before making requests
- Hot reload is still enabled (`--reload` flag)
- All services (postgres, localstack, chromadb) are available in debug mode

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
