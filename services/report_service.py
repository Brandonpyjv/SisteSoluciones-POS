"""Métricas financieras y comerciales derivadas de la facturación.

Convenciones que usa todo el módulo:

* Las notas crédito se guardan con importes negativos, así que la venta neta de un
  periodo es simplemente la suma de los totales de FV, ND y NC.
* Una factura anulada por nota crédito sigue contando como facturación bruta —
  se emitió— y es la NC la que la descuenta. Restar ambas la contaría dos veces.
* Cartera es lo que está por cobrar: estados pendiente (2), parcialmente pagado
  (3) y vencido (4). Anuladas y canceladas no son cartera.
* Sin `cod_empresa` las cifras son consolidadas de todas las empresas emisoras.

Ningún SQL de este módulo usa `%` literal (ni DATE_FORMAT): los helpers de
`database.py` aplican formateo de cadena sobre la consulta y un `%` suelto
rompería según la versión del conector.
"""
from datetime import date, timedelta

from database import get_many, get_one

COBRADO = (1,)
CARTERA = (2, 3, 4)

# `pagos_factura.status` guarda los estados en inglés (salvo los dos que se
# agregaron después, en español). La interfaz es en español, así que se traducen
# al mostrarlos en vez de tocar la tabla, que ya está referenciada por código.
ESTADOS_PAGO = {
    "paid":                 "Pagado",
    "pending":              "Pendiente",
    "partially paid":       "Pago parcial",
    "overdue":              "Vencido",
    "cancelled":            "Cancelado",
    "disputed":             "En disputa",
    "refunded":             "Reembolsado",
    "Anulada":              "Anulada",
    "Parcialmente Anulada": "Parcialmente anulada",
}


def etiqueta_estado(status: str) -> str:
    if not status:
        return "Sin estado"
    return ESTADOS_PAGO.get(status, ESTADOS_PAGO.get(status.lower(), status))


def rango_por_defecto(dias=30):
    """Ventana de los últimos `dias` días, ambos extremos incluidos."""
    hasta = date.today()
    return (hasta - timedelta(days=dias - 1)).isoformat(), hasta.isoformat()


def periodo_anterior(desde, hasta):
    """Ventana inmediatamente anterior, del mismo largo, para comparar."""
    d = date.fromisoformat(str(desde))
    h = date.fromisoformat(str(hasta))
    largo = (h - d).days + 1
    return (d - timedelta(days=largo)).isoformat(), (d - timedelta(days=1)).isoformat()


def _filtro(desde, hasta, cod_empresa, alias="f"):
    """Condiciones y parámetros comunes de periodo y empresa."""
    condiciones = [f"{alias}.fecha >= %s", f"{alias}.fecha < DATE_ADD(%s, INTERVAL 1 DAY)"]
    params = [desde, hasta]
    if cod_empresa:
        condiciones.append(f"{alias}.cod_empresa = %s")
        params.append(cod_empresa)
    return " AND ".join(condiciones), params


def _num(valor):
    return float(valor or 0)


# ── Indicadores de cabecera ─────────────────────────────────────────────────

