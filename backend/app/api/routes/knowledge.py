from fastapi import APIRouter, Depends

from app.api.dependencies import get_container, ok
from app.schemas.api import ApiResponse
from app.services.container import Container

router = APIRouter(tags=["Knowledge Base"])


@router.get("/rules", response_model=ApiResponse, summary="Rule base (read-only)")
def rules(c: Container = Depends(get_container)):
    rb = c.pipeline.rulebase
    return ok({"name": rb.name, "version": rb.version, "rules": [r.to_dict() for r in rb.rules],
               "dependencies": rb.dependencies(),
               "conflict_resolution": [
                   "1. Highest rule priority fires first.", "2. Ties: more specific rule (more matched conditions).",
                   "3. Ties: higher rule severity.", "4. Ties: lower rule id."]})


@router.get("/knowledge-base", response_model=ApiResponse, summary="Predicates, rule dependencies and status")
def knowledge_base(c: Container = Depends(get_container)):
    return ok(c.pipeline.kb.describe())
