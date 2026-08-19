"""
Histórico de operación de Siste Soluciones.

    python seed_historico.py            genera seis meses de operación
    python seed_historico.py --limpiar  lo deshace exactamente

Sirve para que el tablero y los reportes tengan contenido que mostrar. Sin esto
la demostración arranca con las gráficas en cero, que no dice nada de lo que el
sistema sabe hacer.

**Estos documentos no pasaron por FactuGest y no lo fingen.** Quedan marcados
como `HISTORICO`: son las ventas de antes de contratar al proveedor tecnológico,
que es exactamente la situación de cualquier negocio que adopta la facturación
electrónica teniendo años de operación encima. Las últimas quedan pendientes de
emitir, para que la pantalla de reintentos tenga algo real que mostrar.

Es determinista —la misma semilla da los mismos datos— y se verifica a sí mismo.
**No usar en producción.**
"""
import json
import random
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from database import execute_query, execute_update, get_many, get_one
from services.calculo_documento import calcular_documento
from services.inventory_service import registrar_movimiento, registrar_movimientos_documento
from services.invoice_service import create_invoice, create_invoice_detail

MANIFIESTO = Path(__file__).with_name("seed_historico_manifest.json")
SEMILLA = 20260818
MESES = 6

# Ventas que quedan sin emitir, para que la pantalla de pendientes no esté vacía.
VENTAS_PENDIENTES = 3

CLIENTES = [
    ("Distribuciones El Progreso S.A.S.", "31", "9012345671", "JURIDICA", "RESPONSABLE_IVA"),
    ("Papelería La Esquina Ltda.", "31", "9008765432", "JURIDICA", "RESPONSABLE_IVA"),
    ("Colegio San Bartolomé", "31", "8901234567", "JURIDICA", "RESPONSABLE_IVA"),
    ("Carlos Andrés Peña", "13", "1090556677", "NATURAL", "NO_RESPONSABLE_IVA"),
    ("Laura Ximena Duarte", "13", "1094778899", "NATURAL", "NO_RESPONSABLE_IVA"),
    ("Jorge Eliécer Mora", "13", "88245566", "NATURAL", "NO_RESPONSABLE_IVA"),
    ("Sandra Milena Rojas", "13", "60345678", "NATURAL", "NO_RESPONSABLE_IVA"),
    ("Consumidor Final", "13", "222222222222", "NATURAL", "NO_RESPONSABLE_IVA"),
]


class Manifiesto:
    """Registra lo creado para poder deshacerlo exactamente."""

    def __init__(self):
        self.datos = {"clientes": [], "facturas": [], "movimientos": []}

    def guardar(self):
        MANIFIESTO.write_text(json.dumps(self.datos, indent=2), encoding="utf-8")

    @staticmethod
    def cargar():
        if not MANIFIESTO.exists():
            return None
        return json.loads(MANIFIESTO.read_text(encoding="utf-8"))


# ── Limpieza ────────────────────────────────────────────────────────────────

def limpiar():
    datos = Manifiesto.cargar()
    if not datos:
        print("No hay manifiesto: nada que limpiar.")
        return

    borrados = {}
    if datos["facturas"]:
        marcas = ",".join(["%s"] * len(datos["facturas"]))
        borrados["detalle"] = execute_update(
            f"DELETE FROM detalle_factura WHERE cod_factura IN ({marcas})",
            tuple(datos["facturas"]))
        execute_update(f"UPDATE facturas SET cod_factura_referencia = NULL "
                       f"WHERE cod_factura IN ({marcas})", tuple(datos["facturas"]))
    if datos["movimientos"]:
        marcas = ",".join(["%s"] * len(datos["movimientos"]))
        borrados["movimientos"] = execute_update(
            f"DELETE FROM movimientos_inventario WHERE cod_movimiento IN ({marcas})",
            tuple(datos["movimientos"]))
    if datos["facturas"]:
        marcas = ",".join(["%s"] * len(datos["facturas"]))
        borrados["facturas"] = execute_update(
            f"DELETE FROM facturas WHERE cod_factura IN ({marcas})", tuple(datos["facturas"]))
    if datos["clientes"]:
        marcas = ",".join(["%s"] * len(datos["clientes"]))
        borrados["clientes"] = execute_update(
            f"DELETE FROM customers WHERE customer_id IN ({marcas})", tuple(datos["clientes"]))

    ajustados = _reconciliar_stock_con_kardex()

    MANIFIESTO.unlink()
    for que, cuantos in borrados.items():
        print(f"  {que:14} {cuantos} fila(s)")
    print(f"  {ajustados} producto(s) con el stock devuelto a su saldo de apertura")
    print("Histórico eliminado.")


