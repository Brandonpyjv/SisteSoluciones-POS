"""
Reglas de validación del dominio.

Un módulo puro y compartido, no reglas repartidas por las rutas: las mismas
funciones validan los formularios Jinja y los modelos Pydantic de `/api/v1/`, de
modo que una regla se cambia en un solo archivo y cambia en los dos canales.

La validación del navegador es comodidad; **esta es la defensa**. Un `POST` armado
con Postman no pasa por ningún `min` de HTML, y una cantidad negativa que llegue
hasta el cálculo se convierte en dinero inventado.

Cada función devuelve el valor ya normalizado o lanza `ErrorValidacion`. Para un
formulario con varios campos, `Validador` los acumula y permite mostrarlos todos
juntos en lugar de uno por recarga.
"""
import re
from datetime import date, datetime

# ── Errores ─────────────────────────────────────────────────────────────────


class ErrorValidacion(ValueError):
    def __init__(self, campo: str, mensaje: str):
        self.campo = campo
        self.mensaje = mensaje
        super().__init__(f"{campo}: {mensaje}")


class Validador:
    """Acumula los errores de un formulario para mostrarlos todos de una vez."""

    def __init__(self):
        self.errores = {}
        self.datos = {}

    def campo(self, nombre: str, funcion, *args, **kwargs):
        try:
            self.datos[nombre] = funcion(*args, campo=nombre, **kwargs)
        except ErrorValidacion as e:
            self.errores[e.campo] = e.mensaje
        return self

    def pareja(self, nombres, funcion, *args, **kwargs):
        """Para reglas que miran dos campos a la vez, como un rango o unas fechas.

        La función recibe los nombres de los campos y devuelve los dos valores ya
        normalizados; el error queda asociado al campo que la regla señale.
        """
        try:
            resultados = funcion(*args, **kwargs)
        except ErrorValidacion as e:
            self.errores[e.campo] = e.mensaje
            return self
        for nombre, valor in zip(nombres, resultados):
            self.datos[nombre] = valor
        return self

    @property
    def valido(self) -> bool:
        return not self.errores

    def resumen(self) -> str:
        """Un solo texto para las vistas que muestran una sola línea de error."""
        return " · ".join(self.errores.values())


# ── Números ─────────────────────────────────────────────────────────────────

def _a_numero(valor, campo: str):
    if valor is None or (isinstance(valor, str) and not valor.strip()):
        raise ErrorValidacion(campo, "Es obligatorio")
    if isinstance(valor, str):
        # Los formularios pueden llegar con separador de miles o coma decimal.
        valor = valor.strip().replace(" ", "").replace(",", ".")
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        raise ErrorValidacion(campo, "Debe ser un número")
    if numero != numero or numero in (float("inf"), float("-inf")):
        raise ErrorValidacion(campo, "Debe ser un número")
    return numero


def entero(valor, campo: str = "campo", minimo: int = 0, maximo: int = None) -> int:
    numero = _a_numero(valor, campo)
    if numero != int(numero):
        raise ErrorValidacion(campo, "Debe ser un número entero, sin decimales")
    numero = int(numero)
    if numero < minimo:
        raise ErrorValidacion(
            campo, "No puede ser negativo" if minimo == 0 else f"No puede ser menor que {minimo}")
    if maximo is not None and numero > maximo:
        raise ErrorValidacion(campo, f"No puede ser mayor que {maximo}")
    return numero


def decimal(valor, campo: str = "campo", minimo: float = 0, maximo: float = None,
            decimales: int = 2) -> float:
    numero = _a_numero(valor, campo)
    if numero < minimo:
        raise ErrorValidacion(
            campo, "No puede ser negativo" if minimo == 0 else f"No puede ser menor que {minimo}")
    if maximo is not None and numero > maximo:
        raise ErrorValidacion(campo, f"No puede ser mayor que {maximo}")
    return round(numero, decimales)


def dinero(valor, campo: str = "campo", minimo: float = 0) -> float:
    """Un monto en pesos: nunca negativo, con dos decimales."""
    return decimal(valor, campo, minimo=minimo, decimales=2)


