from database import execute_query, execute_update, get_one, get_many
from services.validaciones import (REGIMENES_TRIBUTARIOS, TIPOS_PERSONA, Validador,
                                   correo, nombre_persona, numero_documento, opcion,
                                   razon_social, telefono, texto, tipo_documento)


def validar_cliente(datos: dict, customer_id: int = None) -> Validador:
    """Valida los datos de un cliente vengan de donde vengan.

    Vive en el servicio y no en la ruta para que la API pueda usar exactamente
    las mismas reglas cuando cree clientes. `customer_id` se pasa al editar, para
    que el cliente no choque consigo mismo en la comprobación de duplicados.
    """
    v = Validador()

    v.campo("tipo_persona", opcion, datos.get("tipo_persona"), TIPOS_PERSONA)
    v.campo("regimen_tributario", opcion, datos.get("regimen_tributario"),
            REGIMENES_TRIBUTARIOS)

    # Una empresa puede llamarse «Comercial 3M S.A.S.»; una persona no lleva
    # dígitos en el nombre. La regla depende de qué se está registrando.
    if v.datos.get("tipo_persona") == "JURIDICA":
        v.campo("full_name", razon_social, datos.get("full_name"))
    else:
        v.campo("full_name", nombre_persona, datos.get("full_name"))

    v.campo("document_type", tipo_documento, datos.get("document_type"))
    # Sin un tipo válido no hay con qué decidir si la identificación admite letras.
    if "document_type" not in v.errores:
        v.campo("document_number", numero_documento, datos.get("document_number"),
                tipo=v.datos["document_type"])

    # `document_number` tiene índice único. Sin esta comprobación, repetirlo lanza
    # un error de integridad y la persona ve una pantalla de error del servidor en
    # lugar de un mensaje que le explique que ese cliente ya está registrado.
    if "document_number" in v.datos:
        duplicado = get_one(
            "SELECT customer_id, full_name, activo FROM customers WHERE document_number = %s",
            (v.datos["document_number"],),
        )
        if duplicado and duplicado["customer_id"] != customer_id:
            detalle = "" if duplicado["activo"] else " (inactivo)"
            v.errores["document_number"] = (
                f"Ya hay un cliente con ese documento: {duplicado['full_name']}{detalle}")

    v.campo("phone", telefono, datos.get("phone"))
    v.campo("email", correo, datos.get("email"))
    v.campo("address", texto, datos.get("address"), maximo=255, requerido=False)
    v.campo("pais", texto, datos.get("pais") or "Colombia", maximo=60)

    cod_municipio = (datos.get("cod_municipio") or "").strip()
    if cod_municipio:
        # Se comprueba contra la tabla y no solo el formato: un código inventado
        # rompería la llave foránea y el usuario vería un error del servidor en
        # lugar de un mensaje que le sirva.
        if not get_one("SELECT cod_municipio FROM municipios WHERE cod_municipio = %s",
                       (cod_municipio,)):
            v.errores["cod_municipio"] = "El municipio seleccionado no existe"
        else:
            v.datos["cod_municipio"] = cod_municipio
    else:
        v.datos["cod_municipio"] = None

    return v


def get_all_customers():
    return get_many("""
        SELECT c.*, m.nombre AS municipio_nombre, d.nombre AS departamento_nombre
        FROM customers c
        LEFT JOIN municipios m ON c.cod_municipio = m.cod_municipio
        LEFT JOIN departamentos d ON m.cod_departamento = d.cod_departamento
        WHERE c.activo = 1
        ORDER BY c.full_name
    """)


def get_customer_by_id(customer_id: int):
    return get_one("""
        SELECT c.*, m.nombre AS municipio_nombre, m.cod_departamento,
               d.nombre AS departamento_nombre
        FROM customers c
        LEFT JOIN municipios m ON c.cod_municipio = m.cod_municipio
        LEFT JOIN departamentos d ON m.cod_departamento = d.cod_departamento
        WHERE c.customer_id = %s
    """, (customer_id,))


def create_customer(full_name: str, document_type: str, document_number: str,
                    phone: str, email: str, address: str,
                    cod_municipio: str = None, pais: str = "Colombia",
                    tipo_persona: str = "NATURAL",
                    regimen_tributario: str = "NO_RESPONSABLE_IVA"):
    ciudad = ""
    departamento = ""
    if cod_municipio:
        row = get_one(
            "SELECT m.nombre, d.nombre AS dpto FROM municipios m "
            "JOIN departamentos d ON m.cod_departamento=d.cod_departamento "
            "WHERE m.cod_municipio=%s",
            (cod_municipio,)
        )
        if row:
            ciudad = row["nombre"]
            departamento = row["dpto"]
    query = """
        INSERT INTO customers
            (full_name, document_type, document_number, phone, email, address,
             ciudad, departamento, pais, tipo_persona, regimen_tributario, cod_municipio)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    return execute_query(query, (
        full_name, document_type, document_number, phone, email, address,
        ciudad, departamento, pais, tipo_persona, regimen_tributario,
        cod_municipio or None
    ))


def update_customer(customer_id: int, full_name: str, document_type: str,
                    document_number: str, phone: str, email: str, address: str,
                    cod_municipio: str = None, pais: str = "Colombia",
                    tipo_persona: str = "NATURAL",
                    regimen_tributario: str = "NO_RESPONSABLE_IVA"):
    ciudad = ""
    departamento = ""
    if cod_municipio:
        row = get_one(
            "SELECT m.nombre, d.nombre AS dpto FROM municipios m "
            "JOIN departamentos d ON m.cod_departamento=d.cod_departamento "
            "WHERE m.cod_municipio=%s",
            (cod_municipio,)
        )
        if row:
            ciudad = row["nombre"]
            departamento = row["dpto"]
    query = """
        UPDATE customers
        SET full_name=%s, document_type=%s, document_number=%s,
            phone=%s, email=%s, address=%s, ciudad=%s, departamento=%s, pais=%s,
            tipo_persona=%s, regimen_tributario=%s, cod_municipio=%s
        WHERE customer_id=%s
    """
    return execute_update(query, (
        full_name, document_type, document_number, phone, email, address,
        ciudad, departamento, pais, tipo_persona, regimen_tributario,
        cod_municipio or None, customer_id
    ))


def delete_customer(customer_id: int):
    return execute_update("UPDATE customers SET activo = 0 WHERE customer_id = %s", (customer_id,))
