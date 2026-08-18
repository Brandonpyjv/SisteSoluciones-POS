"""Gestión de la foto de perfil.

Vive fuera de `/users` a propósito: ese prefijo está reservado a roles
administrativos y un cajero también debe poder cambiar su propia foto. El control
real no lo hace el prefijo sino `puede_cambiar_foto`, que permite a cada quien
la suya y a un superior las de sus inferiores.
"""
from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import RedirectResponse

from auth import puede_cambiar_foto
from services.avatar_service import FotoInvalidaError, eliminar_foto, guardar_foto
from services.user_service import get_user_by_id, update_user_photo
from templates_config import templates

router = APIRouter(prefix="/perfil")


def _sincronizar_sesion(request: Request, cod_usuario: int, foto):
    """Si el usuario cambió su propia foto, el navbar debe reflejarlo ya."""
    sesion = request.session.get("user")
    if sesion and sesion.get("cod_usuario") == cod_usuario:
        sesion["foto"] = foto
        request.session["user"] = sesion


@router.get("/foto/{user_id}", name="user_photo_form")
def photo_form(request: Request, user_id: int, error: str = ""):
    actor = request.session.get("user", {})
    objetivo = get_user_by_id(user_id)
    if not objetivo or not puede_cambiar_foto(actor, objetivo):
        return RedirectResponse(url="/", status_code=302)

    return templates.TemplateResponse(request, "perfil/foto.html", {
        "objetivo":  objetivo,
        "es_propia": actor.get("cod_usuario") == objetivo.get("cod_usuario"),
        "error":     error,
    })


@router.post("/foto/{user_id}", name="user_photo_save")
async def photo_save(request: Request, user_id: int,
                     foto: UploadFile = File(...),
                     volver_a: str = Form("")):
    actor = request.session.get("user", {})
    objetivo = get_user_by_id(user_id)
    if not objetivo or not puede_cambiar_foto(actor, objetivo):
        return RedirectResponse(url="/", status_code=303)

    try:
        nombre = guardar_foto(await foto.read(), user_id)
    except FotoInvalidaError as e:
        return RedirectResponse(url=f"/perfil/foto/{user_id}?error={e}", status_code=303)

    eliminar_foto(objetivo.get("foto"))
    update_user_photo(user_id, nombre)
    _sincronizar_sesion(request, user_id, nombre)

    return RedirectResponse(url=volver_a or f"/perfil/foto/{user_id}", status_code=303)


@router.get("/foto/{user_id}/eliminar", name="user_photo_delete")
def photo_delete(request: Request, user_id: int, volver_a: str = ""):
    actor = request.session.get("user", {})
    objetivo = get_user_by_id(user_id)
    if not objetivo or not puede_cambiar_foto(actor, objetivo):
        return RedirectResponse(url="/", status_code=302)

    eliminar_foto(objetivo.get("foto"))
    update_user_photo(user_id, None)
    _sincronizar_sesion(request, user_id, None)

    return RedirectResponse(url=volver_a or f"/perfil/foto/{user_id}", status_code=302)
