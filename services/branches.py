from database import get_all_from_table, execute_query, execute_update, get_one, get_many
from services.validaciones import (REGIMENES_TRIBUTARIOS, Validador, bandera, codigo_ciiu,
                                   correo as validar_correo, decimal, dv as validar_dv,
                                   entero, nit as validar_nit, opcion,
                                   prefijo as validar_prefijo, razon_social,
                                   sitio_web, telefono as validar_telefono, texto)

# El emisor casi siempre es un NIT; el resto existe para el caso de la persona
# natural que factura a nombre propio.
TIPOS_DOCUMENTO_EMISOR = ("NIT", "CC", "CE", "PASAPORTE")


def validar_empresa(datos: dict, branch_id: int = None) -> Validador:
    """Valida una empresa emisora.

    Es el registro más delicado del sistema: de aquí salen el NIT que se imprime
    en la factura, la resolución que autoriza la numeración y el prefijo con el
    que se numera. Un dato mal puesto acá se propaga a todos los documentos.
    """
    v = Validador()

    v.campo("nombre", razon_social, datos.get("nombre"))
    v.campo("tipo_documento", opcion, datos.get("tipo_documento"), TIPOS_DOCUMENTO_EMISOR)
    v.campo("nit", validar_nit, datos.get("nit"))
    v.campo("regimen_tributario", opcion, datos.get("regimen_tributario"),
            REGIMENES_TRIBUTARIOS)
    v.campo("direccion", texto, datos.get("direccion"), maximo=255, requerido=False)
    v.campo("telefono", validar_telefono, datos.get("telefono"))
    v.campo("correo", validar_correo, datos.get("correo"))
    v.campo("website", sitio_web, datos.get("website"))
    v.campo("actividad_economica", codigo_ciiu, datos.get("actividad_economica"))
    v.campo("autoretenedor", bandera, datos.get("autoretenedor"))
    v.campo("gran_contribuyente", bandera, datos.get("gran_contribuyente"))
    v.campo("prefijo_factura", validar_prefijo, datos.get("prefijo_factura") or "FV")

    # El dígito de verificación se comprueba contra el NIT, o se calcula si viene
    # vacío: uno equivocado se imprime en la factura y la DIAN rechaza el documento.
    if "nit" in v.datos:
        v.campo("dv", validar_dv, datos.get("dv"), nit=v.datos["nit"])

        duplicado = get_one("SELECT cod_empresa, nombre FROM empresas WHERE nit = %s",
                            (v.datos["nit"],))
        if duplicado and duplicado["cod_empresa"] != branch_id:
            v.errores["nit"] = f"Ese NIT ya lo tiene «{duplicado['nombre']}»"

    tarifa = (datos.get("tarifa_ica") or "").strip()
    if tarifa:
        v.campo("tarifa_ica", decimal, tarifa, minimo=0, maximo=100, decimales=4)
    else:
        v.datos["tarifa_ica"] = None

    cod_municipio = (datos.get("cod_municipio") or "").strip()
    if cod_municipio:
        if not get_one("SELECT cod_municipio FROM municipios WHERE cod_municipio = %s",
                       (cod_municipio,)):
            v.errores["cod_municipio"] = "El municipio seleccionado no existe"
        else:
            v.datos["cod_municipio"] = cod_municipio
    else:
        v.datos["cod_municipio"] = None

    # La resolución DIAN no se pide aquí: la administra FactuGest, que es quien
    # numera las facturas electrónicas. El prefijo y el consecutivo que siguen sí
    # son de este sistema, y numeran la venta desde que se registra.
    v.campo("consecutivo_actual", entero,
            datos.get("consecutivo_actual") if datos.get("consecutivo_actual") not in (None, "") else 1,
            minimo=1)

    return v


def get_all_branches():
    return get_many("""
        SELECT e.*, m.nombre AS municipio_nombre, d.nombre AS departamento_nombre,
               m.cod_departamento
        FROM empresas e
        LEFT JOIN municipios m ON e.cod_municipio = m.cod_municipio
        LEFT JOIN departamentos d ON m.cod_departamento = d.cod_departamento
        ORDER BY e.nombre
    """)


