"""
Renovar la sesión sin recargar la página.

El aviso de inactividad cuenta el tiempo **en el navegador**, no preguntándole al
servidor cada minuto: una consulta periódica sería ella misma actividad y la
sesión no se cerraría nunca, que es justo lo que se quiere evitar.

Por eso hay un solo endpoint y solo se llama cuando alguien pulsa «seguir
trabajando». La renovación en sí no la hace esta ruta: la hace `AuthMiddleware`,
que corre el reloj en toda petición que pase por él. Aquí solo se devuelve cuánto
quedó, para que el contador del navegador vuelva a arrancar.
"""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from auth import MINUTOS_DE_SESION, segundos_restantes

router = APIRouter(prefix="/sesion")


@router.post("/renovar", name="renovar_sesion")
def renovar(request: Request):
    return JSONResponse({
        "segundos": segundos_restantes(request),
        "minutos": MINUTOS_DE_SESION,
    })
