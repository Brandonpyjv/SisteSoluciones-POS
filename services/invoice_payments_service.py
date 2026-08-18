from database import get_all_from_table, execute_query, execute_update, get_one
from services.validaciones import Validador, texto


def validar_estado_pago(datos: dict, payment_id: int = None) -> Validador:
    v = Validador()
    v.campo("status", texto, datos.get("status"), maximo=40, minimo=2)

    if "status" in v.datos:
        duplicado = get_one(
            "SELECT cod_pago_factura FROM pagos_factura WHERE LOWER(status) = LOWER(%s)",
            (v.datos["status"],))
        if duplicado and duplicado["cod_pago_factura"] != payment_id:
            v.errores["status"] = "Ya existe un estado de pago con ese nombre"

    return v


def get_all_invoice_payments():
    return get_all_from_table('pagos_factura')


def get_invoice_payment_by_id(payment_id: int):
    return get_one("SELECT * FROM pagos_factura WHERE cod_pago_factura = %s", (payment_id,))


def create_invoice_payment(status: str):
    query = "INSERT INTO pagos_factura (status) VALUES (%s)"
    return execute_query(query, (status,))


def update_invoice_payment(payment_id: int, status: str):
    query = "UPDATE pagos_factura SET status=%s WHERE cod_pago_factura=%s"
    return execute_update(query, (status, payment_id))


def delete_invoice_payment(payment_id: int):
    return execute_update("DELETE FROM pagos_factura WHERE cod_pago_factura = %s", (payment_id,))
