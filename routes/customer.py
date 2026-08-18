from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from services.customer_service import (get_all_customers, get_customer_by_id,
                                        create_customer, update_customer, delete_customer,
                                        validar_cliente)
from services.branches import get_branch_by_id
from services.ubicacion_service import (get_all_departamentos, get_municipio_by_id,
                                        get_municipios_by_departamento)
from routes.formularios import formulario_invalido
from templates_config import templates

router = APIRouter(prefix="/customer")

PLANTILLA = "customer/form.html"


def _contexto(customer=None, cod_departamento=None, cod_municipio=None):
    """Datos que necesita el formulario, ya venga vacío, en edición o con errores."""
    return {
        "customer": customer,
        "departamentos": get_all_departamentos(),
        "municipios": get_municipios_by_departamento(cod_departamento) if cod_departamento else [],
        "default_cod_dpto": cod_departamento,
        "default_municipio": cod_municipio,
    }


def _contexto_de_lo_enviado(datos, customer=None):
    """Reconstruye el contexto a partir de lo que la persona alcanzó a llenar.

    El formulario solo envía el municipio, así que el departamento se deduce de
    él; si no, al volver con errores se perdería la ubicación ya seleccionada.
    """
    cod_municipio = (datos.get("cod_municipio") or "").strip() or None
    municipio = get_municipio_by_id(cod_municipio) if cod_municipio else None
    return _contexto(
        customer=customer,
        cod_departamento=municipio["cod_departamento"] if municipio else None,
        cod_municipio=cod_municipio,
    )


@router.get("", name="customer")
def customer(request: Request):
    data = get_all_customers()
    return templates.TemplateResponse(request, "customer/index.html", {"all_customers": data})


@router.get("/new", name="new_customer")
def new_customer(request: Request):
    # Ciudad por defecto = municipio de la sucursal del usuario en sesión
    session_user = request.session.get("user", {})
    cod_empresa = session_user.get("cod_empresa")
    branch = get_branch_by_id(cod_empresa) if cod_empresa else None
    return templates.TemplateResponse(request, PLANTILLA, _contexto(
        cod_departamento=branch.get("cod_departamento") if branch else None,
        cod_municipio=branch.get("cod_municipio") if branch else None,
    ))


@router.post("/new", name="create_customer")
def create_customer_post(
    request: Request,
    full_name: str = Form(...),
    document_type: str = Form(...),
    document_number: str = Form(...),
    phone: str = Form(""),
    email: str = Form(""),
    address: str = Form(""),
    cod_municipio: str = Form(""),
    pais: str = Form("Colombia"),
    tipo_persona: str = Form("NATURAL"),
    regimen_tributario: str = Form("NO_RESPONSABLE_IVA"),
):
    enviado = {
        "full_name": full_name, "document_type": document_type,
        "document_number": document_number, "phone": phone, "email": email,
        "address": address, "cod_municipio": cod_municipio, "pais": pais,
        "tipo_persona": tipo_persona, "regimen_tributario": regimen_tributario,
    }
    v = validar_cliente(enviado)
    if not v.valido:
        return formulario_invalido(request, PLANTILLA, v,
                                   _contexto_de_lo_enviado(enviado), enviado)

    d = v.datos
    create_customer(d["full_name"], d["document_type"], d["document_number"],
                    d["phone"], d["email"], d["address"], d["cod_municipio"],
                    d["pais"], d["tipo_persona"], d["regimen_tributario"])
    return RedirectResponse(url="/customer", status_code=303)


@router.get("/edit/{customer_id}", name="edit_customer")
def edit_customer(request: Request, customer_id: int):
    c = get_customer_by_id(customer_id)
    if not c:
        return RedirectResponse(url="/customer", status_code=302)
    return templates.TemplateResponse(request, PLANTILLA, _contexto(
        customer=c,
        cod_departamento=c.get("cod_departamento"),
        cod_municipio=c.get("cod_municipio"),
    ))


@router.post("/edit/{customer_id}", name="update_customer")
def update_customer_post(
    request: Request,
    customer_id: int,
    full_name: str = Form(...),
    document_type: str = Form(...),
    document_number: str = Form(...),
    phone: str = Form(""),
    email: str = Form(""),
    address: str = Form(""),
    cod_municipio: str = Form(""),
    pais: str = Form("Colombia"),
    tipo_persona: str = Form("NATURAL"),
    regimen_tributario: str = Form("NO_RESPONSABLE_IVA"),
):
    enviado = {
        "full_name": full_name, "document_type": document_type,
        "document_number": document_number, "phone": phone, "email": email,
        "address": address, "cod_municipio": cod_municipio, "pais": pais,
        "tipo_persona": tipo_persona, "regimen_tributario": regimen_tributario,
    }
    v = validar_cliente(enviado, customer_id=customer_id)
    if not v.valido:
        actual = get_customer_by_id(customer_id)
        return formulario_invalido(request, PLANTILLA, v,
                                   _contexto_de_lo_enviado(enviado, customer=actual),
                                   enviado)

    d = v.datos
    update_customer(customer_id, d["full_name"], d["document_type"], d["document_number"],
                    d["phone"], d["email"], d["address"], d["cod_municipio"],
                    d["pais"], d["tipo_persona"], d["regimen_tributario"])
    return RedirectResponse(url="/customer", status_code=303)


@router.get("/delete/{customer_id}", name="delete_customer")
def delete_customer_get(customer_id: int):
    delete_customer(customer_id)
    return RedirectResponse(url="/customer", status_code=302)
