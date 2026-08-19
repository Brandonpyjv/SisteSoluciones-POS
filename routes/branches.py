from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from typing import Optional
from services.branches import (get_all_branches, get_branch_by_id,
                                create_branch, update_branch, delete_branch,
                                validar_empresa)
from services.ubicacion_service import (get_all_departamentos, get_municipio_by_id,
                                        get_municipios_by_departamento)
from routes.formularios import formulario_invalido
from templates_config import templates

router = APIRouter(prefix="/branches")

PLANTILLA = "branches/form.html"

CAMPOS = ("nombre", "nit", "dv", "direccion", "cod_municipio", "telefono", "correo",
          "regimen_tributario", "actividad_economica", "tipo_documento", "website",
          "tarifa_ica", "autoretenedor", "gran_contribuyente", "prefijo_factura",
          "consecutivo_actual")


def _enviado(**valores):
    return {campo: valores.get(campo) for campo in CAMPOS}


def _contexto(datos, branch=None):
    """El formulario solo envía el municipio; el departamento se deduce de él para
    no perder el select al volver con errores."""
    cod_municipio = (datos.get("cod_municipio") or "").strip() or None
    municipio = get_municipio_by_id(cod_municipio) if cod_municipio else None
    cod_dpto = municipio["cod_departamento"] if municipio else None
    return {
        "branch": branch,
        "departamentos": get_all_departamentos(),
        "municipios": get_municipios_by_departamento(cod_dpto) if cod_dpto else [],
    }


def _guardar(v):
    """Argumentos de create_branch / update_branch a partir de lo validado."""
    d = v.datos
    return (d["nombre"], d["nit"], d["dv"], d["direccion"], d["cod_municipio"],
            d["telefono"], d["correo"], d["regimen_tributario"],
            d["actividad_economica"], d["tipo_documento"], d["website"],
            d["tarifa_ica"], d["autoretenedor"], d["gran_contribuyente"],
            d["prefijo_factura"],
            # La resolución DIAN la administra FactuGest; aquí van siempre vacías.
            None, None, None, None, None, d["consecutivo_actual"])


@router.get("", name="branches")
def branches(request: Request):
    data = get_all_branches()
    return templates.TemplateResponse(request, "branches/index.html", {"branches": data})


@router.get("/new", name="new_branch")
def new_branch(request: Request):
    return templates.TemplateResponse(request, "branches/form.html", {
        "branch": None,
        "departamentos": get_all_departamentos(),
        "municipios": [],
    })


@router.post("/new", name="create_branch")
def create_branch_post(
    request: Request,
    nombre: str = Form(...),
    nit: str = Form(...),
    dv: str = Form(""),
    direccion: str = Form(""),
    cod_municipio: str = Form(""),
    telefono: str = Form(""),
    correo: str = Form(""),
    regimen_tributario: str = Form("RESPONSABLE_IVA"),
    actividad_economica: str = Form(""),
    tipo_documento: str = Form("NIT"),
    website: str = Form(""),
    tarifa_ica: str = Form(""),
    autoretenedor: str = Form("0"),
    gran_contribuyente: str = Form("0"),
    prefijo_factura: str = Form("FV"),
    consecutivo_actual: Optional[str] = Form("1"),
):
    enviado = _enviado(**locals())
    v = validar_empresa(enviado)
    if not v.valido:
        return formulario_invalido(request, PLANTILLA, v, _contexto(enviado), enviado)

    create_branch(*_guardar(v))
    return RedirectResponse(url="/branches", status_code=303)


@router.get("/edit/{branch_id}", name="edit_branch")
def edit_branch(request: Request, branch_id: int):
    branch = get_branch_by_id(branch_id)
    if not branch:
        return RedirectResponse(url="/branches", status_code=302)
    municipios = []
    if branch.get("cod_departamento"):
        municipios = get_municipios_by_departamento(branch["cod_departamento"])
    return templates.TemplateResponse(request, "branches/form.html", {
        "branch": branch,
        "departamentos": get_all_departamentos(),
        "municipios": municipios,
    })


@router.post("/edit/{branch_id}", name="update_branch")
def update_branch_post(
    request: Request,
    branch_id: int,
    nombre: str = Form(...),
    nit: str = Form(...),
    dv: str = Form(""),
    direccion: str = Form(""),
    cod_municipio: str = Form(""),
    telefono: str = Form(""),
    correo: str = Form(""),
    regimen_tributario: str = Form("RESPONSABLE_IVA"),
    actividad_economica: str = Form(""),
    tipo_documento: str = Form("NIT"),
    website: str = Form(""),
    tarifa_ica: str = Form(""),
    autoretenedor: str = Form("0"),
    gran_contribuyente: str = Form("0"),
    prefijo_factura: str = Form("FV"),
    consecutivo_actual: Optional[str] = Form("1"),
):
    enviado = _enviado(**locals())
    v = validar_empresa(enviado, branch_id=branch_id)
    if not v.valido:
        return formulario_invalido(request, PLANTILLA, v,
                                   _contexto(enviado, branch=get_branch_by_id(branch_id)),
                                   enviado)

    update_branch(branch_id, *_guardar(v))
    return RedirectResponse(url="/branches", status_code=303)


@router.get("/delete/{branch_id}", name="delete_branch")
def delete_branch_get(branch_id: int):
    delete_branch(branch_id)
    return RedirectResponse(url="/branches", status_code=302)
