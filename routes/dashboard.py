"""Tablero de control: consolida las métricas de facturación e inventario.

Los datos que alimentan las gráficas se serializan aquí, no en la plantilla: MySQL
devuelve `Decimal` y `date`, que `|tojson` no sabe convertir.
"""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Request

from auth import ADMIN_ROLES
from services import report_service as rep
from services.inventory_service import get_alertas_stock, get_resumen_inventario
from services.invoice_service import get_dashboard_stats
from templates_config import templates

router = APIRouter()

_MESES = ["ene", "feb", "mar", "abr", "may", "jun",
          "jul", "ago", "sep", "oct", "nov", "dic"]

# Paleta validada con el validador de accesibilidad (OKLCH: banda de luminosidad,
# piso de croma, separación bajo daltonismo y contraste sobre superficie blanca).
# Los dos primeros son la serie categórica; el resto es la rampa ordinal de una sola
# tinta para los tramos de antigüedad de cartera, que sí tienen orden natural.
SERIE_FACTURADO = "#4e73df"
SERIE_COBRADO = "#17a673"
RAMPA_ANTIGUEDAD = ["#9cb1ec", "#7a94e5", "#5877de", "#3a58c0", "#243c92"]

_PRESETS = {"7": 7, "30": 30, "90": 90, "365": 365}


def _etiqueta_periodo(valor, granularidad):
    if not isinstance(valor, date):
        return str(valor)
    if granularidad == "mes":
        return f"{_MESES[valor.month - 1]} {valor.year}"
    return f"{valor.day:02d}/{valor.month:02d}"


def _resolver_rango(desde, hasta, preset):
    if preset in _PRESETS:
        return rep.rango_por_defecto(_PRESETS[preset])
    if desde and hasta:
        return desde, hasta
    return rep.rango_por_defecto(30)


def _resolver_empresa(request: Request, empresa_param: Optional[str]):
    """Cada usuario ve su empresa; solo ADMIN puede consolidar todas."""
    usuario = request.session.get("user", {})
    if usuario.get("rol") == "ADMIN":
        if empresa_param == "todas":
            return None
        if empresa_param:
            return int(empresa_param)
    return usuario.get("cod_empresa")


@router.get("/", name="index")
def index(request: Request, desde: str = "", hasta: str = "",
          preset: str = "", empresa: str = ""):
    usuario = request.session.get("user", {})

    # El cajero no gestiona finanzas: su panel es operativo.
    if usuario.get("rol") not in ADMIN_ROLES:
        return templates.TemplateResponse(request, "dashboard/cajero.html", {
            "stats":    get_dashboard_stats(),
            "agotados": [a for a in get_alertas_stock(limite=8) if a["estado_stock"] == "AGOTADO"],
        })

    desde, hasta = _resolver_rango(desde, hasta, preset)
    cod_empresa = _resolver_empresa(request, empresa)

    kpis = rep.get_kpis(desde, hasta, cod_empresa)
    cartera = rep.get_cartera(cod_empresa)
    antiguedad = rep.get_cartera_por_antiguedad(cod_empresa)
    serie = rep.get_serie_ventas(desde, hasta, cod_empresa)
    top_productos = rep.get_top_productos(desde, hasta, cod_empresa, limite=6)
    top_clientes = rep.get_top_clientes(desde, hasta, cod_empresa, limite=6)
    metodos_pago = rep.get_ventas_por_metodo_pago(desde, hasta, cod_empresa)
    inventario = get_resumen_inventario()
    alertas = get_alertas_stock(limite=6)

    graficas = {
        "serie": {
            "etiquetas": [_etiqueta_periodo(p["periodo"], serie["granularidad"])
                          for p in serie["puntos"]],
            "facturado": [float(p["ventas"] or 0) for p in serie["puntos"]],
            "cobrado":   [float(p["cobrado"] or 0) for p in serie["puntos"]],
        },
        "top_productos": {
            "etiquetas": [p["nombre"] for p in top_productos],
            "valores":   [float(p["ingresos"] or 0) for p in top_productos],
        },
        "antiguedad": {
            "etiquetas": [t["tramo"] for t in antiguedad],
            "valores":   [float(t["valor"] or 0) for t in antiguedad],
            "colores":   RAMPA_ANTIGUEDAD,
        },
        "metodos_pago": {
            "etiquetas": [m["metodo"] for m in metodos_pago],
            "valores":   [float(m["total"] or 0) for m in metodos_pago],
        },
        "colores": {"facturado": SERIE_FACTURADO, "cobrado": SERIE_COBRADO},
    }

    # Gemelo en tabla de la serie: los mismos números sin depender del tooltip.
    serie_tabla = [
        {"periodo":   graficas["serie"]["etiquetas"][i],
         "facturado": graficas["serie"]["facturado"][i],
         "cobrado":   graficas["serie"]["cobrado"][i],
         "facturas":  serie["puntos"][i]["facturas"]}
        for i in range(len(serie["puntos"]))
    ]

    return templates.TemplateResponse(request, "dashboard/index.html", {
        "kpis":          kpis,
        "cartera":       cartera,
        "antiguedad":    antiguedad,
        "serie":         serie,
        "serie_tabla":   serie_tabla,
        "top_productos": top_productos,
        "top_clientes":  top_clientes,
        "metodos_pago":  metodos_pago,
        "inventario":    inventario,
        "alertas":       alertas,
        "recientes":     get_dashboard_stats()["facturas_recientes"],
        "graficas":      graficas,
        "filtros":       {"desde": desde, "hasta": hasta, "preset": preset,
                          "empresa": empresa},
        "empresas":      rep.get_empresas_disponibles() if usuario.get("rol") == "ADMIN" else [],
        "es_admin":      usuario.get("rol") == "ADMIN",
    })
