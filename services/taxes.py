from database import get_all_from_table, execute_query, execute_update, get_one, get_many
from services.validaciones import (CODIGOS_IMPUESTO_DIAN, Validador, opcion, porcentaje,
                                   texto)


def validar_impuesto(datos: dict, tax_id: int = None) -> Validador:
    """Valida un impuesto del catálogo."""
    v = Validador()

    v.campo("descripcion", texto, datos.get("descripcion"), maximo=60, minimo=2)
    # La tarifa multiplica la base gravable de cada línea; fuera de 0 a 100 no es
    # un impuesto, y por encima de 100 el IVA superaría al producto.
    v.campo("porcentaje", porcentaje, datos.get("porcentaje"))

    # El código es opcional porque los impuestos ya cargados no lo tienen, pero si
    # se escribe tiene que ser uno de la DIAN: es el que viaja en el XML.
    codigo = (datos.get("codigo_dian") or "").strip().upper()
    if codigo:
        v.campo("codigo_dian", opcion, codigo, tuple(CODIGOS_IMPUESTO_DIAN))
    else:
        v.datos["codigo_dian"] = None

    return v


def get_all_invoice_taxes():
    return get_many("SELECT * FROM impuestos ORDER BY descripcion")


def get_tax_by_id(tax_id: int):
    return get_one("SELECT * FROM impuestos WHERE cod_impuesto = %s", (tax_id,))


def create_tax(descripcion: str, porcentaje: float, codigo_dian: str = ""):
    query = "INSERT INTO impuestos (descripcion, porcentaje, codigo_dian) VALUES (%s, %s, %s)"
    return execute_query(query, (descripcion, porcentaje, codigo_dian or None))


def update_tax(tax_id: int, descripcion: str, porcentaje: float, codigo_dian: str = ""):
    query = "UPDATE impuestos SET descripcion=%s, porcentaje=%s, codigo_dian=%s WHERE cod_impuesto=%s"
    return execute_update(query, (descripcion, porcentaje, codigo_dian or None, tax_id))


def delete_tax(tax_id: int):
    return execute_update("DELETE FROM impuestos WHERE cod_impuesto = %s", (tax_id,))
