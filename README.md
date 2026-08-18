# Siste Soluciones — Punto de Venta

Punto de venta de **Siste Soluciones S.A.S.**, comercializadora de productos
tecnológicos en Cúcuta (C.C. Gran Bulevar, local 103).

Vende, controla inventario y cobra. **No sabe facturar electrónicamente**: cuando
necesita una factura válida ante la DIAN se la pide a **FactuGest**, su proveedor
tecnológico, por medio de su API.

Esa es justamente la razón de que este sistema exista: demuestra que un negocio
puede cumplir con la facturación electrónica **sin cambiar el software con el que
ya opera**, agregándole una llamada HTTP.

---

## De dónde sale este código

Es un *fork* del punto de venta de FactuGest. La lógica de ventas, inventario,
kardex, clientes, usuarios y reportes ya estaba resuelta y probada; reescribirla
no habría demostrado nada. Lo que cambia es la marca, los datos del negocio, la
base de datos, y —sobre todo— quién emite las facturas.

| | FactuGest | Siste Soluciones |
|---|---|---|
| Qué es | Proveedor tecnológico | Un negocio que factura |
| Base de datos | `factugest` | `sistesoluciones` |
| Puerto | 8000 | 8001 |
| Numeración DIAN | La administra | La recibe |
| Resolución | Suya y de sus clientes | Ninguna: numera FactuGest |

---

## Requisitos

- Python 3.10 o superior
- MySQL o MariaDB (XAMPP sirve)
- FactuGest corriendo, para poder emitir facturas

## Instalación

```powershell
# 1 · Crear la base de datos e importar el esquema
#     (desde phpMyAdmin, o por consola)
mysql -u root -e "CREATE DATABASE sistesoluciones CHARACTER SET utf8mb4"
mysql -u root sistesoluciones < base/factugest.sql

# 2 · Entorno virtual y dependencias
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# 3 · Configuración
copy .env.example .env
#     y completar FACTUGEST_API_KEY con la llave que entrega FactuGest

# 4 · Migraciones y datos del negocio
python migrate.py
python seed_negocio.py
python seed_catalogo.py
```

> `seed_negocio.py` deja los datos de la empresa y limpia la operación de ejemplo
> que trae el volcado. `seed_catalogo.py` carga las 20 referencias que vende el
> negocio. Los dos son idempotentes.

> El archivo del volcado se llama `factugest.sql` porque es el esquema heredado.
> Se conserva el nombre a propósito: cambiarlo solo escondería de dónde viene.

## Cómo iniciar

```powershell
python main.py
```

Queda en **http://127.0.0.1:8001**. El puerto es 8001 y no 8000 porque FactuGest
ocupa ese, y los dos tienen que poder correr a la vez para que este le hable.

## Pruebas

```powershell
pip install -r requirements-dev.txt
python -m pytest
```

---

## Conexión con FactuGest

Se configura con dos variables del `.env`:

```
FACTUGEST_URL=http://127.0.0.1:8000
FACTUGEST_API_KEY=fg_live_xxxxxxxx.secreto
```

La llave la entrega FactuGest al dar de alta este negocio como cliente de su API,
y **se muestra una sola vez**. Si se pierde, se rota desde allá.

Para comprobar que la conexión funciona:

```powershell
curl -H "X-API-Key: <la llave>" http://127.0.0.1:8000/api/v1/ping
```
