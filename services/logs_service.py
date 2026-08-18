from database import create_connection

def get_all_logs():
    db = create_connection()
    cursor = db.cursor(dictionary=True)
    query = """
            SELECT l.id_log,
                   l.fecha,
                   l.accion,
                   l.descripcion,
                   u.nombre AS cod_usuario
            FROM logs l
                     LEFT JOIN usuarios u ON l.cod_usuario = u.cod_usuario
            """

    cursor.execute(query)
    result = cursor.fetchall()
    cursor.close()
    db.close()
    return result

