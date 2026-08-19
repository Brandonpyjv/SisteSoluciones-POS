"""
Emisión electrónica de una venta a través de FactuGest.

Traduce una venta de este sistema al contrato de la API y guarda lo que
responde. La venta ya existe cuando esto corre: emitir es un paso posterior, no
parte de vender. Así una caída de FactuGest no impide cobrar.
"""
from datetime import datetime

from database import execute_update, get_one, get_many
from services.factugest_client import FactugestError, emitir_factura


def _receptor(cod_cliente: int) -> dict:
    cliente = get_one(
        "SELECT c.*, m.cod_municipio FROM customers c "
        "LEFT JOIN municipios m ON c.cod_municipio = m.cod_municipio "
        "WHERE c.customer_id = %s", (cod_cliente,))
    if not cliente:
        raise FactugestError("La venta no tiene cliente asignado.",
                             codigo="sin_cliente", recuperable=False)
    return {
        # `document_type` ya guarda el código de la DIAN desde la migración 004,
        # así que no hay nada que traducir aquí.
        "tipo_documento": cliente["document_type"],
        "numero_documento": cliente["document_number"],
        "nombre": cliente["full_name"],
        "tipo_persona": cliente.get("tipo_persona") or "NATURAL",
        "regimen_tributario": cliente.get("regimen_tributario") or "NO_RESPONSABLE_IVA",
        "email": cliente.get("email") or None,
        "telefono": cliente.get("phone") or None,
        "direccion": cliente.get("address") or None,
        "cod_municipio": cliente.get("cod_municipio") or None,
    }


def _items(cod_factura: int) -> list:
    lineas = get_many(
        "SELECT d.*, p.nombre AS producto_nombre, p.sku, p.unidad_medida, "
        "       i.codigo_dian "
        "FROM detalle_factura d "
        "LEFT JOIN productos p ON d.cod_producto = p.cod_producto "
        "LEFT JOIN impuestos i ON p.cod_impuesto = i.cod_impuesto "
        "WHERE d.cod_factura = %s ORDER BY d.cod_destalle", (cod_factura,))
    if not lineas:
        raise FactugestError("La venta no tiene productos.", codigo="sin_lineas",
                             recuperable=False)
    return [{
        "codigo": l.get("sku") or None,
        "descripcion": l.get("producto_nombre") or l.get("descripcion") or "Concepto",
        "cantidad": float(l["cantidad"]),
        "precio_unitario": float(l["precio_unitario"]),
        "unidad_medida": l.get("unidad_medida") or "94",
        "descuento_porcentaje": float(l.get("descuento_porcentaje") or 0),
        "descuento_descripcion": l.get("descripcion_descuento") or None,
        "impuesto": {
            # Si el impuesto local no tiene código DIAN se manda el de IVA, que
            # es el caso de casi todo lo que vende este negocio.
            "codigo": l.get("codigo_dian") or "01",
            "porcentaje": float(l.get("impuesto_porcentaje") or 0),
        },
    } for l in lineas]


def construir_peticion(venta: dict) -> dict:
    """Arma el JSON que espera `POST /api/v1/facturas`."""
    items = _items(venta["cod_factura"])

    # El descuento de factura no se guarda aparte: es lo que sobra entre el total
    # de descuentos y la suma de los de cada línea.
    descuentos_linea = sum(
        float(l["precio_unitario"]) * float(l["cantidad"]) *
        float(l.get("descuento_porcentaje") or 0) / 100
        for l in get_many("SELECT precio_unitario, cantidad, descuento_porcentaje "
                          "FROM detalle_factura WHERE cod_factura = %s",
                          (venta["cod_factura"],)))
    descuento_global = round(float(venta.get("total_descuentos") or 0) - descuentos_linea, 2)

    forma_pago = (venta.get("forma_pago") or "CONTADO").upper()
    plazo = 0
    if forma_pago == "CREDITO" and venta.get("fecha_vencimiento"):
        vencimiento = venta["fecha_vencimiento"]
        emision = venta["fecha"]
        if hasattr(emision, "date"):
            emision = emision.date()
        plazo = max(1, (vencimiento - emision).days)

    peticion = {
        # El número interno de la venta es la llave de idempotencia: reintentar
        # no puede emitir dos facturas para la misma venta.
        "referencia_externa": venta.get("numero_factura") or f"VENTA-{venta['cod_factura']}",
        "receptor": _receptor(venta["cod_cliente"]),
        "items": items,
        "forma_pago": forma_pago,
        "plazo_dias": plazo,
        "observaciones": venta.get("observaciones") or None,
        "orden_compra": venta.get("orden_compra") or None,
        "enviar_email": False,
    }
    if descuento_global > 0.01:
        peticion["descuento_global"] = {
            "valor": descuento_global,
            "descripcion": venta.get("descripcion_descuento_factura") or None,
        }
    return peticion


def emitir(venta: dict) -> dict:
    """Emite la venta y guarda el resultado. Devuelve el documento de FactuGest."""
    peticion = construir_peticion(venta)
    try:
        documento = emitir_factura(peticion)
    except FactugestError as e:
        execute_update(
            "UPDATE facturas SET factugest_estado = %s, factugest_error = %s "
            "WHERE cod_factura = %s",
            ("ERROR", f"[{e.codigo}] {e.detalle}", venta["cod_factura"]))
        raise

    execute_update(
        "UPDATE facturas SET factugest_id=%s, factugest_numero=%s, factugest_cufe=%s, "
        "  factugest_estado=%s, factugest_qr=%s, factugest_emitida_en=%s, "
        "  factugest_error=NULL "
        "WHERE cod_factura = %s",
        (documento["id"], documento["numero"], documento.get("cufe"),
         documento["estado"], documento.get("qr"),
         datetime.now().strftime("%Y-%m-%d %H:%M:%S"), venta["cod_factura"]))
    return documento


def pendientes_de_emitir():
    """Ventas que todavía no tienen documento electrónico, o que fallaron."""
    return get_many(
        "SELECT f.cod_factura, f.numero_factura, f.fecha, f.total, "
        "       f.factugest_estado, f.factugest_error, c.full_name AS cliente "
        "FROM facturas f LEFT JOIN customers c ON f.cod_cliente = c.customer_id "
        "WHERE f.tipo_factura = 'FV' "
        "  AND (f.factugest_id IS NULL OR f.factugest_estado IN ('ERROR', 'RECHAZADO')) "
        # HISTORICO marca las ventas anteriores a la integración con FactuGest.
        # Nunca se emitieron y no tiene sentido ofrecerlas para emitir hoy.
        "  AND COALESCE(f.factugest_estado, '') <> 'HISTORICO' "
        "ORDER BY f.fecha DESC")
