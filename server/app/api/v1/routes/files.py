"""File management routes."""
from fastapi import APIRouter, Depends, HTTPException
from app.api.dependencies import get_current_user
from app.services.storage.s3_service import S3Service
from app.services.adr.adr_service import ADRService

router = APIRouter(prefix="/api/files", tags=["files"])

s3_service = S3Service()
adr_service = ADRService()


@router.get("")
def list_uploaded_files(current_user: dict = Depends(get_current_user)):
    """
    Endpoint to list all files uploaded to the S3 bucket.
    """
    file_list = s3_service.list_files()
    if file_list is None:
        raise HTTPException(status_code=500, detail="Could not retrieve file list")
    return file_list


@router.delete("/{object_key:path}")
async def delete_file(object_key: str, current_user: dict = Depends(get_current_user)):
    """
    Endpoint to delete a file from both S3 and the ChromaDB knowledge base.
    """
    try:
        return await adr_service.delete_file(object_key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