def precio(valor, campo: str = "campo") -> float:
    """Un precio de venta: estrictamente mayor que cero."""
    monto = dinero(valor, campo)
    if monto == 0:
        raise ErrorValidacion(campo, "Debe ser mayor que cero")
    return monto


def cantidad(valor, campo: str = "campo", minimo: float = 1, fraccionaria: bool = False):
    """Unidades de una línea. La web factura enteros; la API admite fracciones."""
    if fraccionaria:
        monto = decimal(valor, campo, minimo=0, decimales=3)
        if monto < minimo:
            raise ErrorValidacion(campo, f"Debe ser al menos {minimo}")
        return monto
    return entero(valor, campo, minimo=minimo)


def porcentaje(valor, campo: str = "campo") -> float:
    """De 0 a 100. Un descuento del 150 % dejaría la base gravable en negativo."""
    return decimal(valor, campo, minimo=0, maximo=100, decimales=3)


# ── Texto ───────────────────────────────────────────────────────────────────

# Se valida por categoría de carácter y no con una expresión regular de rangos
# porque `isalpha()` ya entiende tildes y ñ sin listarlas a mano.
_SIGNOS_NOMBRE = set(" '-.")
_SIGNOS_RAZON_SOCIAL = set(" '-.,&/#()")


def texto(valor, campo: str = "campo", maximo: int = 255, minimo: int = 1,
          requerido: bool = True) -> str:
    valor = (valor or "").strip()
    if not valor:
        if requerido:
            raise ErrorValidacion(campo, "Es obligatorio")
        return ""
    if len(valor) < minimo:
        raise ErrorValidacion(campo, f"Debe tener al menos {minimo} caracteres")
    if len(valor) > maximo:
        raise ErrorValidacion(campo, f"No puede pasar de {maximo} caracteres")
    return valor


def nombre_persona(valor, campo: str = "nombre", maximo: int = 200,
                   requerido: bool = True) -> str:
    """Nombre de una persona: letras y espacios, sin dígitos."""
    valor = texto(valor, campo, maximo=maximo, minimo=2, requerido=requerido)
    if not valor:
        return ""
    if any(c.isdigit() for c in valor):
        raise ErrorValidacion(campo, "No puede contener números")
    if not all(c.isalpha() or c in _SIGNOS_NOMBRE for c in valor):
        raise ErrorValidacion(campo, "Solo puede contener letras, espacios, apóstrofos y guiones")
    if not any(c.isalpha() for c in valor):
        raise ErrorValidacion(campo, "Debe contener letras")
    return valor


def razon_social(valor, campo: str = "nombre", maximo: int = 255,
                 requerido: bool = True) -> str:
    """Nombre de una empresa.

    A diferencia del nombre de una persona, aquí los dígitos son legítimos:
    «Comercial 3M S.A.S.» es una razón social válida. Aplicarle la regla de
    «solo letras» rompería el registro de empresas.
    """
    valor = texto(valor, campo, maximo=maximo, minimo=2, requerido=requerido)
    if not valor:
        return ""
    if not all(c.isalnum() or c in _SIGNOS_RAZON_SOCIAL for c in valor):
        raise ErrorValidacion(campo, "Contiene caracteres que no se permiten")
    if not any(c.isalpha() for c in valor):
        raise ErrorValidacion(campo, "Debe contener letras")
    return valor


def sku(valor, campo: str = "sku", maximo: int = 60) -> str:
    valor = texto(valor, campo, maximo=maximo)
    if not all(c.isalnum() or c in "-_./" for c in valor):
        raise ErrorValidacion(campo, "Solo puede contener letras, números, guiones y puntos")
    return valor.upper()


_CORREO = re.compile(r"^[^@\s]+@[^@\s.]+(\.[^@\s.]+)+$")


def correo(valor, campo: str = "correo", requerido: bool = False) -> str:
    valor = (valor or "").strip()
    if not valor:
        if requerido:
            raise ErrorValidacion(campo, "Es obligatorio")
        return ""
    if len(valor) > 150 or not _CORREO.match(valor):
        raise ErrorValidacion(campo, "No parece un correo válido")
    return valor.lower()


