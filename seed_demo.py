"""Genera una operación de demostración de ~6 meses para Siste Soluciones.

    python seed_demo.py            # genera los datos
    python seed_demo.py --limpiar  # deshace exactamente lo generado

Sirve para poder mostrar el tablero y los reportes con contenido real mientras el
sistema todavía no opera con datos de producción. Crea compras de inventario,
ventas, notas crédito totales y parciales, notas débito, cartera repartida en
todos los tramos de antigüedad, mermas y ajustes por conteo.

Dos cosas importantes:

* Todo pasa por el kardex (`inventory_service`), así que el stock, los
  movimientos y los reportes quedan cuadrados entre sí.
* Cada objeto creado se anota en `seed_demo_manifest.json`. `--limpiar` borra
  exactamente eso y restaura los consecutivos y el stock previos: no adivina ni
  borra por rango de fechas.

El generador es determinista (semilla fija), así que dos ejecuciones producen la
misma operación.
"""
import argparse
import json
import os
import random
import sys
from datetime import date, datetime, timedelta

from database import execute_query, execute_update, get_many, get_one
from services.cufe_service import generate_cufe
from services.inventory_service import (ajustar_stock, registrar_movimiento,
                                        registrar_movimientos_documento,
                                        registrar_saldo_inicial)
from services.invoice_service import create_invoice, create_invoice_detail

MANIFIESTO = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "seed_demo_manifest.json")

EMPRESA = 6                  # Gran Caridad — la empresa de los usuarios de prueba
VENDEDORES = [1, 2, 5]       # Administrator (ADMIN), Brandon (ADMIN), Yuliana (CAJERO)
HOY = date(2026, 8, 9)
INICIO = date(2026, 2, 16)

# Estados de pago (tabla pagos_factura)
PAGADA, PENDIENTE, PARCIAL, VENCIDA = 1, 2, 3, 4
ANULADA, PARC_ANULADA = 8, 9

METODOS = [1, 2, 3, 4]       # efectivo, débito, crédito, transferencia
DESC_FACTURA = [(55502, 5.0), (55503, 15.0), (55507, 7.0)]

PRODUCTOS_NUEVOS = [
    # sku, nombre, descripcion, precio, stock_min, cod_impuesto, unidad
    ("TEC-007", "Webcam Full HD 1080p", "Cámara web con micrófono integrado",
     135000, 6, 1, "C62"),
    ("TEC-008", "Audífonos Bluetooth ANC", "Diadema con cancelación de ruido",
     260000, 4, 1, "C62"),
    ("TEC-009", "Disco Duro Externo 1TB", "Portátil USB 3.0",
     215000, 5, 1, "C62"),
    ("TEC-010", "Base Refrigerante para Portátil", "Con doble ventilador",
     72000, 8, 1, "C62"),
    ("PAP-002", "Cuaderno Argollado 100 hojas", "Cuadriculado tamaño carta",
     9500, 25, 8, "C62"),
    ("SER-002", "Instalación de Software", "Servicio técnico por equipo",
     60000, 0, 1, "WSD"),
]

CLIENTES_NUEVOS = [
    # nombre, tipo_doc (codigo DIAN), documento, tel, correo, direccion, ciudad, depto, tipo_persona
    ("Distribuciones El Progreso S.A.S.", "31", "9012345671", "6076541234",
     "compras@elprogreso.com.co", "Calle 10 # 12-34", "Cúcuta",
     "Norte de Santander", "JURIDICA"),
    ("Papelería La Esquina Ltda.", "31", "9008765432", "6072223344",
     "ventas@laesquina.com.co", "Av. 5 # 8-90", "Cúcuta",
     "Norte de Santander", "JURIDICA"),
    ("Carlos Andrés Peña", "13", "1090556677", "3155667788",
     "capena@correo.com", "Barrio Caobos, Casa 14", "Cúcuta",
     "Norte de Santander", "NATURAL"),
    ("Laura Ximena Duarte", "13", "1094778899", "3009988776",
     "lxduarte@correo.com", "Urb. Los Pinos Mz D", "Cúcuta",
     "Norte de Santander", "NATURAL"),
]


# ── Manifiesto ───────────────────────────────────────────────────────────────

class Manifiesto:
    """Lleva la cuenta de lo creado para poder deshacerlo con exactitud."""

    def __init__(self):
        self.datos = {"generado": None, "facturas": [], "productos": [],
                      "clientes": [], "movimientos_sueltos": [],
                      "consecutivos_previos": {}, "stock_previo": {},
                      "fechas_apertura_previas": {}}

    def guardar(self):
        self.datos["generado"] = datetime.now().isoformat(timespec="seconds")
        with open(MANIFIESTO, "w", encoding="utf-8") as f:
            json.dump(self.datos, f, indent=2, ensure_ascii=False)

    @staticmethod
    def cargar():
        if not os.path.exists(MANIFIESTO):
            return None
        with open(MANIFIESTO, encoding="utf-8") as f:
            m = Manifiesto()
            m.datos = json.load(f)
            return m