def get_kpis(desde, hasta, cod_empresa=None):
    """Cifras principales del periodo, con variación contra el periodo anterior."""
    where, params = _filtro(desde, hasta, cod_empresa)

    fila = get_one(f"""
        SELECT COALESCE(SUM(CASE WHEN f.tipo_factura = 'FV' THEN f.total END), 0) AS ventas_brutas,
               COALESCE(SUM(CASE WHEN f.tipo_factura = 'NC' THEN f.total END), 0) AS notas_credito,
               COALESCE(SUM(CASE WHEN f.tipo_factura = 'ND' THEN f.total END), 0) AS notas_debito,
               COALESCE(SUM(f.total), 0)                                          AS ventas_netas,
               COALESCE(SUM(f.total_impuestos), 0)                                AS impuestos,
               COALESCE(SUM(f.total_descuentos), 0)                               AS descuentos,
               COUNT(CASE WHEN f.tipo_factura = 'FV' THEN 1 END)                  AS num_facturas,
               COUNT(DISTINCT f.cod_cliente)                                      AS clientes_facturados
        FROM facturas f
        WHERE {where}
    """, tuple(params)) or {}

    cobrado = get_one(f"""
        SELECT COALESCE(SUM(f.total), 0) AS total
        FROM facturas f
        WHERE {where} AND f.cod_pago IN ({','.join(['%s'] * len(COBRADO))})
    """, tuple(params + list(COBRADO))) or {}

    ventas_netas = _num(fila.get("ventas_netas"))
    num_facturas = int(fila.get("num_facturas") or 0)

    kpis = {
        "ventas_brutas":       _num(fila.get("ventas_brutas")),
        "notas_credito":       abs(_num(fila.get("notas_credito"))),
        "notas_debito":        _num(fila.get("notas_debito")),
        "ventas_netas":        ventas_netas,
        "impuestos":           _num(fila.get("impuestos")),
        "descuentos":          _num(fila.get("descuentos")),
        "num_facturas":        num_facturas,
        "clientes_facturados": int(fila.get("clientes_facturados") or 0),
        "ingresos_cobrados":   _num(cobrado.get("total")),
        "ticket_promedio":     (_num(fila.get("ventas_brutas")) / num_facturas) if num_facturas else 0.0,
    }

    # Variación contra la ventana anterior del mismo largo.
    ant_desde, ant_hasta = periodo_anterior(desde, hasta)
    where_ant, params_ant = _filtro(ant_desde, ant_hasta, cod_empresa)
    anterior = get_one(f"""
        SELECT COALESCE(SUM(f.total), 0)                          AS ventas_netas,
               COUNT(CASE WHEN f.tipo_factura = 'FV' THEN 1 END)  AS num_facturas
        FROM facturas f
        WHERE {where_ant}
    """, tuple(params_ant)) or {}

    ventas_ant = _num(anterior.get("ventas_netas"))
    facturas_ant = int(anterior.get("num_facturas") or 0)
    kpis["ventas_periodo_anterior"] = ventas_ant
    kpis["variacion_ventas"] = ((ventas_netas - ventas_ant) / ventas_ant * 100) if ventas_ant else None
    kpis["variacion_facturas"] = ((num_facturas - facturas_ant) / facturas_ant * 100) if facturas_ant else None

    return kpis


# ── Cartera ─────────────────────────────────────────────────────────────────

def get_cartera(cod_empresa=None):
    """Saldo por cobrar y su parte vencida. No depende del periodo consultado:
    la cartera es una foto del momento, no un flujo."""
    condiciones = [f"f.cod_pago IN ({','.join(['%s'] * len(CARTERA))})", "f.tipo_factura <> 'NC'"]
    params = list(CARTERA)
    if cod_empresa:
        condiciones.append("f.cod_empresa = %s")
        params.append(cod_empresa)
    where = " AND ".join(condiciones)

    fila = get_one(f"""
        SELECT COALESCE(SUM(f.total), 0) AS total,
               COUNT(*)                  AS documentos,
               COALESCE(SUM(CASE WHEN f.fecha_vencimiento < CURDATE() THEN f.total END), 0) AS vencida,
               COUNT(CASE WHEN f.fecha_vencimiento < CURDATE() THEN 1 END)                  AS documentos_vencidos
        FROM facturas f
        WHERE {where}
    """, tuple(params)) or {}

    return {
        "total":               _num(fila.get("total")),
        "vencida":             _num(fila.get("vencida")),
        "por_vencer":          _num(fila.get("total")) - _num(fila.get("vencida")),
        "documentos":          int(fila.get("documentos") or 0),
        "documentos_vencidos": int(fila.get("documentos_vencidos") or 0),
    }


