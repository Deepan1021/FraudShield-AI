from typing import Optional

from fastapi import APIRouter, Depends, Path, Query

from app.api.dependencies import get_container, ok
from app.core.errors import TransactionValidationError
from app.domain.enums import RecommendationAction, RiskLevel
from app.schemas.api import ApiResponse, TransactionIn
from app.services.container import Container

router = APIRouter(prefix="/transactions", tags=["Transactions"])
TID = Path(..., pattern=r"^[A-Za-z0-9_-]{3,40}$", description="Transaction ID")
DATE = r"^\d{4}-\d{2}-\d{2}$"


@router.post("/analyze", response_model=ApiResponse, status_code=201, summary="Run the full expert-system pipeline on a transaction")
def analyze(payload: TransactionIn, c: Container = Depends(get_container)):
    return ok(c.analysis.analyze(payload.model_dump(exclude_none=True), actor="analyst"))


@router.get("", response_model=ApiResponse, summary="Search and filter analysed transactions")
def list_transactions(
    q: Optional[str] = Query(None, max_length=60, description="Transaction or user ID contains"),
    risk: Optional[str] = Query(None, max_length=60, description="Comma separated: LOW,MEDIUM,HIGH,CRITICAL"),
    recommendation: Optional[str] = Query(None, max_length=40),
    location: Optional[str] = Query(None, max_length=60),
    device_trust: Optional[str] = Query(None, max_length=20),
    rule: Optional[str] = Query(None, max_length=10, pattern=r"^R\d{2,3}$"),
    status: Optional[str] = Query(None, max_length=30),
    user_id: Optional[str] = Query(None, max_length=40),
    date_from: Optional[str] = Query(None, pattern=DATE),
    date_to: Optional[str] = Query(None, pattern=DATE),
    sort: str = Query("submitted_at", pattern=r"^(submitted_at|amount|transaction_id|user_id|risk_rank|severity_index)$"),
    order: str = Query("desc", pattern=r"^(asc|desc)$"),
    page: int = Query(1, ge=1, le=100000),
    page_size: int = Query(20, ge=1, le=100),
    c: Container = Depends(get_container),
):
    levels = None
    if risk:
        levels = [r.strip().upper() for r in risk.split(",") if r.strip()]
        valid = {r.value for r in RiskLevel}
        bad = [r for r in levels if r not in valid]
        if bad:
            raise TransactionValidationError(f"Unknown risk level(s): {', '.join(bad)}", field="risk")
    if recommendation and recommendation.upper() not in {a.value for a in RecommendationAction}:
        raise TransactionValidationError("Unknown recommendation action.", field="recommendation")
    return ok(c.transactions.list(
        q=q, risk=levels, recommendation=recommendation.upper() if recommendation else None, location=location,
        device_trust=device_trust.upper() if device_trust else None, rule=rule, status=status, user_id=user_id.upper() if user_id else None,
        date_from=date_from, date_to=date_to, sort=sort, order=order, page=page, page_size=page_size))


@router.get("/{transaction_id}", response_model=ApiResponse, summary="Full forensic detail for one transaction")
def detail(transaction_id: str = TID, c: Container = Depends(get_container)):
    return ok(c.transactions.detail(transaction_id))


@router.get("/{transaction_id}/facts", response_model=ApiResponse, summary="Generated and derived facts")
def facts(transaction_id: str = TID, c: Container = Depends(get_container)):
    return ok(c.transactions.facts(transaction_id))


@router.get("/{transaction_id}/rules", response_model=ApiResponse, summary="Rules evaluated and triggered")
def rules(transaction_id: str = TID, c: Container = Depends(get_container)):
    return ok(c.transactions.rules(transaction_id))


@router.get("/{transaction_id}/trace", response_model=ApiResponse, summary="Forward-chaining trace and reasoning graph")
def trace(transaction_id: str = TID, c: Container = Depends(get_container)):
    return ok(c.transactions.trace(transaction_id))


@router.get("/{transaction_id}/explanation", response_model=ApiResponse, summary="Explainable-AI explanation")
def explanation(transaction_id: str = TID, c: Container = Depends(get_container)):
    return ok(c.transactions.explanation(transaction_id))


@router.get("/{transaction_id}/report", response_model=ApiResponse, summary="Report document (viewable, not exported)")
def report(transaction_id: str = TID, c: Container = Depends(get_container)):
    return ok(c.reports.view(transaction_id))
