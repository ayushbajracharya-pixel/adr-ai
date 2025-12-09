# ADR AI Assistant - Demo Script

## 🎯 Quick Overview (30 seconds)
"Our ADR AI Assistant is an intelligent system that helps teams make better technology decisions by learning from past Architecture Decision Records. Think of it as a smart knowledge base that can answer questions like 'What messaging system should I use?' by finding and summarizing relevant decisions from your organization's ADR history."

---

## 📋 Feature Walkthrough

### 1. **Authentication** (1 minute)
**What to say:**
- "We've implemented secure Google OAuth authentication"
- "Only users with @lftechnology.com emails can access the system"
- "After login, users get a JWT token that's valid for 30 days"

**What to show:**
- Login page with "Login with Google" button
- OAuth flow redirect
- Token-based API access

**Technical highlight:**
- "We use JWT tokens for stateless authentication, and all API endpoints are protected with Bearer token authentication"

---

### 2. **Document Upload & Processing** (2 minutes)
**What to say:**
- "Users can upload ADR documents in multiple formats: PDF, Word, or text files"
- "The system automatically extracts text, analyzes the content, and indexes it for search"

**What to show:**
- Upload a sample ADR document
- Show the upload success message

**Technical highlight:**
- "Behind the scenes, we:
  1. Upload the file to S3 for permanent storage
  2. Extract text using specialized libraries (pypdfium2 for PDFs, python-docx for Word)
  3. Use an LLM to extract structured metadata like ADR number, technologies used, decision rationale
  4. Split the document into intelligent chunks based on ADR section headings
  5. Generate embeddings and store them in ChromaDB vector database for semantic search"

**Key point:**
- "The metadata extraction is intelligent - it identifies technologies, decision makers, context, and rationale automatically"

---

### 3. **Intelligent Query System** (3 minutes)
**What to say:**
- "This is the core feature - users can ask natural language questions about technology decisions"
- "The system understands the intent behind queries and finds the most relevant ADRs"

**What to show:**
- Ask a query like: "What messaging system should I use for a microservices architecture with high throughput?"
- Show the response with references

**Technical highlight:**
- "Here's how it works:
  1. **Intent Extraction**: An LLM analyzes the query to extract technologies, requirements, domain, and compliance needs
  2. **Hybrid Retrieval**: We combine semantic search (vector similarity) with metadata filtering (e.g., 'find ADRs that mention Kafka')
  3. **Context Assembly**: We retrieve the top 5 most relevant document chunks
  4. **Response Generation**: Another LLM generates a comprehensive answer based on the retrieved context
  5. **Reference Formatting**: We provide links to the original ADR documents"

**Key point:**
- "Unlike simple keyword search, our system understands context. If you ask about 'messaging', it knows you might mean Kafka, SQS, or RabbitMQ, and filters accordingly"

---

### 4. **Conversation Management** (2 minutes)
**What to say:**
- "Users can have multiple conversation threads, like a chat interface"
- "Each conversation maintains context, so follow-up questions work naturally"

**What to show:**
- Create a new conversation
- Send multiple messages showing how context is maintained
- Show conversation list with auto-generated titles

**Technical highlight:**
- "Conversations are stored in PostgreSQL with full message history"
- "When you send a message, the system includes the last 10 messages as context for the LLM"
- "This enables natural follow-up questions like 'What about the downsides?' or 'How does that compare to X?'"
- "Conversation titles are auto-generated from the first message"

**Key point:**
- "This makes the system feel like talking to a knowledgeable colleague who remembers your previous questions"

---

### 5. **File Management** (1 minute)
**What to say:**
- "Users can view all uploaded ADRs and delete them if needed"
- "Deletion removes the file from both S3 storage and the vector database"

**What to show:**
- Show the file list
- Demonstrate file deletion

**Technical highlight:**
- "We maintain data consistency - when you delete a file, it's removed from both S3 and ChromaDB"

---

## 🏗️ Architecture Highlights (2 minutes)

**What to say:**
- "Let me quickly explain the technical architecture"

