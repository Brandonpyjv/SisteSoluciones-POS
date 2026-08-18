import io
import os
import hashlib
import qrcode
from PIL import Image as PILImage
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                 Paragraph, Spacer, HRFlowable, Image, KeepTogether)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT
from num2words import num2words

from services.validaciones import nombre_documento


# ── Constantes de color (mismos del sidebar/navbar) ──────────────────────────
PRIMARY   = colors.HexColor('#4e73df')
PRIMARY2  = colors.HexColor('#224abe')
LIGHT_BG  = colors.HexColor('#f8f9fc')
MID_GRAY  = colors.HexColor('#e3e6f0')
DARK      = colors.HexColor('#2d3748')
ORANGE    = colors.HexColor('#e74a3b')

LOGO_PATH = os.path.join(os.path.dirname(__file__), '..', 'static', 'img', 'logodark2.png')


def _fmt(val) -> str:
    return f"{float(val or 0):,.2f}"


def _total_en_letras(total: float) -> str:
    try:
        entero = int(total)
        centavos = round((total - entero) * 100)
        texto = num2words(entero, lang='es').upper()
        c_txt = num2words(centavos, lang='es').upper() if centavos else 'CERO'
        return f"{texto} PESO(S) CON {c_txt} CENTAVO(S)"
    except Exception:
        return ''


def _make_qr(data: str) -> io.BytesIO:
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=4, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf


def _style(name, **kwargs):
    base = ParagraphStyle(name, fontName='Helvetica', fontSize=8,
                          textColor=DARK, leading=11)
    for k, v in kwargs.items():
        setattr(base, k, v)
    return base


