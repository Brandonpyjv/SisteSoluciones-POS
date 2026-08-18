from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from services.invoice_payments_service import (get_all_invoice_payments, get_invoice_payment_by_id,
                                                create_invoice_payment, update_invoice_payment,
                                                delete_invoice_payment, validar_estado_pago)
from routes.formularios import formulario_invalido
from templates_config import templates

router = APIRouter(prefix="/invoice_payments")

PLANTILLA = "invoice_payments/form.html"


@router.get("", name="invoice_payments")
def invoice_payments(request: Request):
    data = get_all_invoice_payments()
    return templates.TemplateResponse(request, "invoice_payments/index.html", {"all_invoices": data})


@router.get("/new", name="invoice_payments_new")
def new_invoice_payment(request: Request):
    return templates.TemplateResponse(request, "invoice_payments/form.html", {"payment": None})


@router.post("/new", name="create_invoice_payment")
def create_invoice_payment_post(request: Request, status: str = Form(...)):
    v = validar_estado_pago({"status": status})
    if not v.valido:
        return formulario_invalido(request, PLANTILLA, v, {"payment": None},
                                   {"status": status})

    create_invoice_payment(v.datos["status"])
    return RedirectResponse(url="/invoice_payments", status_code=303)


@router.get("/edit/{payment_id}", name="edit_invoice_payment")
def edit_invoice_payment(request: Request, payment_id: int):
    payment = get_invoice_payment_by_id(payment_id)
    if not payment:
        return RedirectResponse(url="/invoice_payments", status_code=302)
    return templates.TemplateResponse(request, "invoice_payments/form.html", {"payment": payment})


@router.post("/edit/{payment_id}", name="update_invoice_payment")
def update_invoice_payment_post(request: Request, payment_id: int, status: str = Form(...)):
    v = validar_estado_pago({"status": status}, payment_id=payment_id)
    if not v.valido:
        return formulario_invalido(request, PLANTILLA, v,
                                   {"payment": get_invoice_payment_by_id(payment_id)},
                                   {"status": status})

    update_invoice_payment(payment_id, v.datos["status"])
    return RedirectResponse(url="/invoice_payments", status_code=303)


@router.get("/delete/{payment_id}", name="delete_invoice_payment")
def delete_invoice_payment_get(payment_id: int):
    delete_invoice_payment(payment_id)
    return RedirectResponse(url="/invoice_payments", status_code=302)
