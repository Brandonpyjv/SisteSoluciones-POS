from fastapi import APIRouter
from fastapi.responses import JSONResponse
from services.ubicacion_service import get_all_departamentos, get_municipios_by_departamento

router = APIRouter(prefix="/api/ubicacion")


@router.get("/departamentos", name="api_departamentos")
def api_departamentos():
    return JSONResponse(content=get_all_departamentos())


@router.get("/municipios/{cod_departamento}", name="api_municipios")
def api_municipios(cod_departamento: str):
    return JSONResponse(content=get_municipios_by_departamento(cod_departamento))
