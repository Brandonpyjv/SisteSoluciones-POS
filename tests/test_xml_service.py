"""Pruebas del XML UBL en los puntos donde el emisor cambia la salida."""
import re

import pytest

from services.documento_canonico import CLAVES_EMISOR
from services.xml_service import generate_invoice_xml


def emisor(**cambios):
    base = {c: None for c in CLAVES_EMISOR}
    base.update(nombre="Siste Soluciones", nit="901234567", dv="8",
                prefijo_factura="SETP", regimen_tributario="RESPONSABLE_IVA",
                cod_municipio="54001")
    base.update(cambios)
    return base


def generar(**cambios):
    factura = {"numero_factura": "SETP1", "cufe": "abc", "subtotal": 100000,
               "total_impuestos": 19000, "total": 119000, "total_descuentos": 0}
    return generate_invoice_xml(factura, [], emisor(**cambios))


def etiqueta(xml, nombre):
    encontrado = re.search(rf"<{nombre}>([^<]*)</{nombre}>", xml)
    return encontrado.group(1) if encontrado else None


@pytest.mark.parametrize("regimen,esperado", [
    ("RESPONSABLE_IVA", "O-23"),
    ("GRAN_CONTRIBUYENTE", "O-23"),
    # Contiene la subcadena «RESPONSABLE»; la negación tiene que ganar.
    ("NO_RESPONSABLE_IVA", "O-47"),
])
def test_el_regimen_del_emisor_define_el_nivel_tributario(regimen, esperado):
    assert etiqueta(generar(regimen_tributario=regimen), "cbc:TaxLevelCode") == esperado


def test_sin_regimen_se_asume_responsable_de_iva():
    assert etiqueta(generar(regimen_tributario=None), "cbc:TaxLevelCode") == "O-23"


@pytest.mark.parametrize("tipo,esperado", [
    ("13", "13"),   # cédula
    ("31", "31"),   # NIT: antes se mandaba como 13 y la DIAN lo veía como persona
    ("41", "41"),   # pasaporte
    ("ZZ", "13"),   # desconocido: cae al caso mayoritario en lugar de romper el XML
])
def test_el_tipo_de_documento_del_cliente_viaja_como_codigo_dian(tipo, esperado):
    factura = {"numero_factura": "SETP1", "document_number": "9008765432",
               "document_type": tipo, "subtotal": 100000, "total": 119000}
    xml = generate_invoice_xml(factura, [], emisor())
    encontrados = set(re.findall(r'schemeName="([^"]+)">9008765432', xml))
    assert encontrados == {esperado}


def test_el_prefijo_del_emisor_llega_al_xml():
    assert etiqueta(generar(prefijo_factura="SETP"), "sts:Prefix") == "SETP"
    assert etiqueta(generar(prefijo_factura="FE"), "sts:Prefix") == "FE"
