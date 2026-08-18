"""Reportes consultables en pantalla y exportables a CSV y PDF.

Cada reporte se declara una sola vez en REPORTES: título, columnas y la función
que produce las filas. La vista HTML y las dos exportaciones leen esa misma
definición, así que no pueden quedar desalineadas.
"""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, Response

from services import export_service as exp
from services import report_service as rep
from services.inventory_service import get_inventario_detallado, get_movimientos, MOTIVOS
from templates_config import templates

router = APIRouter(prefix="/reports")

_MESES = ["ene", "feb", "mar", "abr", "may", "jun",
          "jul", "ago", "sep", "oct", "nov", "dic"]


# ── Constructores de filas ──────────────────────────────────────────────────

def _ventas_por_periodo(desde, hasta, empresa):
    serie = rep.get_serie_ventas(desde, hasta, empresa)
    filas = []
    for punto in serie["puntos"]:
        periodo = punto["periodo"]
        if isinstance(periodo, date):
            etiqueta = (f"{_MESES[periodo.month - 1]} {periodo.year}"
                        if serie["granularidad"] == "mes"
                        else periodo.strftime("%d/%m/%Y"))
        else:
            etiqueta = str(periodo)
        filas.append({
            "periodo":   etiqueta,
            "facturas":  punto["facturas"],
            "ventas":    punto["ventas"],
            "cobrado":   punto["cobrado"],
            "pendiente": float(punto["ventas"] or 0) - float(punto["cobrado"] or 0),
        })
    return filas


def _cartera(desde, hasta, empresa):
    filas = rep.get_cartera_detalle(empresa, limite=500)
    for f in filas:
        f["dias_vencido"] = max(int(f.get("dias_vencido") or 0), 0)
        f["estado_pago"] = rep.etiqueta_estado(f.get("estado_pago"))
    return filas


def _por_estado(desde, hasta, empresa):
    filas = rep.get_ventas_por_estado(desde, hasta, empresa)
    for f in filas:
        f["estado"] = rep.etiqueta_estado(f.get("estado"))
    return filas


def _inventario(desde, hasta, empresa):
    filas = get_inventario_detallado()
    for f in filas:
        f["estado_stock"] = {"OK": "Disponible", "BAJO": "Bajo mínimo",
                             "AGOTADO": "Agotado"}.get(f["estado_stock"], f["estado_stock"])
    return filas


def _movimientos(desde, hasta, empresa):
    filas = get_movimientos(desde=desde, hasta=hasta, limite=1000)
    for f in filas:
        f["motivo"] = MOTIVOS.get(f["motivo"], f["motivo"])
        f["tipo"] = f["tipo"].capitalize()
        f["usuario_nombre"] = f.get("usuario_nombre") or "Sistema"
        f["documento"] = f.get("documento") or (f.get("observaciones") or "")
    return filas


def _impuestos(desde, hasta, empresa):
    return rep.get_impuestos_recaudados(desde, hasta, empresa)


def _por_usuario(desde, hasta, empresa):
    return rep.get_ventas_por_usuario(desde, hasta, empresa, limite=100)


