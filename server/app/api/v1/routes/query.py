"""Query routes."""
from fastapi import APIRouter, Depends, HTTPException
from app.api.dependencies import get_current_user
from app.domain.schemas.query import QueryRequest, QueryResponse
from app.services.adr.adr_service import ADRService

router = APIRouter(prefix="/api/query", tags=["query"])

adr_service = ADRService()


@router.post("", response_model=QueryResponse)
async def query_adrs(request: QueryRequest, current_user: dict = Depends(get_current_user)):
    """Query ADRs for GenAI implementations"""
    try:
        response = await adr_service.query_adr(request.query)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

