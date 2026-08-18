"""Control de inventario: kardex de movimientos, alertas y valorización.

Toda modificación de `productos.stock` debe pasar por aquí. El stock no se
actualiza nunca con un UPDATE suelto: cada cambio queda respaldado por una fila
en `movimientos_inventario`, de modo que el saldo siempre es reconstruible.

Los helpers de `database.py` abren y cierran una conexión por llamada, así que no
sirven para operaciones atómicas. Las escrituras de este módulo manejan su propia
transacción sobre una única conexión.
"""
from datetime import datetime

from database import create_connection, get_many, get_one

TIPOS = ("ENTRADA", "SALIDA", "AJUSTE")

MOTIVOS = {
    "VENTA":          "Venta (factura)",
    "COMPRA":         "Compra a proveedor",
    "DEVOLUCION":     "Devolución de cliente (nota crédito)",
    "AJUSTE_MANUAL":  "Ajuste manual de inventario",
    "MERMA":          "Merma, daño o pérdida",
    "INICIAL":        "Saldo de apertura",
    "ANULACION":      "Reverso por anulación de documento",
}


class StockInsuficienteError(Exception):
    """El movimiento dejaría el stock en negativo."""

    def __init__(self, producto: str, disponible: int, solicitado: int):
        self.producto = producto
        self.disponible = disponible
        self.solicitado = solicitado
        super().__init__(
            f"Stock insuficiente de «{producto}»: disponible {disponible}, solicitado {solicitado}"
        )


# ── Escritura ────────────────────────────────────────────────────────────────

def _ahora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")