REPORTES = {
    "ventas": {
        "titulo": "Ventas por periodo",
        "descripcion": "Evolución de la facturación neta y del cobro efectivo.",
        "icono": "bi-graph-up",
        "usa_periodo": True,
        "columnas": [("periodo", "Periodo", "texto"),
                     ("facturas", "Facturas", "numero"),
                     ("ventas", "Facturado", "dinero"),
                     ("cobrado", "Cobrado", "dinero"),
                     ("pendiente", "Por cobrar", "dinero")],
        "datos": _ventas_por_periodo,
    },
    "cartera": {
        "titulo": "Cartera por cobrar",
        "descripcion": "Documentos pendientes, parcialmente pagados o vencidos, "
                       "ordenados por antigüedad. No depende del rango de fechas.",
        "icono": "bi-hourglass-split",
        "usa_periodo": False,
        "columnas": [("numero_factura", "Documento", "texto"),
                     ("tipo_factura", "Tipo", "texto"),
                     ("cliente", "Cliente", "texto"),
                     ("fecha", "Emisión", "fecha"),
                     ("fecha_vencimiento", "Vencimiento", "fecha"),
                     ("dias_vencido", "Días vencido", "numero"),
                     ("estado_pago", "Estado", "texto"),
                     ("total", "Saldo", "dinero")],
        "datos": _cartera,
        "no_totalizar": ["dias_vencido"],
    },
    "top-productos": {
        "titulo": "Productos más vendidos",
        "descripcion": "Ranking de productos por ingresos facturados en el periodo.",
        "icono": "bi-trophy",
        "usa_periodo": True,
        "columnas": [("sku", "SKU", "texto"),
                     ("nombre", "Producto", "texto"),
                     ("unidades", "Unidades", "numero"),
                     ("ingresos", "Ingresos", "dinero")],
        "datos": lambda d, h, e: rep.get_top_productos(d, h, e, limite=200),
    },
    "top-clientes": {
        "titulo": "Clientes por facturación",
        "descripcion": "Ranking de clientes por monto facturado en el periodo.",
        "icono": "bi-people",
        "usa_periodo": True,
        "columnas": [("document_number", "Documento", "texto"),
                     ("cliente", "Cliente", "texto"),
                     ("facturas", "Facturas", "numero"),
                     ("facturado", "Facturado", "dinero")],
        "datos": lambda d, h, e: rep.get_top_clientes(d, h, e, limite=200),
    },
    "inventario": {
        "titulo": "Existencias y valorización",
        "descripcion": "Stock actual, mínimo configurado y valor del inventario. "
                       "Es una foto del momento, no depende del rango de fechas.",
        "icono": "bi-boxes",
        "usa_periodo": False,
        "columnas": [("sku", "SKU", "texto"),
                     ("nombre", "Producto", "texto"),
                     ("stock", "Stock", "numero"),
                     ("stock_minimo", "Mínimo", "numero"),
                     ("estado_stock", "Estado", "texto"),
                     ("precio_unitario", "Costo unitario", "dinero"),
                     ("valor_inventario", "Valor", "dinero")],
        "datos": _inventario,
        "no_totalizar": ["stock_minimo", "precio_unitario"],
    },
    "movimientos": {
        "titulo": "Movimientos de inventario",
        "descripcion": "Entradas, salidas y ajustes registrados en el periodo.",
        "icono": "bi-arrow-left-right",
        "usa_periodo": True,
        "columnas": [("fecha", "Fecha", "fecha"),
                     ("sku", "SKU", "texto"),
                     ("producto_nombre", "Producto", "texto"),
                     ("tipo", "Tipo", "texto"),
                     ("motivo", "Motivo", "texto"),
                     ("cantidad", "Cantidad", "numero"),
                     ("stock_nuevo", "Saldo", "numero"),
                     ("documento", "Documento", "texto"),
                     ("usuario_nombre", "Usuario", "texto")],
        "datos": _movimientos,
        "no_totalizar": ["stock_nuevo"],
    },
    "impuestos": {
        "titulo": "Resumen tributario",
        "descripcion": "Base gravable e impuesto por tarifa, prorrateado igual que "
                       "en los documentos emitidos.",
        "icono": "bi-percent",
        "usa_periodo": True,
        "columnas": [("tarifa", "Tarifa", "porcentaje"),
                     ("documentos", "Documentos", "numero"),
                     ("base_gravable", "Base gravable", "dinero"),
                     ("impuesto", "Impuesto", "dinero")],
        "datos": _impuestos,
        "no_totalizar": ["documentos"],
    },
    "por-estado": {
        "titulo": "Facturación por estado de pago",
        "descripcion": "Cómo se reparte lo facturado entre cobrado, pendiente, "
                       "vencido y anulado.",
        "icono": "bi-pie-chart",
        "usa_periodo": True,
        "columnas": [("estado", "Estado", "texto"),
                     ("documentos", "Documentos", "numero"),
                     ("total", "Total", "dinero")],
        "datos": _por_estado,
    },
    "por-usuario": {
        "titulo": "Facturación por usuario",
        "descripcion": "Documentos emitidos y monto facturado por cada usuario.",
        "icono": "bi-person-badge",
        "usa_periodo": True,
        "columnas": [("usuario", "Usuario", "texto"),
                     ("rol", "Rol", "texto"),
                     ("facturas", "Facturas", "numero"),
                     ("total", "Facturado", "dinero")],
        "datos": _por_usuario,
    },
}


