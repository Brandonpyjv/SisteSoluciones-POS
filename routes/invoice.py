from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse, Response, JSONResponse
from typing import List, Optional
from datetime import datetime, timedelta, date as date_type
from services.invoice_service import (get_all_invoices_detailed, get_invoice_by_id,
                                       get_invoice_by_numero_factura, get_invoice_details,
                                       create_invoice, create_invoice_detail,
                                       update_invoice_status, delete_invoice,
                                       get_notas_by_referencia, validar_factura,
                                       validar_nota_credito, validar_nota_debito)
from services.calculo_documento import calcular_documento
from services.branches import get_all_branches, get_branch_by_id
from services.payment_methods_service import get_all_payment_methods
from services.invoice_payments_service import get_all_invoice_payments
from services.pdf_service import generate_invoice_pdf
from services.xml_service import generate_invoice_xml
from services.cufe_service import generate_cufe
from services.user_service import get_user_by_id
from services.inventory_service import (verificar_disponibilidad,
                                         registrar_movimientos_documento,
                                         revertir_movimientos_de_factura,
                                         documento_afecto_inventario,
                                         StockInsuficienteError)
from services.numeracion_service import reservar_numero, RangoResolucionAgotadoError
from services.documento_canonico import emisor_desde_factura
from services.validaciones import abreviatura_documento
from templates_config import templates
from database import get_one, get_many, execute_update, transaction

router = APIRouter(prefix="/invoice")


@router.get("", name="invoice")
def invoice(request: Request):
    data = get_all_invoices_detailed()
    return templates.TemplateResponse(request, "invoice/index.html", {"all_invoices": data})


def _render_invoice_form(request: Request, error: str = None, status_code: int = 200):
    session_user = request.session.get("user", {})
    cod_empresa = session_user.get("cod_empresa")

    # Si la sesión es antigua y no trae cod_empresa, consultarlo de la BD
    if not cod_empresa:
        cod_usuario = session_user.get("cod_usuario")
        if cod_usuario:
            db_user = get_user_by_id(cod_usuario)
            if db_user:
                cod_empresa = db_user.get("cod_empresa")
                request.session["user"]["cod_empresa"] = cod_empresa
                request.session["user"]["empresa_nombre"] = db_user.get("empresa_nombre")

    empresa = get_one(
        "SELECT cod_empresa, nombre, nit, dv FROM empresas WHERE cod_empresa = %s",
        (cod_empresa,)
    ) if cod_empresa else None
    invoice_discounts = get_many(
        "SELECT cod_descuento, descripcion, porcentaje FROM descuentos "
        "WHERE aplica_a_factura = 1 ORDER BY descripcion"
    )
    return templates.TemplateResponse(request, "invoice/form.html", {
        "empresa": empresa,
        "metodos_pago": get_all_payment_methods(),
        "pagos_factura": get_all_invoice_payments(),
        "invoice_discounts": invoice_discounts,
        "invoice": None,
        "error": error,
    }, status_code=status_code)


@router.get("/new", name="new_invoice")
def new_invoice(request: Request):
    return _render_invoice_form(request)


