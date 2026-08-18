from fastapi import APIRouter, Request
from services.logs_service import get_all_logs
from templates_config import templates

router = APIRouter()


@router.get("/logs", name="logs")
def logs(request: Request):
    data = get_all_logs()
    return templates.TemplateResponse(request, "logs/index.html", {"logs": data})