def get_cartera_por_antiguedad(cod_empresa=None):
    """Cartera repartida en tramos de días vencidos."""
    condiciones = [f"f.cod_pago IN ({','.join(['%s'] * len(CARTERA))})", "f.tipo_factura <> 'NC'"]
    params = list(CARTERA)
    if cod_empresa:
        condiciones.append("f.cod_empresa = %s")
        params.append(cod_empresa)
    where = " AND ".join(condiciones)

    fila = get_one(f"""
        SELECT COALESCE(SUM(CASE WHEN DATEDIFF(CURDATE(), f.fecha_vencimiento) <= 0
                                 THEN f.total END), 0) AS por_vencer,
               COALESCE(SUM(CASE WHEN DATEDIFF(CURDATE(), f.fecha_vencimiento) BETWEEN 1 AND 30
                                 THEN f.total END), 0) AS d1_30,
               COALESCE(SUM(CASE WHEN DATEDIFF(CURDATE(), f.fecha_vencimiento) BETWEEN 31 AND 60
                                 THEN f.total END), 0) AS d31_60,
               COALESCE(SUM(CASE WHEN DATEDIFF(CURDATE(), f.fecha_vencimiento) BETWEEN 61 AND 90
                                 THEN f.total END), 0) AS d61_90,
               COALESCE(SUM(CASE WHEN DATEDIFF(CURDATE(), f.fecha_vencimiento) > 90
                                 THEN f.total END), 0) AS d90_mas
        FROM facturas f
        WHERE {where}
    """, tuple(params)) or {}

    return [
        {"tramo": "Por vencer",   "valor": _num(fila.get("por_vencer"))},
        {"tramo": "1–30 días",    "valor": _num(fila.get("d1_30"))},
        {"tramo": "31–60 días",   "valor": _num(fila.get("d31_60"))},
        {"tramo": "61–90 días",   "valor": _num(fila.get("d61_90"))},
        {"tramo": "Más de 90",    "valor": _num(fila.get("d90_mas"))},
    ]


def get_cartera_detalle(cod_empresa=None, solo_vencida=False, limite=50):
    """Documentos por cobrar, los más vencidos primero."""
    condiciones = [f"f.cod_pago IN ({','.join(['%s'] * len(CARTERA))})", "f.tipo_factura <> 'NC'"]
    params = list(CARTERA)
    if cod_empresa:
        condiciones.append("f.cod_empresa = %s")
        params.append(cod_empresa)
    if solo_vencida:
        condiciones.append("f.fecha_vencimiento < CURDATE()")
    params.append(int(limite))

    return get_many(f"""
        SELECT f.cod_factura, f.numero_factura, f.fecha, f.fecha_vencimiento, f.total,
               f.tipo_factura,
               c.full_name AS cliente,
               pf.status   AS estado_pago,
               DATEDIFF(CURDATE(), f.fecha_vencimiento) AS dias_vencido
        FROM facturas f
            LEFT JOIN customers c      ON f.cod_cliente = c.customer_id
            LEFT JOIN pagos_factura pf ON f.cod_pago    = pf.cod_pago_factura
        WHERE {' AND '.join(condiciones)}
        ORDER BY dias_vencido DESC, f.total DESC
        LIMIT %s
    """, tuple(params))


# ── Series y rankings ───────────────────────────────────────────────────────

def get_serie_ventas(desde, hasta, cod_empresa=None, granularidad=None):
    """Evolución de la venta neta. Agrupa por día en rangos cortos y por mes en
    rangos largos, para que la gráfica no quede ilegible."""
    if granularidad is None:
        dias = (date.fromisoformat(str(hasta)) - date.fromisoformat(str(desde))).days
        granularidad = "dia" if dias <= 92 else "mes"

    # Sin DATE_FORMAT a propósito: ver la nota del encabezado del módulo.
    periodo = ("DATE(f.fecha)" if granularidad == "dia"
               else "DATE(f.fecha - INTERVAL (DAY(f.fecha) - 1) DAY)")

    where, params = _filtro(desde, hasta, cod_empresa)
    filas = get_many(f"""
        SELECT {periodo}                                                     AS periodo,
               COALESCE(SUM(f.total), 0)                                     AS ventas,
               COALESCE(SUM(CASE WHEN f.cod_pago = 1 THEN f.total END), 0)   AS cobrado,
               COUNT(CASE WHEN f.tipo_factura = 'FV' THEN 1 END)             AS facturas
        FROM facturas f
        WHERE {where}
        GROUP BY periodo
        ORDER BY periodo
    """, tuple(params))

    return {"granularidad": granularidad, "puntos": filas}


