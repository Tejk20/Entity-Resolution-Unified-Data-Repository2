from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import MasterEntity
from app.schemas import SearchRequest, SearchResult
from app.services.matching import build_entity_card, progressive_search

router = APIRouter(prefix="/api", tags=["search"])


@router.post("/search", response_model=SearchResult)
def search(payload: SearchRequest, db: Session = Depends(get_db)):
    result = progressive_search(db, payload.query, payload.identifier_type)
    return result


@router.get("/search")
def search_get(
    q: str = Query(..., min_length=1),
    identifier_type: str | None = None,
    db: Session = Depends(get_db),
):
    return progressive_search(db, q, identifier_type)


@router.get("/entities")
def list_entities(
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    q = db.query(MasterEntity).order_by(MasterEntity.updated_at.desc())
    if status:
        q = q.filter(MasterEntity.status == status)
    total = q.count()
    rows = q.offset(offset).limit(limit).all()
    return {
        "total": total,
        "items": [
            {
                "id": e.id,
                "status": e.status,
                "display_name": e.display_name,
                "match_count": e.match_count,
                "source_count": e.source_count,
                "updated_at": e.updated_at,
            }
            for e in rows
        ],
    }


@router.get("/entities/{entity_id}")
def get_entity(entity_id: int, db: Session = Depends(get_db)):
    card = build_entity_card(db, entity_id)
    if not card:
        raise HTTPException(404, "Entity not found")
    return card