def telefono(valor, campo: str = "telefono", requerido: bool = False) -> str:
    valor = (valor or "").strip()
    if not valor:
        if requerido:
            raise ErrorValidacion(campo, "Es obligatorio")
        return ""
    if not all(c.isdigit() or c in " +-()" for c in valor):
        raise ErrorValidacion(campo, "Solo puede contener números, espacios, + y guiones")
    digitos = sum(c.isdigit() for c in valor)
    if not 7 <= digitos <= 15:
        raise ErrorValidacion(campo, "Debe tener entre 7 y 15 dígitos")
    return valor


# ── Identificación ──────────────────────────────────────────────────────────

# Códigos del anexo técnico de la DIAN, que es también lo que se guarda en
# `customers.document_type` y viaja al XML sin traducción. `solo_digitos` distingue
# los documentos colombianos numéricos de los que pueden traer letras, como el
# pasaporte; `abreviatura` es lo que se le muestra a una persona, porque nadie lee
# «13» y entiende «cédula».
TIPOS_DOCUMENTO = {
    "11": {"abreviatura": "RC",     "nombre": "Registro civil",
           "solo_digitos": True,  "largo": (6, 15)},
    "12": {"abreviatura": "TI",     "nombre": "Tarjeta de identidad",
           "solo_digitos": True,  "largo": (6, 15)},
    "13": {"abreviatura": "CC",     "nombre": "Cédula de ciudadanía",
           "solo_digitos": True,  "largo": (4, 10)},
    "21": {"abreviatura": "TE",     "nombre": "Tarjeta de extranjería",
           "solo_digitos": False, "largo": (4, 20)},
    "22": {"abreviatura": "CE",     "nombre": "Cédula de extranjería",
           "solo_digitos": False, "largo": (4, 20)},
    "31": {"abreviatura": "NIT",    "nombre": "NIT",
           "solo_digitos": True,  "largo": (8, 10)},
    "41": {"abreviatura": "PA",     "nombre": "Pasaporte",
           "solo_digitos": False, "largo": (5, 20)},
    "42": {"abreviatura": "DIE",    "nombre": "Documento de identificación extranjero",
           "solo_digitos": False, "largo": (3, 30)},
    "50": {"abreviatura": "NIT-EX", "nombre": "NIT de otro país",
           "solo_digitos": False, "largo": (3, 30)},
    "91": {"abreviatura": "NUIP",   "nombre": "NUIP",
           "solo_digitos": True,  "largo": (6, 15)},
}

# El orden en que se ofrecen en los formularios: primero lo que más se factura.
ORDEN_TIPOS_DOCUMENTO = ("13", "31", "22", "41", "12", "11", "21", "42", "50", "91")


def tipo_documento(valor, campo: str = "tipo_documento") -> str:
    valor = (valor or "").strip()
    if valor not in TIPOS_DOCUMENTO:
        raise ErrorValidacion(campo, "No es un tipo de documento válido")
    return valor


def abreviatura_documento(codigo) -> str:
    """«13» → «CC». Para badges, listados y la representación gráfica."""
    tipo = TIPOS_DOCUMENTO.get(str(codigo or "").strip())
    return tipo["abreviatura"] if tipo else (str(codigo or "").strip() or "")


def nombre_documento(codigo) -> str:
    """«13» → «Cédula de ciudadanía». Para el PDF y los formularios."""
    tipo = TIPOS_DOCUMENTO.get(str(codigo or "").strip())
    return tipo["nombre"] if tipo else (str(codigo or "").strip() or "")


def tipos_documento_ordenados():
    """Pares (código, etiqueta) para poblar un `<select>`.

    La etiqueta lleva la abreviatura al frente porque es como la gente los nombra,
    salvo cuando la abreviatura y el nombre son el mismo texto: «NIT - NIT» sobra.
    """
    pares = []
    for codigo in ORDEN_TIPOS_DOCUMENTO:
        tipo = TIPOS_DOCUMENTO[codigo]
        abreviatura, nombre = tipo["abreviatura"], tipo["nombre"]
        pares.append((codigo, nombre if abreviatura == nombre else f"{abreviatura} - {nombre}"))
    return pares


