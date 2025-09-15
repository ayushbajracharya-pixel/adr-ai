from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.services.adr_service import ADRService
from app.models.schemas import QueryRequest

from app.services.uploader_service import UploaderService

app = FastAPI(title="ADR AI Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

adr_service = ADRService()
uploader = UploaderService()


@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}


@app.post("/api/upload")
async def upload(file: UploadFile):
    """Upload and process ADR document"""
    try:
        result = await adr_service.process_adr(file)
        return {"message": "ADR processed successfully", "doc_id": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/query")
async def query_adrs(request: QueryRequest):
    """Query ADRs for GenAI implementations"""
    try:
        response = await adr_service.query_adr(request.query)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