# ── Utilidades ───────────────────────────────────────────────────────────────

def _dt(dia: date, hora=None, minuto=None):
    """Fecha con una hora comercial plausible."""
    hora = hora if hora is not None else random.randint(8, 18)
    minuto = minuto if minuto is not None else random.randint(0, 59)
    return datetime(dia.year, dia.month, dia.day, hora, minuto,
                    random.randint(0, 59))


def _dias_habiles(desde: date, hasta: date):
    dia = desde
    while dia <= hasta:
        if dia.weekday() < 6:          # se factura de lunes a sábado
            yield dia
        dia += timedelta(days=1)


def _consecutivo(campo):
    fila = get_one(f"SELECT {campo} AS n FROM empresas WHERE cod_empresa = %s", (EMPRESA,))
    return int(fila["n"] or 1)


def _avanzar(campo, valor):
    execute_update(f"UPDATE empresas SET {campo} = %s WHERE cod_empresa = %s",
                   (valor, EMPRESA))


# ── Emisión de documentos ────────────────────────────────────────────────────

def emitir_factura(manifiesto, cuando: datetime, cod_cliente, cod_usuario, lineas,
                   cod_metodo_pago, cod_pago, fecha_vencimiento,
                   descuento_factura=None, observaciones=""):
    """Replica el cálculo de routes/invoice.py para que los totales cuadren.

    Los importes no se inventan: misma secuencia de redondeos que la ruta real,
    incluido el prorrateo del IVA cuando hay descuento global.
    """
    empresa = get_one("SELECT * FROM empresas WHERE cod_empresa = %s", (EMPRESA,))

    subtotal_bruto = total_descuentos = total_impuestos = 0.0
    detalle = []
    for cod_producto, cantidad, desc_pct in lineas:
        prod = get_one(
            "SELECT p.precio_unitario, i.porcentaje AS tax_pct FROM productos p "
            "LEFT JOIN impuestos i ON p.cod_impuesto = i.cod_impuesto "
            "WHERE p.cod_producto = %s", (cod_producto,))
        precio = float(prod["precio_unitario"])
        tax_pct = float(prod["tax_pct"] or 0)

        valor_bruto = precio * cantidad
        desc_valor = round(valor_bruto * desc_pct / 100, 2)
        base = valor_bruto - desc_valor
        imp_valor = round(base * tax_pct / 100, 2)

        subtotal_bruto += valor_bruto
        total_descuentos += desc_valor
        total_impuestos += imp_valor
        detalle.append({
            "cod_producto": cod_producto, "cantidad": cantidad,
            "precio_unitario": precio, "subtotal": base,
            "descuento_porcentaje": desc_pct, "descuento_valor": desc_valor,
            "descuento_descripcion": "Seasonal Discount" if desc_pct else "",
            "impuesto_porcentaje": tax_pct, "impuesto_valor": imp_valor,
        })

    cod_desc_fac, desc_fac_pct = (descuento_factura or (None, 0.0))
    base_neta = subtotal_bruto - total_descuentos
    valor_desc_factura = round(base_neta * desc_fac_pct / 100, 2) if desc_fac_pct else 0.0

    if base_neta > 0 and valor_desc_factura > 0:
        ajuste = round(total_impuestos * (valor_desc_factura / base_neta), 2)
        total_impuestos = round(total_impuestos - ajuste, 2)

    descripcion_desc = ""
    if cod_desc_fac:
        fila = get_one("SELECT descripcion FROM descuentos WHERE cod_descuento = %s",
                       (cod_desc_fac,))
        descripcion_desc = fila["descripcion"] if fila else ""

    total_descuentos = round(total_descuentos + valor_desc_factura, 2)
    subtotal_neto = round(subtotal_bruto - total_descuentos, 2)
    total_impuestos = round(total_impuestos, 2)
    total = round(subtotal_neto + total_impuestos, 2)

    consecutivo = _consecutivo("consecutivo_actual")
    numero = f"{empresa.get('prefijo_factura') or 'FV'}{consecutivo}"
    cliente = get_one("SELECT document_number FROM customers WHERE customer_id = %s",
                      (cod_cliente,)) or {}

    cufe = generate_cufe({
        "numero_factura": numero, "fecha": cuando, "subtotal": subtotal_neto,
        "total_impuestos": total_impuestos, "total": total,
        "document_number": cliente.get("document_number", ""),
    }, empresa)

    cod_factura = create_invoice(
        cod_cliente=cod_cliente, cod_usuario=cod_usuario, cod_empresa=EMPRESA,
        cod_metodo_pago=cod_metodo_pago, cod_pago=cod_pago,
        fecha=cuando.strftime("%Y-%m-%d %H:%M:%S"),
        total=total, subtotal=subtotal_neto, total_descuentos=total_descuentos,
        total_impuestos=total_impuestos, tipo_factura="FV",
        observaciones=observaciones,
        fecha_vencimiento=fecha_vencimiento.strftime("%Y-%m-%d"),
        cufe=cufe, numero_factura=numero,
        forma_pago="CONTADO" if cod_pago == PAGADA else "CREDITO",
        cod_descuento_factura=cod_desc_fac,
        descripcion_descuento_factura=descripcion_desc or None,
    )
    manifiesto.datos["facturas"].append(cod_factura)

    for d in detalle:
        create_invoice_detail(cod_factura=cod_factura, **d)

    registrar_movimientos_documento(
        detalle, tipo="SALIDA", motivo="VENTA", cod_factura=cod_factura,
        cod_usuario=cod_usuario, observaciones=f"Venta {numero}",
        fecha=cuando.strftime("%Y-%m-%d %H:%M:%S"))

    _avanzar("consecutivo_actual", consecutivo + 1)
    return {"cod_factura": cod_factura, "numero": numero, "total": total,
            "detalle": detalle, "fecha": cuando, "cod_cliente": cod_cliente,
            "cod_usuario": cod_usuario, "cod_metodo_pago": cod_metodo_pago,
            "documento_cliente": cliente.get("document_number", "")}


