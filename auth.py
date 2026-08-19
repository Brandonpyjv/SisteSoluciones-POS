import bcrypt
from fastapi import Request
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

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


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        if any(path.startswith(p) for p in _PUBLIC_PREFIXES):
            return await call_next(request)

        user = request.session.get("user")
        if not user:
            return RedirectResponse("/login", status_code=302)

        rol = user.get("rol")

        # Rutas solo para roles admin
        if any(path.startswith(p) for p in _ADMIN_ONLY_PREFIXES):
            if rol not in ADMIN_ROLES:
                return RedirectResponse("/", status_code=302)

        # Acciones de escritura bloqueadas para CAJERO
        if rol == "CAJERO" and any(path.startswith(p) for p in _CAJERO_BLOCKED_PREFIXES):
            return RedirectResponse("/", status_code=302)

        return await call_next(request)
