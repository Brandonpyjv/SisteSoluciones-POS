"""
Contrato de entrada de `pdf_service` y `xml_service`.

Ambos servicios reciben diccionarios sueltos, y hasta ahora esos diccionarios
eran, de hecho, lo que devolvía `get_invoice_by_id`: un contrato implícito que
solo se podía descubrir leyendo el código. Al abrir la API, los documentos
emitidos para terceros no salen de esa consulta, así que el contrato tiene que
estar escrito en alguna parte. Es este módulo.

Un documento se representa con tres piezas:

    cabecera  totales, fechas, número, CUFE y los datos del receptor con
              prefijo `cliente_` / `document_`
    lineas    una por ítem, con base, descuento e impuesto ya calculados
    emisor    una fila de `empresas`, con los nombres de columna tal cual

`claves_faltantes()` permite que quien arme un documento desde otra fuente
—la API, un importador— verifique que no dejó ningún campo por fuera antes de
generar el PDF o el XML.
"""

# El PDF lee la cabecera y el emisor del mismo diccionario, con los alias que les
# pone la consulta; el XML recibe el emisor aparte, con los nombres de columna.
CLAVES_CABECERA = frozenset({
    "cod_factura", "numero_factura", "tipo_factura", "fecha", "fecha_vencimiento",
    "subtotal", "total_descuentos", "total_impuestos", "total",
    "cufe", "forma_pago", "observaciones", "orden_compra", "nombre_vendedor",
    "descripcion_descuento_factura", "metodo_pago_nombre",
    "cliente_nombre", "cliente_email", "cliente_phone", "cliente_address",
    "cliente_ciudad", "cliente_departamento", "cliente_cod_municipio",
    "document_type", "document_number",
})

CLAVES_LINEA = frozenset({
    "producto_nombre", "sku", "unidad_medida", "cantidad", "precio_unitario",
    "subtotal", "descuento_porcentaje", "descuento_valor", "descripcion_descuento",
    "impuesto_porcentaje", "impuesto_valor", "impuesto_codigo_dian",
})

CLAVES_EMISOR = frozenset({
    "nombre", "nit", "dv", "direccion", "ciudad", "telefono", "correo", "website",
    "regimen_tributario", "actividad_economica", "cod_municipio",
    "tarifa_ica", "autoretenedor", "gran_contribuyente",
    "prefijo_factura", "resolucion_dian",
    "resolucion_fecha_desde", "resolucion_fecha_hasta",
    "resolucion_desde", "resolucion_hasta",
})

# `get_invoice_by_id` renombra las columnas de `empresas` para que no choquen con
# las de `facturas`. Deshacer ese renombrado quitando el prefijo «empresa_» no
# funciona en todos los casos: `empresa_regimen` viene de `regimen_tributario` y
# `empresa_prefijo` de `prefijo_factura`. Recortar el prefijo dejaba esas dos
# claves con un nombre que el XML no busca, y el emisor salía con los valores por
# defecto en lugar de los suyos.
_ALIAS_EMISOR = {
    "empresa_nombre":                 "nombre",
    "empresa_nit":                    "nit",
    "empresa_dv":                     "dv",
    "empresa_direccion":              "direccion",
    "empresa_ciudad":                 "ciudad",
    "empresa_telefono":               "telefono",
    "empresa_correo":                 "correo",
    "empresa_website":                "website",
    "empresa_regimen":                "regimen_tributario",
    "empresa_cod_municipio":          "cod_municipio",
    "empresa_tarifa_ica":             "tarifa_ica",
    "empresa_autoretenedor":          "autoretenedor",
    "empresa_gran_contribuyente":     "gran_contribuyente",
    "empresa_prefijo":                "prefijo_factura",
    "empresa_resolucion_dian":        "resolucion_dian",
    "empresa_resolucion_fecha_desde": "resolucion_fecha_desde",
    "empresa_resolucion_fecha_hasta": "resolucion_fecha_hasta",
    "empresa_resolucion_desde":       "resolucion_desde",
    "empresa_resolucion_hasta":       "resolucion_hasta",
    # Esta la consulta la trae sin renombrar.
    "actividad_economica":            "actividad_economica",
}


def emisor_desde_factura(inv: dict) -> dict:
    """Extrae el emisor de una fila de `get_invoice_by_id` / `get_invoice_by_numero_factura`."""
    return {destino: inv.get(origen) for origen, destino in _ALIAS_EMISOR.items()}


def emisor_desde_empresa(empresa: dict) -> dict:
    """Normaliza una fila de `empresas` leída directamente.

    Las columnas ya se llaman como el contrato espera; esto solo garantiza que
    estén todas presentes, para que quien genera el XML no dependa de si la
    consulta seleccionó una columna o no.
    """
    return {clave: empresa.get(clave) for clave in CLAVES_EMISOR}


def claves_faltantes(cabecera: dict, lineas=None, emisor: dict = None) -> dict:
    """Reporta qué claves del contrato no llegaron, para diagnosticar armados nuevos.

    Devuelve un dict con las listas que estén incompletas; vacío si todo está.
    Una clave presente con valor None cuenta como presente: hay campos
    legítimamente vacíos, como el vencimiento de una factura de contado.
    """
    faltan = {}

    ausentes = sorted(CLAVES_CABECERA - set(cabecera or {}))
    if ausentes:
        faltan["cabecera"] = ausentes

    for i, linea in enumerate(lineas or []):
        ausentes = sorted(CLAVES_LINEA - set(linea))
        if ausentes:
            faltan.setdefault("lineas", {})[i] = ausentes

    if emisor is not None:
        ausentes = sorted(CLAVES_EMISOR - set(emisor))
        if ausentes:
            faltan["emisor"] = ausentes

    return faltan