def emitir_nota_credito(manifiesto, factura, cuando: datetime, motivo,
                        parcial_de=None):
    """NC total o parcial. `parcial_de` es {cod_producto: cantidad}."""
    empresa = get_one("SELECT * FROM empresas WHERE cod_empresa = %s", (EMPRESA,))
    consecutivo = _consecutivo("consecutivo_nc")
    numero = f"NC{consecutivo}"

    lineas_nc, subtotal = [], 0.0
    total_desc = total_imp = 0.0

    for d in factura["detalle"]:
        if parcial_de is not None:
            cantidad = parcial_de.get(d["cod_producto"], 0)
            if cantidad <= 0:
                continue
            ratio = cantidad / d["cantidad"]
        else:
            cantidad, ratio = d["cantidad"], 1.0

        sub = -round(d["subtotal"] * ratio, 2)
        des = -round(d["descuento_valor"] * ratio, 2)
        imp = -round(d["impuesto_valor"] * ratio, 2)
        subtotal += sub
        total_desc += des
        total_imp += imp
        lineas_nc.append({**d, "cantidad": cantidad, "subtotal": sub,
                          "descuento_valor": des, "impuesto_valor": imp})

    if not lineas_nc:
        return None

    subtotal = round(subtotal, 2)
    total_imp = round(total_imp, 2)
    total = round(subtotal + total_imp, 2)

    cufe = generate_cufe({
        "numero_factura": numero, "fecha": cuando, "subtotal": abs(subtotal),
        "total_impuestos": abs(total_imp), "total": abs(total),
        "document_number": factura["documento_cliente"],
    }, empresa)

    cod_nc = create_invoice(
        cod_cliente=factura["cod_cliente"], cod_usuario=factura["cod_usuario"],
        cod_empresa=EMPRESA, cod_metodo_pago=factura["cod_metodo_pago"],
        cod_pago=PAGADA, fecha=cuando.strftime("%Y-%m-%d %H:%M:%S"),
        total=total, subtotal=subtotal, total_descuentos=round(total_desc, 2),
        total_impuestos=total_imp, tipo_factura="NC", observaciones=motivo,
        fecha_vencimiento=cuando.strftime("%Y-%m-%d"),
        cufe=cufe, numero_factura=numero, forma_pago="CONTADO")
    manifiesto.datos["facturas"].append(cod_nc)

    for d in lineas_nc:
        create_invoice_detail(
            cod_factura=cod_nc, cod_producto=d["cod_producto"], cantidad=d["cantidad"],
            precio_unitario=d["precio_unitario"], subtotal=d["subtotal"],
            descuento_porcentaje=d["descuento_porcentaje"],
            descuento_valor=d["descuento_valor"],
            descuento_descripcion=d["descuento_descripcion"],
            impuesto_porcentaje=d["impuesto_porcentaje"],
            impuesto_valor=d["impuesto_valor"])

    execute_update(
        "UPDATE facturas SET cod_factura_referencia = %s, motivo_nota = %s "
        "WHERE cod_factura = %s", (factura["cod_factura"], motivo, cod_nc))
    execute_update("UPDATE facturas SET cod_pago = %s WHERE cod_factura = %s",
                   (PARC_ANULADA if parcial_de else ANULADA, factura["cod_factura"]))

    registrar_movimientos_documento(
        [{"cod_producto": d["cod_producto"], "cantidad": abs(d["cantidad"])}
         for d in lineas_nc],
        tipo="ENTRADA", motivo="DEVOLUCION", cod_factura=cod_nc,
        cod_usuario=factura["cod_usuario"],
        observaciones=f"Devolución por {numero} sobre {factura['numero']}",
        fecha=cuando.strftime("%Y-%m-%d %H:%M:%S"))

    _avanzar("consecutivo_nc", consecutivo + 1)
    return cod_nc


