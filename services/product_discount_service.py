from database import create_connection

def get_all_product_discounts():
    db = create_connection()
    cursor = db.cursor(dictionary=True)

    # Eliminamos las barras invertidas; las triples comillas ya manejan el salto de línea
    query = """
            SELECT 
                p.nombre AS nombre_producto,
                d.descripcion AS descuento_aplicado,
                d.porcentaje
            FROM 
                productos p
            JOIN 
                producto_descuento pd ON p.cod_producto = pd.cod_producto
            JOIN 
                descuentos d ON pd.cod_descuento = d.cod_descuento
            WHERE 
                d.aplica_a_producto = 1;
            """

    cursor.execute(query)
    result = cursor.fetchall()
    cursor.close()
    db.close()
    return result