"""
Catálogo de Siste Soluciones.

    python seed_catalogo.py

Carga los productos que vende el negocio: portátiles, periféricos, monitores,
impresoras, almacenamiento, redes, consumibles y dos servicios de taller.

Es idempotente: los productos se identifican por su SKU y los que ya existen se
actualizan en lugar de duplicarse. El stock inicial entra por el kardex y no con
un UPDATE suelto, porque en este sistema el saldo siempre tiene que ser
reconstruible a partir de sus movimientos.
"""
from database import execute_query, execute_update, get_one
from services.inventory_service import registrar_saldo_inicial

# sku, nombre, descripcion, precio, stock, stock_minimo, unidad, controla_stock
CATALOGO = [
    # ── Portátiles ──────────────────────────────────────────────────────────
    ("PC-LEN-IP3", "Portátil Lenovo IdeaPad 3 15\"",
     "Ryzen 5 5500U, 8 GB RAM, 512 GB SSD, Windows 11", 2190000, 6, 2, "94", 1),
    ("PC-HP-250G9", "Portátil HP 250 G9 15.6\"",
     "Core i5 1235U, 8 GB RAM, 512 GB SSD, FreeDOS", 2450000, 4, 2, "94", 1),
    ("PC-ASU-VB15", "Portátil Asus VivoBook 15",
     "Core i3 1215U, 8 GB RAM, 256 GB SSD", 1790000, 5, 2, "94", 1),

    # ── Monitores ───────────────────────────────────────────────────────────
    ("MON-SAM-24", "Monitor Samsung 24\" F24T350",
     "IPS 75 Hz, FreeSync, HDMI y VGA", 649000, 8, 3, "94", 1),
    ("MON-LG-22", "Monitor LG 22\" 22MP410",
     "IPS Full HD, bordes delgados", 489000, 6, 3, "94", 1),

    # ── Periféricos ─────────────────────────────────────────────────────────
    ("TEC-RED-K552", "Teclado mecánico Redragon K552",
     "Switch azul, retroiluminado, español", 189000, 20, 5, "94", 1),
    ("MOU-LOG-M170", "Mouse inalámbrico Logitech M170",
     "Receptor USB, 1000 dpi", 59900, 30, 8, "94", 1),
    ("AUD-HYX-CS", "Diadema HyperX Cloud Stinger",
     "Micrófono con silencio por rotación", 249000, 10, 3, "94", 1),
    ("MOU-PAD-XL", "Mousepad extendido XL",
     "800 x 300 mm, base antideslizante", 45000, 25, 8, "94", 1),

    # ── Impresión ───────────────────────────────────────────────────────────
    ("IMP-EPS-L3250", "Impresora Epson EcoTank L3250",
     "Multifuncional con sistema de tinta continua, wifi", 899000, 5, 2, "94", 1),
    ("IMP-HP-2374", "Impresora HP DeskJet Ink Advantage 2374",
     "Multifuncional de cartuchos", 289000, 7, 3, "94", 1),
    ("TIN-EPS-544", "Tinta Epson T544 (por color)",
     "Botella de 65 ml compatible con serie L", 39900, 40, 12, "94", 1),
    ("PAP-RES-CAR", "Resma de papel carta 75 g",
     "500 hojas", 18900, 50, 15, "94", 1),

    # ── Almacenamiento ──────────────────────────────────────────────────────
    ("SSD-KIN-480", "SSD Kingston A400 480 GB",
     "SATA III 2.5 pulgadas", 179000, 15, 5, "94", 1),
    ("USB-SAN-64", "Memoria USB SanDisk 64 GB",
     "USB 3.0", 39900, 35, 10, "94", 1),
    ("HDD-EXT-1TB", "Disco externo Seagate 1 TB",
     "USB 3.0, portátil", 289000, 8, 3, "94", 1),

    # ── Redes ───────────────────────────────────────────────────────────────
    ("RED-TPL-AC12", "Router TP-Link Archer C20 AC750",
     "Doble banda, 3 antenas", 149000, 12, 4, "94", 1),
    ("RED-UTP-CAT6", "Cable UTP Cat 6 (por metro)",
     "Certificado, para instalaciones internas", 2500, 300, 50, "MTR", 1),

    # ── Servicios de taller ─────────────────────────────────────────────────
    ("SRV-MTTO-PRE", "Mantenimiento preventivo de equipo",
     "Limpieza física, cambio de pasta térmica y revisión general", 65000, 0, 0, "WSD", 0),
    ("SRV-INST-SO", "Instalación de sistema operativo y ofimática",
     "Formateo, instalación y configuración inicial", 80000, 0, 0, "WSD", 0),
]

# Los del volcado venían en inglés y son de otro negocio.
DESCUENTOS = [
    (55501, "Promoción de temporada", 10.0, 1, 1),
    (55504, "Descuento por volumen", 8.0, 1, 1),
    (55506, "Liquidación de inventario", 20.0, 1, 0),
    (55502, "Cliente frecuente", 5.0, 0, 1),
    (55505, "Promoción pago con tarjeta", 12.0, 0, 1),
]