@router.post("/new", name="create_invoice")
async def create_invoice_post(
    request: Request,
    cod_cliente: str = Form(...),
    cod_metodo_pago: str = Form(...),
    cod_pago: str = Form(...),
    tipo_factura: str = Form("FV"),
    observaciones: str = Form(""),
    cod_producto: List[str] = Form(...),
    # El formulario también envía `precio_unitario`, pero no se declara a
    # propósito: el precio sale de la base. Ver validar_factura.
    cantidad: List[str] = Form(...),
    descuento_porcentaje: Optional[List[str]] = Form(None),
    descuento_descripcion: Optional[List[str]] = Form(None),
    cod_descuento_factura: Optional[str] = Form(None),
    valor_descuento_factura: str = Form("0"),
    plazo_pago: str = Form("0"),
):
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Los arreglos de la tabla de productos vienen en paralelo y tienen que
    # cuadrar entre sí: un largo distinto significa que la petición no la armó el
    # formulario, y leer por índice reventaría con un IndexError.
    cantidades = cantidad or []
    descuentos = descuento_porcentaje or []
    descripciones = descuento_descripcion or []
    if len(cantidades) != len(cod_producto):
        return _render_invoice_form(
            request, error="Los datos de los productos llegaron incompletos.",
            status_code=422)

    lineas_enviadas = [
        {
            "cod_producto": cod_producto[i],
            "cantidad": cantidades[i],
            "descuento_porcentaje": descuentos[i] if i < len(descuentos) else 0,
            "descuento_descripcion": descripciones[i] if i < len(descripciones) else "",
        }
        for i in range(len(cod_producto))
    ]

    v = validar_factura({
        "cod_cliente": cod_cliente, "cod_metodo_pago": cod_metodo_pago,
        "cod_pago": cod_pago, "tipo_factura": tipo_factura,
        "observaciones": observaciones, "plazo_pago": plazo_pago,
        "cod_descuento_factura": cod_descuento_factura,
        "valor_descuento_factura": valor_descuento_factura,
        "lineas": lineas_enviadas,
    })
    if not v.valido:
        return _render_invoice_form(request, error=v.resumen(), status_code=422)

    d = v.datos
    cod_cliente = d["cod_cliente"]
    cod_metodo_pago = d["cod_metodo_pago"]
    cod_pago = d["cod_pago"]
    tipo_factura = d["tipo_factura"]
    observaciones = d["observaciones"]
    cod_descuento_factura = d["cod_descuento_factura"]

    # El vencimiento se deriva del plazo pactado, no se escribe a mano: así el
    # PDF, el XML y la cartera cuentan siempre la misma historia. 0 días = contado.
    plazo_pago = d["plazo_pago"]
    forma_pago = "CONTADO" if plazo_pago == 0 else "CREDITO"
    fecha_vencimiento = (date_type.today() + timedelta(days=plazo_pago)).strftime("%Y-%m-%d")

    calculo = calcular_documento(d["lineas"], d["valor_descuento_factura"])
    lineas           = calculo["lineas"]
    total_descuentos = calculo["total_descuentos"]
    subtotal_neto    = calculo["subtotal"]
    total_impuestos  = calculo["total_impuestos"]
    total            = calculo["total"]

    # Obtener descripción del descuento de factura
    descripcion_descuento_factura = ''
    if cod_descuento_factura:
        row_desc = get_one("SELECT descripcion FROM descuentos WHERE cod_descuento = %s",
                           (cod_descuento_factura,))
        if row_desc:
            descripcion_descuento_factura = row_desc['descripcion']

    # Validar inventario antes de consumir un consecutivo autorizado: una factura
    # rechazada por falta de stock no debe quemar un número de la resolución DIAN.
    faltantes = verificar_disponibilidad(lineas)
    if faltantes:
        detalle = "; ".join(
            f"«{f['producto']}»: disponible {f['disponible']}, solicitado {f['solicitado']}"
            for f in faltantes
        )
        return _render_invoice_form(request, error=f"Stock insuficiente — {detalle}",
                                    status_code=422)

    session_user = request.session.get("user", {})
    cod_usuario = session_user.get("cod_usuario", 1)
    cod_empresa = session_user.get("cod_empresa", 1)

    empresa = get_branch_by_id(cod_empresa) or {}
    cliente = get_one("SELECT document_number FROM customers WHERE customer_id = %s", (cod_cliente,)) or {}

    # Reservar el número, guardar la factura y descontar el inventario son una sola
    # operación: si el stock se agotó entre la validación de arriba y este punto, se
    # revierte todo y el consecutivo de la resolución DIAN queda libre.
    try:
        with transaction() as cur:
            numeracion = reservar_numero(cod_empresa, tipo_factura, cursor=cur)
            numero_factura = numeracion["numero"]

            cufe = generate_cufe({
                'numero_factura': numero_factura,
                'fecha': fecha,
                'subtotal': subtotal_neto,
                'total_impuestos': total_impuestos,
                'total': total,
                'document_number': cliente.get('document_number', ''),
            }, empresa)

            invoice_id = create_invoice(
                cod_cliente=cod_cliente, cod_usuario=cod_usuario, cod_empresa=cod_empresa,
                cod_metodo_pago=cod_metodo_pago, cod_pago=cod_pago, fecha=fecha,
                total=total, subtotal=subtotal_neto,
                total_descuentos=total_descuentos,
                total_impuestos=total_impuestos,
                tipo_factura=tipo_factura,
                observaciones=observaciones,
                fecha_vencimiento=fecha_vencimiento or None,
                cufe=cufe,
                numero_factura=numero_factura,
                forma_pago=forma_pago,
                cod_descuento_factura=cod_descuento_factura,
                descripcion_descuento_factura=descripcion_descuento_factura,
                cursor=cur,
            )

            for linea in lineas:
                create_invoice_detail(
                    cod_factura=invoice_id,
                    cod_producto=linea["cod_producto"],
                    cantidad=linea["cantidad"],
                    precio_unitario=linea["precio_unitario"],
                    subtotal=linea["subtotal"],
                    descuento_porcentaje=linea["descuento_porcentaje"],
                    descuento_valor=linea["descuento_valor"],
                    descuento_descripcion=linea["descuento_descripcion"],
                    impuesto_porcentaje=linea["impuesto_porcentaje"],
                    impuesto_valor=linea["impuesto_valor"],
                    cursor=cur,
                )

            registrar_movimientos_documento(
                lineas, tipo="SALIDA", motivo="VENTA",
                cod_factura=invoice_id, cod_usuario=cod_usuario,
                observaciones=f"Venta {numero_factura}",
                cursor=cur,
            )
    except StockInsuficienteError as e:
        return _render_invoice_form(request, error=f"Stock insuficiente — {e}",
                                    status_code=422)
    except RangoResolucionAgotadoError as e:
        return _render_invoice_form(request, error=str(e), status_code=422)

    return RedirectResponse(url=f"/invoice/{numero_factura}", status_code=303)