def _reconciliar_stock_con_kardex():
    """Devuelve el stock al saldo que dicen los movimientos que quedaron.

    Borrar las salidas de venta sin tocar `productos.stock` dejaría el saldo por
    debajo de lo que sostiene el kardex, que es justo el descuadre que el
    invariante de inventario existe para impedir. Este es el único UPDATE directo
    al stock de todo el sistema, y es legítimo porque va en la dirección
    contraria: no cambia el inventario, lo devuelve a lo que el kardex afirma.
    """
    ajustados = 0
    for producto in get_many(
            "SELECT p.cod_producto, p.stock, "
            "       COALESCE(SUM(CASE WHEN m.tipo = 'ENTRADA' THEN m.cantidad "
            "                         ELSE -m.cantidad END), 0) AS kardex "
            "FROM productos p "
            "LEFT JOIN movimientos_inventario m ON p.cod_producto = m.cod_producto "
            "WHERE p.controla_stock = 1 "
            "GROUP BY p.cod_producto, p.stock"):
        if int(producto["stock"] or 0) != int(producto["kardex"]):
            execute_update("UPDATE productos SET stock = %s WHERE cod_producto = %s",
                           (int(producto["kardex"]), producto["cod_producto"]))
            ajustados += 1
    return ajustados


# ── Siembra ─────────────────────────────────────────────────────────────────

def sembrar_clientes(m: Manifiesto, cod_municipio: str):
    for nombre, tipo_doc, documento, persona, regimen in CLIENTES:
        if get_one("SELECT customer_id FROM customers WHERE document_number = %s",
                   (documento,)):
            continue
        cod = execute_query(
            "INSERT INTO customers (full_name, document_type, document_number, phone, "
            "  email, address, cod_municipio, pais, tipo_persona, regimen_tributario, activo) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, 'Colombia', %s, %s, 1)",
            (nombre, tipo_doc, documento, "60755" + documento[-5:],
             documento[:6].lower() + "@correo.com", "Cúcuta", cod_municipio,
             persona, regimen))
        m.datos["clientes"].append(cod)


def comprar(m: Manifiesto, productos, azar, cuando: datetime):
    """Entradas por compra a proveedor: sin esto el stock se agota a mitad del histórico."""
    for producto in azar.sample(productos, k=min(6, len(productos))):
        if not producto["controla_stock"]:
            continue
        mov = registrar_movimiento(
            producto["cod_producto"], "ENTRADA", "COMPRA", azar.randint(5, 25),
            observaciones="Reposición de inventario",
            fecha=cuando.strftime("%Y-%m-%d %H:%M:%S"))
        if mov:
            m.datos["movimientos"].append(mov["cod_movimiento"])