def _resolver_empresa(request: Request, empresa_param: Optional[str]):
    usuario = request.session.get("user", {})
    if usuario.get("rol") == "ADMIN":
        if empresa_param == "todas":
            return None
        if empresa_param:
            return int(empresa_param)
    return usuario.get("cod_empresa")


def _preparar(clave, request, desde, hasta, empresa):
    definicion = REPORTES[clave]
    if not desde or not hasta:
        desde, hasta = rep.rango_por_defecto(30)
    cod_empresa = _resolver_empresa(request, empresa)
    filas = definicion["datos"](desde, hasta, cod_empresa)
    totales = exp.calcular_totales(definicion["columnas"], filas,
                                   excluir=definicion.get("no_totalizar", ()))
    return definicion, filas, totales, desde, hasta


def _subtitulo(definicion, desde, hasta):
    if definicion["usa_periodo"]:
        return f"Periodo del {desde} al {hasta}"
    return f"Consultado el {date.today().isoformat()}"


@router.get("", name="reports")
def reports(request: Request, reporte: str = "ventas", desde: str = "",
            hasta: str = "", empresa: str = ""):
    if reporte not in REPORTES:
        return RedirectResponse(url="/reports", status_code=302)

    definicion, filas, totales, desde, hasta = _preparar(reporte, request, desde, hasta, empresa)
    usuario = request.session.get("user", {})

    return templates.TemplateResponse(request, "reports/index.html", {
        "reportes":   REPORTES,
        "clave":      reporte,
        "definicion": definicion,
        "filas":      filas,
        "totales":    totales,
        "formatear":  exp.formatear,
        "filtros":    {"desde": desde, "hasta": hasta, "empresa": empresa},
        "empresas":   rep.get_empresas_disponibles() if usuario.get("rol") == "ADMIN" else [],
        "es_admin":   usuario.get("rol") == "ADMIN",
    })


@router.get("/{reporte}/export.csv", name="report_csv")
def report_csv(request: Request, reporte: str, desde: str = "", hasta: str = "",
               empresa: str = ""):
    if reporte not in REPORTES:
        return RedirectResponse(url="/reports", status_code=302)

    definicion, filas, totales, desde, hasta = _preparar(reporte, request, desde, hasta, empresa)
    contenido = exp.to_csv(definicion["columnas"], filas, totales)
    archivo = exp.nombre_archivo(reporte, desde, hasta, "csv")
    return Response(
        content=contenido,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{archivo}"'},
    )


@router.get("/{reporte}/export.pdf", name="report_pdf")
def report_pdf(request: Request, reporte: str, desde: str = "", hasta: str = "",
               empresa: str = ""):
    if reporte not in REPORTES:
        return RedirectResponse(url="/reports", status_code=302)

    definicion, filas, totales, desde, hasta = _preparar(reporte, request, desde, hasta, empresa)
    cod_empresa = _resolver_empresa(request, empresa)
    nombre_empresa = "Todas las empresas"
    if cod_empresa:
        fila = next((e for e in rep.get_empresas_disponibles()
                     if e["cod_empresa"] == cod_empresa), None)
        nombre_empresa = fila["nombre"] if fila else ""

    contenido = exp.to_pdf(
        definicion["titulo"], _subtitulo(definicion, desde, hasta),
        definicion["columnas"], filas, totales, empresa=nombre_empresa,
    )
    archivo = exp.nombre_archivo(reporte, desde, hasta, "pdf")
    return Response(
        content=contenido,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{archivo}"'},
    )
