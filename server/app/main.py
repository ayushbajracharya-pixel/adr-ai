from fastapi import FastAPI, UploadFile, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from contextlib import asynccontextmanager
import os
from app.services.adr_service import ADRService
from app.services.uploader_service import UploaderService
from app.models.schemas import QueryRequest
from app.routers import auth, conversations
from app.routers.auth import get_current_user
from app.config.settings import settings
from app.config.database import init_db

# Configure LangSmith if API key is provided
if settings.LANGCHAIN_API_KEY:
    os.environ["LANGCHAIN_TRACING_V2"] = settings.LANGCHAIN_TRACING_V2 or "true"
    os.environ["LANGCHAIN_ENDPOINT"] = settings.LANGCHAIN_ENDPOINT or "https://api.smith.langchain.com"
    os.environ["LANGCHAIN_API_KEY"] = settings.LANGCHAIN_API_KEY
    if settings.LANGCHAIN_PROJECT:
        os.environ["LANGCHAIN_PROJECT"] = settings.LANGCHAIN_PROJECT


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize database
    await init_db()
    yield
    # Shutdown: Cleanup if needed
    pass


app = FastAPI(title="ADR AI Assistant", lifespan=lifespan)

# Add session middleware (required for OAuth)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    max_age=3600,  # Session expires after 1 hour
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(conversations.router)

adr_service = ADRService()
uploader = UploaderService()


@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}


@app.post("/api/upload")
async def upload(file: UploadFile, current_user: dict = Depends(get_current_user)):
    """Upload and process ADR document"""
    try:
        doc_ids, file_info = await adr_service.process_adr(file)
        # Return file information in the format expected by the frontend
        return file_info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/query")
async def query_adrs(request: QueryRequest, current_user: dict = Depends(get_current_user)):
    """Query ADRs for GenAI implementations"""
    try:
        response = await adr_service.query_adr(request.query)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/files")
def list_uploaded_files(current_user: dict = Depends(get_current_user)):
    """
    Endpoint to list all files uploaded to the S3 bucket.
    """
    file_list = uploader.list_files()
    if file_list is None:
        raise HTTPException(status_code=500, detail="Could not retrieve file list")
    return file_list


@app.delete("/api/files/{object_key:path}")
async def delete_file(object_key: str, current_user: dict = Depends(get_current_user)):
    """
    Endpoint to delete a file from both S3 and the ChromaDB knowledge base.
    """
    try:
        return await adr_service.delete_file(object_key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
