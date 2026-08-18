"""Exportación genérica de reportes a CSV y PDF.

Un reporte se define una sola vez (título, columnas, filas) y desde ahí se
renderiza en pantalla, en CSV y en PDF. Las tres salidas comparten la misma
definición para que no puedan quedar desalineadas.
"""
import csv
import io
from datetime import date, datetime
from decimal import Decimal

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (HRFlowable, Paragraph, SimpleDocTemplate, Spacer,
                                Table, TableStyle)

# Mismos colores del resto del sistema.
PRIMARY  = colors.HexColor('#4e73df')
LIGHT_BG = colors.HexColor('#f8f9fc')
MID_GRAY = colors.HexColor('#e3e6f0')
DARK     = colors.HexColor('#2d3748')
MUTED    = colors.HexColor('#858796')

# Excel en configuración regional española interpreta la coma como separador
# decimal, no de campos: con «,» un reporte de pesos se parte mal en columnas.
CSV_DELIMITADOR = ';'


def formatear(valor, tipo, para='pantalla'):
    """Formatea una celda según su tipo.

    En CSV los números van crudos y con punto decimal para que la hoja de
    cálculo los reconozca como números y no como texto.
    """
    if valor is None:
        return '' if para == 'csv' else '—'

    if tipo == 'dinero':
        numero = float(valor)
        return f"{numero:.2f}" if para == 'csv' else f"${numero:,.2f}"

    if tipo == 'numero':
        numero = float(valor)
        entero = int(numero)
        if para == 'csv':
            return str(entero) if numero == entero else f"{numero:.2f}"
        return f"{entero:,}" if numero == entero else f"{numero:,.2f}"

    if tipo == 'porcentaje':
        return f"{float(valor):.2f}" if para == 'csv' else f"{float(valor):.2f}%"

    if tipo == 'fecha':
        if isinstance(valor, (date, datetime)):
            return valor.strftime('%Y-%m-%d' if para == 'csv' else '%d/%m/%Y')
        return str(valor)

    if isinstance(valor, Decimal):
        return str(valor)
    return str(valor)


def calcular_totales(columnas, filas, excluir=()):
    """Suma las columnas de dinero y de cantidades.

    Los porcentajes nunca se suman, y `excluir` sirve para las columnas donde el
    total no significa nada: un saldo de stock, un costo unitario o unos días de
    vencimiento sumados no son un dato, son ruido.
    """
    totales = {}
    for clave, _, tipo in columnas:
        if tipo not in ('dinero', 'numero') or clave in excluir:
            continue
        totales[clave] = sum(float(f.get(clave) or 0) for f in filas)
    return totales


def to_csv(columnas, filas, totales=None) -> bytes:
    buffer = io.StringIO()
    escritor = csv.writer(buffer, delimiter=CSV_DELIMITADOR, lineterminator='\r\n')
    escritor.writerow([titulo for _, titulo, _ in columnas])

    for fila in filas:
        escritor.writerow([formatear(fila.get(clave), tipo, 'csv')
                           for clave, _, tipo in columnas])

    if totales:
        escritor.writerow([
            'TOTAL' if i == 0 else formatear(totales.get(clave), tipo, 'csv') if clave in totales else ''
            for i, (clave, _, tipo) in enumerate(columnas)
        ])

    # BOM UTF-8: sin él Excel abre el archivo en ANSI y las tildes salen rotas.
    return b'\xef\xbb\xbf' + buffer.getvalue().encode('utf-8')


def to_pdf(titulo, subtitulo, columnas, filas, totales=None, empresa=None) -> bytes:
    buffer = io.BytesIO()
    # Apaisado: estos reportes son anchos y en vertical las columnas se aprietan.
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(letter),
        leftMargin=1.5 * cm, rightMargin=1.5 * cm,
        topMargin=1.2 * cm, bottomMargin=1.5 * cm,
        title=titulo, author='Siste Soluciones',
    )

    est_titulo = ParagraphStyle('titulo', fontName='Helvetica-Bold', fontSize=15,
                                textColor=DARK, leading=18)
    est_sub = ParagraphStyle('sub', fontName='Helvetica', fontSize=9,
                             textColor=MUTED, leading=12)
    est_celda = ParagraphStyle('celda', fontName='Helvetica', fontSize=7.5,
                               textColor=DARK, leading=9.5)
    est_celda_num = ParagraphStyle('celdaNum', parent=est_celda, alignment=TA_RIGHT)
    est_cabecera = ParagraphStyle('cabecera', fontName='Helvetica-Bold', fontSize=7.5,
                                  textColor=colors.white, leading=9.5)

    historia = [Paragraph(titulo, est_titulo)]
    if empresa:
        historia.append(Paragraph(empresa, est_sub))
    if subtitulo:
        historia.append(Paragraph(subtitulo, est_sub))
    historia.append(Spacer(1, 0.3 * cm))
    historia.append(HRFlowable(width='100%', thickness=1, color=MID_GRAY))
    historia.append(Spacer(1, 0.4 * cm))

    numericas = {i for i, (_, _, tipo) in enumerate(columnas)
                 if tipo in ('dinero', 'numero', 'porcentaje')}

    datos = [[Paragraph(t, est_cabecera) for _, t, _ in columnas]]
    for fila in filas:
        datos.append([
            Paragraph(formatear(fila.get(clave), tipo), est_celda_num if i in numericas else est_celda)
            for i, (clave, _, tipo) in enumerate(columnas)
        ])

    if not filas:
        datos.append([Paragraph('Sin datos para los filtros seleccionados.', est_celda)]
                     + [Paragraph('', est_celda)] * (len(columnas) - 1))

    if totales and filas:
        est_total = ParagraphStyle('total', parent=est_celda, fontName='Helvetica-Bold')
        est_total_num = ParagraphStyle('totalNum', parent=est_total, alignment=TA_RIGHT)
        datos.append([
            Paragraph('TOTAL' if i == 0 else
                      (formatear(totales.get(clave), tipo) if clave in totales else ''),
                      est_total_num if i in numericas else est_total)
            for i, (clave, _, tipo) in enumerate(columnas)
        ])

    tabla = Table(datos, repeatRows=1, hAlign='LEFT')
    estilo = [
        ('BACKGROUND',    (0, 0), (-1, 0), PRIMARY),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',    (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING',   (0, 0), (-1, -1), 6),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 6),
        ('LINEBELOW',     (0, 0), (-1, -2), 0.4, MID_GRAY),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
    ]
    if totales and filas:
        estilo += [
            ('BACKGROUND', (0, -1), (-1, -1), MID_GRAY),
            ('LINEABOVE',  (0, -1), (-1, -1), 0.8, PRIMARY),
        ]
    tabla.setStyle(TableStyle(estilo))

    historia.append(tabla)
    historia.append(Spacer(1, 0.5 * cm))
    historia.append(Paragraph(
        f"Generado por Siste Soluciones el {datetime.now().strftime('%d/%m/%Y %H:%M')} · "
        f"{len(filas)} registro(s)", est_sub))

    doc.build(historia)
    return buffer.getvalue()


def nombre_archivo(clave, desde=None, hasta=None, extension='csv'):
    partes = ['siste', clave]
    if desde and hasta:
        partes.append(f"{desde}_a_{hasta}")
    return '-'.join(partes) + '.' + extension
