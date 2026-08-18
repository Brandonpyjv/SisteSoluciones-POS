"""Pruebas del contrato de entrada de pdf_service y xml_service."""
from services.documento_canonico import (CLAVES_CABECERA, CLAVES_EMISOR, CLAVES_LINEA,
                                         claves_faltantes, emisor_desde_empresa,
                                         emisor_desde_factura)


def test_los_alias_de_la_consulta_se_traducen_al_nombre_de_columna():
    """Recortar el prefijo «empresa_» no basta: estos dos alias no coinciden."""
    inv = {
        "empresa_regimen": "GRAN_CONTRIBUYENTE",
        "empresa_prefijo": "SETP",
        "empresa_nit": "900112144",
    }
    emisor = emisor_desde_factura(inv)

    assert emisor["regimen_tributario"] == "GRAN_CONTRIBUYENTE"
    assert emisor["prefijo_factura"] == "SETP"
    assert emisor["nit"] == "900112144"


def test_el_emisor_extraido_trae_el_contrato_completo():
    emisor = emisor_desde_factura({"empresa_nit": "900112144"})
    assert set(emisor) == CLAVES_EMISOR


def test_el_emisor_desde_empresa_rellena_lo_que_no_selecciono_la_consulta():
    emisor = emisor_desde_empresa({"nit": "900112144", "nombre": "Siste Soluciones"})
    assert set(emisor) == CLAVES_EMISOR
    assert emisor["nit"] == "900112144"
    assert emisor["resolucion_dian"] is None


def test_no_hay_claves_faltantes_cuando_el_documento_esta_completo():
    cabecera = {c: None for c in CLAVES_CABECERA}
    linea = {c: None for c in CLAVES_LINEA}
    emisor = {c: None for c in CLAVES_EMISOR}
    assert claves_faltantes(cabecera, [linea], emisor) == {}


def test_se_reportan_las_claves_ausentes_de_cada_pieza():
    cabecera = {c: None for c in CLAVES_CABECERA if c != "cufe"}
    linea_ok = {c: None for c in CLAVES_LINEA}
    linea_mala = {c: None for c in CLAVES_LINEA if c != "impuesto_codigo_dian"}
    emisor = {c: None for c in CLAVES_EMISOR if c != "resolucion_dian"}

    faltan = claves_faltantes(cabecera, [linea_ok, linea_mala], emisor)

    assert faltan["cabecera"] == ["cufe"]
    assert faltan["lineas"] == {1: ["impuesto_codigo_dian"]}
    assert faltan["emisor"] == ["resolucion_dian"]


def test_una_clave_presente_en_nulo_cuenta_como_presente():
    """El vencimiento de una factura de contado va vacío y eso no es un error."""
    cabecera = {c: None for c in CLAVES_CABECERA}
    cabecera["fecha_vencimiento"] = None
    assert "cabecera" not in claves_faltantes(cabecera)