def emitir_nota_debito(manifiesto, factura, cuando: datetime, motivo, valor):
    """ND por flete, interés u otro cargo adicional, con IVA descompuesto."""
    empresa = get_one("SELECT * FROM empresas WHERE cod_empresa = %s", (EMPRESA,))
    consecutivo = _consecutivo("consecutivo_nd")
    numero = f"ND{consecutivo}"

    original = get_one("SELECT subtotal, total_impuestos FROM facturas WHERE cod_factura = %s",
                       (factura["cod_factura"],))
    sub_orig = float(original["subtotal"] or 1)
    tasa = float(original["total_impuestos"] or 0) / sub_orig if sub_orig else 0
    subtotal = round(valor / (1 + tasa), 2)
    impuesto = round(valor - subtotal, 2)
    total = round(subtotal + impuesto, 2)

    cufe = generate_cufe({
        "numero_factura": numero, "fecha": cuando, "subtotal": subtotal,
        "total_impuestos": impuesto, "total": total,
        "document_number": factura["documento_cliente"],
    }, empresa)

    cod_nd = create_invoice(
        cod_cliente=factura["cod_cliente"], cod_usuario=factura["cod_usuario"],
        cod_empresa=EMPRESA, cod_metodo_pago=factura["cod_metodo_pago"],
        cod_pago=PENDIENTE, fecha=cuando.strftime("%Y-%m-%d %H:%M:%S"),
        total=total, subtotal=subtotal, total_descuentos=0,
        total_impuestos=impuesto, tipo_factura="ND", observaciones=motivo,
        fecha_vencimiento=(cuando.date() + timedelta(days=30)).strftime("%Y-%m-%d"),
        cufe=cufe, numero_factura=numero, forma_pago="CREDITO")
    manifiesto.datos["facturas"].append(cod_nd)

    execute_update(
        "UPDATE facturas SET cod_factura_referencia = %s, motivo_nota = %s "
        "WHERE cod_factura = %s", (factura["cod_factura"], motivo, cod_nd))
    _avanzar("consecutivo_nd", consecutivo + 1)
    return cod_nd


# ── Generación ───────────────────────────────────────────────────────────────

def crear_catalogo(manifiesto, apertura: datetime):
    """Amplía productos y clientes para que los rankings tengan variedad.

    `apertura` es el instante común de todos los saldos iniciales: debe ser
    anterior a la primera compra, o el kardex quedaría contando la historia al
    revés para los productos nuevos.
    """
    for sku, nombre, desc, precio, minimo, imp, unidad in PRODUCTOS_NUEVOS:
        if get_one("SELECT cod_producto FROM productos WHERE sku = %s", (sku,)):
            continue
        cod = execute_query(
            "INSERT INTO productos (sku, nombre, descripcion, precio_unitario, stock, "
            "stock_minimo, cod_impuesto, unidad_medida, activo, controla_stock) "
            "VALUES (%s,%s,%s,%s,0,%s,%s,%s,1,%s)",
            (sku, nombre, desc, precio, minimo, imp, unidad,
             0 if unidad == "WSD" else 1))
        manifiesto.datos["productos"].append(cod)
        registrar_saldo_inicial(cod, cod_usuario=2,
                                observaciones="Alta del producto",
                                fecha=apertura.strftime("%Y-%m-%d %H:%M:%S"))

    for nombre, tipo_doc, doc, tel, correo, dir_, ciudad, depto, persona in CLIENTES_NUEVOS:
        if get_one("SELECT customer_id FROM customers WHERE document_number = %s", (doc,)):
            continue
        cod = execute_query(
            "INSERT INTO customers (full_name, document_type, document_number, phone, "
            "email, address, ciudad, departamento, pais, tipo_persona, "
            "regimen_tributario, activo) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'Colombia',%s,%s,1)",
            (nombre, tipo_doc, doc, tel, correo, dir_, ciudad, depto, persona,
             "RESPONSABLE_IVA" if persona == "JURIDICA" else "NO_RESPONSABLE_IVA"))
        manifiesto.datos["clientes"].append(cod)


