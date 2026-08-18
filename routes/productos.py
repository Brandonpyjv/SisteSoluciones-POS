from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from services.products_service import (get_all_products_detailed, get_product_by_id,
                                        create_product, update_product, delete_product,
                                        validar_producto)
from services.inventory_service import ajustar_stock, registrar_saldo_inicial
from services.taxes import get_all_invoice_taxes
from routes.formularios import formulario_invalido
from templates_config import templates

router = APIRouter(prefix="/products")

PLANTILLA = "product/form.html"

# Los campos numéricos se reciben como texto y se convierten al validar. Si se
# declararan como int o float, un valor forjado que no sea número lo rechazaría
# FastAPI con su propia página JSON en lugar del formulario con el mensaje.
CAMPOS = ("sku", "nombre", "descripcion", "precio_unitario", "stock", "stock_minimo",
          "cod_impuesto", "unidad_medida", "codigo_barras", "activo", "controla_stock")


def _enviado(**valores):
    return {campo: valores.get(campo) for campo in CAMPOS}


@router.get("/product", name="product")
def products(request: Request):
    data = get_all_products_detailed()
    return templates.TemplateResponse(request, "product/index.html", {"products": data})


@router.get("/product/new", name="product_new")
def product_new(request: Request):
    taxes = get_all_invoice_taxes()
    return templates.TemplateResponse(request, "product/form.html", {"product": None, "taxes": taxes})


@router.post("/product/new", name="create_product")
def create_product_post(
    request: Request,
    sku: str = Form(...),
    nombre: str = Form(...),
    descripcion: str = Form(""),
    precio_unitario: str = Form(...),
    stock: str = Form("0"),
    stock_minimo: str = Form("5"),
    cod_impuesto: str = Form("1"),
    unidad_medida: str = Form("C62"),
    codigo_barras: str = Form(""),
    activo: str = Form("1"),
    controla_stock: str = Form("1"),
):
    enviado = _enviado(**locals())
    v = validar_producto(enviado)
    if not v.valido:
        return formulario_invalido(request, PLANTILLA, v,
                                   {"product": None, "taxes": get_all_invoice_taxes()},
                                   enviado)

    d = v.datos
    product_id = create_product(d["sku"], d["nombre"], d["descripcion"],
                                d["precio_unitario"], d["stock"], d["stock_minimo"],
                                d["cod_impuesto"], d["unidad_medida"], d["codigo_barras"],
                                d["activo"], d["controla_stock"])
    registrar_saldo_inicial(
        product_id,
        cod_usuario=request.session.get("user", {}).get("cod_usuario"),
        observaciones="Saldo inicial al crear el producto",
    )
    return RedirectResponse(url="/products/product", status_code=303)


@router.get("/product/edit/{product_id}", name="edit_product")
def edit_product(request: Request, product_id: int):
    product = get_product_by_id(product_id)
    taxes = get_all_invoice_taxes()
    if not product:
        return RedirectResponse(url="/products/product", status_code=302)
    return templates.TemplateResponse(request, "product/form.html", {"product": product, "taxes": taxes})


@router.post("/product/edit/{product_id}", name="update_product")
def update_product_post(
    request: Request,
    product_id: int,
    sku: str = Form(...),
    nombre: str = Form(...),
    descripcion: str = Form(""),
    precio_unitario: str = Form(...),
    stock: str = Form("0"),
    stock_minimo: str = Form("5"),
    cod_impuesto: str = Form("1"),
    unidad_medida: str = Form("C62"),
    codigo_barras: str = Form(""),
    activo: str = Form("1"),
    controla_stock: str = Form("1"),
):
    anterior = get_product_by_id(product_id)
    if not anterior:
        return RedirectResponse(url="/products/product", status_code=302)

    enviado = _enviado(**locals())
    v = validar_producto(enviado, product_id=product_id)
    if not v.valido:
        return formulario_invalido(request, PLANTILLA, v,
                                   {"product": anterior, "taxes": get_all_invoice_taxes()},
                                   enviado)

    d = v.datos
    cod_usuario = request.session.get("user", {}).get("cod_usuario")
    ya_controlaba = bool(anterior.get("controla_stock"))

    # Si el producto ya lleva kardex, el stock no se pisa desde el formulario: se
    # conserva el saldo y la diferencia entra como un ajuste trazable.
    stock_a_guardar = anterior["stock"] if (d["controla_stock"] and ya_controlaba) else d["stock"]

    update_product(product_id, d["sku"], d["nombre"], d["descripcion"],
                   d["precio_unitario"], stock_a_guardar, d["stock_minimo"],
                   d["cod_impuesto"], d["unidad_medida"], d["codigo_barras"],
                   d["activo"], d["controla_stock"])

    if d["controla_stock"] and ya_controlaba:
        ajustar_stock(product_id, d["stock"], cod_usuario=cod_usuario,
                      observaciones="Ajuste desde el formulario de producto")
    elif d["controla_stock"] and not ya_controlaba:
        registrar_saldo_inicial(product_id, cod_usuario=cod_usuario,
                                observaciones="Saldo de apertura al activar control de inventario")

    return RedirectResponse(url="/products/product", status_code=303)


@router.get("/product/delete/{product_id}", name="delete_product")
def delete_product_get(product_id: int):
    delete_product(product_id)
    return RedirectResponse(url="/products/product", status_code=302)