# Qué descuento se puede aplicar a qué producto, para que el desplegable del
# formulario de factura ofrezca algo.
DESCUENTOS_POR_PRODUCTO = {
    55501: ["TEC-RED-K552", "MOU-LOG-M170", "AUD-HYX-CS", "MOU-PAD-XL"],
    55504: ["PAP-RES-CAR", "TIN-EPS-544", "USB-SAN-64", "RED-UTP-CAT6"],
    55506: ["MON-LG-22", "IMP-HP-2374"],
}


def sembrar_descuentos():
    creados = actualizados = 0
    for cod, descripcion, porcentaje, a_producto, a_factura in DESCUENTOS:
        if get_one("SELECT cod_descuento FROM descuentos WHERE cod_descuento = %s", (cod,)):
            execute_update(
                "UPDATE descuentos SET descripcion=%s, porcentaje=%s, "
                "  aplica_a_producto=%s, aplica_a_factura=%s WHERE cod_descuento=%s",
                (descripcion, porcentaje, a_producto, a_factura, cod))
            actualizados += 1
        else:
            execute_query(
                "INSERT INTO descuentos (cod_descuento, descripcion, porcentaje, "
                "  aplica_a_producto, aplica_a_factura) VALUES (%s, %s, %s, %s, %s)",
                (cod, descripcion, porcentaje, a_producto, a_factura))
            creados += 1

    # Los que quedaron del volcado y no están en la lista no son de este negocio.
    sobrantes = execute_update(
        "DELETE FROM descuentos WHERE cod_descuento NOT IN (%s) "
        "AND cod_descuento NOT IN (SELECT DISTINCT cod_descuento FROM producto_descuento)"
        % ",".join(str(d[0]) for d in DESCUENTOS))
    return creados, actualizados, sobrantes


def sembrar_productos(cod_impuesto: int):
    creados = actualizados = 0
    for sku, nombre, descripcion, precio, stock, minimo, unidad, controla in CATALOGO:
        existente = get_one("SELECT cod_producto FROM productos WHERE sku = %s", (sku,))
        if existente:
            execute_update(
                "UPDATE productos SET nombre=%s, descripcion=%s, precio_unitario=%s, "
                "  stock_minimo=%s, cod_impuesto=%s, unidad_medida=%s, "
                "  controla_stock=%s, activo=1 WHERE cod_producto=%s",
                (nombre, descripcion, precio, minimo, cod_impuesto, unidad, controla,
                 existente["cod_producto"]))
            actualizados += 1
            continue

        cod = execute_query(
            "INSERT INTO productos (sku, nombre, descripcion, precio_unitario, stock, "
            "  stock_minimo, cod_impuesto, unidad_medida, controla_stock, activo) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 1)",
            (sku, nombre, descripcion, precio, stock, minimo, cod_impuesto, unidad,
             controla))
        # El saldo entra por el kardex: en este sistema el stock nunca se toca
        # con un UPDATE suelto.
        if controla and stock:
            registrar_saldo_inicial(cod, observaciones="Inventario inicial del catálogo")
        creados += 1
    return creados, actualizados


def enlazar_descuentos():
    enlaces = 0
    for cod_descuento, skus in DESCUENTOS_POR_PRODUCTO.items():
        for sku in skus:
            producto = get_one("SELECT cod_producto FROM productos WHERE sku = %s", (sku,))
            if not producto:
                continue
            ya = get_one("SELECT 1 AS x FROM producto_descuento "
                         "WHERE cod_producto=%s AND cod_descuento=%s",
                         (producto["cod_producto"], cod_descuento))
            if not ya:
                execute_query("INSERT INTO producto_descuento (cod_producto, cod_descuento) "
                              "VALUES (%s, %s)", (producto["cod_producto"], cod_descuento))
                enlaces += 1
    return enlaces


def main():
    iva = get_one("SELECT cod_impuesto FROM impuestos WHERE porcentaje = 19 LIMIT 1")
    if not iva:
        raise SystemExit("No está cargado el IVA del 19 %. Importa base/factugest.sql.")

    creados_d, actualizados_d, sobrantes = sembrar_descuentos()
    print(f"  descuentos: {creados_d} creados, {actualizados_d} traducidos, "
          f"{sobrantes} ajenos eliminados")

    creados, actualizados = sembrar_productos(iva["cod_impuesto"])
    print(f"  productos : {creados} creados, {actualizados} actualizados")

    print(f"  descuentos enlazados a productos: {enlazar_descuentos()}")

    valor = get_one("SELECT COALESCE(SUM(stock * precio_unitario), 0) AS v FROM productos "
                    "WHERE controla_stock = 1")["v"]
    servicios = get_one("SELECT COUNT(*) n FROM productos WHERE controla_stock = 0")["n"]
    print(f"\n  catálogo: {len(CATALOGO)} referencias ({servicios} son servicios)")
    print(f"  inventario valorizado en ${valor:,.0f}")


if __name__ == "__main__":
    print("Siste Soluciones — catálogo")
    main()
    print("Listo.")
