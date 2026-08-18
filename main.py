import os
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv

load_dotenv()

from auth import AuthMiddleware, hash_password, role_label, puede_cambiar_foto
from templates_config import templates
from routes.login import router as login_router
from routes.invoice import router as invoice_router
from routes.users import router as users_router
from routes.customer import router as customer_router
from routes.payment_methods import router as payment_methods_router
from routes.discounts import router as discount_router
from routes.taxes import router as invoice_taxes_router
from routes.branches import router as branches_router
from routes.invoice_payments import router as invoice_payments_router
from routes.productos import router as products_router
from routes.inventory import router as inventory_router
from routes.logs import router as logs_router
from routes.product_discount import router as product_discount_router
from routes.ubicacion import router as ubicacion_router
from services.report_service import etiqueta_estado
from services.validaciones import (abreviatura_documento, nombre_documento,
                                   tipos_documento_ordenados)
from routes.dashboard import router as dashboard_router
from routes.reports import router as reports_router
from routes.perfil import router as perfil_router

app = FastAPI(title="Siste Soluciones", description="Punto de Venta")

# Los middlewares se ejecutan en orden inverso al registro:
# AuthMiddleware corre primero, luego SessionMiddleware lo prepara.
app.add_middleware(AuthMiddleware)
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET", "siste-dev-secret"))

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(login_router)
app.include_router(users_router)
app.include_router(customer_router)
app.include_router(invoice_router)
app.include_router(payment_methods_router)
app.include_router(discount_router)
app.include_router(invoice_taxes_router)
app.include_router(branches_router)
app.include_router(invoice_payments_router)
app.include_router(products_router)
app.include_router(inventory_router)
app.include_router(logs_router)
app.include_router(product_discount_router)
app.include_router(ubicacion_router)
app.include_router(reports_router)
app.include_router(perfil_router)
app.include_router(dashboard_router)

# Registrar url_for como global en Jinja2
templates.env.globals["url_for"] = app.url_path_for


def avatar_url(foto: str = None) -> str:
    """URL de la foto de perfil, o la silueta genérica si no tiene."""
    if foto:
        return app.url_path_for("static", path=f"img/perfiles/{foto}")
    return app.url_path_for("static", path="img/avatar-generico.svg")


def fecha_iso(valor) -> str:
    """Valor de un <input type="date">.

    Al volver de una validación fallida la fecha llega como el texto que envió el
    formulario; desde la base llega como date. El template no debería tener que
    saber cuál de las dos es.
    """
    if not valor:
        return ""
    if hasattr(valor, "strftime"):
        return valor.strftime("%Y-%m-%d")
    return str(valor)[:10]


templates.env.globals["avatar_url"] = avatar_url
templates.env.globals["fecha_iso"] = fecha_iso
templates.env.globals["role_label"] = role_label
templates.env.globals["puede_cambiar_foto"] = puede_cambiar_foto
templates.env.globals["etiqueta_estado"] = etiqueta_estado

# Los tipos de documento se guardan con el código de la DIAN; las vistas muestran
# la abreviatura, porque nadie lee «13» y entiende «cédula».
templates.env.globals["abreviatura_documento"] = abreviatura_documento
templates.env.globals["nombre_documento"] = nombre_documento
templates.env.globals["tipos_documento"] = tipos_documento_ordenados


@app.on_event("startup")
def migrate_passwords():
    """Hashea contraseñas en texto plano al arrancar (idempotente)."""
    from database import get_many, execute_update
    users = get_many("SELECT cod_usuario, contrasena FROM usuarios")
    for u in users:
        pwd = u.get("contrasena") or ""
        if pwd and not pwd.startswith("$2"):
            hashed = hash_password(pwd)
            execute_update(
                "UPDATE usuarios SET contrasena=%s WHERE cod_usuario=%s",
                (hashed, u["cod_usuario"]),
            )


# El navegador pide /favicon.ico en la raíz aunque los <link> apunten a /static.
@app.get("/favicon.ico")
def favicon():
    return FileResponse("static/img/favicon.ico", media_type="image/x-icon")


@app.get("/settings", name="setting")
def setting(request: Request):
    return templates.TemplateResponse(request, "settings/index.html")


@app.get("/settings/new", name="settings_new")
def setting_new(request: Request):
    return templates.TemplateResponse(request, "settings/form.html")


if __name__ == "__main__":
    import uvicorn
    # 8001 y no 8000: FactuGest ocupa el 8000, y los dos tienen que poder
    # correr a la vez para que el punto de venta le pueda hablar.
    uvicorn.run("main:app", host="127.0.0.1",
                port=int(os.getenv("PORT", "8001")), reload=True)