def generate_invoice_pdf(invoice: dict, details: list) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            rightMargin=1.5 * cm, leftMargin=1.5 * cm,
                            topMargin=1.5 * cm, bottomMargin=2 * cm)

    styles   = getSampleStyleSheet()
    s_normal = _style('n')
    s_bold   = _style('b', fontName='Helvetica-Bold')
    s_small  = _style('sm', fontSize=7, textColor=colors.HexColor('#555555'))
    s_right  = _style('r', alignment=TA_RIGHT)
    s_right_bold = _style('rb', alignment=TA_RIGHT, fontName='Helvetica-Bold')
    s_center = _style('c', alignment=TA_CENTER)
    s_white  = _style('w', textColor=colors.white, fontName='Helvetica-Bold', fontSize=7)
    s_hdr_sm = _style('hs', textColor=colors.white, fontName='Helvetica-Bold', fontSize=6.5)
    s_cell   = _style('cl', fontSize=7.5)
    s_cell_r = _style('clr', fontSize=7.5, alignment=TA_RIGHT)

    story = []

    # ══════════════════════════════════════════════════════════════════
    # 1. ENCABEZADO: LOGO | INFO EMPRESA | TIPO + NÚMERO FACTURA
    # ══════════════════════════════════════════════════════════════════
    emp = invoice  # invoice ya trae los campos empresa_* del JOIN

    emp_nombre   = emp.get('empresa_nombre', 'Siste Soluciones')
    emp_nit      = emp.get('empresa_nit', '')
    emp_dv       = emp.get('empresa_dv', '')
    emp_dir      = emp.get('empresa_direccion', '')
    emp_ciudad   = emp.get('empresa_ciudad', '')
    emp_tel      = emp.get('empresa_telefono', '')
    emp_correo   = emp.get('empresa_correo', '')
    emp_web      = emp.get('empresa_website', '')
    emp_regimen  = (emp.get('empresa_regimen') or '').replace('_', ' ')
    emp_ciiu     = emp.get('actividad_economica', '')
    emp_ica      = emp.get('empresa_tarifa_ica', 0)
    emp_autore   = emp.get('empresa_autoretenedor', 0)
    emp_gran_c   = emp.get('empresa_gran_contribuyente', 0)
    emp_prefijo  = emp.get('empresa_prefijo', '')
    res_num      = emp.get('empresa_resolucion_dian', '')
    res_f_desde  = emp.get('empresa_resolucion_fecha_desde', '')
    res_f_hasta  = emp.get('empresa_resolucion_fecha_hasta', '')
    res_desde    = emp.get('empresa_resolucion_desde', '')
    res_hasta    = emp.get('empresa_resolucion_hasta', '')

    nit_str = f"NIT. {emp_nit}-{emp_dv}" if emp_dv else f"NIT. {emp_nit}"

    tipo_factura = invoice.get('tipo_factura', 'FV')
    tipo_map     = {'FV': 'Factura Electrónica de Venta',
                    'NC': 'Nota Crédito Electrónica',
                    'ND': 'Nota Débito Electrónica'}
    tipo_label   = tipo_map.get(tipo_factura, 'Factura Electrónica de Venta')

    num_factura = invoice.get('numero_factura') or str(invoice.get('cod_factura', ''))

    fecha_val = invoice.get('fecha')
    from datetime import datetime
    if hasattr(fecha_val, 'strftime'):
        fecha_str = fecha_val.strftime('%d/%m/%Y, %I:%M %p').replace(' 0', ' ', 1)
    else:
        fecha_str = str(fecha_val or '')

    vencimiento = invoice.get('fecha_vencimiento')
    venc_str = vencimiento.strftime('%d/%m/%Y') if hasattr(vencimiento, 'strftime') else (str(vencimiento) if vencimiento else '')

    # Notas empresa
    notes = []
    if emp_ica:
        notes.append(f"Actividad Económica {emp_ciiu} Tarifa ICA {emp_ica} x Mil")
    if not emp_autore:
        notes.append("No somos Autorretenedores")
    if emp_gran_c:
        notes.append("Somos Grandes Contribuyentes")
    notes_str = ' - '.join(notes) if notes else ''

    # Resolución DIAN
    if res_num and res_f_desde and res_f_hasta:
        def _fmt_date(d):
            if hasattr(d, 'strftime'):
                return d.strftime('%d/%m/%Y')
            s = str(d)[:10]
            if len(s) == 10:
                parts = s.split('-')
                return f"{parts[2]}/{parts[1]}/{parts[0]}"
            return s
        res_text = (f"RESOLUCION DIAN No. {res_num} DEL {_fmt_date(res_f_desde)} "
                    f"AUTORIZA DEL {emp_prefijo} {res_desde} AL {emp_prefijo} {res_hasta} "
                    f"FECHA VIGENCIA DESDE {_fmt_date(res_f_desde)} HASTA {_fmt_date(res_f_hasta)}")
    else:
        res_text = ''

    # Columna central: info empresa
    emp_lines = [
        Paragraph(f'<b><font color="#4e73df" size="13">{emp_nombre}</font></b>',
                  _style('en', alignment=TA_CENTER, fontSize=13, textColor=PRIMARY, fontName='Helvetica-Bold')),
        Paragraph(f'<font color="#4e73df"><b>{nit_str}</b> {emp_regimen}</font>',
                  _style('en2', alignment=TA_CENTER, fontSize=7.5, textColor=PRIMARY)),
    ]
    if notes_str:
        emp_lines.append(Paragraph(notes_str, _style('en3', alignment=TA_CENTER, fontSize=7, textColor=colors.HexColor('#555'))))
    if emp_dir or emp_ciudad:
        emp_lines.append(Paragraph(f'{emp_dir} - {emp_ciudad}', _style('en4', alignment=TA_CENTER, fontSize=7)))
    contact_parts = []
    if emp_tel:
        contact_parts.append(f'Teléfonos: {emp_tel}')
    if emp_web:
        contact_parts.append(f'Web: {emp_web}')
    if emp_correo:
        contact_parts.append(f'Contacto: {emp_correo}')
    if contact_parts:
        emp_lines.append(Paragraph('  '.join(contact_parts), _style('en5', alignment=TA_CENTER, fontSize=7)))
    if res_text:
        emp_lines.append(Paragraph(res_text, _style('en6', alignment=TA_CENTER, fontSize=6.5,
                                                     textColor=colors.HexColor('#333'))))

    # Columna derecha: tipo + número + fechas
    right_lines = [
        Paragraph(f'<b>{tipo_label}</b>',
                  _style('tr', alignment=TA_RIGHT, fontSize=10, textColor=DARK, fontName='Helvetica-Bold')),
        Paragraph(f'<b>{num_factura}</b>',
                  _style('tr2', alignment=TA_RIGHT, fontSize=11, textColor=PRIMARY, fontName='Helvetica-Bold')),
        Spacer(1, 4),
        Paragraph(f'Fecha de Generación: {fecha_str}', _style('tr3', alignment=TA_RIGHT, fontSize=7.5)),
        Paragraph(f'Fecha de Expedición: {fecha_str}', _style('tr4', alignment=TA_RIGHT, fontSize=7.5)),
        Paragraph(f'Fecha de Vencimiento: {venc_str}', _style('tr5', alignment=TA_RIGHT, fontSize=7.5)),
    ]

    # Logo
    logo_cell = ''
    if os.path.exists(LOGO_PATH):
        try:
            logo_cell = Image(LOGO_PATH, width=3 * cm, height=2 * cm, kind='proportional')
        except Exception:
            logo_cell = Paragraph(emp_nombre, s_bold)
    else:
        logo_cell = Paragraph(emp_nombre, s_bold)

    header_data = [[logo_cell, emp_lines, right_lines]]
    header_table = Table(header_data, colWidths=[3.5 * cm, 9.5 * cm, 5.5 * cm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
    ]))
    story.append(header_table)
    story.append(HRFlowable(width='100%', thickness=2, color=PRIMARY, spaceAfter=6))

    # ══════════════════════════════════════════════════════════════════
    # 2. DATOS CLIENTE | INFO PAGO
    # ══════════════════════════════════════════════════════════════════
    # El mapa que había aquí no tenía entrada para los clientes jurídicos, así que la
    # factura de una empresa se imprimía con «J: 900123456» en lugar de «NIT».
    cli_doc_tipo = nombre_documento(invoice.get('document_type'))
    cli_doc_num  = invoice.get('document_number', '')
    cli_nombre   = invoice.get('cliente_nombre', '')
    cli_dir_val  = invoice.get('cliente_address', '') or ''
    cli_ciudad_v = invoice.get('cliente_ciudad', '') or ''
    cli_dpto     = invoice.get('cliente_departamento', '') or ''
    cli_pais     = 'COLOMBIA'
    cli_tel      = invoice.get('cliente_phone', '') or ''
    cli_correo   = (invoice.get('cliente_email', '') or '').upper()

    forma_pago    = invoice.get('forma_pago', 'CONTADO')
    metodo_pago   = invoice.get('metodo_pago_nombre', '')
    vendedor      = invoice.get('nombre_vendedor', '') or ''
    orden_compra  = invoice.get('orden_compra', '') or ''

    def cli_row(label, value):
        return [Paragraph(f'<b>{label}</b>', _style(f'cl{label}', fontSize=7.5, fontName='Helvetica-Bold')),
                Paragraph(str(value or ''), _style(f'cv{label}', fontSize=7.5))]

    cli_left = Table([
        [Paragraph('<b>Cliente:</b>', _style('clh', fontSize=7.5, fontName='Helvetica-Bold')),
         Paragraph(cli_nombre.upper(), _style('clv', fontSize=7.5))],
        [Paragraph('<b>Nº Identificación:</b>', _style('clh2', fontSize=7.5, fontName='Helvetica-Bold')),
         Paragraph(f'{cli_doc_tipo} {cli_doc_num}', _style('clv2', fontSize=7.5))],
        [Paragraph(cli_dir_val, _style('clad', fontSize=7.5, textColor=colors.HexColor('#555'))), ''],
        [Paragraph(f'<b>Ciudad:</b>', _style('clh3', fontSize=7.5, fontName='Helvetica-Bold')),
         Paragraph(cli_ciudad_v.upper(), _style('clv3', fontSize=7.5))],
        [Paragraph(f'<b>Departamento:</b>', _style('clh4', fontSize=7.5, fontName='Helvetica-Bold')),
         Paragraph(cli_dpto.upper(), _style('clv4', fontSize=7.5))],
        [Paragraph(f'<b>País:</b>', _style('clh5', fontSize=7.5, fontName='Helvetica-Bold')),
         Paragraph(cli_pais, _style('clv5', fontSize=7.5))],
        [Paragraph(f'<b>Teléfono:</b>', _style('clh6', fontSize=7.5, fontName='Helvetica-Bold')),
         Paragraph(cli_tel, _style('clv6', fontSize=7.5))],
        [Paragraph(f'<b>Correo:</b>', _style('clh7', fontSize=7.5, fontName='Helvetica-Bold')),
         Paragraph(cli_correo, _style('clv7', fontSize=7.5))],
    ], colWidths=[3.2 * cm, 5.6 * cm])
    cli_left.setStyle(TableStyle([
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('SPAN', (0, 2), (1, 2)),
    ]))

    cli_right = Table([
        [Paragraph('<b>Nombre Vendedor:</b>', _style('rvh', fontSize=7.5, fontName='Helvetica-Bold')),
         Paragraph(vendedor, _style('rvv', fontSize=7.5))],
        [Paragraph('<b>Orden de Compra:</b>', _style('roh', fontSize=7.5, fontName='Helvetica-Bold')),
         Paragraph(orden_compra, _style('rov', fontSize=7.5))],
        [Paragraph('<b>Forma de Pago:</b>', _style('rfh', fontSize=7.5, fontName='Helvetica-Bold')),
         Paragraph(forma_pago, _style('rfv', fontSize=7.5))],
        [Paragraph('<b>Medio de Pago:</b>', _style('rmh', fontSize=7.5, fontName='Helvetica-Bold')),
         Paragraph(metodo_pago, _style('rmv', fontSize=7.5))],
    ], colWidths=[3.2 * cm, 5.3 * cm])
    cli_right.setStyle(TableStyle([
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
    ]))

    cli_block = Table([[cli_left, cli_right]], colWidths=[9.2 * cm, 9.3 * cm])
    cli_block.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOX', (0, 0), (-1, -1), 0.5, MID_GRAY),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(cli_block)
    story.append(Spacer(1, 8))

    # ══════════════════════════════════════════════════════════════════
    # 3. TABLA DE PRODUCTOS
    # ══════════════════════════════════════════════════════════════════
    col_headers = [
        Paragraph('ID', s_hdr_sm),
        Paragraph('CÓDIGO\nPRINCIPAL', s_hdr_sm),
        Paragraph('DESCRIPCIÓN', s_hdr_sm),
        Paragraph('CANTIDAD', s_hdr_sm),
        Paragraph('UND\nMEDIDA', s_hdr_sm),
        Paragraph('PRECIO\nUNITARIO', _style('ph', textColor=colors.white, fontName='Helvetica-Bold',
                                              fontSize=6.5, alignment=TA_RIGHT)),
        Paragraph('BRUTO', _style('bh', textColor=colors.white, fontName='Helvetica-Bold',
                                   fontSize=6.5, alignment=TA_RIGHT)),
        Paragraph('%IVA', _style('ih', textColor=colors.white, fontName='Helvetica-Bold',
                                  fontSize=6.5, alignment=TA_RIGHT)),
        Paragraph('IVA', _style('ivh', textColor=colors.white, fontName='Helvetica-Bold',
                                 fontSize=6.5, alignment=TA_RIGHT)),
        Paragraph('TOTAL', _style('th', textColor=colors.white, fontName='Helvetica-Bold',
                                   fontSize=6.5, alignment=TA_RIGHT)),
    ]
    rows = [col_headers]

    total_lineas = 0
    for i, d in enumerate(details, start=1):
        qty      = float(d.get('cantidad', 1))
        price    = float(d.get('precio_unitario', 0))
        desc_pct = float(d.get('descuento_porcentaje', 0))
        base     = float(d.get('subtotal', 0))
        iva_pct  = float(d.get('impuesto_porcentaje', 0))
        iva_val  = float(d.get('impuesto_valor', 0))
        linea_total = base + iva_val
        und      = d.get('unidad_medida', '') or ''
        sku      = d.get('sku', '') or ''
        nombre   = d.get('producto_nombre', '')
        total_lineas += 1

        desc_desc = d.get('descripcion_descuento', '') or ''
        desc_label = (f' <font color="#888888" size="6">▸ Dto: {desc_desc} ({desc_pct:.1f}%)</font>' if desc_pct > 0 and desc_desc
                      else f' <font color="#888888" size="6">▸ Dto: {desc_pct:.1f}%</font>' if desc_pct > 0
                      else '')
        nombre_cell = Paragraph(nombre + desc_label, _style(f'nm{i}', fontSize=7.5))

        rows.append([
            Paragraph(str(i), s_cell),
            Paragraph(sku, s_cell),
            nombre_cell,
            Paragraph(f"{qty:.2f}", _style(f'qty{i}', fontSize=7.5, alignment=TA_RIGHT)),
            Paragraph(und, _style(f'und{i}', fontSize=7.5, alignment=TA_CENTER)),
            Paragraph(_fmt(price), s_cell_r),
            Paragraph(_fmt(base), s_cell_r),
            Paragraph(f"{iva_pct:.2f}", s_cell_r),
            Paragraph(_fmt(iva_val), s_cell_r),
            Paragraph(_fmt(linea_total), _style(f'tot{i}', fontSize=7.5, alignment=TA_RIGHT,
                                                  fontName='Helvetica-Bold')),
        ])

    col_widths = [0.7*cm, 1.8*cm, 4.5*cm, 1.5*cm, 1.2*cm, 2.0*cm, 1.9*cm, 1.0*cm, 1.7*cm, 2.2*cm]
    prod_table = Table(rows, colWidths=col_widths, repeatRows=1)
    prod_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
        ('GRID', (0, 0), (-1, -1), 0.3, MID_GRAY),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (1, 0), 'CENTER'),
    ]))
    story.append(prod_table)
    story.append(Spacer(1, 10))

    # ══════════════════════════════════════════════════════════════════
    # 4. QR + TOTALES
    # ══════════════════════════════════════════════════════════════════
    total_val    = float(invoice.get('total', 0))
    subtotal_val = float(invoice.get('subtotal', 0))
    total_imp    = float(invoice.get('total_impuestos', 0))
    total_desc   = float(invoice.get('total_descuentos', 0))
    cufe         = invoice.get('cufe', '')
    desc_factura_label = invoice.get('descripcion_descuento_factura', '') or ''

    qr_data = f"NumFac:{num_factura};NitEmi:{emp_nit};DocAdq:{cli_doc_num};Total:{_fmt(total_val)};CUFE:{cufe}"
    qr_buf  = _make_qr(qr_data)
    qr_img  = Image(qr_buf, width=2.8 * cm, height=2.8 * cm)

    subtotal_bruto_pdf = subtotal_val + total_desc
    # Calcular porcentaje del descuento de factura (excluyendo descuentos de productos)
    product_disc_sum  = sum(float(d.get('descuento_valor', 0) or 0) for d in details)
    invoice_disc_val  = max(0.0, total_desc - product_disc_sum)
    base_for_inv_pct  = subtotal_val + invoice_disc_val
    invoice_disc_pct  = round(invoice_disc_val / base_for_inv_pct * 100, 1) if base_for_inv_pct > 0 and invoice_disc_val > 0 else 0.0

    totals_data = [
        [Paragraph('Total de Líneas', s_right), Paragraph(str(total_lineas), _style('tln', alignment=TA_RIGHT, fontName='Helvetica-Bold'))],
        [Paragraph('Bruto / Subtotal', s_right), Paragraph(f'$ {_fmt(subtotal_bruto_pdf)}', _style('tsub', alignment=TA_RIGHT, fontName='Helvetica-Bold'))],
    ]
    if total_desc > 0:
        if desc_factura_label:
            desc_label_txt = f'(-) Dto: {desc_factura_label} ({invoice_disc_pct:.1f}%)'
        else:
            desc_label_txt = f'(-) Descuentos ({invoice_disc_pct:.1f}%)'
        totals_data.append([
            Paragraph(f'<font color="#cc0000">{desc_label_txt}</font>', _style('tdesc', alignment=TA_RIGHT, fontSize=7.5)),
            Paragraph(f'<font color="#cc0000">-$ {_fmt(total_desc)}</font>', _style('tdescv', alignment=TA_RIGHT, fontName='Helvetica-Bold', fontSize=7.5)),
        ])
    totals_data += [
        [Paragraph('Base Gravable', s_right), Paragraph(f'$ {_fmt(subtotal_val)}', _style('tbg', alignment=TA_RIGHT, fontName='Helvetica-Bold'))],
        [Paragraph('IVA', s_right), Paragraph(f'$ {_fmt(total_imp)}', _style('tiva', alignment=TA_RIGHT, fontName='Helvetica-Bold'))],
        [Paragraph('Moneda', s_right), Paragraph('COP', _style('tmon', alignment=TA_RIGHT, fontName='Helvetica-Bold'))],
        [Paragraph('<b>TOTAL A PAGAR</b>', _style('ttp', alignment=TA_RIGHT, fontName='Helvetica-Bold',
                                                    textColor=PRIMARY, fontSize=9)),
         Paragraph(f'<b>$ {_fmt(total_val)}</b>', _style('ttpv', alignment=TA_RIGHT, fontName='Helvetica-Bold',
                                                           textColor=colors.white, fontSize=9))],
    ]
    totals_right = Table(totals_data, colWidths=[3.5 * cm, 3.0 * cm])
    last_row = len(totals_data) - 1
    totals_right.setStyle(TableStyle([
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('LINEBELOW', (0, 0), (-1, last_row - 1), 0.3, MID_GRAY),
        ('BACKGROUND', (0, last_row), (-1, last_row), PRIMARY),
        ('TEXTCOLOR', (0, last_row), (-1, last_row), colors.white),
    ]))

    qr_totals = Table([[qr_img, totals_right]], colWidths=[3.2 * cm, 6.8 * cm])
    qr_totals.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
    ]))

    bottom_block = Table([[Spacer(1, 1), qr_totals]], colWidths=[8.5 * cm, 10.0 * cm])
    bottom_block.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
    ]))
    story.append(bottom_block)
    story.append(Spacer(1, 8))

    # ══════════════════════════════════════════════════════════════════
    # 5. TOTAL EN LETRAS + OBSERVACIONES
    # ══════════════════════════════════════════════════════════════════
    total_letras = _total_en_letras(total_val)
    story.append(Paragraph(f'<b>SON:</b>  {total_letras}',
                            _style('son', fontSize=8, fontName='Helvetica')))
    story.append(Spacer(1, 6))

    obs = invoice.get('observaciones', '') or ''
    story.append(Paragraph(f'<b>Observaciones:</b>  {obs}',
                            _style('obs', fontSize=8)))
    story.append(Spacer(1, 10))

    # ══════════════════════════════════════════════════════════════════
    # 6. PIE: CUFE + PÁGINA
    # ══════════════════════════════════════════════════════════════════
    story.append(HRFlowable(width='100%', thickness=2, color=PRIMARY, spaceAfter=4))
    story.append(Paragraph(
        f'CUFE: {cufe}&nbsp;&nbsp;&nbsp;&nbsp;Página 1 de 1',
        _style('cufe', fontSize=6.5, textColor=colors.HexColor('#444'))
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()
