"""
Deja la base con los datos de Siste Soluciones.

    python seed_negocio.py              solo los datos de la empresa
    python seed_negocio.py --reiniciar  ademas, deja la operacion en cero

El volcado de `base/` trae el esquema y los catálogos —municipios, impuestos,
estados de pago, métodos de pago—, que sirven igual aquí. Pero también trae las
empresas, los clientes, los productos y las facturas de ejemplo de FactuGest, que
son de otro negocio: un punto de venta nuevo no arranca con las ventas de otro.

Con `--reiniciar` deja la base en el estado con el que abre el negocio: los
catálogos intactos y la operación en cero. **Eso borra ventas, productos y
clientes**, así que es solo para la instalación inicial; sin la bandera el script
se limita a los datos de la empresa y no toca nada más.

Sin `--reiniciar` es idempotente y seguro: correrlo dos veces deja lo mismo.
"""
import sys

from database import execute_query, execute_update, get_many, get_one
from services.validaciones import calcular_dv

NIT = "901555444"
NOMBRE = "Siste Soluciones S.A.S."
COD_MUNICIPIO = "54001"   # Cúcuta, Norte de Santander


def limpiar_operacion_heredada():
    """Borra la operación de ejemplo que venía en el volcado.

    Se van las facturas, el kardex, los productos y los clientes; se quedan los
    catálogos y los usuarios, que sirven igual. El orden respeta las llaves
    foráneas: primero lo que cuelga, después lo que sostiene.
    """
    borrados = {}
    for tabla in ("detalle_factura", "factura_impuesto", "factura_descuento",
                  "movimientos_inventario", "facturas", "producto_descuento",
                  "productos", "customers"):
        try:
            n = execute_update(f"DELETE FROM {tabla}")
        except Exception:
            # Alguna de esas tablas puede no existir en un volcado más viejo.
            continue
        if n:
            borrados[tabla] = n
    return borrados


def main(reiniciar=False):
    dv = str(calcular_dv(NIT))

    # Solo bajo petición explícita: borrar la operación de un sistema que lleva
    # meses vendiendo no puede ser el comportamiento por defecto de un script que
    # se ejecuta para corregir un dato de la empresa.
    borrados = limpiar_operacion_heredada() if reiniciar else {}
    if borrados:
        print("  operación de ejemplo de FactuGest eliminada:")
        for tabla, n in borrados.items():
            print(f"     {tabla:26} {n} fila(s)")

    municipio = get_one("SELECT nombre FROM municipios WHERE cod_municipio = %s",
                        (COD_MUNICIPIO,))
    if not municipio:
        raise SystemExit("No están cargados los municipios. Importa base/factugest.sql.")

    datos = (NOMBRE, NIT, dv, "C.C. Gran Bulevar, local 103", municipio["nombre"],
             COD_MUNICIPIO, "6075551234", "facturacion@sistesoluciones.com",
             "sistesoluciones.com", "RESPONSABLE_IVA", "4741", "NIT")

    empresa = get_one("SELECT cod_empresa FROM empresas WHERE nit = %s", (NIT,))
    if empresa:
        execute_update(
            "UPDATE empresas SET nombre=%s, dv=%s, direccion=%s, ciudad=%s, "
            "  cod_municipio=%s, telefono=%s, correo=%s, website=%s, "
            "  regimen_tributario=%s, actividad_economica=%s, tipo_documento=%s "
            "WHERE cod_empresa=%s",
            (NOMBRE, dv, datos[3], datos[4], COD_MUNICIPIO, datos[6], datos[7],
             datos[8], datos[9], datos[10], datos[11], empresa["cod_empresa"]))
        cod_empresa = empresa["cod_empresa"]
        print(f"empresa actualizada (cod_empresa={cod_empresa})")
    else:
        cod_empresa = execute_query(
            "INSERT INTO empresas (nombre, nit, dv, direccion, ciudad, cod_municipio, "
            "  telefono, correo, website, regimen_tributario, actividad_economica, "
            "  tipo_documento) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (datos[0], datos[1], datos[2], datos[3], datos[4], datos[5], datos[6],
             datos[7], datos[8], datos[9], datos[10], datos[11]))
        print(f"empresa creada (cod_empresa={cod_empresa})")

    # La resolución y los consecutivos ya no son asunto de este sistema: los
    # administra FactuGest, que es quien numera. Se dejan vacíos a propósito para
    # que nadie los llene aquí creyendo que sirven.
    execute_update(
        "UPDATE empresas SET resolucion_dian=NULL, resolucion_desde=NULL, "
        "  resolucion_hasta=NULL, resolucion_fecha_desde=NULL, "
        "  resolucion_fecha_hasta=NULL WHERE cod_empresa=%s", (cod_empresa,))

    # Las demás empresas del volcado son de FactuGest y solo estorban en el
    # desplegable de la factura.
    ajenas = get_many("SELECT cod_empresa, nombre FROM empresas WHERE cod_empresa <> %s",
                      (cod_empresa,))
    for otra in ajenas:
        execute_update("UPDATE usuarios SET cod_empresa=%s WHERE cod_empresa=%s",
                       (cod_empresa, otra["cod_empresa"]))
        execute_update("DELETE FROM empresas WHERE cod_empresa=%s", (otra["cod_empresa"],))
    if ajenas:
        print(f"  {len(ajenas)} empresa(s) ajenas eliminadas: "
              f"{', '.join(e['nombre'] for e in ajenas)}")

    afectados = execute_update(
        "UPDATE usuarios SET cod_empresa=%s WHERE cod_empresa IS NULL OR cod_empresa<>%s",
        (cod_empresa, cod_empresa))

    # Los usuarios llegaron del fork con el correo del otro negocio, y con ese
    # correo es con el que inician sesión.
    correos = execute_update(
        "UPDATE usuarios SET correo = REPLACE(correo, '@factugest.com', "
        "  '@sistesoluciones.com') WHERE correo LIKE '%@factugest.com'")
    if correos:
        print(f"  {correos} correo(s) de usuario pasados a @sistesoluciones.com")

    print(f"  NIT {NIT}-{dv}  ·  {datos[3]}, {datos[4]}")
    print(f"  {afectados} usuario(s) apuntados a la empresa")
    print(f"  resolución y consecutivos vacíos: los administra FactuGest")


if __name__ == "__main__":
    reiniciar = "--reiniciar" in sys.argv
    print("Siste Soluciones — datos del negocio"
          + (" (reiniciando la operación)" if reiniciar else ""))
    main(reiniciar)
    if not reiniciar:
        n = get_one("SELECT COUNT(*) n FROM facturas")["n"]
        if n:
            print(f"  la operación no se tocó: {n} venta(s) siguen ahí")
    print("Listo.")
