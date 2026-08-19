"""
Auditoría: el rastro de lo que hicieron los usuarios.

Es una pantalla de solo lectura, y no por falta de tiempo: no hay forma de editar
ni de borrar un registro desde ningún lado. Un rastro que se puede corregir no
prueba nada.

Se llega por Configuración › Auditoría, y solo con rol administrativo: el registro
dice qué hizo cada quien, y eso no es información para todo el mundo.
"""
from fastapi import APIRouter, Request

from services import auditoria_service as auditoria, listados
from templates_config import templates

router = APIRouter(prefix="/auditoria")


@router.get("", name="auditoria")
def ver_auditoria(request: Request, q: str = "", accion: str = "", entidad: str = "",
                  usuario: str = "", desde: str = "", hasta: str = "", pagina: int = 1):
    todos = auditoria.get_auditoria()

    filas = listados.buscar(todos, q, ("descripcion", "usuario_nombre", "entidad",
                                       "entidad_id", "ip"))
    filas = listados.igual_a(filas, "accion", accion)
    filas = listados.igual_a(filas, "entidad", entidad)
    filas = listados.igual_a(filas, "usuario_nombre", usuario)
    filas = listados.entre_fechas(filas, "fecha", desde, hasta)

    pagina_filas, meta = listados.paginar(filas, pagina)
    filtros = {"q": q, "accion": accion, "entidad": entidad, "usuario": usuario,
               "desde": desde, "hasta": hasta}

    return templates.TemplateResponse(request, "auditoria/index.html", {
        "registros": pagina_filas,
        "meta": meta,
        "filtros": filtros,
        "consulta": listados.query(filtros),
        "acciones": auditoria.ACCIONES,
        "colores": auditoria.COLOR_ACCION,
        "entidades": sorted({r["entidad"] for r in todos if r.get("entidad")}),
        "usuarios": [u["usuario_nombre"] for u in auditoria.usuarios_con_actividad()],
        "resumen": auditoria.resumen(),
    })
