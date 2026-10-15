from fastapi import APIRouter, Depends, Path
from fastapi.responses import FileResponse

from app.api.dependencies import get_container, ok
from app.schemas.api import ApiResponse, ReportRequest
from app.services.container import Container

router = APIRouter(prefix="/reports", tags=["Reports"])
RID = Path(..., pattern=r"^RPT-[A-Z0-9]{6,16}$")


@router.post("", response_model=ApiResponse, status_code=201, summary="Generate and export a report (json, csv or pdf)")
def create_report(body: ReportRequest, c: Container = Depends(get_container)):
    return ok(c.reports.generate(body.transaction_id, body.format, actor="analyst"))


@router.get("", response_model=ApiResponse, summary="List generated reports")
def list_reports(c: Container = Depends(get_container)):
    return ok(c.reports.list())


@router.get("/{report_id}", response_model=ApiResponse, summary="Report document for the in-app viewer")
def get_report(report_id: str = RID, c: Container = Depends(get_container)):
    return ok(c.reports.get_document(report_id))


@router.get("/{report_id}/download", summary="Download the exported report file")
def download(report_id: str = RID, c: Container = Depends(get_container)):
    path, media_type, filename = c.reports.file_for(report_id)
    return FileResponse(path, media_type=media_type, filename=filename)
