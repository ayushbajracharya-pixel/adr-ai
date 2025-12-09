# ADR AI Assistant - Feature Documentation

## Overview
The ADR AI Assistant is an intelligent system that helps teams make technology decisions by leveraging past Architecture Decision Records (ADRs). It uses RAG (Retrieval-Augmented Generation) to provide contextual answers based on historical architectural decisions.

---

## 🎯 Core Features

### 1. **Authentication & Authorization**
**What it does:**
- Google OAuth 2.0 authentication for secure access
- Domain-restricted access (only @lftechnology.com emails allowed)
- JWT-based token authentication for API requests
- Session management with secure token storage

**How it works:**
- Users click "Login with Google" → redirected to Google OAuth
- After authentication, system validates email domain
- JWT token is generated and sent to frontend
- All API requests require Bearer token in Authorization header
- Token expires after 30 days

**Endpoints:**
- `GET /api/auth/google/login` - Initiate Google login
- `GET /api/auth/google/callback` - OAuth callback handler
- `GET /api/auth/me` - Get current user info
- `POST /api/auth/logout` - Logout endpoint

---

### 2. **Document Upload & Processing**
**What it does:**
- Upload ADR documents (PDF, DOCX, TXT, MD formats)
- Automatic text extraction from documents
- Intelligent metadata extraction using LLM
- Document storage in S3 (or LocalStack for local dev)
- Vector embedding and indexing in ChromaDB

**How it works:**
1. **File Upload**: User uploads ADR document via API
2. **S3 Storage**: File is uploaded to S3 bucket with organized naming (`adr_uploads/filename`)
3. **Text Extraction**: 
   - PDFs: Uses `pypdfium2` for text extraction
   - DOCX: Uses `python-docx` library
   - TXT/MD: Direct text decoding
4. **Metadata Extraction**: 
   - LLM (GPT-4.1-nano) extracts structured metadata:
     - ADR number, title, status, date, author
     - Decision makers, context, considered options
     - Decision, rationale, technologies used
   - Metadata is one-hot encoded for technologies (e.g., `tech_kafka: true`)
5. **Document Chunking**: 
   - Dynamic text splitting based on ADR section headings
   - Uses canonical heading mapping (e.g., "Context", "Decision", "Rationale")
   - Chunk size: 1000 chars with 200 char overlap
6. **Vector Indexing**: 
   - Each chunk is embedded using OpenAI embeddings
   - Stored in ChromaDB vector database with metadata
   - Enables semantic search capabilities

**Endpoints:**
- `POST /api/upload` - Upload and process ADR document

**Technical Details:**
- Supports multiple file formats (PDF, DOCX, TXT, MD)
- Handles in-memory file processing (no temporary files)
- Error handling for S3 upload failures, text extraction errors, and LLM failures
- Public read policy on S3 bucket for document access

---

### 3. **Intelligent Query System (RAG)**
**What it does:**
- Natural language queries about technology decisions
- Intent extraction from user queries
- Hybrid retrieval with metadata filtering
- Contextual response generation with references
- Conversation history support

**How it works:**
1. **Query Intent Extraction**:
   - LLM analyzes user query to extract:
     - Technologies mentioned/inferred
     - Requirements (technical/business)
     - Domain/industry context
     - Compliance needs (HIPAA, GDPR, PCI-DSS)
     - Use case information
   
2. **Hybrid Retrieval**:
   - Semantic search using vector similarity
   - Metadata filtering based on extracted intent:
     - Technology filters (e.g., `tech_kafka: true`)
     - Domain filters
     - Combined with logical AND operators
   - Retrieves top 5 most relevant document chunks

3. **Response Generation**:
   - Enhanced prompt includes:
     - Retrieved ADR context
     - Conversation history (last 10 messages)
     - Extracted intent information
   - LLM generates comprehensive HTML-formatted response
   - Response includes relevant ADR references

4. **Reference Formatting**:
   - Unique references from retrieved documents
   - Includes: filename, ADR number, title, status, author, date
   - Provides S3 URI and public URL for document access

**Endpoints:**
- `POST /api/query` - Query ADRs (standalone)
- `POST /api/conversations/{id}/messages` - Query within conversation context

**Technical Details:**
- Uses GPT-4.1-nano for cost-effective inference
- Temperature set to 0.1 for consistent responses
- Fallback to basic search if intent extraction fails
- HTML-formatted responses for rich UI display

---

### 4. **Conversation Management**
**What it does:**
- Create and manage multiple conversation threads
- Persistent conversation history
- Auto-generated conversation titles
- Context-aware responses using conversation history

**How it works:**
1. **Conversation Creation**:
   - User creates a new conversation (optional title)
   - System generates unique conversation ID
   - Linked to user's email for isolation

2. **Message Storage**:
   - Each message stored with:
     - Role (user/assistant)
     - Content
     - References (for assistant messages)
     - Timestamp
   - Messages linked to conversation via foreign key

3. **Context-Aware Queries**:
   - When sending a message, system:
     - Retrieves conversation history (last 100 messages)
     - Passes history to RAG system
     - LLM uses history for contextual responses
   - Auto-generates title from first user message (first 50 chars)

4. **Conversation Management**:
   - List all conversations (sorted by updated_at)
   - Update conversation title
   - Delete conversation (cascades to messages)
   - Get full conversation with all messages

**Endpoints:**
- `GET /api/conversations` - List all conversations
- `POST /api/conversations` - Create new conversation
- `GET /api/conversations/{id}` - Get conversation with messages
- `PATCH /api/conversations/{id}` - Update conversation title
- `DELETE /api/conversations/{id}` - Delete conversation
- `POST /api/conversations/{id}/messages` - Send message in conversation

