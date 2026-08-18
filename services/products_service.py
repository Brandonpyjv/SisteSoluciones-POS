from database import create_connection, execute_query, execute_update, get_one
from services.validaciones import (Validador, bandera, entero, precio, sku as validar_sku,
                                   texto)


def validar_producto(datos: dict, product_id: int = None) -> Validador:
    """Valida un producto venga del formulario o de la API."""
    v = Validador()

    v.campo("sku", validar_sku, datos.get("sku"))
    v.campo("nombre", texto, datos.get("nombre"), maximo=150, minimo=2)
    v.campo("descripcion", texto, datos.get("descripcion"), maximo=500, requerido=False)
    v.campo("codigo_barras", texto, datos.get("codigo_barras"), maximo=60, requerido=False)
    v.campo("unidad_medida", texto, datos.get("unidad_medida") or "C62", maximo=10)

    # El precio es lo que multiplica la cantidad en cada línea de factura: un valor
    # negativo se convierte en un total negativo, o sea en dinero inventado.
    v.campo("precio_unitario", precio, datos.get("precio_unitario"))
    v.campo("stock", entero, datos.get("stock") if datos.get("stock") not in (None, "") else 0)
    v.campo("stock_minimo", entero,
            datos.get("stock_minimo") if datos.get("stock_minimo") not in (None, "") else 0)
    v.campo("activo", bandera, datos.get("activo"))
    v.campo("controla_stock", bandera, datos.get("controla_stock"))

    v.campo("cod_impuesto", entero, datos.get("cod_impuesto"), minimo=1)
    if "cod_impuesto" in v.datos and not get_one(
            "SELECT cod_impuesto FROM impuestos WHERE cod_impuesto = %s",
            (v.datos["cod_impuesto"],)):
        v.errores["cod_impuesto"] = "El impuesto seleccionado no existe"

    # `sku` tiene índice único: sin esto, repetirlo lanza un error de integridad y
    # la persona ve una pantalla de error en lugar de saber cuál producto lo ocupa.
    if "sku" in v.datos:
        duplicado = get_one(
            "SELECT cod_producto, nombre FROM productos WHERE sku = %s", (v.datos["sku"],))
        if duplicado and duplicado["cod_producto"] != product_id:
            v.errores["sku"] = f"Ese SKU ya lo usa «{duplicado['nombre']}»"

    return v


def get_all_products_detailed():
    db = create_connection()
    cursor = db.cursor(dictionary=True)
    query = """
            SELECT p.cod_producto,
                   p.sku,
                   p.nombre,
                   p.descripcion,
                   p.precio_unitario,
                   p.stock,
                   p.stock_minimo,
                   p.controla_stock,
                   p.cod_impuesto,
                   p.unidad_medida,
                   p.codigo_barras,
                   p.activo,
                   p.tipo_item,
                   i.descripcion AS tax_name,
                   i.porcentaje  AS tax_porcentaje
            FROM productos p
                     LEFT JOIN impuestos i ON p.cod_impuesto = i.cod_impuesto
            ORDER BY p.nombre
            """
    cursor.execute(query)
    result = cursor.fetchall()
    cursor.close()
    db.close()
    return result


def get_product_by_id(product_id: int):
    return get_one("SELECT * FROM productos WHERE cod_producto = %s", (product_id,))


def create_product(sku: str, nombre: str, descripcion: str, precio_unitario: float,
                   stock: int, stock_minimo: int, cod_impuesto: int,
                   unidad_medida: str, codigo_barras: str, activo: int,
                   controla_stock: int = 1):
    query = """INSERT INTO productos (sku, nombre, descripcion, precio_unitario, stock, stock_minimo,
               cod_impuesto, unidad_medida, codigo_barras, activo, controla_stock)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
    return execute_query(query, (sku, nombre, descripcion, precio_unitario, stock, stock_minimo,
                                  cod_impuesto, unidad_medida, codigo_barras or None, activo,
                                  controla_stock))


def update_product(product_id: int, sku: str, nombre: str, descripcion: str,
                   precio_unitario: float, stock: int, stock_minimo: int,
                   cod_impuesto: int, unidad_medida: str, codigo_barras: str, activo: int,
                   controla_stock: int = 1):
    query = """UPDATE productos SET sku=%s, nombre=%s, descripcion=%s, precio_unitario=%s,
               stock=%s, stock_minimo=%s, cod_impuesto=%s, unidad_medida=%s,
               codigo_barras=%s, activo=%s, controla_stock=%s WHERE cod_producto=%s"""
    return execute_update(query, (sku, nombre, descripcion, precio_unitario, stock, stock_minimo,
                                   cod_impuesto, unidad_medida, codigo_barras or None, activo,
                                   controla_stock, product_id))


def delete_product(product_id: int):
    return execute_update("DELETE FROM productos WHERE cod_producto = %s", (product_id,))
