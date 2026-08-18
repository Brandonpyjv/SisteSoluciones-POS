from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from typing import Optional

from services.inventory_service import (MOTIVOS, StockInsuficienteError, ajustar_stock,
                                        get_inventario_detallado, get_kardex, get_movimientos,
                                        get_resumen_inventario, registrar_movimiento)
from services.products_service import get_product_by_id
from templates_config import templates

router = APIRouter(prefix="/inventory")

# Motivos que tienen sentido según la dirección del movimiento.
_MOTIVOS_POR_TIPO = {
    "ENTRADA": ["COMPRA", "DEVOLUCION", "AJUSTE_MANUAL"],
    "SALIDA":  ["MERMA", "AJUSTE_MANUAL"],
}


@router.get("", name="inventory")
def inventory(request: Request, alertas: int = 0, q: str = ""):
    return templates.TemplateResponse(request, "inventory/index.html", {
        "resumen":    get_resumen_inventario(),
        "productos":  get_inventario_detallado(solo_alertas=bool(alertas), busqueda=q or None),
        "solo_alertas": bool(alertas),
        "busqueda":   q,
    })


@router.get("/movimientos", name="inventory_movimientos")
def movimientos(request: Request, desde: str = "", hasta: str = "",
                tipo: str = "", cod_producto: Optional[int] = None):
    return templates.TemplateResponse(request, "inventory/movimientos.html", {
        "movimientos": get_movimientos(desde=desde or None, hasta=hasta or None,
                                       tipo=tipo or None, cod_producto=cod_producto),
        "productos":   get_inventario_detallado(),
        "filtros":     {"desde": desde, "hasta": hasta, "tipo": tipo,
                        "cod_producto": cod_producto},
        "motivos":     MOTIVOS,
    })


@router.get("/kardex/{product_id}", name="inventory_kardex")
def kardex(request: Request, product_id: int):
    producto = get_product_by_id(product_id)
    if not producto:
        return RedirectResponse(url="/inventory", status_code=302)
    return templates.TemplateResponse(request, "inventory/kardex.html", {
        "producto":    producto,
        "movimientos": get_kardex(product_id, limite=200),
        "motivos":     MOTIVOS,
    })


@router.get("/movimiento/new", name="inventory_movimiento_new")
def movimiento_new(request: Request, cod_producto: Optional[int] = None):
    return templates.TemplateResponse(request, "inventory/form.html", {
        "productos":        get_inventario_detallado(),
        "motivos_por_tipo": _MOTIVOS_POR_TIPO,
        "motivos":          MOTIVOS,
        "seleccionado":     cod_producto,
        "error":            None,
    })


@router.post("/movimiento/new", name="inventory_movimiento_create")
def movimiento_create(
    request: Request,
    cod_producto: int = Form(...),
    tipo: str = Form(...),
    motivo: str = Form("AJUSTE_MANUAL"),
    cantidad: int = Form(0),
    nuevo_stock: int = Form(0),
    observaciones: str = Form(""),
):
    cod_usuario = request.session.get("user", {}).get("cod_usuario")

    def con_error(mensaje):
        # 422 y no 200: quien llame la ruta desde fuera necesita saber que el
        # movimiento se rechazó, no recibir la página como si hubiera funcionado.
        return templates.TemplateResponse(request, "inventory/form.html", {
            "productos":        get_inventario_detallado(),
            "motivos_por_tipo": _MOTIVOS_POR_TIPO,
            "motivos":          MOTIVOS,
            "seleccionado":     cod_producto,
            "error":            mensaje,
        }, status_code=422)

    if tipo not in ("AJUSTE", *_MOTIVOS_POR_TIPO):
        return con_error(f"«{tipo}» no es un tipo de movimiento válido.")
    if not get_product_by_id(cod_producto):
        return con_error("El producto seleccionado no existe.")

    try:
        if tipo == "AJUSTE":
            ajustar_stock(cod_producto, nuevo_stock, cod_usuario=cod_usuario,
                          observaciones=observaciones or "Ajuste por conteo físico")
        else:
            if motivo not in _MOTIVOS_POR_TIPO.get(tipo, []):
                return con_error(f"El motivo «{motivo}» no aplica a una {tipo.lower()}.")
            registrar_movimiento(cod_producto, tipo, motivo, cantidad,
                                 cod_usuario=cod_usuario, observaciones=observaciones or None)
    except StockInsuficienteError as e:
        return con_error(str(e))
    except ValueError as e:
        return con_error(str(e))

    return RedirectResponse(url=f"/inventory/kardex/{cod_producto}", status_code=303)