def vender(m: Manifiesto, productos, clientes, azar, cuando: datetime,
           empresa, usuario, metodo, estado_pago, historico=True):
    """Registra una venta con su detalle y su salida de inventario."""
    disponibles = [p for p in productos
                   if not p["controla_stock"] or _stock(p["cod_producto"]) >= 3]
    if not disponibles:
        return None

    lineas = []
    for producto in azar.sample(disponibles, k=azar.randint(1, 3)):
        maximo = 3 if producto["controla_stock"] else 2
        lineas.append({
            "cod_producto": producto["cod_producto"],
            "cantidad": azar.randint(1, maximo),
            "precio_unitario": float(producto["precio_unitario"]),
            "descuento_porcentaje": azar.choice([0, 0, 0, 5, 10]),
            "descuento_descripcion": "",
            "impuesto_porcentaje": float(producto["tax_pct"] or 0),
        })

    calculo = calcular_documento(lineas)

    empresa_actual = get_one("SELECT prefijo_factura, consecutivo_actual FROM empresas "
                             "WHERE cod_empresa = %s", (empresa,))
    consecutivo = int(empresa_actual["consecutivo_actual"] or 1)
    numero = f"{empresa_actual['prefijo_factura'] or 'LS'}{consecutivo}"

    a_credito = azar.random() < 0.25
    vencimiento = (cuando.date() + timedelta(days=30)) if a_credito else None

    cod_factura = create_invoice(
        cod_cliente=azar.choice(clientes), cod_usuario=usuario, cod_empresa=empresa,
        cod_metodo_pago=metodo, cod_pago=estado_pago,
        fecha=cuando.strftime("%Y-%m-%d %H:%M:%S"),
        total=calculo["total"], subtotal=calculo["subtotal"],
        total_descuentos=calculo["total_descuentos"],
        total_impuestos=calculo["total_impuestos"],
        tipo_factura="FV", observaciones=None,
        fecha_vencimiento=vencimiento.strftime("%Y-%m-%d") if vencimiento else None,
        numero_factura=numero, forma_pago="CREDITO" if a_credito else "CONTADO")
    m.datos["facturas"].append(cod_factura)

    for linea in calculo["lineas"]:
        create_invoice_detail(
            cod_factura=cod_factura, cod_producto=linea["cod_producto"],
            cantidad=linea["cantidad"], precio_unitario=linea["precio_unitario"],
            subtotal=linea["subtotal"],
            descuento_porcentaje=linea["descuento_porcentaje"],
            descuento_valor=linea["descuento_valor"],
            impuesto_porcentaje=linea["impuesto_porcentaje"],
            impuesto_valor=linea["impuesto_valor"])

    movimientos = registrar_movimientos_documento(
        calculo["lineas"], tipo="SALIDA", motivo="VENTA", cod_factura=cod_factura,
        observaciones=f"Venta {numero}", fecha=cuando.strftime("%Y-%m-%d %H:%M:%S"))
    for mov in movimientos:
        m.datos["movimientos"].append(mov["cod_movimiento"])

    execute_update("UPDATE empresas SET consecutivo_actual = %s WHERE cod_empresa = %s",
                   (consecutivo + 1, empresa))

    if historico:
        # No se inventa un CUFE: se deja constancia de que esta venta es anterior
        # a la integración con FactuGest.
        execute_update("UPDATE facturas SET factugest_estado = 'HISTORICO' "
                       "WHERE cod_factura = %s", (cod_factura,))
    return cod_factura


def _stock(cod_producto):
    fila = get_one("SELECT stock FROM productos WHERE cod_producto = %s", (cod_producto,))
    return int(fila["stock"] or 0) if fila else 0