def get_branch_by_id(branch_id: int):
    return get_one("""
        SELECT e.*, m.nombre AS municipio_nombre, d.nombre AS departamento_nombre,
               m.cod_departamento
        FROM empresas e
        LEFT JOIN municipios m ON e.cod_municipio = m.cod_municipio
        LEFT JOIN departamentos d ON m.cod_departamento = d.cod_departamento
        WHERE e.cod_empresa = %s
    """, (branch_id,))


def create_branch(nombre: str, nit: str, dv: str, direccion: str, cod_municipio: str,
                  telefono: str, correo: str, regimen_tributario: str = "RESPONSABLE_IVA",
                  actividad_economica: str = "", tipo_documento: str = "NIT",
                  website: str = "", tarifa_ica: str = "", autoretenedor: int = 0,
                  gran_contribuyente: int = 0, prefijo_factura: str = "FV",
                  resolucion_dian: str = "", resolucion_fecha_desde: str = None,
                  resolucion_fecha_hasta: str = None, resolucion_desde: int = None,
                  resolucion_hasta: int = None, consecutivo_actual: int = 1):
    ciudad = ""
    if cod_municipio:
        row = get_one("SELECT nombre FROM municipios WHERE cod_municipio = %s", (cod_municipio,))
        if row:
            ciudad = row["nombre"]
    query = """
        INSERT INTO empresas
            (nombre, nit, dv, direccion, ciudad, telefono, correo,
             regimen_tributario, actividad_economica, tipo_documento, cod_municipio,
             website, tarifa_ica, autoretenedor, gran_contribuyente,
             prefijo_factura, resolucion_dian, resolucion_fecha_desde,
             resolucion_fecha_hasta, resolucion_desde, resolucion_hasta, consecutivo_actual)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    return execute_query(query, (
        nombre, nit, dv or None, direccion, ciudad, telefono, correo,
        regimen_tributario, actividad_economica or None, tipo_documento,
        cod_municipio or None, website or None, tarifa_ica or None,
        autoretenedor, gran_contribuyente, prefijo_factura or 'FV',
        resolucion_dian or None, resolucion_fecha_desde or None,
        resolucion_fecha_hasta or None, resolucion_desde or None,
        resolucion_hasta or None, consecutivo_actual or 1
    ))


def update_branch(branch_id: int, nombre: str, nit: str, dv: str, direccion: str,
                  cod_municipio: str, telefono: str, correo: str,
                  regimen_tributario: str = "RESPONSABLE_IVA",
                  actividad_economica: str = "", tipo_documento: str = "NIT",
                  website: str = "", tarifa_ica: str = "", autoretenedor: int = 0,
                  gran_contribuyente: int = 0, prefijo_factura: str = "FV",
                  resolucion_dian: str = "", resolucion_fecha_desde: str = None,
                  resolucion_fecha_hasta: str = None, resolucion_desde: int = None,
                  resolucion_hasta: int = None, consecutivo_actual: int = 1):
    ciudad = ""
    if cod_municipio:
        row = get_one("SELECT nombre FROM municipios WHERE cod_municipio = %s", (cod_municipio,))
        if row:
            ciudad = row["nombre"]
    query = """
        UPDATE empresas
        SET nombre=%s, nit=%s, dv=%s, direccion=%s, ciudad=%s,
            telefono=%s, correo=%s, regimen_tributario=%s,
            actividad_economica=%s, tipo_documento=%s, cod_municipio=%s,
            website=%s, tarifa_ica=%s, autoretenedor=%s, gran_contribuyente=%s,
            prefijo_factura=%s, resolucion_dian=%s, resolucion_fecha_desde=%s,
            resolucion_fecha_hasta=%s, resolucion_desde=%s, resolucion_hasta=%s,
            consecutivo_actual=%s
        WHERE cod_empresa=%s
    """
    return execute_update(query, (
        nombre, nit, dv or None, direccion, ciudad, telefono, correo,
        regimen_tributario, actividad_economica or None, tipo_documento,
        cod_municipio or None, website or None, tarifa_ica or None,
        autoretenedor, gran_contribuyente, prefijo_factura or 'FV',
        resolucion_dian or None, resolucion_fecha_desde or None,
        resolucion_fecha_hasta or None, resolucion_desde or None,
        resolucion_hasta or None, consecutivo_actual or 1, branch_id
    ))


def delete_branch(branch_id: int):
    return execute_update("DELETE FROM empresas WHERE cod_empresa = %s", (branch_id,))