def numero_documento(valor, tipo: str, campo: str = "numero_documento") -> str:
    """Valida la identificación según su tipo.

    Una cédula solo admite dígitos; un pasaporte admite letras y números. Sin el
    tipo no se puede decidir, así que este es el par que hay que validar junto.
    """
    tipo = tipo_documento(tipo)
    regla = TIPOS_DOCUMENTO[tipo]
    # Los puntos y guiones de separación se descartan, no se rechazan: quien
    # escribe «1.090.234.567» no está cometiendo un error.
    valor = (valor or "").strip().replace(".", "").replace("-", "").replace(" ", "")
    if not valor:
        raise ErrorValidacion(campo, "Es obligatorio")

    if regla["solo_digitos"]:
        if not valor.isdigit():
            raise ErrorValidacion(campo, f"El {regla['nombre']} solo admite números")
    elif not valor.isalnum():
        raise ErrorValidacion(campo, f"El {regla['nombre']} solo admite letras y números")

    minimo, maximo = regla["largo"]
    if not minimo <= len(valor) <= maximo:
        raise ErrorValidacion(
            campo, f"El {regla['nombre']} debe tener entre {minimo} y {maximo} caracteres")
    return valor.upper() if not regla["solo_digitos"] else valor


# Pesos del algoritmo de la DIAN para el dígito de verificación del NIT.
_PESOS_DV = [3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71]


def calcular_dv(nit: str) -> int:
    """Dígito de verificación de un NIT, según el algoritmo de la DIAN."""
    digitos = "".join(c for c in str(nit or "") if c.isdigit())
    if not digitos:
        raise ErrorValidacion("nit", "Es obligatorio")
    if len(digitos) > len(_PESOS_DV):
        raise ErrorValidacion("nit", "Tiene demasiados dígitos para ser un NIT")
    suma = sum(int(d) * _PESOS_DV[i] for i, d in enumerate(reversed(digitos)))
    resto = suma % 11
    return resto if resto < 2 else 11 - resto


def nit(valor, campo: str = "nit") -> str:
    """El NIT es el documento tipo 31: solo dígitos, sin el de verificación."""
    return numero_documento(valor, "31", campo)


def codigo_ciiu(valor, campo: str = "actividad_economica", requerido: bool = False) -> str:
    """Actividad económica: el CIIU son cuatro dígitos."""
    valor = (valor or "").strip()
    if not valor:
        if requerido:
            raise ErrorValidacion(campo, "Es obligatoria")
        return ""
    if not valor.isdigit() or len(valor) != 4:
        raise ErrorValidacion(campo, "El código CIIU son cuatro dígitos")
    return valor


def prefijo(valor, campo: str = "prefijo_factura", maximo: int = 10) -> str:
    """Prefijo de la numeración autorizada, como FV o SETP."""
    valor = (valor or "").strip().upper()
    if not valor:
        raise ErrorValidacion(campo, "Es obligatorio")
    if len(valor) > maximo:
        raise ErrorValidacion(campo, f"No puede pasar de {maximo} caracteres")
    if not valor.isalnum():
        raise ErrorValidacion(campo, "Solo puede contener letras y números")
    return valor


def contrasena(valor, campo: str = "contrasena", minimo: int = 8,
               requerido: bool = True) -> str:
    """Al editar se deja vacía para conservar la actual, de ahí `requerido`."""
    valor = valor or ""
    if not valor:
        if requerido:
            raise ErrorValidacion(campo, "Es obligatoria")
        return ""
    if len(valor) < minimo:
        raise ErrorValidacion(campo, f"Debe tener al menos {minimo} caracteres")
    if len(valor) > 100:
        raise ErrorValidacion(campo, "No puede pasar de 100 caracteres")
    return valor


def sitio_web(valor, campo: str = "website", requerido: bool = False) -> str:
    valor = (valor or "").strip()
    if not valor:
        if requerido:
            raise ErrorValidacion(campo, "Es obligatorio")
        return ""
    if len(valor) > 255 or " " in valor or "." not in valor:
        raise ErrorValidacion(campo, "No parece una dirección web válida")
    return valor


