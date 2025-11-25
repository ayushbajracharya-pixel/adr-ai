# ADR AI Assistant - Quick Reference

## 🎯 What We Built

An intelligent RAG-based system that helps teams make technology decisions by querying past Architecture Decision Records (ADRs) using natural language.

---

## ✅ Core Features

### 1. **Authentication**
- Google OAuth 2.0 login
- Domain restriction (@lftechnology.com)
- JWT token-based API access (30-day expiry)

### 2. **Document Upload & Processing**
- Supports: PDF, DOCX, TXT, MD
- Auto text extraction
- LLM-based metadata extraction (ADR number, technologies, decision, rationale, etc.)
- Intelligent chunking based on ADR section headings
- Vector embedding & indexing in ChromaDB
- S3 storage for documents

### 3. **Intelligent Query System (RAG)**
- Natural language queries
- Intent extraction (technologies, requirements, domain, compliance)
- Hybrid retrieval: semantic search + metadata filtering
- Contextual response generation
- HTML-formatted responses with references

### 4. **Conversation Management**
- Multiple conversation threads
- Persistent message history
- Context-aware responses (uses last 10 messages)
- Auto-generated conversation titles
- Full CRUD operations

### 5. **File Management**
- List all uploaded ADRs
- Delete from S3 + vector database
- View file metadata

---

## 🏗️ Tech Stack

- **Backend**: FastAPI (Python, async)
- **Database**: PostgreSQL (conversations, messages)
- **Vector DB**: ChromaDB (semantic search)
- **Storage**: AWS S3 / LocalStack
- **LLM**: OpenAI GPT-4.1-nano
- **Embeddings**: OpenAI
- **Auth**: Google OAuth + JWT

---

## 📡 API Endpoints

### Auth
- `GET /api/auth/google/login` - Google login
- `GET /api/auth/me` - Current user
- `POST /api/auth/logout` - Logout

### ADR Management
- `POST /api/upload` - Upload ADR
- `GET /api/files` - List files
- `DELETE /api/files/{object_key}` - Delete file

### Conversations
- `GET /api/conversations` - List conversations
- `POST /api/conversations` - Create conversation
- `GET /api/conversations/{id}` - Get conversation
- `PATCH /api/conversations/{id}` - Update title
- `DELETE /api/conversations/{id}` - Delete conversation
- `POST /api/conversations/{id}/messages` - Send message

### Query
- `POST /api/query` - Standalone query

---

## 🔄 Data Flow

**Upload:**
```
File → S3 → Text Extraction → Metadata Extraction (LLM) 
→ Chunking → Embedding → ChromaDB
```

**Query:**
```
Query → Intent Extraction (LLM) → Hybrid Retrieval 
→ Response Generation (LLM) → References
```

---

## 💡 Key Differentiators

1. **Intent Understanding**: Extracts technologies, requirements, domain from queries
2. **Hybrid Retrieval**: Semantic search + metadata filtering
3. **Conversation Context**: Maintains context across messages
4. **Structured Metadata**: Rich extraction enables precise filtering
5. **Production-Ready**: Auth, error handling, data isolation

---

## 📊 Database Schema

**Conversations:**
- id, user_email, title, created_at, updated_at

**Messages:**
- id, conversation_id, role, content, references (JSON), created_at

---

## 🎯 Use Cases

- New team members learning from past decisions
- Architects making similar decisions
- Compliance teams checking regulatory alignment
- Product managers understanding trade-offs

---

## 🔐 Security

- Google OAuth with domain restriction
- JWT tokens (30-day expiry)
- User-specific data isolation
- Bearer token authentication
- CORS configured

---

## 📈 Stats

- **File Formats**: 4 (PDF, DOCX, TXT, MD)
- **Chunk Size**: 1000 chars (200 overlap)
- **Retrieval**: Top 5 chunks
- **Context Window**: Last 10 messages
- **Token Expiry**: 30 days