def comprar(manifiesto, cuando: datetime, compras):
    """Entradas por compra a proveedor."""
    for cod_producto, cantidad in compras:
        mov = registrar_movimiento(
            cod_producto, "ENTRADA", "COMPRA", cantidad, cod_usuario=2,
            observaciones="Compra a proveedor",
            fecha=cuando.strftime("%Y-%m-%d %H:%M:%S"))
        if mov:
            manifiesto.datos["movimientos_sueltos"].append(mov["cod_movimiento"])


def generar(manifiesto):
    random.seed(20260809)

    productos = get_many(
        "SELECT cod_producto, precio_unitario, controla_stock, stock "
        "FROM productos WHERE activo = 1")
    manifiesto.datos["stock_previo"] = {
        str(p["cod_producto"]): int(p["stock"] or 0) for p in productos}
    manifiesto.datos["consecutivos_previos"][str(EMPRESA)] = {
        "consecutivo_actual": _consecutivo("consecutivo_actual"),
        "consecutivo_nc": _consecutivo("consecutivo_nc"),
        "consecutivo_nd": _consecutivo("consecutivo_nd"),
    }

    # Los saldos de apertura de la migración quedaron fechados el día en que se
    # aplicó, o sea después de la operación que estamos por generar. El kardex
    # mostraría "saldo de apertura" al final de la lista, detrás de las ventas.
    apertura = _dt(INICIO - timedelta(days=2), 6, 0)
    manifiesto.datos["fechas_apertura_previas"] = {
        str(m["cod_movimiento"]): m["fecha"].strftime("%Y-%m-%d %H:%M:%S.%f")
        for m in get_many("SELECT cod_movimiento, fecha FROM movimientos_inventario "
                          "WHERE motivo = 'INICIAL' AND fecha > %s", (apertura,))
    }
    execute_update(
        "UPDATE movimientos_inventario SET fecha = %s "
        "WHERE motivo = 'INICIAL' AND fecha > %s",
        (apertura.strftime("%Y-%m-%d %H:%M:%S"), apertura))

    crear_catalogo(manifiesto, apertura)

    con_stock = [p["cod_producto"] for p in get_many(
        "SELECT cod_producto FROM productos WHERE activo = 1 AND controla_stock = 1")]
    servicios = [p["cod_producto"] for p in get_many(
        "SELECT cod_producto FROM productos WHERE activo = 1 AND controla_stock = 0")]
    vendibles = con_stock + servicios
    clientes = [c["customer_id"] for c in get_many(
        "SELECT customer_id FROM customers WHERE activo = 1 AND customer_id <> 1")]

    # Abastecimiento inicial: sin esto las primeras ventas no tendrían saldo.
    # Las cantidades se calibran contra el volumen de ventas para que el
    # inventario final equivalga a un par de meses de rotación y no a un año.
    comprar(manifiesto, _dt(INICIO - timedelta(days=1), 7, 30),
            [(p, random.randint(28, 55)) for p in con_stock])

    dias = list(_dias_habiles(INICIO, HOY - timedelta(days=1)))
    facturas = []
    proxima_compra = INICIO + timedelta(days=25)

    for dia in dias:
        if dia >= proxima_compra:
            # Se repone lo que va quedando bajo, no todo el catálogo a ciegas.
            bajos = [p["cod_producto"] for p in get_many(
                "SELECT cod_producto FROM productos "
                "WHERE activo = 1 AND controla_stock = 1 AND stock <= stock_minimo * 3 "
                "ORDER BY stock LIMIT 5")]
            if bajos:
                comprar(manifiesto, _dt(dia, 7, 45),
                        [(p, random.randint(15, 35)) for p in bajos])
            proxima_compra = dia + timedelta(days=random.randint(18, 26))

        # Entre 0 y 3 facturas por día hábil: unos días sin ventas dan una serie
        # más creíble que un flujo perfectamente parejo.
        for _ in range(random.choices([0, 1, 2, 3], weights=[18, 40, 30, 12])[0]):
            n_lineas = random.choices([1, 2, 3, 4], weights=[42, 33, 18, 7])[0]
            elegidos = random.sample(vendibles, min(n_lineas, len(vendibles)))
            lineas = []
            for cod in elegidos:
                cantidad = random.choices([1, 2, 3, 5, 8], weights=[46, 26, 15, 9, 4])[0]
                if cod in con_stock:
                    disponible = get_one(
                        "SELECT stock FROM productos WHERE cod_producto = %s", (cod,))["stock"]
                    if disponible < cantidad:
                        continue
                desc = random.choices([0, 5, 10, 20], weights=[68, 14, 13, 5])[0]
                lineas.append((cod, cantidad, float(desc)))
            if not lineas:
                continue

            a_credito = random.random() < 0.38
            venc = dia + timedelta(days=30) if a_credito else dia
            estado = PENDIENTE if a_credito else PAGADA

            facturas.append(emitir_factura(
                manifiesto, _dt(dia), random.choice(clientes),
                random.choices(VENDEDORES, weights=[15, 45, 40])[0], lineas,
                random.choice(METODOS), estado, venc,
                descuento_factura=random.choice(DESC_FACTURA) if random.random() < 0.16 else None,
                observaciones=random.choice(
                    ["", "", "", "Entrega en tienda", "Cliente frecuente",
                     "Despacho a domicilio"])))

    # ── Cartera: repartir vencimientos en todos los tramos ──────────────────
    # Sin esto la gráfica de antigüedad quedaría concentrada en un solo tramo.
    candidatas = [f for f in facturas
                  if get_one("SELECT cod_pago FROM facturas WHERE cod_factura = %s",
                             (f["cod_factura"],))["cod_pago"] == PENDIENTE]
    random.shuffle(candidatas)

    tramos = [
        (VENCIDA, 100, 150, 3),   # más de 90 días vencida
        (VENCIDA, 62, 89, 3),     # 61–90
        (PARCIAL, 33, 58, 4),     # 31–60, con abono parcial
        (VENCIDA, 4, 28, 5),      # 1–30
        (PENDIENTE, -25, -3, 6),  # todavía por vencer
    ]
    i = 0
    for estado, dmin, dmax, cuantas in tramos:
        for _ in range(cuantas):
            if i >= len(candidatas):
                break
            f = candidatas[i]
            i += 1
            venc = HOY - timedelta(days=random.randint(dmin, dmax))
            execute_update(
                "UPDATE facturas SET cod_pago = %s, fecha_vencimiento = %s, "
                "forma_pago = 'CREDITO' WHERE cod_factura = %s",
                (estado, venc.strftime("%Y-%m-%d"), f["cod_factura"]))

    # El resto de las pendientes viejas se dan por cobradas.
    for f in candidatas[i:]:
        execute_update("UPDATE facturas SET cod_pago = %s WHERE cod_factura = %s",
                       (PAGADA, f["cod_factura"]))

    # ── Devoluciones y ajustes al cliente ───────────────────────────────────
    con_productos = [f for f in facturas
                     if any(d["cod_producto"] in con_stock for d in f["detalle"])]
    random.shuffle(con_productos)

    motivos_nc = ["Producto defectuoso reportado por el cliente",
                  "Error en la cantidad facturada",
                  "Devolución por garantía",
                  "Anulación solicitada por el cliente"]

    for f in con_productos[:5]:                       # NC totales
        emitir_nota_credito(manifiesto, f,
                            _dt(f["fecha"].date() + timedelta(days=random.randint(2, 12))),
                            random.choice(motivos_nc))

    for f in con_productos[5:11]:                     # NC parciales
        devolver = {d["cod_producto"]: max(1, d["cantidad"] // 2)
                    for d in f["detalle"] if d["cod_producto"] in con_stock}
        if devolver:
            emitir_nota_credito(
                manifiesto, f,
                _dt(f["fecha"].date() + timedelta(days=random.randint(2, 15))),
                "Devolución parcial de mercancía", parcial_de=devolver)

    motivos_nd = [("Flete por despacho a domicilio", 45000),
                  ("Intereses por mora", 78000),
                  ("Cargo por reposición de empaque", 32000),
                  ("Ajuste de precio por diferencia en lista", 96000)]
    for f, (motivo, valor) in zip(con_productos[11:15], motivos_nd):
        emitir_nota_debito(manifiesto, f,
                           _dt(f["fecha"].date() + timedelta(days=random.randint(3, 20))),
                           motivo, valor)

    # ── Mermas y conteos físicos ────────────────────────────────────────────
    for cod, cantidad, motivo, dias_atras in [
            (con_stock[0], 3, "Unidades dañadas en bodega", 95),
            (con_stock[2], 2, "Producto vencido en exhibición", 58),
            (con_stock[4], 4, "Rotura durante el transporte", 21)]:
        try:
            mov = registrar_movimiento(
                cod, "SALIDA", "MERMA", cantidad, cod_usuario=2,
                observaciones=motivo,
                fecha=_dt(HOY - timedelta(days=dias_atras)).strftime("%Y-%m-%d %H:%M:%S"))
            if mov:
                manifiesto.datos["movimientos_sueltos"].append(mov["cod_movimiento"])
        except Exception:
            pass

    # ── Dejar el inventario con alertas visibles ────────────────────────────
    # El panel debe mostrar productos agotados y bajo mínimo, que es justamente
    # lo que el objetivo de inventario promete detectar.
    saldos_finales = [
        (con_stock[1], 0,  "Conteo físico: producto agotado"),
        (con_stock[3], 2,  "Conteo físico de fin de mes"),
        (con_stock[5], 3,  "Conteo físico de fin de mes"),
    ]
    for cod, saldo, nota in saldos_finales:
        try:
            r = ajustar_stock(cod, saldo, cod_usuario=2, observaciones=nota,
                              fecha=_dt(HOY - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S"))
            if r:
                fila = get_one("SELECT MAX(cod_movimiento) m FROM movimientos_inventario "
                               "WHERE cod_producto = %s", (cod,))
                manifiesto.datos["movimientos_sueltos"].append(fila["m"])
        except Exception:
            pass

    return facturas


# ── Verificación ─────────────────────────────────────────────────────────────

def verificar():
    """Comprueba que lo generado sea internamente consistente."""
    problemas = []

    descuadres = get_many("""
        SELECT f.cod_factura, f.numero_factura, f.total,
               ROUND(f.subtotal + f.total_impuestos, 2) AS recalculado
        FROM facturas f
        WHERE ABS(f.total - ROUND(f.subtotal + f.total_impuestos, 2)) > 0.02
    """)
    if descuadres:
        problemas.append(f"{len(descuadres)} facturas donde total <> subtotal + impuestos")

    huerfanas = get_many("""
        SELECT f.cod_factura FROM facturas f
        WHERE f.tipo_factura = 'FV'
          AND NOT EXISTS (SELECT 1 FROM detalle_factura d WHERE d.cod_factura = f.cod_factura)
    """)
    if huerfanas:
        problemas.append(f"{len(huerfanas)} facturas de venta sin líneas de detalle")

    negativos = get_many("SELECT cod_producto, stock FROM productos WHERE stock < 0")
    if negativos:
        problemas.append(f"{len(negativos)} productos con stock negativo")

    # La cadena del kardex se sigue por orden de inserción, no por fecha: es el
    # orden en que realmente se aplicaron los saldos.
    desalineados = get_many("""
        SELECT p.cod_producto, p.nombre, p.stock, m.stock_nuevo
        FROM productos p
            JOIN movimientos_inventario m ON m.cod_movimiento = (
                SELECT MAX(cod_movimiento) FROM movimientos_inventario
                WHERE cod_producto = p.cod_producto)
        WHERE p.controla_stock = 1 AND p.stock <> m.stock_nuevo
    """)
    if desalineados:
        problemas.append(
            f"{len(desalineados)} productos donde el kardex no cuadra con el stock: "
            + ", ".join(f"{d['nombre']} ({d['stock']} vs {d['stock_nuevo']})"
                        for d in desalineados[:3]))

    # Y las fechas deben contar la misma historia: nada puede ser anterior al
    # saldo de apertura del producto, o el kardex se leería al revés.
    fuera_de_orden = get_many("""
        SELECT p.nombre, COUNT(*) AS n
        FROM movimientos_inventario m
            JOIN productos p ON p.cod_producto = m.cod_producto
            JOIN (SELECT cod_producto, MIN(fecha) AS apertura
                  FROM movimientos_inventario WHERE motivo = 'INICIAL'
                  GROUP BY cod_producto) a ON a.cod_producto = m.cod_producto
        WHERE m.motivo <> 'INICIAL' AND m.fecha < a.apertura
        GROUP BY p.nombre
    """)
    if fuera_de_orden:
        problemas.append(
            f"{len(fuera_de_orden)} productos con movimientos anteriores a su saldo "
            "de apertura")

    return problemas


def resumen():
    filas = get_many("""
        SELECT tipo_factura, COUNT(*) n, COALESCE(SUM(total),0) t
        FROM facturas GROUP BY tipo_factura ORDER BY tipo_factura""")
    estados = get_many("""
        SELECT pf.status, COUNT(*) n, COALESCE(SUM(f.total),0) t
        FROM facturas f JOIN pagos_factura pf ON f.cod_pago = pf.cod_pago_factura
        WHERE f.tipo_factura = 'FV' GROUP BY pf.status ORDER BY n DESC""")
    cartera = get_one("""
        SELECT COALESCE(SUM(total),0) t,
               COALESCE(SUM(CASE WHEN fecha_vencimiento < CURDATE() THEN total END),0) v
        FROM facturas WHERE cod_pago IN (2,3,4) AND tipo_factura <> 'NC'""")
    inv = get_one("""
        SELECT COUNT(*) n, COALESCE(SUM(stock*precio_unitario),0) v,
               COALESCE(SUM(stock <= 0),0) ag,
               COALESCE(SUM(stock > 0 AND stock <= stock_minimo),0) bajo
        FROM productos WHERE activo = 1 AND controla_stock = 1""")
    movs = get_one("SELECT COUNT(*) n FROM movimientos_inventario")

    print("\n--- Resumen de la operacion " + "-" * 30)
    for f in filas:
        print(f"  {f['tipo_factura']}: {f['n']:>4} documentos   ${float(f['t']):>16,.0f}")
    print("  Estados de pago (FV):")
    for e in estados:
        print(f"    {e['status']:<22} {e['n']:>4}   ${float(e['t']):>14,.0f}")
    print(f"  Cartera por cobrar:  ${float(cartera['t']):>14,.0f} "
          f"(vencida ${float(cartera['v']):,.0f})")
    print(f"  Inventario: {inv['n']} productos, ${float(inv['v']):,.0f} · "
          f"{inv['ag']} agotados, {inv['bajo']} bajo mínimo")
    print(f"  Movimientos de kardex: {movs['n']}")


# ── Limpieza ─────────────────────────────────────────────────────────────────

def limpiar():
    m = Manifiesto.cargar()
    if not m:
        print("No hay manifiesto: no se generó nada con este script o ya se limpió.")
        return

    d = m.datos
    for cod in d["facturas"]:
        execute_update("DELETE FROM detalle_factura WHERE cod_factura = %s", (cod,))
        execute_update("DELETE FROM movimientos_inventario WHERE cod_factura = %s", (cod,))
        execute_update("DELETE FROM facturas WHERE cod_factura_referencia = %s", (cod,))
    for cod in d["facturas"]:
        execute_update("DELETE FROM facturas WHERE cod_factura = %s", (cod,))

    for cod in d["movimientos_sueltos"]:
        execute_update("DELETE FROM movimientos_inventario WHERE cod_movimiento = %s", (cod,))

    # Los movimientos de los productos nuevos se van en cascada con el producto.
    for cod in d["productos"]:
        execute_update("DELETE FROM detalle_factura WHERE cod_producto = %s", (cod,))
        execute_update("DELETE FROM productos WHERE cod_producto = %s", (cod,))
    for cod in d["clientes"]:
        execute_update("DELETE FROM facturas WHERE cod_cliente = %s", (cod,))
        execute_update("DELETE FROM customers WHERE customer_id = %s", (cod,))

    for cod_movimiento, fecha in d.get("fechas_apertura_previas", {}).items():
        execute_update("UPDATE movimientos_inventario SET fecha = %s WHERE cod_movimiento = %s",
                       (fecha, int(cod_movimiento)))

    for cod_producto, stock in d["stock_previo"].items():
        execute_update("UPDATE productos SET stock = %s WHERE cod_producto = %s",
                       (stock, int(cod_producto)))

    for cod_empresa, cons in d["consecutivos_previos"].items():
        execute_update(
            "UPDATE empresas SET consecutivo_actual=%s, consecutivo_nc=%s, "
            "consecutivo_nd=%s WHERE cod_empresa=%s",
            (cons["consecutivo_actual"], cons["consecutivo_nc"],
             cons["consecutivo_nd"], int(cod_empresa)))

    os.remove(MANIFIESTO)
    print(f"Limpieza completa: {len(d['facturas'])} documentos, "
          f"{len(d['productos'])} productos y {len(d['clientes'])} clientes eliminados; "
          f"stock y consecutivos restaurados.")


def main():
    # La consola de Windows usa cp1252 y no puede imprimir tildes ni guiones
    # largos; sin esto el resumen revienta al final de una generación correcta.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass

    parser = argparse.ArgumentParser(description="Datos de demostración de Siste Soluciones")
    parser.add_argument("--limpiar", action="store_true",
                        help="deshace exactamente lo generado por este script")
    args = parser.parse_args()

    if args.limpiar:
        limpiar()
        return

    if os.path.exists(MANIFIESTO):
        print("Ya hay datos de demostración generados.\n"
              "Ejecuta primero:  python seed_demo.py --limpiar")
        sys.exit(1)

    print("Generando operación de demostración de Siste Soluciones...")
    manifiesto = Manifiesto()
    try:
        facturas = generar(manifiesto)
    finally:
        manifiesto.guardar()   # aunque falle a la mitad, lo creado queda deshacible

    print(f"  {len(facturas)} facturas de venta emitidas")
    problemas = verificar()
    resumen()

    if problemas:
        print("\n[!] Inconsistencias detectadas:")
        for p in problemas:
            print("    -", p)
        sys.exit(1)
    print("\nVerificación: los totales, el detalle y el kardex cuadran.")


if __name__ == "__main__":
    main()