**Database Schema:**
- `Conversations` table: id, user_email, title, created_at, updated_at
- `Messages` table: id, conversation_id, role, content, references (JSON), created_at
- Foreign key with CASCADE delete for data integrity

---

### 5. **File Management**
**What it does:**
- List all uploaded ADR documents
- Delete documents from both S3 and vector database
- View file metadata (size, upload date, URLs)

**How it works:**
1. **List Files**:
   - Queries S3 bucket for all files in `adr_uploads/` folder
   - Returns metadata: filename, size, last modified, public URL
   - Excludes folder entries

2. **Delete Files**:
   - Deletes from ChromaDB vector store (filters by S3 URI)
   - Deletes from S3 bucket
   - Handles partial failures gracefully

**Endpoints:**
- `GET /api/files` - List all uploaded files
- `DELETE /api/files/{object_key}` - Delete file from S3 and vector store

---

## 🏗️ Technical Architecture

### **Backend Stack:**
- **Framework**: FastAPI (Python)
- **Database**: PostgreSQL (async with SQLAlchemy)
- **Vector DB**: ChromaDB (for semantic search)
- **Storage**: AWS S3 / LocalStack (for document storage)
- **LLM**: OpenAI GPT-4.1-nano (via LangChain)
- **Embeddings**: OpenAI text-embedding models
- **Auth**: Google OAuth 2.0 + JWT tokens

### **Key Libraries:**
- `langchain` - LLM orchestration and RAG chains
- `langchain-chroma` - ChromaDB integration
- `langchain-openai` - OpenAI integration
- `sqlalchemy` - Database ORM
- `authlib` - OAuth implementation
- `boto3` - AWS S3 client
- `pypdfium2` - PDF text extraction
- `python-docx` - Word document processing

### **Data Flow:**

**Upload Flow:**
```
File Upload → S3 Storage → Text Extraction → Metadata Extraction (LLM) 
→ Text Chunking → Embedding Generation → ChromaDB Indexing
```

**Query Flow:**
```
User Query → Intent Extraction (LLM) → Hybrid Retrieval (Vector + Metadata) 
→ Context Assembly → Response Generation (LLM) → Reference Formatting → Response
```

---

## 🔍 Advanced Features

### **1. Dynamic Text Splitting**
- Analyzes document structure to find ADR section headings
- Uses canonical heading mapping (handles synonyms)
- Creates intelligent chunk boundaries at section breaks
- Ensures chunks contain meaningful, complete information

### **2. Metadata-Based Filtering**
- One-hot encoding for technologies (e.g., `tech_kafka`, `tech_sqs`)
- Domain-based filtering
- Logical AND combination of multiple filters
- Enables precise retrieval based on query intent

### **3. Conversation Context**
- Maintains conversation history across messages
- Passes last 10 messages to LLM for context
- Enables follow-up questions and clarifications
- Auto-generates meaningful conversation titles

### **4. Error Handling**
- Graceful fallbacks (e.g., basic search if intent extraction fails)
- Comprehensive error messages
- Transaction rollback on failures
- Partial failure handling (e.g., S3 delete succeeds but vector delete fails)

---

## 📊 Database Schema

### **Conversations Table**
- `id` (UUID, Primary Key)
- `user_email` (String, Indexed)
- `title` (String, Nullable)
- `created_at` (Timestamp)
- `updated_at` (Timestamp)

### **Messages Table**
- `id` (UUID, Primary Key)
- `conversation_id` (Foreign Key → Conversations.id, CASCADE DELETE)
- `role` (String: 'user' or 'assistant')
- `content` (Text)
- `references` (JSON, Nullable)
- `created_at` (Timestamp)

---

## 🔐 Security Features

1. **Authentication**: Google OAuth with domain restriction
2. **Authorization**: JWT tokens with 30-day expiration
3. **Data Isolation**: User-specific conversation access
4. **Secure Storage**: S3 bucket with public-read policy for documents
5. **CORS**: Configured for specific frontend origins

---

## 🚀 Deployment Features

- **Docker Compose** support for local development
- **LocalStack** integration for S3 emulation
- **Environment-based configuration** (.env files)
- **Health check endpoint** for monitoring
- **LangSmith integration** for LLM tracing (optional)

---

## 📝 Usage Examples

### **Upload an ADR:**
```bash
POST /api/upload
Content-Type: multipart/form-data
Authorization: Bearer <token>

file: <ADR-0001.pdf>
```

### **Query ADRs:**
```bash
POST /api/query
Authorization: Bearer <token>
Content-Type: application/json

{
  "query": "What messaging system should I use for a microservices architecture with high throughput requirements?"
}
```

### **Create Conversation:**
```bash
POST /api/conversations
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "Microservices Architecture Discussion"
}
```

### **Send Message in Conversation:**
```bash
POST /api/conversations/{conversation_id}/messages
Authorization: Bearer <token>
Content-Type: application/json

{
  "query": "What are the trade-offs between Kafka and SQS?"
}
```

---

## 🎯 Key Differentiators

1. **Intelligent Intent Extraction**: Understands user queries beyond keyword matching
2. **Hybrid Retrieval**: Combines semantic search with metadata filtering
3. **Conversation Context**: Maintains context across multiple interactions
4. **Structured Metadata**: Rich metadata extraction enables precise filtering
5. **Production-Ready**: Error handling, authentication, data isolation
6. **Scalable Architecture**: Async operations, vector database, cloud storage

---

## 📈 Future Enhancement Opportunities

- Multi-user collaboration on conversations
- ADR versioning and supersession tracking
- Advanced analytics and insights dashboard
- Export conversations as reports
- Integration with ADR authoring tools
- Real-time notifications for new ADRs
- Advanced search filters (date range, author, status)

