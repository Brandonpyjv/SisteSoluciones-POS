"""
Aritmética tributaria de un documento electrónico.

Este módulo es deliberadamente puro: no abre conexiones, no lee sesión y no
sabe de dónde vienen las líneas. Esa independencia es lo que permite que la
misma implementación alimente el formulario web —donde los precios y el IVA
salen de nuestra tabla `productos`— y la API de integración, donde el sistema
externo envía sus propios ítems con sus propias tarifas.

Es también el único lugar del proyecto donde vive el prorrateo del IVA sobre el
descuento global, que es la regla más fácil de implementar mal.
"""


def _num(valor, defecto=0.0) -> float:
    try:
        return float(valor)
    except (TypeError, ValueError):
        return defecto


def calcular_linea(linea: dict) -> dict:
    """Calcula una línea y devuelve una copia con los valores derivados.

    Espera `cantidad`, `precio_unitario` y, opcionalmente,
    `descuento_porcentaje` e `impuesto_porcentaje`. Las claves de entrada se
    devuelven tal como llegaron —incluidas las ajenas al cálculo, como
    cod_producto o sku— y solo se agregan las derivadas: quien llama sigue
    viendo los tipos que envió.
    """
    cantidad = _num(linea.get("cantidad"))
    precio = _num(linea.get("precio_unitario"))
    desc_pct = _num(linea.get("descuento_porcentaje"))
    imp_pct = _num(linea.get("impuesto_porcentaje"))

    valor_bruto = precio * cantidad
    descuento_valor = round(valor_bruto * desc_pct / 100, 2)
    base_gravable = valor_bruto - descuento_valor
    impuesto_valor = round(base_gravable * imp_pct / 100, 2)

    return {
        **linea,
        "valor_bruto": valor_bruto,
        "descuento_valor": descuento_valor,
        # `subtotal` es el nombre que usa la columna en detalle_factura.
        "subtotal": base_gravable,
        "impuesto_valor": impuesto_valor,
    }


def calcular_documento(lineas, descuento_global: float = 0.0) -> dict:
    """Calcula las líneas y los totales de un documento.

    `descuento_global` es un valor en pesos, no un porcentaje: es un descuento
    sobre el total de la factura, aparte de los descuentos por línea.

    Devuelve las líneas ya calculadas y los cinco totales que van a la cabecera:
    subtotal_bruto, total_descuentos, subtotal (base gravable neta),
    total_impuestos y total.
    """
    calculadas = [calcular_linea(l) for l in lineas]

    subtotal_bruto = sum(l["valor_bruto"] for l in calculadas)
    total_descuentos = sum(l["descuento_valor"] for l in calculadas)
    total_impuestos = sum(l["impuesto_valor"] for l in calculadas)

    descuento_global = _num(descuento_global)

    # El descuento global también reduce la base gravable, así que el IVA ya
    # calculado por línea queda de más. Se recorta en la misma proporción en
    # que el descuento reduce la base: sin esto la factura cobraría IVA sobre
    # un dinero que el cliente nunca pagó.
    base_neta_lineas = subtotal_bruto - total_descuentos
    if base_neta_lineas > 0 and descuento_global > 0:
        proporcion = descuento_global / base_neta_lineas
        total_impuestos = round(total_impuestos - round(total_impuestos * proporcion, 2), 2)

    total_descuentos = round(total_descuentos + descuento_global, 2)
    subtotal = round(subtotal_bruto - total_descuentos, 2)
    total = round(subtotal + total_impuestos, 2)

    return {
        "lineas": calculadas,
        "subtotal_bruto": round(subtotal_bruto, 2),
        "total_descuentos": total_descuentos,
        "subtotal": subtotal,
        "total_impuestos": round(total_impuestos, 2),
        "total": total,
    }