def _aplicar_movimiento(cursor, cod_producto, tipo, motivo, cantidad,
                        cod_usuario=None, cod_factura=None, observaciones=None,
                        costo_unitario=None, permitir_negativo=False, fecha=None):
    """Aplica un movimiento dentro de una transacción ya abierta.

    `fecha` permite fechar el movimiento en el pasado; se usa al cargar datos
    históricos. En la operación normal se omite y queda la fecha del momento.

    Retorna el dict del movimiento, o None si el producto no controla stock.
    """
    if tipo not in TIPOS:
        raise ValueError(f"Tipo de movimiento inválido: {tipo}")
    if motivo not in MOTIVOS:
        raise ValueError(f"Motivo de movimiento inválido: {motivo}")

    cantidad = int(cantidad)
    if cantidad <= 0:
        raise ValueError("La cantidad del movimiento debe ser mayor a cero")

    # FOR UPDATE bloquea la fila hasta el commit: dos facturas simultáneas del mismo
    # producto no pueden leer el mismo stock y pisarse el resultado.
    cursor.execute(
        "SELECT cod_producto, nombre, stock, controla_stock, precio_unitario "
        "FROM productos WHERE cod_producto = %s FOR UPDATE",
        (cod_producto,),
    )
    prod = cursor.fetchone()
    if not prod:
        raise ValueError(f"El producto {cod_producto} no existe")
    if not prod["controla_stock"]:
        return None

    stock_anterior = int(prod["stock"] or 0)
    delta = cantidad if tipo == "ENTRADA" else -cantidad
    stock_nuevo = stock_anterior + delta

    if stock_nuevo < 0 and not permitir_negativo:
        raise StockInsuficienteError(prod["nombre"], stock_anterior, cantidad)

    fecha = fecha or _ahora()

    cursor.execute(
        "UPDATE productos SET stock = %s WHERE cod_producto = %s",
        (stock_nuevo, cod_producto),
    )
    cursor.execute(
        """INSERT INTO movimientos_inventario
               (cod_producto, tipo, motivo, cantidad, stock_anterior, stock_nuevo,
                costo_unitario, cod_factura, cod_usuario, observaciones, fecha)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (cod_producto, tipo, motivo, cantidad, stock_anterior, stock_nuevo,
         costo_unitario if costo_unitario is not None else prod["precio_unitario"],
         cod_factura, cod_usuario, observaciones, fecha),
    )

    return {
        "cod_movimiento": cursor.lastrowid,
        "cod_producto":   cod_producto,
        "producto":       prod["nombre"],
        "tipo":           tipo,
        "motivo":         motivo,
        "cantidad":       cantidad,
        "stock_anterior": stock_anterior,
        "stock_nuevo":    stock_nuevo,
    }


def registrar_movimiento(cod_producto, tipo, motivo, cantidad, cod_usuario=None,
                         cod_factura=None, observaciones=None, costo_unitario=None,
                         permitir_negativo=False, fecha=None):
    """Registra un movimiento individual con su propia transacción."""
    db = create_connection()
    cursor = db.cursor(dictionary=True)
    try:
        mov = _aplicar_movimiento(
            cursor, cod_producto, tipo, motivo, cantidad,
            cod_usuario=cod_usuario, cod_factura=cod_factura,
            observaciones=observaciones, costo_unitario=costo_unitario,
            permitir_negativo=permitir_negativo, fecha=fecha,
        )
        db.commit()
        return mov
    except Exception:
        db.rollback()
        raise
    finally:
        cursor.close()
        db.close()


def registrar_movimientos_documento(lineas, tipo, motivo, cod_factura=None,
                                    cod_usuario=None, observaciones=None,
                                    permitir_negativo=False, fecha=None, cursor=None):
    """Aplica en bloque los movimientos de un documento (factura, NC…).

    `lineas` es una lista de dicts con al menos `cod_producto` y `cantidad`.
    O se registran todas o no se registra ninguna: si una línea no tiene stock
    suficiente, la factura completa debe fallar antes de emitirse.

    Con `cursor` los movimientos se aplican dentro de la transacción de quien
    emite el documento, para que un fallo posterior también los deshaga junto
    con la factura y el consecutivo. Sin él abre su propia transacción.
    """
    def _aplicar_todos(cur):
        aplicados = []
        for linea in lineas:
            mov = _aplicar_movimiento(
                cur,
                linea["cod_producto"], tipo, motivo, abs(int(linea["cantidad"])),
                cod_usuario=cod_usuario, cod_factura=cod_factura,
                observaciones=observaciones,
                costo_unitario=linea.get("precio_unitario"),
                permitir_negativo=permitir_negativo, fecha=fecha,
            )
            if mov:
                aplicados.append(mov)
        return aplicados

    if cursor is not None:
        return _aplicar_todos(cursor)

    db = create_connection()
    propio = db.cursor(dictionary=True)
    try:
        aplicados = _aplicar_todos(propio)
        db.commit()
        return aplicados
    except Exception:
        db.rollback()
        raise
    finally:
        propio.close()
        db.close()


def ajustar_stock(cod_producto, nuevo_stock, cod_usuario=None, observaciones=None,
                  fecha=None):
    """Fija el stock a un valor absoluto (conteo físico) y registra la diferencia."""
    nuevo_stock = int(nuevo_stock)
    if nuevo_stock < 0:
        raise ValueError("El stock no puede ser negativo")

    db = create_connection()
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT nombre, stock, controla_stock, precio_unitario "
            "FROM productos WHERE cod_producto = %s FOR UPDATE",
            (cod_producto,),
        )
        prod = cursor.fetchone()
        if not prod:
            raise ValueError(f"El producto {cod_producto} no existe")
        if not prod["controla_stock"]:
            raise ValueError(f"«{prod['nombre']}» no maneja inventario")

        stock_anterior = int(prod["stock"] or 0)
        diferencia = nuevo_stock - stock_anterior
        if diferencia == 0:
            return None

        fecha = fecha or _ahora()
        cursor.execute("UPDATE productos SET stock = %s WHERE cod_producto = %s",
                       (nuevo_stock, cod_producto))
        cursor.execute(
            """INSERT INTO movimientos_inventario
                   (cod_producto, tipo, motivo, cantidad, stock_anterior, stock_nuevo,
                    costo_unitario, cod_usuario, observaciones, fecha)
               VALUES (%s, 'AJUSTE', 'AJUSTE_MANUAL', %s, %s, %s, %s, %s, %s, %s)""",
            (cod_producto, abs(diferencia), stock_anterior, nuevo_stock,
             prod["precio_unitario"], cod_usuario, observaciones, fecha),
        )
        db.commit()
        return {
            "cod_movimiento": cursor.lastrowid,
            "producto":       prod["nombre"],
            "stock_anterior": stock_anterior,
            "stock_nuevo":    nuevo_stock,
            "diferencia":     diferencia,
        }
    except Exception:
        db.rollback()
        raise
    finally:
        cursor.close()
        db.close()


def registrar_saldo_inicial(cod_producto, cod_usuario=None, observaciones=None,
                            fecha=None):
    """Abre el kardex de un producto con el stock que ya tiene registrado.

    No modifica `productos.stock`: lo toma como saldo de apertura. Se usa al crear
    un producto o al activarle el control de inventario.
    """
    prod = get_one(
        "SELECT nombre, stock, controla_stock, precio_unitario "
        "FROM productos WHERE cod_producto = %s",
        (cod_producto,),
    )
    if not prod or not prod["controla_stock"]:
        return None

    cantidad = int(prod["stock"] or 0)
    db = create_connection()
    cursor = db.cursor()
    try:
        cursor.execute(
            """INSERT INTO movimientos_inventario
                   (cod_producto, tipo, motivo, cantidad, stock_anterior, stock_nuevo,
                    costo_unitario, cod_usuario, observaciones, fecha)
               VALUES (%s, 'ENTRADA', 'INICIAL', %s, 0, %s, %s, %s, %s, %s)""",
            (cod_producto, cantidad, cantidad, prod["precio_unitario"], cod_usuario,
             observaciones or "Saldo de apertura", fecha or _ahora()),
        )
        db.commit()
        return {"cod_movimiento": cursor.lastrowid, "producto": prod["nombre"],
                "stock_nuevo": cantidad}
    except Exception:
        db.rollback()
        raise
    finally:
        cursor.close()
        db.close()


def revertir_movimientos_de_factura(cod_factura, cod_usuario=None):
    """Deshace el efecto en inventario de un documento que se elimina.

    Genera movimientos contrarios en lugar de borrar los originales: el kardex es
    un histórico y no debe perder trazabilidad.
    """
    movimientos = get_many(
        "SELECT cod_producto, tipo, cantidad FROM movimientos_inventario "
        "WHERE cod_factura = %s AND motivo <> 'ANULACION'",
        (cod_factura,),
    )
    if not movimientos:
        return []

    db = create_connection()
    cursor = db.cursor(dictionary=True)
    revertidos = []
    try:
        for mov in movimientos:
            contrario = "ENTRADA" if mov["tipo"] == "SALIDA" else "SALIDA"
            aplicado = _aplicar_movimiento(
                cursor, mov["cod_producto"], contrario, "ANULACION", mov["cantidad"],
                cod_usuario=cod_usuario, cod_factura=cod_factura,
                observaciones=f"Reverso por eliminación del documento {cod_factura}",
                permitir_negativo=True,
            )
            if aplicado:
                revertidos.append(aplicado)
        db.commit()
        return revertidos
    except Exception:
        db.rollback()
        raise
    finally:
        cursor.close()
        db.close()


# ── Lectura ──────────────────────────────────────────────────────────────────

def verificar_disponibilidad(lineas):
    """Retorna los productos sin stock suficiente, sin escribir en la BD.

    Permite avisar al usuario antes de intentar emitir la factura. Las cantidades
    se suman por producto: un mismo producto en dos líneas compite contra el mismo
    saldo.
    """
    solicitado_por_producto = {}
    for linea in lineas:
        cod = linea["cod_producto"]
        solicitado_por_producto[cod] = solicitado_por_producto.get(cod, 0) + abs(int(linea["cantidad"]))

    faltantes = []
    for cod, solicitado in solicitado_por_producto.items():
        prod = get_one(
            "SELECT nombre, stock, controla_stock FROM productos WHERE cod_producto = %s",
            (cod,),
        )
        if not prod or not prod["controla_stock"]:
            continue
        disponible = int(prod["stock"] or 0)
        if solicitado > disponible:
            faltantes.append({
                "cod_producto": cod,
                "producto":     prod["nombre"],
                "disponible":   disponible,
                "solicitado":   solicitado,
            })
    return faltantes


def documento_afecto_inventario(cod_factura) -> bool:
    """¿Este documento llegó a descontar inventario?

    Las facturas emitidas antes de existir el kardex no descontaron stock; devolver
    unidades por una nota crédito sobre ellas inflaría el inventario.
    """
    row = get_one(
        "SELECT COUNT(*) AS n FROM movimientos_inventario "
        "WHERE cod_factura = %s AND motivo = 'VENTA'",
        (cod_factura,),
    )
    return bool(row and row["n"])


def get_inventario_detallado(solo_alertas=False, busqueda=None):
    """Listado de productos con su situación de inventario."""
    condiciones = ["p.activo = 1", "p.controla_stock = 1"]
    params = []

    if solo_alertas:
        condiciones.append("p.stock <= p.stock_minimo")
    if busqueda:
        condiciones.append("(p.nombre LIKE %s OR p.sku LIKE %s)")
        params.extend([f"%{busqueda}%", f"%{busqueda}%"])

    return get_many(f"""
        SELECT p.cod_producto,
               p.sku,
               p.nombre,
               p.stock,
               p.stock_minimo,
               p.precio_unitario,
               p.unidad_medida,
               (p.stock * p.precio_unitario) AS valor_inventario,
               CASE WHEN p.stock <= 0                 THEN 'AGOTADO'
                    WHEN p.stock <= p.stock_minimo    THEN 'BAJO'
                    ELSE 'OK' END                     AS estado_stock,
               (SELECT MAX(m.fecha) FROM movimientos_inventario m
                 WHERE m.cod_producto = p.cod_producto) AS ultimo_movimiento
        FROM productos p
        WHERE {' AND '.join(condiciones)}
        ORDER BY (p.stock <= p.stock_minimo) DESC, p.nombre
    """, tuple(params))


def get_resumen_inventario():
    """Cifras de cabecera para el panel de inventario y el dashboard."""
    row = get_one("""
        SELECT COUNT(*)                                                   AS productos_controlados,
               COALESCE(SUM(stock), 0)                                    AS unidades_totales,
               COALESCE(SUM(stock * precio_unitario), 0)                  AS valor_inventario,
               COALESCE(SUM(stock <= 0), 0)                               AS agotados,
               COALESCE(SUM(stock > 0 AND stock <= stock_minimo), 0)      AS bajo_minimo
        FROM productos
        WHERE activo = 1 AND controla_stock = 1
    """) or {}
    return {
        "productos_controlados": int(row.get("productos_controlados") or 0),
        "unidades_totales":      int(row.get("unidades_totales") or 0),
        "valor_inventario":      float(row.get("valor_inventario") or 0),
        "agotados":              int(row.get("agotados") or 0),
        "bajo_minimo":           int(row.get("bajo_minimo") or 0),
    }


def get_alertas_stock(limite=10):
    """Productos agotados o por debajo del mínimo, los más críticos primero."""
    return get_many("""
        SELECT cod_producto, sku, nombre, stock, stock_minimo,
               CASE WHEN stock <= 0 THEN 'AGOTADO' ELSE 'BAJO' END AS estado_stock,
               GREATEST(stock_minimo - stock, 0)                   AS faltante
        FROM productos
        WHERE activo = 1 AND controla_stock = 1 AND stock <= stock_minimo
        ORDER BY (stock <= 0) DESC, (stock_minimo - stock) DESC, nombre
        LIMIT %s
    """, (int(limite),))


def get_kardex(cod_producto, limite=100):
    """Historial de movimientos de un producto, del más reciente al más antiguo."""
    return get_many("""
        SELECT m.*,
               u.nombre          AS usuario_nombre,
               f.numero_factura  AS documento
        FROM movimientos_inventario m
            LEFT JOIN usuarios u ON m.cod_usuario = u.cod_usuario
            LEFT JOIN facturas f ON m.cod_factura = f.cod_factura
        WHERE m.cod_producto = %s
        ORDER BY m.fecha DESC, m.cod_movimiento DESC
        LIMIT %s
    """, (cod_producto, int(limite)))


def get_movimientos(desde=None, hasta=None, tipo=None, cod_producto=None, limite=200):
    """Movimientos de todos los productos, con filtros opcionales."""
    condiciones = ["1 = 1"]
    params = []

    if desde:
        condiciones.append("m.fecha >= %s")
        params.append(desde)
    if hasta:
        condiciones.append("m.fecha < DATE_ADD(%s, INTERVAL 1 DAY)")
        params.append(hasta)
    if tipo:
        condiciones.append("m.tipo = %s")
        params.append(tipo)
    if cod_producto:
        condiciones.append("m.cod_producto = %s")
        params.append(cod_producto)

    params.append(int(limite))
    return get_many(f"""
        SELECT m.*,
               p.nombre          AS producto_nombre,
               p.sku,
               u.nombre          AS usuario_nombre,
               f.numero_factura  AS documento
        FROM movimientos_inventario m
            LEFT JOIN productos p ON m.cod_producto = p.cod_producto
            LEFT JOIN usuarios  u ON m.cod_usuario  = u.cod_usuario
            LEFT JOIN facturas  f ON m.cod_factura  = f.cod_factura
        WHERE {' AND '.join(condiciones)}
        ORDER BY m.fecha DESC, m.cod_movimiento DESC
        LIMIT %s
    """, tuple(params))


def get_productos_mas_movidos(desde=None, hasta=None, limite=5):
    """Productos con mayor salida de inventario en el periodo."""
    condiciones = ["m.tipo = 'SALIDA'", "m.motivo = 'VENTA'"]
    params = []
    if desde:
        condiciones.append("m.fecha >= %s")
        params.append(desde)
    if hasta:
        condiciones.append("m.fecha < DATE_ADD(%s, INTERVAL 1 DAY)")
        params.append(hasta)
    params.append(int(limite))

    return get_many(f"""
        SELECT p.cod_producto, p.nombre, p.sku,
               SUM(m.cantidad) AS unidades_salidas
        FROM movimientos_inventario m
            JOIN productos p ON m.cod_producto = p.cod_producto
        WHERE {' AND '.join(condiciones)}
        GROUP BY p.cod_producto, p.nombre, p.sku
        ORDER BY unidades_salidas DESC
        LIMIT %s
    """, tuple(params))