def sembrar():
    if MANIFIESTO.exists():
        raise SystemExit("Ya hay un histórico sembrado. Ejecuta --limpiar primero.")

    empresa = get_one("SELECT cod_empresa, cod_municipio FROM empresas LIMIT 1")
    usuario = get_one("SELECT cod_usuario FROM usuarios LIMIT 1")
    metodo = get_one("SELECT cod_pago FROM metodos_pago LIMIT 1")
    estados = get_many("SELECT cod_pago_factura, status FROM pagos_factura")
    productos = get_many(
        "SELECT p.cod_producto, p.precio_unitario, p.controla_stock, i.porcentaje AS tax_pct "
        "FROM productos p LEFT JOIN impuestos i ON p.cod_impuesto = i.cod_impuesto "
        "WHERE p.activo = 1")
    if not productos:
        raise SystemExit("No hay catálogo. Ejecuta primero: python seed_catalogo.py")
    if not (empresa and usuario and metodo and estados):
        raise SystemExit("Faltan datos base. Ejecuta primero: python seed_negocio.py")

    pagado = next((e["cod_pago_factura"] for e in estados
                   if (e["status"] or "").lower() in ("paid", "pagado")), estados[0]["cod_pago_factura"])
    pendiente = next((e["cod_pago_factura"] for e in estados
                      if (e["status"] or "").lower() in ("pending", "pendiente")), pagado)

    azar = random.Random(SEMILLA)
    m = Manifiesto()

    sembrar_clientes(m, empresa["cod_municipio"])
    clientes = [c["customer_id"] for c in get_many("SELECT customer_id FROM customers")]

    hoy = date.today()
    inicio = hoy - timedelta(days=MESES * 30)
    ventas = 0

    dia = inicio
    while dia <= hoy:
        # Los domingos no se abre.
        if dia.weekday() == 6:
            dia += timedelta(days=1)
            continue

        # Reposición al empezar cada semana.
        if dia.weekday() == 0:
            comprar(m, productos, azar, datetime.combine(dia, datetime.min.time().replace(hour=8)))

        for _ in range(azar.randint(0, 3)):
            hora = datetime.combine(dia, datetime.min.time()).replace(
                hour=azar.randint(9, 18), minute=azar.randint(0, 59))
            # La cartera se reparte: lo viejo cobrado, lo reciente por cobrar.
            cobrado = (hoy - dia).days > 45 or azar.random() < 0.7
            if vender(m, productos, clientes, azar, hora, empresa["cod_empresa"],
                      usuario["cod_usuario"], metodo["cod_pago"],
                      pagado if cobrado else pendiente):
                ventas += 1

        # Alguna merma ocasional, para que el kardex muestre los tres motivos.
        if azar.random() < 0.04:
            producto = azar.choice([p for p in productos if p["controla_stock"]])
            if _stock(producto["cod_producto"]) > 2:
                mov = registrar_movimiento(
                    producto["cod_producto"], "SALIDA", "MERMA", 1,
                    observaciones="Unidad averiada en bodega",
                    fecha=datetime.combine(dia, datetime.min.time().replace(hour=17))
                        .strftime("%Y-%m-%d %H:%M:%S"))
                if mov:
                    m.datos["movimientos"].append(mov["cod_movimiento"])

        dia += timedelta(days=1)

    # Las últimas ventas quedan pendientes de emitir: son las de después de
    # contratar a FactuGest, y le dan contenido a la pantalla de reintentos.
    recientes = get_many(
        "SELECT cod_factura FROM facturas WHERE factugest_estado = 'HISTORICO' "
        "ORDER BY fecha DESC LIMIT %s", (VENTAS_PENDIENTES,))
    for f in recientes:
        execute_update("UPDATE facturas SET factugest_estado = NULL WHERE cod_factura = %s",
                       (f["cod_factura"],))

    m.guardar()
    return ventas, len(recientes)


def verificar():
    """El histórico no sirve si deja el inventario descuadrado."""
    descuadres = get_many("""
        SELECT p.sku, p.stock,
               COALESCE(SUM(CASE WHEN m.tipo = 'ENTRADA' THEN m.cantidad
                                 ELSE -m.cantidad END), 0) AS kardex
        FROM productos p
        LEFT JOIN movimientos_inventario m ON p.cod_producto = m.cod_producto
        WHERE p.controla_stock = 1
        GROUP BY p.cod_producto, p.sku, p.stock
        HAVING p.stock <> kardex
    """)
    negativos = get_many("SELECT sku FROM productos WHERE stock < 0")
    return descuadres, negativos


if __name__ == "__main__":
    if "--limpiar" in sys.argv:
        print("Siste Soluciones — limpiando el histórico")
        limpiar()
        sys.exit()

    print("Siste Soluciones — histórico de operación")
    ventas, pendientes = sembrar()

    descuadres, negativos = verificar()
    resumen = get_one(
        "SELECT COUNT(*) AS n, COALESCE(SUM(total), 0) AS total FROM facturas "
        "WHERE tipo_factura = 'FV'")
    cartera = get_one(
        "SELECT COALESCE(SUM(f.total), 0) AS v FROM facturas f "
        "JOIN pagos_factura p ON f.cod_pago = p.cod_pago_factura "
        "WHERE LOWER(p.status) IN ('pending', 'pendiente')")
    movimientos = get_one("SELECT COUNT(*) AS n FROM movimientos_inventario")

    print(f"  {ventas} ventas en {MESES} meses, ${resumen['total']:,.0f} facturados")
    print(f"  cartera por cobrar: ${cartera['v']:,.0f}")
    print(f"  {movimientos['n']} movimientos de inventario")
    print(f"  {pendientes} ventas quedan pendientes de emitir")
    print(f"  descuadres de kardex: {descuadres or 'ninguno'}")
    print(f"  productos en negativo: {negativos or 'ninguno'}")
    if descuadres or negativos:
        raise SystemExit("El histórico dejó el inventario inconsistente.")
    print("Listo.")
