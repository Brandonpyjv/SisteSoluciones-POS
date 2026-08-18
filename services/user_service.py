from database import get_all_from_table, execute_query, execute_update, get_one
from auth import ROLE_HIERARCHY, hash_password
from services.validaciones import (Validador, contrasena as validar_contrasena,
                                   correo as validar_correo, entero, nombre_persona,
                                   opcion)


def validar_usuario(datos: dict, user_id: int = None) -> Validador:
    """Valida un usuario del sistema.

    `user_id` se pasa al editar: sirve para que el usuario no choque consigo
    mismo en la comprobación del correo, y para saber que la contraseña puede
    venir vacía porque se está conservando la actual.
    """
    v = Validador()

    v.campo("nombre", nombre_persona, datos.get("nombre"))
    v.campo("correo", validar_correo, datos.get("correo"), requerido=True)
    v.campo("rol", opcion, datos.get("rol"), tuple(ROLE_HIERARCHY))
    # Al crear es obligatoria; al editar, vacía significa «déjala como está».
    v.campo("contrasena", validar_contrasena, datos.get("contrasena"),
            requerido=user_id is None)

    # `correo` tiene índice único y además es con lo que se inicia sesión: dos
    # cuentas con el mismo correo dejarían una de ellas inaccesible.
    if "correo" in v.datos:
        duplicado = get_one(
            "SELECT cod_usuario, nombre, activo FROM usuarios WHERE correo = %s",
            (v.datos["correo"],))
        if duplicado and duplicado["cod_usuario"] != user_id:
            detalle = "" if duplicado["activo"] else " (inactivo)"
            v.errores["correo"] = f"Ese correo ya lo usa {duplicado['nombre']}{detalle}"

    cod_empresa = datos.get("cod_empresa")
    if cod_empresa not in (None, "", "None"):
        v.campo("cod_empresa", entero, cod_empresa, minimo=1)
        if "cod_empresa" in v.datos and not get_one(
                "SELECT cod_empresa FROM empresas WHERE cod_empresa = %s",
                (v.datos["cod_empresa"],)):
            v.errores["cod_empresa"] = "La empresa seleccionada no existe"
    else:
        v.datos["cod_empresa"] = None

    return v


def get_all_users():
    from database import get_many
    return get_many(
        "SELECT u.*, e.nombre AS empresa_nombre "
        "FROM usuarios u LEFT JOIN empresas e ON u.cod_empresa = e.cod_empresa "
        "WHERE u.activo = 1 "
        "ORDER BY u.nombre"
    )


def get_user_by_id(user_id: int):
    return get_one(
        "SELECT u.*, e.nombre AS empresa_nombre "
        "FROM usuarios u LEFT JOIN empresas e ON u.cod_empresa = e.cod_empresa "
        "WHERE u.cod_usuario = %s",
        (user_id,)
    )


def get_user_by_email(correo: str):
    return get_one(
        "SELECT u.*, e.nombre AS empresa_nombre "
        "FROM usuarios u LEFT JOIN empresas e ON u.cod_empresa = e.cod_empresa "
        "WHERE u.correo = %s",
        (correo,)
    )


def create_user(nombre: str, correo: str, contrasena: str, rol: str, cod_empresa: int = None):
    hashed = hash_password(contrasena)
    query = "INSERT INTO usuarios (nombre, correo, contrasena, rol, cod_empresa) VALUES (%s, %s, %s, %s, %s)"
    return execute_query(query, (nombre, correo, hashed, rol, cod_empresa))


def update_user(user_id: int, nombre: str, correo: str, rol: str, contrasena: str = None, cod_empresa: int = None):
    if contrasena:
        hashed = hash_password(contrasena)
        query = "UPDATE usuarios SET nombre=%s, correo=%s, rol=%s, contrasena=%s, cod_empresa=%s WHERE cod_usuario=%s"
        return execute_update(query, (nombre, correo, rol, hashed, cod_empresa, user_id))
    else:
        query = "UPDATE usuarios SET nombre=%s, correo=%s, rol=%s, cod_empresa=%s WHERE cod_usuario=%s"
        return execute_update(query, (nombre, correo, rol, cod_empresa, user_id))


def update_user_photo(user_id: int, foto: str = None):
    """Asocia (o quita, con None) el archivo de foto de perfil."""
    return execute_update("UPDATE usuarios SET foto = %s WHERE cod_usuario = %s",
                          (foto, user_id))


def delete_user(user_id: int):
    return execute_update("UPDATE usuarios SET activo = 0 WHERE cod_usuario = %s", (user_id,))