def get_top_productos(desde, hasta, cod_empresa=None, limite=8):
    """Productos que más facturan en el periodo. Solo FV: las NC ya se reflejan
    en el inventario y contarlas aquí ensuciaría el ranking comercial."""
    where, params = _filtro(desde, hasta, cod_empresa)
    params.append(int(limite))
    return get_many(f"""
        SELECT p.cod_producto, p.nombre, p.sku,
               SUM(d.cantidad)              AS unidades,
               COALESCE(SUM(d.subtotal), 0) AS ingresos
        FROM detalle_factura d
            JOIN facturas  f ON d.cod_factura  = f.cod_factura
            JOIN productos p ON d.cod_producto = p.cod_producto
        WHERE {where} AND f.tipo_factura = 'FV'
        GROUP BY p.cod_producto, p.nombre, p.sku
        ORDER BY ingresos DESC
        LIMIT %s
    """, tuple(params))


def get_top_clientes(desde, hasta, cod_empresa=None, limite=8):
    """Clientes por facturación neta del periodo."""
    where, params = _filtro(desde, hasta, cod_empresa)
    params.append(int(limite))
    return get_many(f"""
        SELECT c.customer_id, c.full_name AS cliente, c.document_number,
               COALESCE(SUM(f.total), 0)                        AS facturado,
               COUNT(CASE WHEN f.tipo_factura = 'FV' THEN 1 END) AS facturas
        FROM facturas f
            JOIN customers c ON f.cod_cliente = c.customer_id
        WHERE {where}
        GROUP BY c.customer_id, c.full_name, c.document_number
        ORDER BY facturado DESC
        LIMIT %s
    """, tuple(params))


def get_ventas_por_metodo_pago(desde, hasta, cod_empresa=None):
    where, params = _filtro(desde, hasta, cod_empresa)
    return get_many(f"""
        SELECT COALESCE(mp.descripcion, 'Sin método') AS metodo,
               COALESCE(SUM(f.total), 0)              AS total,
               COUNT(*)                               AS documentos
        FROM facturas f
            LEFT JOIN metodos_pago mp ON f.cod_metodo_pago = mp.cod_pago
        WHERE {where} AND f.tipo_factura = 'FV'
        GROUP BY mp.descripcion
        ORDER BY total DESC
    """, tuple(params))


def get_ventas_por_estado(desde, hasta, cod_empresa=None):
    """Reparto de la facturación según el estado de cobro."""
    where, params = _filtro(desde, hasta, cod_empresa)
    return get_many(f"""
        SELECT COALESCE(pf.status, 'Sin estado') AS estado,
               COALESCE(SUM(f.total), 0)         AS total,
               COUNT(*)                          AS documentos
        FROM facturas f
            LEFT JOIN pagos_factura pf ON f.cod_pago = pf.cod_pago_factura
        WHERE {where} AND f.tipo_factura = 'FV'
        GROUP BY pf.status
        ORDER BY total DESC
    """, tuple(params))


def get_ventas_por_usuario(desde, hasta, cod_empresa=None, limite=10):
    """Facturación por quien emitió el documento."""
    where, params = _filtro(desde, hasta, cod_empresa)
    params.append(int(limite))
    return get_many(f"""
        SELECT COALESCE(u.nombre, 'Sin usuario') AS usuario,
               u.rol,
               COALESCE(SUM(f.total), 0)         AS total,
               COUNT(CASE WHEN f.tipo_factura = 'FV' THEN 1 END) AS facturas
        FROM facturas f
            LEFT JOIN usuarios u ON f.cod_usuario = u.cod_usuario
        WHERE {where}
        GROUP BY u.nombre, u.rol
        ORDER BY total DESC
        LIMIT %s
    """, tuple(params))


