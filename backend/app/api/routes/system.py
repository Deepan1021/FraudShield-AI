from fastapi import APIRouter, Depends

from app.api.dependencies import get_container, ok
from app.schemas.api import ApiResponse
from app.services.container import Container

router = APIRouter(tags=["System"])


@router.get("/health", response_model=ApiResponse, summary="Live system status")
def health(c: Container = Depends(get_container)):
    return ok(c.system.health())


@router.get("/system/info", response_model=ApiResponse, summary="Versions, configuration and thresholds (read-only)")
def info(c: Container = Depends(get_container)):
    return ok(c.system.info())


@router.get("/system/startup-report", response_model=ApiResponse, summary="Results of the startup validation checks")
def startup_report(c: Container = Depends(get_container)):
    return ok(c.startup_report)


@router.post("/system/backup", response_model=ApiResponse, status_code=201, summary="Write a database snapshot (never overwrites)")
def backup(c: Container = Depends(get_container)):
    return ok(c.system.backup())


@router.post("/system/seed-demo", response_model=ApiResponse, status_code=201,
             summary="Seed synthetic demonstration data (idempotent)")
def seed_demo(c: Container = Depends(get_container)):
    return ok(c.system.seed_demo(actor="analyst"))
