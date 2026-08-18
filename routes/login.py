from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from services.user_service import get_user_by_email
from auth import verify_password
from templates_config import templates

router = APIRouter()


@router.get("/login", name="login")
def login_get(request: Request):
    if request.session.get("user"):
        return RedirectResponse("/", status_code=302)
    error = "error" in request.query_params
    logout = "logout" in request.query_params
    return templates.TemplateResponse(request, "login.html", {"error": error, "logout": logout})


@router.post("/login", name="login_post")
def login_post(
    request: Request,
    correo: str = Form(...),
    contrasena: str = Form(...),
):
    user = get_user_by_email(correo)
    if not user or not verify_password(contrasena, user["contrasena"]):
        return templates.TemplateResponse(
            request, "login.html",
            {"error": True, "logout": False},
            status_code=401,
        )

    request.session["user"] = {
        "cod_usuario":   user["cod_usuario"],
        "nombre":        user["nombre"],
        "correo":        user["correo"],
        "rol":           user["rol"],
        "cod_empresa":   user.get("cod_empresa"),
        "empresa_nombre": user.get("empresa_nombre"),
        "foto":          user.get("foto"),
    }
    return RedirectResponse("/", status_code=303)


@router.get("/logout", name="logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login?logout=true", status_code=302)
