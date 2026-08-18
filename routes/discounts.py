from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from services.discounts import (get_all_discount, get_discount_by_id,
                                 create_discount, update_discount, delete_discount,
                                 validar_descuento)
from routes.formularios import formulario_invalido
from templates_config import templates

router = APIRouter(prefix="/discount")

PLANTILLA = "discount/form.html"


@router.get("", name="discount")
def discount(request: Request):
    data = get_all_discount()
    return templates.TemplateResponse(request, "discount/index.html", {"all_discount": data})


@router.get("/new", name="new_discount")
def new_discount(request: Request):
    return templates.TemplateResponse(request, "discount/form.html", {"discount": None})


@router.post("/new", name="create_discount")
def create_discount_post(
    request: Request,
    descripcion: str = Form(...),
    porcentaje: str = Form(...),
    aplica_a_producto: str = Form("0"),
    aplica_a_factura: str = Form("0"),
):
    enviado = {"descripcion": descripcion, "porcentaje": porcentaje,
               "aplica_a_producto": aplica_a_producto, "aplica_a_factura": aplica_a_factura}
    v = validar_descuento(enviado)
    if not v.valido:
        return formulario_invalido(request, PLANTILLA, v, {"discount": None}, enviado)

    d = v.datos
    create_discount(d["descripcion"], d["porcentaje"], d["aplica_a_producto"],
                    d["aplica_a_factura"])
    return RedirectResponse(url="/discount", status_code=303)


@router.get("/edit/{discount_id}", name="edit_discount")
def edit_discount(request: Request, discount_id: int):
    d = get_discount_by_id(discount_id)
    if not d:
        return RedirectResponse(url="/discount", status_code=302)
    return templates.TemplateResponse(request, "discount/form.html", {"discount": d})


@router.post("/edit/{discount_id}", name="update_discount")
def update_discount_post(
    request: Request,
    discount_id: int,
    descripcion: str = Form(...),
    porcentaje: str = Form(...),
    aplica_a_producto: str = Form("0"),
    aplica_a_factura: str = Form("0"),
):
    enviado = {"descripcion": descripcion, "porcentaje": porcentaje,
               "aplica_a_producto": aplica_a_producto, "aplica_a_factura": aplica_a_factura}
    v = validar_descuento(enviado, discount_id=discount_id)
    if not v.valido:
        return formulario_invalido(request, PLANTILLA, v,
                                   {"discount": get_discount_by_id(discount_id)}, enviado)

    d = v.datos
    update_discount(discount_id, d["descripcion"], d["porcentaje"],
                    d["aplica_a_producto"], d["aplica_a_factura"])
    return RedirectResponse(url="/discount", status_code=303)


@router.get("/delete/{discount_id}", name="delete_discount")
def delete_discount_get(discount_id: int):
    delete_discount(discount_id)
    return RedirectResponse(url="/discount", status_code=302)