def get_impuestos_recaudados(desde, hasta, cod_empresa=None):
    """Base gravable e impuesto por tarifa, para el resumen tributario.

    Dos correcciones sobre la suma ingenua de las líneas:

    * El IVA de las líneas no suma lo que declara la factura cuando hay descuento
      global: ese descuento rebaja la base y `facturas.total_impuestos` ya viene
      prorrateado. Se aplica el mismo factor a cada línea.
    * Las notas débito llevan impuesto pero no tienen líneas de detalle, así que
      un reporte construido solo sobre `detalle_factura` las omitiría. Se suman
      aparte, con la tarifa efectiva que declara el documento.
    """
    where, params = _filtro(desde, hasta, cod_empresa, alias="origen")
    return get_many(f"""
        SELECT origen.tarifa                                AS tarifa,
               COALESCE(SUM(origen.base_gravable), 0)       AS base_gravable,
               COALESCE(SUM(origen.impuesto), 0)            AS impuesto,
               COUNT(DISTINCT origen.cod_factura)           AS documentos
        FROM (
            SELECT d.impuesto_porcentaje        AS tarifa,
                   d.subtotal * f.factor        AS base_gravable,
                   d.impuesto_valor * f.factor  AS impuesto,
                   f.cod_factura, f.fecha, f.cod_empresa
            FROM detalle_factura d
                JOIN (
                    SELECT fa.cod_factura, fa.fecha, fa.cod_empresa,
                           CASE WHEN l.iva_lineas <> 0
                                THEN fa.total_impuestos / l.iva_lineas
                                ELSE 1 END AS factor
                    FROM facturas fa
                        JOIN (SELECT cod_factura, SUM(impuesto_valor) AS iva_lineas
                              FROM detalle_factura GROUP BY cod_factura) l
                          ON l.cod_factura = fa.cod_factura
                ) f ON d.cod_factura = f.cod_factura

            UNION ALL

            SELECT COALESCE((
                       -- La nota débito calcula su IVA con la tasa promedio de la
                       -- factura origen, que con descuentos globales no cae exacta
                       -- en 19%. Se declara bajo la tarifa real de esa factura y no
                       -- bajo un 18,34% que no existe en la normativa.
                       SELECT d3.impuesto_porcentaje
                       FROM detalle_factura d3
                       WHERE d3.cod_factura = nd.cod_factura_referencia
                       GROUP BY d3.impuesto_porcentaje
                       ORDER BY SUM(ABS(d3.impuesto_valor)) DESC
                       LIMIT 1),
                     ROUND(nd.total_impuestos / NULLIF(nd.subtotal, 0) * 100, 0)
                   ) AS tarifa,
                   nd.subtotal, nd.total_impuestos,
                   nd.cod_factura, nd.fecha, nd.cod_empresa
            FROM facturas nd
            WHERE nd.total_impuestos <> 0
              AND NOT EXISTS (SELECT 1 FROM detalle_factura d2
                              WHERE d2.cod_factura = nd.cod_factura)
        ) origen
        WHERE {where}
        GROUP BY origen.tarifa
        ORDER BY origen.tarifa DESC
    """, tuple(params))


def get_documentos_emitidos(desde, hasta, cod_empresa=None):
    """Conteo por tipo de documento electrónico (FV / NC / ND)."""
    where, params = _filtro(desde, hasta, cod_empresa)
    return get_many(f"""
        SELECT f.tipo_factura            AS tipo,
               COUNT(*)                  AS documentos,
               COALESCE(SUM(f.total), 0) AS total
        FROM facturas f
        WHERE {where}
        GROUP BY f.tipo_factura
        ORDER BY documentos DESC
    """, tuple(params))


def get_empresas_disponibles():
    """Empresas emisoras, para el selector del panel."""
    return get_many("SELECT cod_empresa, nombre, nit FROM empresas ORDER BY nombre")