def dv(valor, nit: str, campo: str = "dv") -> str:
    """Verifica el dígito contra el NIT, o lo calcula si viene vacío.

    Un NIT con dígito equivocado se imprime mal en la representación gráfica y la
    DIAN lo rechaza; es un error que conviene atajar en el formulario.
    """
    esperado = calcular_dv(nit)
    valor = (valor or "").strip()
    if not valor:
        return str(esperado)
    if not valor.isdigit() or int(valor) != esperado:
        raise ErrorValidacion(
            campo, f"El dígito de verificación no corresponde al NIT; debería ser {esperado}")
    return valor


# ── Rangos y fechas ─────────────────────────────────────────────────────────

def rango(desde, hasta, campo_desde: str = "desde", campo_hasta: str = "hasta",
          minimo: int = 1, requerido: bool = True):
    """Un rango de numeración autorizado: enteros positivos y desde ≤ hasta."""
    vacio_desde = desde is None or (isinstance(desde, str) and not desde.strip())
    vacio_hasta = hasta is None or (isinstance(hasta, str) and not hasta.strip())
    if vacio_desde and vacio_hasta:
        if requerido:
            raise ErrorValidacion(campo_desde, "Es obligatorio")
        return None, None

    inicio = entero(desde, campo_desde, minimo=minimo)
    fin = entero(hasta, campo_hasta, minimo=minimo)
    if fin < inicio:
        raise ErrorValidacion(campo_hasta, "No puede ser menor que el valor inicial")
    return inicio, fin


def _a_fecha(valor, campo: str):
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    valor = (str(valor) if valor is not None else "").strip()
    if not valor:
        return None
    try:
        return datetime.strptime(valor[:10], "%Y-%m-%d").date()
    except ValueError:
        raise ErrorValidacion(campo, "No es una fecha válida")


def fecha(valor, campo: str = "fecha", requerido: bool = True):
    resultado = _a_fecha(valor, campo)
    if resultado is None and requerido:
        raise ErrorValidacion(campo, "Es obligatoria")
    return resultado


def fechas_ordenadas(desde, hasta, campo_desde: str = "desde", campo_hasta: str = "hasta",
                     requerido: bool = True):
    inicio = fecha(desde, campo_desde, requerido=requerido)
    fin = fecha(hasta, campo_hasta, requerido=requerido)
    if inicio and fin and fin < inicio:
        raise ErrorValidacion(campo_hasta, "No puede ser anterior a la fecha inicial")
    return inicio, fin


# ── Catálogos ───────────────────────────────────────────────────────────────

# Que el formulario ofrezca un `<select>` no impide que llegue otra cosa, así que
# las listas blancas viven aquí y no solo en el HTML.
TIPOS_PERSONA = ("NATURAL", "JURIDICA")

REGIMENES_TRIBUTARIOS = (
    "NO_RESPONSABLE_IVA", "RESPONSABLE_IVA", "GRAN_CONTRIBUYENTE",
    "AUTORETENEDOR", "REGIMEN_SIMPLE",
)

TIPOS_DOCUMENTO_FISCAL = ("FV", "NC", "ND")

# Códigos de impuesto de la DIAN, los mismos que documenta el proyecto y que usa
# `cufe_service` al armar la cadena del CUFE.
CODIGOS_IMPUESTO_DIAN = {
    "01": "IVA",
    "02": "Impuesto al consumo",
    "03": "ICA",
    "04": "INC",
    "05": "Retención en la fuente",
    "06": "ReteICA",
    "07": "ReteIVA",
    "08": "ReteCREE",
    "ZY": "Exento",
}


def bandera(valor, campo: str = "campo") -> int:
    """Una casilla de sí/no. Llega del formulario como «0» o «1»."""
    return entero(valor, campo, minimo=0, maximo=1)

def opcion(valor, permitidas, campo: str = "campo", requerido: bool = True) -> str:
    """Un valor de un catálogo cerrado.

    Que el formulario ofrezca un `<select>` no impide que llegue otra cosa: la
    lista blanca tiene que estar también en el servidor.
    """
    valor = (valor or "").strip()
    if not valor:
        if requerido:
            raise ErrorValidacion(campo, "Es obligatorio")
        return ""
    if valor not in permitidas:
        raise ErrorValidacion(campo, "No es una opción válida")
    return valor