**Key components:**
1. **FastAPI Backend**: Modern async Python framework
2. **PostgreSQL**: Stores conversations and messages
3. **ChromaDB**: Vector database for semantic search
4. **AWS S3**: Document storage (LocalStack for local dev)
5. **OpenAI GPT-4.1-nano**: LLM for intent extraction, metadata extraction, and response generation
6. **LangChain**: Orchestrates the RAG pipeline

**Data flow:**
- "Upload: File → S3 → Text Extraction → Metadata Extraction → Chunking → Embedding → ChromaDB"
- "Query: User Query → Intent Extraction → Hybrid Retrieval → Response Generation → References"

---

## 💡 Key Differentiators (1 minute)

**What makes this special:**
1. **Intelligent Intent Understanding**: Not just keyword matching - understands what you're really asking
2. **Hybrid Retrieval**: Combines semantic search with precise metadata filtering
3. **Conversation Context**: Maintains context across multiple interactions
4. **Production-Ready**: Authentication, error handling, data isolation, scalable architecture
5. **Structured Metadata**: Rich metadata extraction enables precise filtering by technology, domain, compliance needs

---

## 🎯 Use Cases

**What to say:**
- "This system is perfect for:
  - New team members learning from past decisions
  - Architects making similar decisions in new projects
  - Compliance teams ensuring decisions align with regulations
  - Product managers understanding technical trade-offs"

---

## 📊 Demo Flow Summary

1. **Login** → Show Google OAuth
2. **Upload ADR** → Show upload and processing
3. **Query** → Ask a question, show intelligent response with references
4. **Conversation** → Create conversation, show context maintenance
5. **Follow-up** → Ask follow-up question showing context awareness
6. **File Management** → Show file list and deletion

**Total time: ~10-12 minutes**

---

## 🎤 Talking Points

### **Opening:**
"Today I'll show you our ADR AI Assistant - a system that makes your organization's architectural knowledge searchable and accessible through natural language queries."

### **Closing:**
"This system transforms how teams access and learn from past architectural decisions. Instead of searching through documents manually, you can ask questions naturally and get contextual answers with references to the original ADRs. It's like having an expert architect available 24/7 who knows all your past decisions."

---

## ⚠️ Common Questions & Answers

**Q: How accurate are the responses?**
A: "The system uses RAG (Retrieval-Augmented Generation), which means it only answers based on the ADRs in the knowledge base. It doesn't hallucinate - if there's no relevant ADR, it says so."

**Q: What if an ADR is outdated?**
A: "ADRs include status metadata (Accepted, Superseded). The system can filter by status, and you can delete outdated ADRs. We're planning to add versioning support."

**Q: How does it handle multiple conflicting ADRs?**
A: "The system retrieves multiple relevant ADRs and presents them in the response. The LLM synthesizes the information, showing different perspectives and trade-offs."

**Q: Is the data secure?**
A: "Yes. We use Google OAuth with domain restriction, JWT tokens, user-specific data isolation, and secure S3 storage. Each user only sees their own conversations."

**Q: Can it learn from new ADRs automatically?**
A: "Currently, ADRs need to be uploaded manually. We're exploring integrations with ADR authoring tools for automatic ingestion."

---

## 🔧 Technical Deep Dive (If Asked)

### **Intent Extraction:**
- Uses GPT-4.1-nano with structured output parsing
- Extracts: technologies, requirements, domain, compliance needs, use case
- Enables precise metadata filtering

### **Hybrid Retrieval:**
- Vector similarity search finds semantically similar content
- Metadata filters narrow down by technology/domain
- Logical AND combination of filters
- Returns top 5 most relevant chunks

### **Response Generation:**
- Enhanced prompt includes: context, conversation history, intent info
- LLM generates HTML-formatted responses
- Includes references with links to original documents
- Temperature 0.1 for consistent responses

### **Metadata Extraction:**
- One-hot encoding for technologies (tech_kafka: true)
- Extracts: ADR number, title, status, date, author, decision makers, context, options, decision, rationale, technologies
- Enables powerful filtering capabilities

---

## 📝 Notes for Presenter

- **Practice the flow** before the demo
- **Have sample ADRs ready** to upload
- **Prepare example queries** that showcase different features
- **Be ready to explain** the technical architecture if asked
- **Emphasize the business value**: Time savings, knowledge preservation, better decisions
- **Mention scalability**: System can handle thousands of ADRs and concurrent users

