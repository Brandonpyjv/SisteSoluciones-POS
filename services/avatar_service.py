"""Fotos de perfil: validación, normalizado y almacenamiento.

Nunca se guarda el archivo tal como llega. La imagen se abre con Pillow, se
recorta a un cuadrado y se vuelve a codificar como PNG: eso confirma que es una
imagen de verdad y descarta cualquier carga útil incrustada en un archivo que
solo tenía extensión de imagen.

El nombre del archivo lo genera el servidor. El nombre que envía el navegador no
se usa jamás: es entrada del usuario y puede traer rutas («../../main.py»).
"""
import os
import uuid

from PIL import Image, UnidentifiedImageError

CARPETA = os.path.join(os.path.dirname(__file__), '..', 'static', 'img', 'perfiles')
LADO = 320                       # px del cuadrado final
MAX_BYTES = 5 * 1024 * 1024      # 5 MB


class FotoInvalidaError(Exception):
    """El archivo no es una imagen utilizable."""


def _ruta(nombre):
    return os.path.join(CARPETA, nombre)


def _recortar_cuadrado(img):
    """Recorta al cuadrado centrado más grande que quepa."""
    lado = min(img.width, img.height)
    izq = (img.width - lado) // 2
    arriba = (img.height - lado) // 2
    return img.crop((izq, arriba, izq + lado, arriba + lado))


def guardar_foto(contenido: bytes, cod_usuario: int) -> str:
    """Procesa y guarda la imagen. Retorna el nombre del archivo generado."""
    if not contenido:
        raise FotoInvalidaError("No se recibió ningún archivo.")
    if len(contenido) > MAX_BYTES:
        raise FotoInvalidaError(
            f"La imagen pesa {len(contenido) / 1024 / 1024:.1f} MB; el máximo es 5 MB.")

    import io
    try:
        img = Image.open(io.BytesIO(contenido))
        img.verify()                              # detecta archivos corruptos
        img = Image.open(io.BytesIO(contenido))   # verify() deja el objeto inutilizable
    except (UnidentifiedImageError, OSError):
        raise FotoInvalidaError("El archivo no es una imagen válida (JPG, PNG, WEBP o GIF).")

    # Los GIF animados y los modos con paleta se aplanan a RGBA.
    img = img.convert("RGBA")
    img = _recortar_cuadrado(img).resize((LADO, LADO), Image.LANCZOS)

    os.makedirs(CARPETA, exist_ok=True)
    nombre = f"u{cod_usuario}-{uuid.uuid4().hex[:12]}.png"
    img.save(_ruta(nombre), format="PNG", optimize=True)
    return nombre


def eliminar_foto(nombre: str) -> bool:
    """Borra el archivo si existe. Silencioso si ya no está."""
    if not nombre:
        return False
    # Defensa en profundidad: aunque el nombre lo genere el servidor, se verifica
    # que no escape de la carpeta antes de borrar nada.
    ruta = os.path.abspath(_ruta(nombre))
    if not ruta.startswith(os.path.abspath(CARPETA) + os.sep):
        return False
    try:
        os.remove(ruta)
        return True
    except FileNotFoundError:
        return False