@router.get("/{numero_factura}", name="view_invoice")
def view_invoice(request: Request, numero_factura: str):
    inv = get_invoice_by_numero_factura(numero_factura)
    if not inv:
        return RedirectResponse(url="/invoice", status_code=302)
    details    = get_invoice_details(inv['cod_factura'])
    pagos      = get_all_invoice_payments()
    notas      = get_notas_by_referencia(inv['cod_factura'])
    # Si esta factura es NC/ND, cargar la factura original
    inv_origen = None
    if inv.get('cod_factura_referencia'):
        inv_origen = get_invoice_by_id(inv['cod_factura_referencia'])
    return templates.TemplateResponse(request, "invoice/view.html", {
        "invoice": inv,
        "details": details,
        "pagos_factura": pagos,
        "notas": notas,
        "inv_origen": inv_origen,
    })


@router.post("/{invoice_id}/status", name="update_invoice_status")
def update_status_post(invoice_id: int, cod_pago: int = Form(...)):
    update_invoice_status(invoice_id, cod_pago)
    row = get_one("SELECT numero_factura FROM facturas WHERE cod_factura = %s", (invoice_id,))
    num = row['numero_factura'] if row and row.get('numero_factura') else invoice_id
    return RedirectResponse(url=f"/invoice/{num}", status_code=303)


@router.get("/{invoice_id}/pdf", name="invoice_pdf")
def invoice_pdf(invoice_id: int):
    inv = get_invoice_by_id(invoice_id)
    if not inv:
        return RedirectResponse(url="/invoice", status_code=302)
    details = get_invoice_details(invoice_id)
    pdf_bytes = generate_invoice_pdf(inv, details)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="factura_{invoice_id}.pdf"'},
    )


