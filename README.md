# ADR AI Assistant

An intelligent RAG (Retrieval-Augmented Generation) system that helps teams make technology decisions by querying past Architecture Decision Records (ADRs) using natural language.

## What It Does

- **Ingests ADR Documents**: Upload and process ADR documents (PDF, DOCX, TXT, MD) with automatic metadata extraction
- **Intelligent Search**: Query ADRs using natural language with hybrid retrieval (semantic + keyword + metadata filtering)
- **Conversation Management**: Multi-threaded conversations with context-aware responses
- **Smart Retrieval**: Combines vector similarity search, BM25 keyword search, and metadata filtering for accurate results

## Tech Stack

- **Frontend**: React + TypeScript + Vite
- **Backend**: FastAPI (Python) with async operations
- **Vector Database**: ChromaDB for semantic search
- **Database**: PostgreSQL for conversations and messages
- **Storage**: AWS S3 (LocalStack for local development)
- **LLM**: OpenAI GPT-4.1-nano for query processing and response generation
- **Authentication**: Google OAuth 2.0 with JWT tokens

## Project Structure

```
adr-ai/
├── client/     # React frontend application
└── server/     # FastAPI backend application
```

## Getting Started

This is a monorepo with separate frontend and backend applications. Each has its own setup instructions:

- **[Client README](./client/README.md)** - Frontend setup and development guide
- **[Server README](./server/README.md)** - Backend setup, API documentation, and RAG pipeline architecture

For detailed installation, configuration, and running instructions, please refer to the respective README files above.

## Quick Overview

1. **Backend** (`server/`): FastAPI server that handles document processing, vector storage, query processing, and conversation management
2. **Frontend** (`client/`): React application providing the user interface for uploading ADRs, querying the knowledge base, and managing conversations

Both applications need to be running for the full system to work. See the individual READMEs for setup details.

