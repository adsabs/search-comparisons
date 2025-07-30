"""
Quepid API routes for the search-comparisons application.
"""
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from ...services.quepid_service import QuepidService

router = APIRouter()
quepid_service = QuepidService()
limiter = Limiter(key_func=get_remote_address)

@router.get("/judgments/{case_id}")
@limiter.limit("20/minute")
async def get_judgments(
    request: Request,
    case_id: int,
    query: str = Query(..., description="The search query to get judgments for")
) -> List[Dict[str, Any]]:
    """
    Get judged documents for a specific Quepid case and query.
    
    Args:
        case_id: The Quepid case ID
        query: The search query to get judgments for
        
    Returns:
        List[Dict[str, Any]]: List of judged documents with their metadata and scores
    """
    try:
        judgments = await quepid_service.get_judged_documents_by_text(case_id, query)
        return judgments
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting Quepid judgments: {str(e)}"
        ) 