from fastapi import APIRouter, Depends

from app.api.dependencies import get_container, ok
from app.schemas.api import ApiResponse
from app.services.container import Container

router = APIRouter(tags=["Analytics"])


@router.get("/dashboard/summary", response_model=ApiResponse, summary="Dashboard metrics")
def dashboard(c: Container = Depends(get_container)):
    return ok(c.analytics.dashboard())


@router.get("/analytics", response_model=ApiResponse, summary="Full analytics")
@router.get("/analytics/summary", response_model=ApiResponse, include_in_schema=False)
def analytics(c: Container = Depends(get_container)):
    return ok(c.analytics.analytics())


@router.get("/analytics/risk-distribution", response_model=ApiResponse, summary="Risk distribution")
def risk_distribution(c: Container = Depends(get_container)):
    return ok(c.db.read().analytics.risk_distribution())
