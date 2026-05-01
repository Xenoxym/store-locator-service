from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.store import StoreSearchRequest, StoreSearchResponse
from app.services.store_search import search_stores
from app.core.rate_limit import rate_limit_public_search


router = APIRouter(
    prefix="/api/stores",
    tags=["Public Store Search"],
)


@router.post("/search", response_model=StoreSearchResponse)
def search_public_stores(
    request_body: StoreSearchRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    rate_limit_public_search(request)

    try:
        return search_stores(db, request_body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))