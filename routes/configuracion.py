"""
Configuración: los catálogos y la conexión con el proveedor de facturación.

Impuestos, descuentos, métodos de pago y estados de pago vivían sueltos en el
menú lateral, al mismo nivel que vender. No es donde van: no son trabajo del día,
son parámetros que se ajustan cuando algo cambia.

Aquí también queda a la vista la conexión con FactuGest, que hasta ahora solo
existía en el archivo `.env`. Es lo primero que hay que mirar cuando una venta no
se puede emitir, y no tenía ninguna pantalla.
"""
import os

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from database import get_one
from services import factugest_client
from services.emision_service import contar_pendientes
from templates_config import templates

router = APIRouter(prefix="/configuracion")


def _cuantos(tabla: str, condicion: str = "") -> int:
    fila = get_one(f"SELECT COUNT(*) AS n FROM {tabla} {condicion}")
    return int(fila["n"] if fila else 0)


@router.get("", name="configuracion")
def configuracion(request: Request):
    return templates.TemplateResponse(request, "configuracion/index.html", {
        "conteos": {
            "impuestos":    _cuantos("impuestos"),
            "descuentos":   _cuantos("descuentos"),
            "metodos_pago": _cuantos("metodos_pago"),
            "estados_pago": _cuantos("pagos_factura"),
            "empresas":     _cuantos("empresas"),
            "usuarios":     _cuantos("usuarios", "WHERE activo = 1"),
            "pendientes":   contar_pendientes(),
            "auditoria":    _cuantos("auditoria"),
        },
        "factugest": {
            "url": os.getenv("FACTUGEST_URL") or "http://127.0.0.1:8000",
            "configurado": factugest_client.configurado(),
        },
        "prueba": request.session.pop("prueba_conexion", None),
    })


@router.post("/probar-conexion", name="probar_conexion")
def probar_conexion(request: Request):
    """Llama a `GET /api/v1/ping` y guarda qué contestó.

    Es la misma comprobación que hace quien se integra por primera vez: si esto
    responde, la llave sirve y se sabe con qué emisor se va a numerar. Se hace
    desde el servidor porque la llave no puede llegar al navegador.
    """
    try:
        respuesta = factugest_client.ping()
        emisor = respuesta.get("emisor") or {}
        request.session["prueba_conexion"] = {
            "ok": True,
            "texto": f"Responde. La llave es de «{respuesta.get('cliente')}», plan "
                     f"{respuesta.get('plan')}, y se numera con "
                     f"{emisor.get('nombre')} (NIT {emisor.get('nit')}).",
        }
    except factugest_client.FactugestError as e:
        request.session["prueba_conexion"] = {"ok": False, "texto": e.detalle}

    return RedirectResponse(url="/configuracion", status_code=303)
