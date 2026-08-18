"""
Pruebas de la aritmética tributaria.

Los valores esperados están escritos a mano, no copiados de la salida del
código: una prueba que se limita a repetir lo que el programa devuelve no
verifica nada. La última prueba compara contra una transcripción literal del
cálculo que vivía dentro de routes/invoice.py antes de extraerlo, para dejar
constancia de que el refactor no movió ni un peso.
"""
import pytest

from services.calculo_documento import calcular_documento, calcular_linea


def linea(cantidad, precio, desc_pct=0, imp_pct=0, **extra):
    return {
        "cantidad": cantidad,
        "precio_unitario": precio,
        "descuento_porcentaje": desc_pct,
        "impuesto_porcentaje": imp_pct,
        **extra,
    }


# ── Línea individual ────────────────────────────────────────────────────────

def test_linea_simple_con_iva():
    r = calcular_linea(linea(2, 189000, imp_pct=19))
    assert r["valor_bruto"] == 378000
    assert r["descuento_valor"] == 0
    assert r["subtotal"] == 378000
    assert r["impuesto_valor"] == 71820


def test_linea_con_descuento_propio():
    r = calcular_linea(linea(2, 189000, desc_pct=5, imp_pct=19))
    assert r["descuento_valor"] == 18900
    assert r["subtotal"] == 359100
    assert r["impuesto_valor"] == 68229


def test_linea_exenta_no_genera_impuesto():
    r = calcular_linea(linea(3, 12000, imp_pct=0))
    assert r["subtotal"] == 36000
    assert r["impuesto_valor"] == 0


def test_la_linea_conserva_las_claves_ajenas():
    r = calcular_linea(linea(1, 1000, cod_producto=42, sku="TEC-014"))
    assert r["cod_producto"] == 42
    assert r["sku"] == "TEC-014"


# ── Documento completo ──────────────────────────────────────────────────────

def test_documento_de_una_linea():
    r = calcular_documento([linea(2, 189000, imp_pct=19)])
    assert r["subtotal_bruto"] == 378000
    assert r["total_descuentos"] == 0
    assert r["subtotal"] == 378000
    assert r["total_impuestos"] == 71820
    assert r["total"] == 449820


def test_tarifas_mixtas_en_el_mismo_documento():
    r = calcular_documento([
        linea(2, 50000, imp_pct=19),              # base 100000 · iva 19000
        linea(1, 30000, desc_pct=10, imp_pct=5),  # base  27000 · iva  1350
        linea(4, 8000, imp_pct=0),                # base  32000 · iva     0
    ])
    assert r["subtotal_bruto"] == 162000
    assert r["total_descuentos"] == 3000
    assert r["subtotal"] == 159000
    assert r["total_impuestos"] == 20350
    assert r["total"] == 179350


def test_descuento_global_prorratea_el_iva():
    """Con una sola tarifa el prorrateo debe dar exactamente el IVA de la base neta."""
    r = calcular_documento([linea(1, 100000, imp_pct=19)], descuento_global=10000)
    assert r["total_descuentos"] == 10000
    assert r["subtotal"] == 90000
    # 90000 × 19 % = 17100, no los 19000 que salían antes del descuento
    assert r["total_impuestos"] == 17100
    assert r["total"] == 107100


def test_descuento_global_con_tarifas_mixtas():
    r = calcular_documento([
        linea(2, 50000, imp_pct=19),
        linea(1, 30000, desc_pct=10, imp_pct=5),
        linea(4, 8000, imp_pct=0),
    ], descuento_global=9000)
    assert r["total_descuentos"] == 12000
    assert r["subtotal"] == 150000
    # 20350 − round(20350 × 9000/159000, 2) = 20350 − 1151.89
    assert r["total_impuestos"] == 19198.11
    assert r["total"] == 169198.11


def test_descuento_global_sobre_documento_sin_base_no_divide_por_cero():
    r = calcular_documento([], descuento_global=5000)
    assert r["total_impuestos"] == 0
    assert r["subtotal"] == -5000


def test_valores_ausentes_o_vacios_se_tratan_como_cero():
    r = calcular_documento([{"cantidad": 2, "precio_unitario": 1000}])
    assert r["total_impuestos"] == 0
    assert r["total"] == 2000

    r = calcular_documento([
        {"cantidad": 1, "precio_unitario": 1000,
         "descuento_porcentaje": None, "impuesto_porcentaje": ""},
    ])
    assert r["total"] == 1000


# ── Equivalencia con la implementación anterior ─────────────────────────────

def _calculo_anterior(lineas, valor_descuento_factura=0.0):
    """Transcripción literal del cálculo que estaba dentro del POST /invoice/new.

    Se conserva aquí, y solo aquí, como oráculo del refactor.
    """
    subtotal_bruto = 0.0
    total_descuentos = 0.0
    total_impuestos = 0.0

    for l in lineas:
        tax_pct = float(l.get("impuesto_porcentaje") or 0)
        precio = float(l["precio_unitario"])
        cant = int(l["cantidad"])
        desc_pct = float(l.get("descuento_porcentaje") or 0) or 0.0

        valor_bruto = precio * cant
        desc_valor = round(valor_bruto * desc_pct / 100, 2)
        base_imponible = valor_bruto - desc_valor
        imp_valor = round(base_imponible * tax_pct / 100, 2)

        subtotal_bruto += valor_bruto
        total_descuentos += desc_valor
        total_impuestos += imp_valor

    base_neta_productos = subtotal_bruto - total_descuentos
    if base_neta_productos > 0 and valor_descuento_factura > 0:
        ratio = valor_descuento_factura / base_neta_productos
        ajuste_iva = round(total_impuestos * ratio, 2)
        total_impuestos = round(total_impuestos - ajuste_iva, 2)

    total_descuentos = round(total_descuentos + valor_descuento_factura, 2)
    subtotal_neto = round(subtotal_bruto - total_descuentos, 2)
    total = round(subtotal_neto + total_impuestos, 2)

    return {
        "total_descuentos": round(total_descuentos, 2),
        "subtotal": subtotal_neto,
        "total_impuestos": round(total_impuestos, 2),
        "total": total,
    }


ESCENARIOS = [
    ([linea(1, 100000, imp_pct=19)], 0),
    ([linea(1, 100000, imp_pct=19)], 10000),
    ([linea(3, 33333, imp_pct=19)], 0),
    ([linea(3, 33333, imp_pct=19)], 7777),
    ([linea(7, 14990, desc_pct=12.5, imp_pct=19)], 0),
    ([linea(7, 14990, desc_pct=12.5, imp_pct=19)], 3333),
    ([linea(2, 50000, imp_pct=19), linea(1, 30000, desc_pct=10, imp_pct=5),
      linea(4, 8000, imp_pct=0)], 0),
    ([linea(2, 50000, imp_pct=19), linea(1, 30000, desc_pct=10, imp_pct=5),
      linea(4, 8000, imp_pct=0)], 9000),
    ([linea(1, 999999, desc_pct=33.33, imp_pct=19),
      linea(11, 1234, desc_pct=0, imp_pct=5)], 12345),
]


@pytest.mark.parametrize("lineas,descuento_global", ESCENARIOS)
def test_los_totales_coinciden_con_el_calculo_anterior(lineas, descuento_global):
    nuevo = calcular_documento(lineas, descuento_global)
    viejo = _calculo_anterior(lineas, descuento_global)

    for campo in ("subtotal", "total_descuentos", "total_impuestos", "total"):
        assert nuevo[campo] == viejo[campo], campo