@router.get("/{invoice_id}/xml", name="invoice_xml")
def invoice_xml_download(invoice_id: int):
    inv = get_invoice_by_id(invoice_id)
    if not inv:
        return RedirectResponse(url="/invoice", status_code=302)
    details  = get_invoice_details(invoice_id)
    xml_str  = generate_invoice_xml(inv, details, emisor_desde_factura(inv))
    filename = f"{inv.get('numero_factura', invoice_id)}.xml"
    return Response(
        content=xml_str.encode('utf-8'),
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/delete/{invoice_id}", name="delete_invoice")
def delete_invoice_get(request: Request, invoice_id: int):
    cod_usuario = request.session.get("user", {}).get("cod_usuario")
    revertir_movimientos_de_factura(invoice_id, cod_usuario=cod_usuario)
    delete_invoice(invoice_id)
    return RedirectResponse(url="/invoice", status_code=302)


# ── Nota Crédito ─────────────────────────────────────────────────────────────

@router.get("/{invoice_id}/nc", name="new_nota_credito")
def new_nota_credito(request: Request, invoice_id: int):
    inv = get_invoice_by_id(invoice_id)
    if not inv or inv.get('tipo_factura') not in ('FV', 'ND'):
        return RedirectResponse(url="/invoice", status_code=302)
    details = get_invoice_details(invoice_id)
    return templates.TemplateResponse(request, "invoice/nota_credito_form.html", {
        "invoice": inv,
        "details": details,
        "pagos_factura": get_all_invoice_payments(),
    })


@router.post("/{invoice_id}/nc", name="create_nota_credito")
async def create_nota_credito_post(
    request: Request,
    invoice_id: int,
    motivo: str = Form(...),
    tipo_nc: str = Form("total"),
    cod_producto: Optional[List[str]] = Form(None),
    cantidad: Optional[List[str]] = Form(None),
):
    inv = get_invoice_by_id(invoice_id)
    if not inv:
        return RedirectResponse(url="/invoice", status_code=302)

    lineas_originales = get_invoice_details(invoice_id)
    v = validar_nota_credito({"motivo": motivo, "tipo_nc": tipo_nc,
                              "cod_producto": cod_producto, "cantidad": cantidad},
                             lineas_originales)
    if not v.valido:
        return templates.TemplateResponse(request, "invoice/nota_credito_form.html", {
            "invoice": inv,
            "details": lineas_originales,
            "pagos_factura": get_all_invoice_payments(),
            "error": v.resumen(),
        }, status_code=422)

    motivo = v.datos["motivo"]
    tipo_nc = v.datos["tipo_nc"]

    session_user = request.session.get("user", {})
    cod_usuario  = session_user.get("cod_usuario", 1)
    cod_empresa  = inv['cod_empresa']

    empresa     = get_branch_by_id(cod_empresa) or {}
    prefijo_nc  = 'NC'
    consec_nc   = int(empresa.get('consecutivo_nc') or 1)
    numero_nc   = f"{prefijo_nc}{consec_nc}"
    fecha       = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if tipo_nc == "total":
        # Anulación total: revertir todos los valores
        total_nc       = -round(float(inv['total']), 2)
        subtotal_nc    = -round(float(inv['subtotal']), 2)
        total_desc_nc  = -round(float(inv.get('total_descuentos') or 0), 2)
        total_imp_nc   = -round(float(inv.get('total_impuestos') or 0), 2)
        lineas_orig    = get_invoice_details(invoice_id)
        lineas_nc      = [
            {**d, 'subtotal': -float(d['subtotal']),
                  'descuento_valor': -float(d.get('descuento_valor') or 0),
                  'impuesto_valor': -float(d.get('impuesto_valor') or 0),
                  'descripcion_descuento': d.get('descripcion_descuento', '')}
            for d in lineas_orig
        ]
        # Marcar factura original como Anulada (cod 8)
        update_invoice_status(invoice_id, 8)
    else:
        # NC parcial por productos seleccionados
        lineas_orig = get_invoice_details(invoice_id)
        lineas_nc   = []
        total_nc = subtotal_nc = total_desc_nc = total_imp_nc = 0.0
        qty_map = v.datos["devueltas"]
        for d in lineas_orig:
            nc_qty = qty_map.get(d['cod_producto'], 0)
            if nc_qty <= 0:
                continue
            ratio      = nc_qty / float(d['cantidad'])
            sub_nc     = -round(float(d['subtotal']) * ratio, 2)
            desc_nc    = -round(float(d.get('descuento_valor') or 0) * ratio, 2)
            imp_nc     = -round(float(d.get('impuesto_valor') or 0) * ratio, 2)
            subtotal_nc   += sub_nc
            total_desc_nc += desc_nc
            total_imp_nc  += imp_nc
            lineas_nc.append({**d, 'cantidad': nc_qty,
                              'subtotal': sub_nc, 'descuento_valor': desc_nc,
                              'impuesto_valor': imp_nc,
                              'descripcion_descuento': d.get('descripcion_descuento', '')})
        total_nc = round(subtotal_nc + total_imp_nc, 2)
        # Marcar original como Parcialmente Anulada (cod 9)
        update_invoice_status(invoice_id, 9)

    cufe_data = {
        'numero_factura': numero_nc, 'fecha': fecha,
        'subtotal': abs(subtotal_nc),
        'total_impuestos': abs(total_imp_nc),
        'total': abs(total_nc),
        'document_number': inv.get('document_number', ''),
    }
    cufe_nc = generate_cufe(cufe_data, empresa)

    nc_id = create_invoice(
        cod_cliente=inv['cod_cliente'], cod_usuario=cod_usuario,
        cod_empresa=cod_empresa, cod_metodo_pago=inv['cod_metodo_pago'],
        cod_pago=1, fecha=fecha,
        total=total_nc, subtotal=subtotal_nc,
        total_descuentos=total_desc_nc, total_impuestos=total_imp_nc,
        tipo_factura='NC', observaciones=motivo,
        numero_factura=numero_nc, cufe=cufe_nc,
        forma_pago=inv.get('forma_pago', 'CONTADO'),
        descripcion_descuento_factura=inv.get('descripcion_descuento_factura'),
    )

    # Guardar referencia a la factura original
    execute_update("UPDATE facturas SET cod_factura_referencia = %s, motivo_nota = %s WHERE cod_factura = %s",
                   (invoice_id, motivo, nc_id))

    for d in lineas_nc:
        create_invoice_detail(
            cod_factura=nc_id, cod_producto=d['cod_producto'],
            cantidad=d['cantidad'], precio_unitario=float(d['precio_unitario']),
            subtotal=d['subtotal'],
            descuento_porcentaje=float(d.get('descuento_porcentaje') or 0),
            descuento_valor=d['descuento_valor'],
            descuento_descripcion=d.get('descripcion_descuento', ''),
            impuesto_porcentaje=float(d.get('impuesto_porcentaje') or 0),
            impuesto_valor=d['impuesto_valor'],
            # Se conserva por si la línea original era un concepto y no un producto.
            descripcion=d.get('descripcion'),
        )

    # Reingresar al inventario lo devuelto, solo si la factura original llegó a
    # descontarlo (las emitidas antes del kardex no lo hicieron).
    if documento_afecto_inventario(invoice_id):
        registrar_movimientos_documento(
            [{"cod_producto": d["cod_producto"], "cantidad": abs(int(d["cantidad"]))}
             for d in lineas_nc],
            tipo="ENTRADA", motivo="DEVOLUCION",
            cod_factura=nc_id, cod_usuario=cod_usuario,
            observaciones=f"Devolución por {numero_nc} sobre {inv.get('numero_factura')}",
        )

    execute_update(
        "UPDATE empresas SET consecutivo_nc = %s WHERE cod_empresa = %s",
        (consec_nc + 1, cod_empresa)
    )
    return RedirectResponse(url=f"/invoice/{numero_nc}", status_code=303)


# ── Nota Débito ──────────────────────────────────────────────────────────────

@router.get("/{invoice_id}/nd", name="new_nota_debito")
def new_nota_debito(request: Request, invoice_id: int):
    inv = get_invoice_by_id(invoice_id)
    if not inv or inv.get('tipo_factura') not in ('FV',):
        return RedirectResponse(url="/invoice", status_code=302)
    return templates.TemplateResponse(request, "invoice/nota_debito_form.html", {
        "invoice": inv,
        "pagos_factura": get_all_invoice_payments(),
    })


@router.post("/{invoice_id}/nd", name="create_nota_debito")
async def create_nota_debito_post(
    request: Request,
    invoice_id: int,
    motivo: str = Form(...),
    valor_ajuste: str = Form(...),
    incluye_iva: str = Form("si"),
):
    inv = get_invoice_by_id(invoice_id)
    if not inv:
        return RedirectResponse(url="/invoice", status_code=302)

    v = validar_nota_debito({"motivo": motivo, "valor_ajuste": valor_ajuste,
                             "incluye_iva": incluye_iva})
    if not v.valido:
        return templates.TemplateResponse(request, "invoice/nota_debito_form.html", {
            "invoice": inv,
            "pagos_factura": get_all_invoice_payments(),
            "error": v.resumen(),
        }, status_code=422)

    motivo = v.datos["motivo"]
    valor_ajuste = v.datos["valor_ajuste"]
    incluye_iva = v.datos["incluye_iva"]

    session_user = request.session.get("user", {})
    cod_usuario  = session_user.get("cod_usuario", 1)
    cod_empresa  = inv['cod_empresa']

    empresa    = get_branch_by_id(cod_empresa) or {}
    prefijo_nd = 'ND'
    consec_nd  = int(empresa.get('consecutivo_nd') or 1)
    numero_nd  = f"{prefijo_nd}{consec_nd}"
    fecha      = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Calcular base e IVA del ajuste
    if incluye_iva == "si":
        # El valor ingresado ya incluye IVA → descomponer
        # Asumimos tarifa IVA promedio de la factura original
        total_imp_orig = float(inv.get('total_impuestos') or 0)
        subtotal_orig  = float(inv.get('subtotal') or 1)
        tasa_prom      = total_imp_orig / subtotal_orig if subtotal_orig else 0
        subtotal_nd    = round(valor_ajuste / (1 + tasa_prom), 2)
        imp_nd         = round(valor_ajuste - subtotal_nd, 2)
    else:
        subtotal_nd = round(valor_ajuste, 2)
        imp_nd      = 0.0

    total_nd = round(subtotal_nd + imp_nd, 2)

    cufe_data = {
        'numero_factura': numero_nd, 'fecha': fecha,
        'subtotal': subtotal_nd, 'total_impuestos': imp_nd, 'total': total_nd,
        'document_number': inv.get('document_number', ''),
    }
    cufe_nd = generate_cufe(cufe_data, empresa)

    nd_id = create_invoice(
        cod_cliente=inv['cod_cliente'], cod_usuario=cod_usuario,
        cod_empresa=cod_empresa, cod_metodo_pago=inv['cod_metodo_pago'],
        cod_pago=2, fecha=fecha,
        total=total_nd, subtotal=subtotal_nd,
        total_descuentos=0, total_impuestos=imp_nd,
        tipo_factura='ND', observaciones=motivo,
        numero_factura=numero_nd, cufe=cufe_nd,
        forma_pago=inv.get('forma_pago', 'CONTADO'),
    )

    # La nota débito también lleva su línea. Sin ella el XML sale sin InvoiceLine
    # y la DIAN lo rechaza; el ajuste es un concepto —un flete, un interés—, así
    # que la línea va sin producto y con el motivo como descripción.
    tasa_nd = round(imp_nd / subtotal_nd * 100, 2) if subtotal_nd else 0
    create_invoice_detail(
        cod_factura=nd_id, cod_producto=None, descripcion=motivo[:300],
        cantidad=1, precio_unitario=subtotal_nd, subtotal=subtotal_nd,
        impuesto_porcentaje=tasa_nd, impuesto_valor=imp_nd,
    )

    execute_update(
        "UPDATE facturas SET cod_factura_referencia = %s, motivo_nota = %s WHERE cod_factura = %s",
        (invoice_id, motivo, nd_id)
    )
    execute_update(
        "UPDATE empresas SET consecutivo_nd = %s WHERE cod_empresa = %s",
        (consec_nd + 1, cod_empresa)
    )
    return RedirectResponse(url=f"/invoice/{numero_nd}", status_code=303)


# ── Endpoints AJAX para el formulario de nueva factura ──────────────────────

@router.get("/api/customers/search", name="api_customers_search")
def api_customers_search(q: str = ""):
    results = get_many(
        "SELECT customer_id, full_name, document_number, document_type FROM customers "
        "WHERE full_name LIKE %s OR document_number LIKE %s ORDER BY full_name LIMIT 10",
        (f"%{q}%", f"%{q}%"),
    )
    # El buscador muestra «CC 1090…», no el código DIAN que guarda la columna.
    for r in results:
        r["document_type_label"] = abreviatura_documento(r["document_type"])
    return JSONResponse(content=results)


@router.get("/api/products/search", name="api_products_search")
def api_products_search(q: str = ""):
    results = get_many(
        "SELECT p.cod_producto, p.sku, p.nombre, p.precio_unitario, "
        "p.stock, p.controla_stock, "
        "i.porcentaje AS tax_porcentaje "
        "FROM productos p LEFT JOIN impuestos i ON p.cod_impuesto = i.cod_impuesto "
        "WHERE p.activo = 1 AND (p.sku LIKE %s OR p.nombre LIKE %s) "
        "ORDER BY p.nombre LIMIT 10",
        (f"%{q}%", f"%{q}%"),
    )
    for r in results:
        r["precio_unitario"] = float(r["precio_unitario"])
        r["tax_porcentaje"] = float(r["tax_porcentaje"] or 0)
        r["stock"] = int(r["stock"] or 0)
        r["controla_stock"] = int(r["controla_stock"] or 0)
    return JSONResponse(content=results)


@router.get("/api/products/{product_id}/discounts", name="api_product_discounts")
def api_product_discounts(product_id: int):
    results = get_many(
        "SELECT d.cod_descuento, d.descripcion, d.porcentaje "
        "FROM descuentos d "
        "JOIN producto_descuento pd ON d.cod_descuento = pd.cod_descuento "
        "WHERE pd.cod_producto = %s",
        (product_id,),
    )
    return JSONResponse(content=results)


@router.get("/api/discounts", name="api_invoice_discounts")
def api_invoice_discounts():
    results = get_many(
        "SELECT cod_descuento, descripcion, porcentaje FROM descuentos "
        "WHERE aplica_a_factura = 1 ORDER BY descripcion"
    )
    return JSONResponse(content=results)
