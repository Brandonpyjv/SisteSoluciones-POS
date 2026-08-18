"""
Reserva de consecutivos por emisor.

La numeración de una resolución DIAN es un recurso autorizado y finito, y dos
documentos con el mismo número son dos documentos rechazados. Leer el
consecutivo y después actualizarlo en dos sentencias distintas funciona
mientras haya un solo usuario en un navegador; con varios puntos de venta
llamando a la API al mismo tiempo, dos peticiones leen el mismo valor y ambas
emiten con él.

Aquí la reserva es una sola sentencia UPDATE, que MySQL serializa por fila, y el
valor reservado se recupera con LAST_INSERT_ID() —que es propio de la sesión, no
global— sobre la misma conexión.
"""
from database import transaction

# Solo la factura de venta lleva prefijo configurable por empresa; las notas usan
# su propia serie, que el proyecto ha manejado siempre con prefijo fijo.
_SERIES = {
    "FV": {"columna": "consecutivo_actual", "prefijo_fijo": None},
    "NC": {"columna": "consecutivo_nc",     "prefijo_fijo": "NC"},
    "ND": {"columna": "consecutivo_nd",     "prefijo_fijo": "ND"},
}


class EmisorNoEncontradoError(Exception):
    """La empresa emisora no existe."""


class RangoResolucionAgotadoError(Exception):
    """El consecutivo se salió del rango que autorizó la DIAN."""


def _reservar(cursor, cod_empresa: int, tipo: str) -> dict:
    serie = _SERIES[tipo]
    columna = serie["columna"]

    # COALESCE porque el consecutivo puede venir nulo en empresas cargadas a mano.
    cursor.execute(
        f"UPDATE empresas "
        f"SET {columna} = LAST_INSERT_ID(COALESCE({columna}, 1)) + 1 "
        f"WHERE cod_empresa = %s",
        (cod_empresa,),
    )
    if cursor.rowcount == 0:
        raise EmisorNoEncontradoError(f"No existe la empresa {cod_empresa}")

    cursor.execute(
        "SELECT LAST_INSERT_ID() AS reservado, prefijo_factura, "
        "       resolucion_desde, resolucion_hasta "
        "FROM empresas WHERE cod_empresa = %s",
        (cod_empresa,),
    )
    # fetchall y no fetchone: el cursor sigue usándose para guardar la factura, y
    # dejar el result set a medio leer hace fallar el siguiente execute.
    filas = cursor.fetchall()
    if not filas:
        raise EmisorNoEncontradoError(f"No existe la empresa {cod_empresa}")
    fila = filas[0]

    consecutivo = int(fila["reservado"])
    prefijo = serie["prefijo_fijo"] or (fila.get("prefijo_factura") or "FV")

    # El rango solo aplica a la factura de venta, y solo se puede verificar si la
    # empresa lo tiene cargado: hay emisores registrados sin resolución todavía.
    if tipo == "FV":
        desde, hasta = fila.get("resolucion_desde"), fila.get("resolucion_hasta")
        if desde is not None and hasta is not None:
            if not (int(desde) <= consecutivo <= int(hasta)):
                raise RangoResolucionAgotadoError(
                    f"El consecutivo {consecutivo} está fuera del rango autorizado "
                    f"{desde}–{hasta} de la resolución DIAN"
                )

    return {
        "consecutivo": consecutivo,
        "prefijo": prefijo,
        "numero": f"{prefijo}{consecutivo}",
    }


def reservar_numero(cod_empresa: int, tipo: str = "FV", cursor=None) -> dict:
    """Reserva y devuelve el siguiente número de la serie `tipo` del emisor.

    Devuelve `{consecutivo, prefijo, numero}`. El número reservado ya quedó
    consumido: quien lo pide se compromete a usarlo o a revertir la transacción.

    Se le puede pasar un `cursor` para que la reserva viaje dentro de la
    transacción de quien emite; así, si la emisión falla, el consecutivo se
    devuelve solo. Sin cursor abre su propia transacción y confirma de una vez.
    """
    if tipo not in _SERIES:
        raise ValueError(f"Tipo de documento desconocido: {tipo}")

    if cursor is not None:
        return _reservar(cursor, cod_empresa, tipo)

    with transaction() as propio:
        return _reservar(propio, cod_empresa, tipo)
