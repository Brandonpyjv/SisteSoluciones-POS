"""
Respuesta única para un formulario que no pasó la validación.

Todas las rutas de escritura devuelven el error igual: se vuelve a mostrar el
mismo formulario, con los mensajes junto a cada campo y conservando lo que la
persona ya había escrito, para que no tenga que llenarlo otra vez.
"""
from fastapi import Request

from templates_config import templates


def formulario_invalido(request: Request, plantilla: str, validador,
                        contexto: dict = None, valores: dict = None):
    """Vuelve a mostrar el formulario con los errores y los datos enviados.

    Responde 422 y no 200: el navegador pinta la página igual, pero quien llame
    la ruta desde fuera —Postman, un script, el sistema de un tercero— recibe un
    código que dice que los datos se rechazaron. Esa es la diferencia entre
    validar de verdad y solo decorar el formulario.
    """
    return templates.TemplateResponse(
        request,
        plantilla,
        {
            **(contexto or {}),
            "errores": validador.errores,
            "valores": valores or {},
        },
        status_code=422,
    )
