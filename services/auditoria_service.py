"""
Registro de auditoría: quién hizo qué, cuándo y desde dónde.

Se escribe desde las rutas, con una línea:

    auditoria.registrar(request, "EMITIO", "factura", numero,
                        f"Emitió la factura {numero} por ${total:,.0f}")

Cuatro reglas que definen para qué sirve esto:

**Solo se escribe, nunca se corrige.** No hay función para actualizar ni para
borrar un registro. Un rastro que se puede editar no prueba nada; si algo quedó
mal escrito, se escribe otro registro contándolo.

**Se registra lo que cambia algo, no lo que se mira.** Anotar cada pantalla
abierta llenaría la tabla de ruido y enterraría lo que sí importa. Las lecturas
no dejan rastro; las escrituras, todas.

**Registrar no puede tumbar la operación.** Si la auditoría falla —la tabla no
existe todavía, la base se cayó a mitad—, la venta se guarda igual y el fallo se
queda en el log del servidor. Al revés sería peor: un sistema que deja de
facturar porque no pudo anotar que facturó.

**La frase se escribe en el momento.** «Emitió la factura FG60 por $653.310» se
guarda tal cual, no se reconstruye después leyendo la factura: esa factura puede
anularse, cambiar de estado o desaparecer, y lo que pasó ese día no cambia.
"""
import json
import logging
from datetime import datetime

from database import execute_query, get_many, get_one

registro = logging.getLogger("siste.auditoria")

# Las acciones que se registran. Está cerrado a propósito: si cada ruta inventa
# su verbo, filtrar por acción deja de servir.
ACCIONES = {
    "INGRESO":    "Inició sesión",
    "SALIDA":     "Cerró sesión",
    "INGRESO_FALLIDO": "Intento de ingreso fallido",
    "CREO":       "Creó",
    "ACTUALIZO":  "Modificó",
    "ELIMINO":    "Eliminó",
    "EMITIO":     "Emitió",
    "ANULO":      "Anuló",
    "COBRO":      "Cobró",
    "ROTO_LLAVE": "Rotó una llave",
    "CAMBIO_ESTADO": "Cambió el estado",
    "AJUSTO_STOCK": "Ajustó existencias",
}

# Cómo se pinta cada acción en el listado.
COLOR_ACCION = {
    "CREO": "success", "EMITIO": "success", "INGRESO": "secondary",
    "ACTUALIZO": "primary", "COBRO": "success", "AJUSTO_STOCK": "primary",
    "ELIMINO": "danger", "ANULO": "danger", "INGRESO_FALLIDO": "danger",
    "SALIDA": "secondary", "ROTO_LLAVE": "warning", "CAMBIO_ESTADO": "warning",
}


def _ip(request) -> str:
    """La IP de quien hizo la petición, mirando primero el proxy.

    Detrás de un proxy —que es como va a quedar en producción— `client.host` es
    la del proxy y no la de la persona. `X-Forwarded-For` trae la cadena real y
    el primero de la lista es el origen.
    """
    if request is None:
        return None
    reenviada = request.headers.get("x-forwarded-for")
    if reenviada:
        return reenviada.split(",")[0].strip()[:45]
    return getattr(getattr(request, "client", None), "host", None)


def registrar(request, accion: str, entidad: str = None, entidad_id=None,
              descripcion: str = "", cambios: dict = None, usuario: dict = None):
    """Anota una acción. Nunca lanza: ver el porqué en el docstring del módulo."""
    try:
        actor = usuario if usuario is not None else (
            request.session.get("user", {}) if request is not None else {})

        execute_query(
            "INSERT INTO auditoria (fecha, cod_usuario, usuario_nombre, usuario_rol, "
            "  accion, entidad, entidad_id, descripcion, cambios, ip) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
             actor.get("cod_usuario"), (actor.get("nombre") or "Sistema")[:120],
             actor.get("rol"), accion, entidad,
             str(entidad_id)[:60] if entidad_id is not None else None,
             (descripcion or ACCIONES.get(accion, accion))[:300],
             json.dumps(cambios, ensure_ascii=False, default=str) if cambios else None,
             _ip(request)))
    except Exception:
        registro.exception("No se pudo registrar en auditoría: %s %s %s",
                           accion, entidad, entidad_id)


def diferencias(antes: dict, despues: dict, campos=None) -> dict:
    """Qué cambió entre dos versiones de una fila.

    Solo los campos que de verdad cambiaron: guardar la fila entera en cada
    modificación obliga a comparar a mano para ver qué se movió, que es
    justamente el trabajo que el registro debería ahorrar.
    """
    antes = antes or {}
    despues = despues or {}
    campos = campos or set(antes) | set(despues)
    cambios = {}
    for campo in campos:
        viejo, nuevo = antes.get(campo), despues.get(campo)
        if str(viejo) != str(nuevo):
            cambios[campo] = {"antes": viejo, "despues": nuevo}
    return cambios


# ── Consulta ────────────────────────────────────────────────────────────────

def get_auditoria(limite: int = 2000) -> list:
    """El rastro, del más reciente al más antiguo.

    Trae un tope alto en lugar de todo: la tabla crece para siempre y nadie
    necesita ver el año pasado en una pantalla. Para eso están los filtros.
    """
    return get_many(
        "SELECT a.*, u.nombre AS usuario_actual "
        "FROM auditoria a LEFT JOIN usuarios u ON a.cod_usuario = u.cod_usuario "
        "ORDER BY a.fecha DESC, a.cod_auditoria DESC LIMIT %s", (limite,))


def usuarios_con_actividad() -> list:
    return get_many(
        "SELECT DISTINCT usuario_nombre FROM auditoria "
        "WHERE usuario_nombre IS NOT NULL ORDER BY usuario_nombre")


def resumen() -> dict:
    fila = get_one(
        "SELECT COUNT(*) AS total, "
        "       SUM(DATE(fecha) = CURDATE()) AS hoy, "
        "       COUNT(DISTINCT cod_usuario) AS usuarios, "
        "       SUM(accion IN ('ELIMINO', 'ANULO', 'INGRESO_FALLIDO')) AS delicadas "
        "FROM auditoria") or {}
    return {k: int(fila.get(k) or 0) for k in ("total", "hoy", "usuarios", "delicadas")}
