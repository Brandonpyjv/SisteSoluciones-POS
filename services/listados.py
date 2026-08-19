"""
Buscar, filtrar y paginar los listados del panel.

Todas las tablas del sistema traían la tabla entera a la pantalla. Con veinte
filas eso no se nota; con cientos, la única forma de encontrar algo es el buscador
del navegador, y la página tarda en abrir. Aquí está la pieza que las tres cosas
comparten, para que un listado nuevo no tenga que reinventarla —ni salirse del
comportamiento de los demás.

**Filtra en memoria, no en SQL.** Es una decisión consciente: estas consultas ya
existen, están probadas y devuelven decenas o cientos de filas, no millones.
Reescribirlas todas para paginar en la base sería mucho más código y más riesgo a
cambio de una diferencia que nadie va a percibir. Los dos listados que sí pueden
crecer sin techo —`documentos` y el kardex— sí paginan en SQL, porque ahí la
diferencia es real.
"""
from datetime import date, datetime

POR_PAGINA = 10


def _texto_de(valor) -> str:
    if valor is None:
        return ""
    if isinstance(valor, (date, datetime)):
        return valor.strftime("%d/%m/%Y")
    return str(valor)


def buscar(filas, texto: str, campos) -> list:
    """Deja las filas donde el texto aparece en alguno de esos campos.

    Sin distinguir mayúsculas ni acentos de más: quien busca «drogueria» espera
    encontrar «Droguería». Cada palabra tiene que aparecer en algún campo, así que
    «juan 900» encuentra al cliente Juan con NIT 900…, aunque estén en columnas
    distintas.
    """
    texto = (texto or "").strip().lower()
    if not texto:
        return list(filas)

    palabras = [_sin_tildes(p) for p in texto.split()]
    resultado = []
    for fila in filas:
        heno = _sin_tildes(" ".join(_texto_de(fila.get(c)) for c in campos).lower())
        if all(p in heno for p in palabras):
            resultado.append(fila)
    return resultado


def _sin_tildes(texto: str) -> str:
    for con, sin in (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"),
                     ("ñ", "n"), ("ü", "u")):
        texto = texto.replace(con, sin)
    return texto


def entre_fechas(filas, campo: str, desde: str = None, hasta: str = None) -> list:
    """Filtra por un rango de fechas sobre una columna de fecha."""
    if not desde and not hasta:
        return list(filas)

    def dia_de(fila):
        valor = fila.get(campo)
        if isinstance(valor, datetime):
            return valor.date()
        if isinstance(valor, date):
            return valor
        try:
            return datetime.strptime(str(valor)[:10], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return None

    inicio = _a_fecha(desde)
    fin = _a_fecha(hasta)
    resultado = []
    for fila in filas:
        d = dia_de(fila)
        if d is None:
            continue
        if inicio and d < inicio:
            continue
        if fin and d > fin:
            continue
        resultado.append(fila)
    return resultado


def _a_fecha(valor):
    if not valor:
        return None
    try:
        return datetime.strptime(str(valor)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def igual_a(filas, campo: str, valor) -> list:
    """Filtra por un valor exacto. Vacío significa «todos», no «los vacíos»."""
    if valor in (None, "", "todos"):
        return list(filas)
    return [f for f in filas if str(f.get(campo)) == str(valor)]


def paginar(filas, pagina, por_pagina: int = POR_PAGINA) -> tuple:
    """Devuelve las filas de la página y lo que el pie necesita para dibujarse.

    La página que se pide se acota al rango válido en vez de devolver una lista
    vacía: llegar por un enlace viejo a la página 9 de un listado que ahora tiene
    dos no debería mostrar una tabla en blanco.
    """
    try:
        pagina = int(pagina or 1)
    except (TypeError, ValueError):
        pagina = 1

    total = len(filas)
    paginas = max(1, -(-total // por_pagina))
    pagina = min(max(1, pagina), paginas)
    inicio = (pagina - 1) * por_pagina

    return filas[inicio:inicio + por_pagina], {
        "total": total,
        "pagina": pagina,
        "paginas": paginas,
        "por_pagina": por_pagina,
        "desde": inicio + 1 if total else 0,
        "hasta": min(inicio + por_pagina, total),
        # Con una sola página no hay nada que recorrer, y el pie se queda con el
        # conteo. Es la diferencia entre informar y estorbar.
        "hay_paginas": paginas > 1,
    }


def query(filtros: dict) -> str:
    """La cadena de consulta sin la página, para armar los enlaces del pie."""
    from urllib.parse import urlencode
    limpios = {k: v for k, v in (filtros or {}).items()
               if v not in (None, "") and k != "pagina"}
    return urlencode(limpios)
