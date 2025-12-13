"""File upload routes."""
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from app.api.dependencies import get_current_user
from app.services.adr.adr_service import ADRService

router = APIRouter(prefix="/api/upload", tags=["upload"])

adr_service = ADRService()


@router.post("")
async def upload(file: UploadFile, current_user: dict = Depends(get_current_user)):
    """Upload and process ADR document"""
    try:
        doc_ids, file_info = await adr_service.process_adr(file)
        # Return file information in the format expected by the frontend
        return file_info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

