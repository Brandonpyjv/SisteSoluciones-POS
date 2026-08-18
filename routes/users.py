from fastapi import APIRouter, File, Request, Form, UploadFile
from fastapi.responses import RedirectResponse
from typing import Optional
from services.user_service import (get_all_users, get_user_by_id, create_user, update_user,
                                    delete_user, update_user_photo, validar_usuario)
from services.avatar_service import FotoInvalidaError, eliminar_foto, guardar_foto
from services.branches import get_all_branches
from routes.formularios import formulario_invalido
from auth import can_manage, ROLE_HIERARCHY, ROLE_LABELS
from templates_config import templates

router = APIRouter(prefix="/users")

PLANTILLA = "users/form.html"

# Roles que un actor puede asignar, filtrados por jerarquía
def _assignable_roles(actor_rol: str) -> list:
    actor_level = ROLE_HIERARCHY.get(actor_rol, 0)
    order = ["ADMIN", "JEFE_TIENDA", "SUPERVISOR", "CAJERO"]
    return [
        {"value": r, "label": ROLE_LABELS[r]}
        for r in order
        if ROLE_HIERARCHY[r] < actor_level
    ]


async def _aplicar_foto(archivo: UploadFile, cod_usuario: int, foto_anterior=None):
    """Guarda la foto adjunta al formulario, si viene alguna.

    Un fallo aquí no debe tumbar el alta o la edición del usuario: los datos ya
    se guardaron y la foto es accesoria. Se reporta pero no se revierte nada.
    """
    if not archivo or not archivo.filename:
        return None
    try:
        nombre = guardar_foto(await archivo.read(), cod_usuario)
    except FotoInvalidaError:
        return None
    eliminar_foto(foto_anterior)
    update_user_photo(cod_usuario, nombre)
    return nombre


@router.get("", name="users")
def users(request: Request):
    actor = request.session.get("user", {})
    data = get_all_users()
    return templates.TemplateResponse(request, "users/index.html", {
        "usuarios": data,
        "actor_rol": actor.get("rol", ""),
    })


@router.get("/new", name="new_user")
def new_user(request: Request):
    actor = request.session.get("user", {})
    roles = _assignable_roles(actor.get("rol", ""))
    return templates.TemplateResponse(request, "users/form.html", {
        "user": None,
        "empresas": get_all_branches(),
        "roles_disponibles": roles,
    })


@router.post("/new", name="create_user")
async def create_user_post(
    request: Request,
    nombre: str = Form(...),
    correo: str = Form(...),
    contrasena: str = Form(...),
    rol: str = Form(...),
    cod_empresa: Optional[str] = Form(None),
    foto: UploadFile = File(None),
):
    actor = request.session.get("user", {})
    if not can_manage(actor.get("rol", ""), rol):
        return RedirectResponse(url="/users", status_code=303)

    enviado = {"nombre": nombre, "correo": correo, "contrasena": contrasena,
               "rol": rol, "cod_empresa": cod_empresa}
    v = validar_usuario(enviado)
    if not v.valido:
        return formulario_invalido(request, PLANTILLA, v, {
            "user": None,
            "empresas": get_all_branches(),
            "roles_disponibles": _assignable_roles(actor.get("rol", "")),
        }, enviado)

    d = v.datos
    nuevo_id = create_user(d["nombre"], d["correo"], d["contrasena"], d["rol"],
                           d["cod_empresa"])
    await _aplicar_foto(foto, nuevo_id)
    return RedirectResponse(url="/users", status_code=303)


@router.get("/edit/{user_id}", name="edit_user")
def edit_user(request: Request, user_id: int):
    actor = request.session.get("user", {})
    user = get_user_by_id(user_id)
    if not user or not can_manage(actor.get("rol", ""), user.get("rol", "")):
        return RedirectResponse(url="/users", status_code=302)
    roles = _assignable_roles(actor.get("rol", ""))
    return templates.TemplateResponse(request, "users/form.html", {
        "user": user,
        "empresas": get_all_branches(),
        "roles_disponibles": roles,
    })


@router.post("/edit/{user_id}", name="update_user")
async def update_user_post(
    request: Request,
    user_id: int,
    nombre: str = Form(...),
    correo: str = Form(...),
    rol: str = Form(...),
    contrasena: str = Form(""),
    cod_empresa: Optional[str] = Form(None),
    foto: UploadFile = File(None),
):
    actor = request.session.get("user", {})
    target = get_user_by_id(user_id)
    if not target or not can_manage(actor.get("rol", ""), target.get("rol", "")):
        return RedirectResponse(url="/users", status_code=303)
    if not can_manage(actor.get("rol", ""), rol):
        return RedirectResponse(url="/users", status_code=303)

    enviado = {"nombre": nombre, "correo": correo, "contrasena": contrasena,
               "rol": rol, "cod_empresa": cod_empresa}
    v = validar_usuario(enviado, user_id=user_id)
    if not v.valido:
        return formulario_invalido(request, PLANTILLA, v, {
            "user": target,
            "empresas": get_all_branches(),
            "roles_disponibles": _assignable_roles(actor.get("rol", "")),
        }, enviado)

    d = v.datos
    update_user(user_id, d["nombre"], d["correo"], d["rol"],
                d["contrasena"] or None, d["cod_empresa"])
    await _aplicar_foto(foto, user_id, target.get("foto"))
    return RedirectResponse(url="/users", status_code=303)


@router.get("/delete/{user_id}", name="delete_user")
def delete_user_get(request: Request, user_id: int):
    actor = request.session.get("user", {})
    target = get_user_by_id(user_id)
    if not target or not can_manage(actor.get("rol", ""), target.get("rol", "")):
        return RedirectResponse(url="/users", status_code=302)
    delete_user(user_id)
    return RedirectResponse(url="/users", status_code=302)
