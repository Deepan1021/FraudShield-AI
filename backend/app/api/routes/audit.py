from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_container, ok
from app.schemas.api import ApiResponse
from app.services.container import Container

router = APIRouter(tags=["Audit"])
DATE = r"^\d{4}-\d{2}-\d{2}$"


@router.get("/audit-logs", response_model=ApiResponse, summary="Searchable audit trail")
def audit_logs(q: Optional[str] = Query(None, max_length=60), event_type: Optional[str] = Query(None, max_length=40),
               risk: Optional[str] = Query(None, pattern=r"^(LOW|MEDIUM|HIGH|CRITICAL)$"),
               transaction_id: Optional[str] = Query(None, max_length=40),
               date_from: Optional[str] = Query(None, pattern=DATE), date_to: Optional[str] = Query(None, pattern=DATE),
               page: int = Query(1, ge=1, le=100000), page_size: int = Query(50, ge=1, le=200),
               c: Container = Depends(get_container)):
    uow = c.db.read()
    items, total = uow.audit.search(q, event_type, risk, transaction_id.upper() if transaction_id else None, date_from, date_to, page, page_size)
    return ok({"items": items, "total": total, "page": page, "page_size": page_size, "pages": max(1, -(-total // page_size)),
               "event_types": uow.audit.event_types()})
