import os
import time

import bcrypt
from fastapi import Request
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

# ── Duración de la sesión ───────────────────────────────────────────────────
#
# La sesión duraba lo que trae Starlette por defecto: catorce días, y contados
# desde el momento de entrar, no desde la última actividad. En la práctica eso es
# una sesión que no se cierra: un equipo de mostrador queda abierto a quien pase
# por ahí, y un turno que termina no termina la sesión.
#
# Ahora se cierra por inactividad. Cada petición renueva el reloj, así que trabajar
# nunca la corta; lo que la corta es dejar de trabajar. Se avisa antes de cerrar
# —ver el aviso en `layout.html`— porque una sesión que se cae sin decir nada hace
# perder una factura a medio llenar.
MINUTOS_DE_SESION = int(os.getenv("SESION_MINUTOS", "30"))
MINUTOS_DE_AVISO = int(os.getenv("SESION_AVISO_MINUTOS", "2"))

# Marca de la última petición, dentro de la propia sesión firmada. No hace falta
# guardarla en la base: la cookie va firmada, así que el navegador no puede
# adelantar su propio reloj para estirar la sesión.
_CLAVE_VISTO = "visto_en"

# `/api/v1` no lleva sesión: la API de integración se autentica con la llave del
# cliente, y este middleware la mandaría al formulario de login. La documentación
# de Swagger queda abierta a propósito, porque es lo que lee quien se va a
# integrar; no expone datos, solo la forma de los endpoints.
_PUBLIC_PREFIXES = ("/login", "/static", "/favicon.ico",
                    "/api/v1", "/docs", "/redoc", "/openapi.json")

# Roles con permisos completos de administración
ADMIN_ROLES = {"ADMIN", "SUPERVISOR", "JEFE_TIENDA"}

# Jerarquía de roles: mayor número = mayor autoridad
ROLE_HIERARCHY = {
    "ADMIN":       4,
    "JEFE_TIENDA": 3,
    "SUPERVISOR":  2,
    "CAJERO":      1,
}

ROLE_LABELS = {
    "ADMIN":       "Administrador",
    "JEFE_TIENDA": "Jefe de Tienda",
    "SUPERVISOR":  "Supervisor",
    "CAJERO":      "Cajero",
}


def role_level(rol: str) -> int:
    return ROLE_HIERARCHY.get(rol, 0)


def role_label(rol: str) -> str:
    return ROLE_LABELS.get(rol, rol or "")


def can_manage(actor_rol: str, target_rol: str) -> bool:
    """Retorna True si actor_rol puede crear/editar/eliminar a target_rol."""
    return role_level(actor_rol) > role_level(target_rol)


def puede_cambiar_foto(actor: dict, objetivo: dict) -> bool:
    """Quién puede cambiar la foto de quién.

    Un superior puede cambiar la de sus inferiores. Además cada quien puede
    cambiar la suya: sin esto ningún ADMIN podría tener foto, porque `can_manage`
    exige un rol estrictamente mayor y no hay ninguno por encima de ADMIN.
    """
    if not actor or not objetivo:
        return False
    if actor.get("cod_usuario") == objetivo.get("cod_usuario"):
        return True
    return can_manage(actor.get("rol", ""), objetivo.get("rol", ""))

# Rutas exclusivas de roles admin (bloqueadas para CAJERO).
# La pantalla de pendientes de emitir no esta aqui a proposito: el cajero es quien
# ve que una venta se quedo sin factura y quien la reintenta.
_ADMIN_ONLY_PREFIXES = (
    "/users", "/auditoria", "/branches",
    "/payment_methods", "/invoice_taxes", "/invoice_payments",
    "/inventory", "/reports", "/configuracion",
)

# Acciones de escritura bloqueadas para CAJERO.
# Los productos viven bajo /products/product/... (el router tiene prefix="/products");
# las rutas cortas /product/... nunca existieron y dejaban el gate sin efecto.
_CAJERO_BLOCKED_PREFIXES = (
    "/products/product/new", "/products/product/edit", "/products/product/delete",
    "/discount/new", "/discount/edit", "/discount/delete",
    "/invoice/delete",
)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    if not hashed:
        return False
    if not hashed.startswith("$2"):
        return plain == hashed
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def get_session_user(request: Request):
    return request.session.get("user")


def is_admin(user: dict) -> bool:
    return user.get("rol") in ADMIN_ROLES


def segundos_restantes(request: Request) -> int:
    """Cuánto le queda a la sesión antes de cerrarse por inactividad.

    Al pintar una página siempre devuelve el máximo, y está bien: pedir esa página
    fue actividad, así que el reloj acaba de arrancar de cero. El valor sirve para
    que el contador del navegador sepa desde dónde contar.

    Se calcula, no se guarda: el reloj es la marca de la última petición y el tope
    configurado, nada más.
    """
    visto = request.session.get(_CLAVE_VISTO)
    if not visto:
        return MINUTOS_DE_SESION * 60
    return max(0, int(MINUTOS_DE_SESION * 60 - (time.time() - visto)))


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        if any(path.startswith(p) for p in _PUBLIC_PREFIXES):
            return await call_next(request)

        user = request.session.get("user")
        if not user:
            return RedirectResponse("/login", status_code=302)

        # Inactividad. Se mira antes de dejar pasar la petición: una sesión vencida
        # no ejecuta la acción y después cierra, cierra y no la ejecuta.
        visto = request.session.get(_CLAVE_VISTO)
        if visto and (time.time() - visto) > MINUTOS_DE_SESION * 60:
            request.session.clear()
            return RedirectResponse("/login?expirada=1", status_code=302)

        # Cada petición corre el reloj. Escribir en la sesión también hace que
        # Starlette reenvíe la cookie, así que su vencimiento se renueva con ella.
        request.session[_CLAVE_VISTO] = int(time.time())

        rol = user.get("rol")

        # Rutas solo para roles admin
        if any(path.startswith(p) for p in _ADMIN_ONLY_PREFIXES):
            if rol not in ADMIN_ROLES:
                return RedirectResponse("/", status_code=302)

        # Acciones de escritura bloqueadas para CAJERO
        if rol == "CAJERO" and any(path.startswith(p) for p in _CAJERO_BLOCKED_PREFIXES):
            return RedirectResponse("/", status_code=302)

        return await call_next(request)
