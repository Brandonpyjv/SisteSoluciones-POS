"""
Cliente de la API de FactuGest.

Siste Soluciones vende y controla su inventario, pero no sabe emitir una factura
electrónica: se la pide a FactuGest, que es su proveedor tecnológico. Este módulo
es toda la conexión entre los dos sistemas.

La llave viaja en el `.env` y **nunca sale de aquí**: si el navegador pudiera ver
el PDF directamente en FactuGest, tendría que llevar la llave, y cualquiera que
abriera las herramientas de desarrollo podría emitir facturas a nombre del
negocio. Por eso el PDF y el XML se piden desde el servidor y se reenvían.
"""
import os

import httpx

# Un POS no puede quedarse colgado esperando: si FactuGest no contesta en este
# tiempo, la venta ya está guardada y la emisión se reintenta después.
TIEMPO_LIMITE = 20.0


class FactugestError(Exception):
    """No se pudo emitir. `detalle` es lo que se le muestra al cajero."""

    def __init__(self, detalle: str, codigo: str = None, recuperable: bool = True):
        self.detalle = detalle
        self.codigo = codigo
        # Recuperable: tiene sentido reintentar. Un problema de red lo es; unos
        # datos que la API rechaza, no, hasta que se corrijan.
        self.recuperable = recuperable
        super().__init__(detalle)


def _url() -> str:
    return (os.getenv("FACTUGEST_URL") or "http://127.0.0.1:8000").rstrip("/")


def _llave() -> str:
    llave = (os.getenv("FACTUGEST_API_KEY") or "").strip()
    if not llave:
        raise FactugestError(
            "Falta la llave de FactuGest. Complétala en el archivo .env "
            "(FACTUGEST_API_KEY) y reinicia el sistema.",
            codigo="sin_llave", recuperable=False)
    return llave


def configurado() -> bool:
    """Para que la vista no ofrezca un botón que no puede funcionar."""
    return bool((os.getenv("FACTUGEST_API_KEY") or "").strip())


def _pedir(metodo: str, ruta: str, **kwargs) -> httpx.Response:
    try:
        with httpx.Client(timeout=TIEMPO_LIMITE) as cliente:
            return cliente.request(metodo, _url() + ruta,
                                   headers={"X-API-Key": _llave()}, **kwargs)
    except httpx.TimeoutException:
        raise FactugestError(
            "FactuGest no respondió a tiempo. La venta quedó guardada; "
            "vuelve a intentar la emisión en un momento.", codigo="timeout")
    except httpx.RequestError:
        raise FactugestError(
            f"No se pudo conectar con FactuGest en {_url()}. Revisa que esté "
            "encendido y que la dirección del .env sea la correcta.",
            codigo="sin_conexion")


def _revisar(respuesta: httpx.Response) -> dict:
    """Traduce la respuesta de la API a algo que el cajero pueda leer."""
    if respuesta.status_code < 400:
        return respuesta.json()

    try:
        detalle = respuesta.json().get("detail")
    except Exception:
        detalle = None

    # La API responde con {codigo, mensaje} para sus errores, y con la lista de
    # Pydantic cuando el problema es de los datos enviados.
    if isinstance(detalle, dict):
        codigo, mensaje = detalle.get("codigo"), detalle.get("mensaje")
    elif isinstance(detalle, list):
        codigo = "datos_invalidos"
        mensaje = "; ".join(
            f"{'.'.join(str(p) for p in e.get('loc', [])[1:])}: {e.get('msg')}"
            for e in detalle[:4])
    else:
        codigo, mensaje = "error", str(detalle or respuesta.text)[:300]

    # Un 5xx puede pasar; un 4xx significa que hay que corregir algo primero.
    recuperable = respuesta.status_code >= 500 or respuesta.status_code == 429
    raise FactugestError(mensaje or "FactuGest rechazó el documento.",
                         codigo=codigo, recuperable=recuperable)


# ── Operaciones ─────────────────────────────────────────────────────────────

def ping() -> dict:
    """Comprueba la llave y devuelve con qué emisor se va a numerar."""
    return _revisar(_pedir("GET", "/api/v1/ping"))


def emitir_factura(peticion: dict) -> dict:
    """Emite una factura y devuelve el documento.

    Si la venta ya se había emitido, FactuGest devuelve la misma —responde 200 en
    lugar de 201— en vez de gastar otro número de la resolución. Por eso reintentar
    es seguro.
    """
    return _revisar(_pedir("POST", "/api/v1/facturas", json=peticion))


def descargar_pdf(id_documento: str) -> bytes:
    respuesta = _pedir("GET", f"/api/v1/documentos/{id_documento}/pdf")
    if respuesta.status_code >= 400:
        _revisar(respuesta)
    return respuesta.content


def descargar_xml(id_documento: str) -> bytes:
    respuesta = _pedir("GET", f"/api/v1/documentos/{id_documento}/xml")
    if respuesta.status_code >= 400:
        _revisar(respuesta)
    return respuesta.content
