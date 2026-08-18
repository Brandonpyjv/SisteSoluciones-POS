import hashlib
from datetime import datetime


def _fmt_amount(value) -> str:
    return f"{float(value or 0):.2f}"


def generate_cufe(invoice: dict, empresa: dict) -> str:
    """
    Genera el CUFE (Código Único de Factura Electrónica) según la fórmula DIAN.
    SHA384( NumFac + FecFac + HorFac + ValFac + CodImp1 + ValImp1 +
            CodImp2 + ValImp2 + CodImp3 + ValImp3 + ValTot + NitOFE +
            NumAdq + ClTec + tipAmbiente )

    En modo pre-producción: tipAmbiente = "2", ClTec = NIT empresa (placeholder).
    """
    fecha = invoice.get('fecha') or datetime.now()
    if hasattr(fecha, 'strftime'):
        fec_fac = fecha.strftime('%Y-%m-%d')
        hor_fac = fecha.strftime('%H:%M:%S') + '-05:00'
    else:
        fec_fac = str(fecha)[:10]
        hor_fac = '00:00:00-05:00'

    num_fac   = str(invoice.get('numero_factura') or invoice.get('cod_factura', ''))
    val_fac   = _fmt_amount(invoice.get('subtotal', 0))
    val_imp1  = _fmt_amount(invoice.get('total_impuestos', 0))  # IVA
    val_imp2  = _fmt_amount(0)                                   # INC
    val_imp3  = _fmt_amount(0)                                   # ICA
    val_tot   = _fmt_amount(invoice.get('total', 0))
    nit_ofe   = str(empresa.get('nit', '')).strip()
    num_adq   = str(invoice.get('document_number') or invoice.get('cliente_doc', ''))
    cl_tec    = nit_ofe  # placeholder hasta tener clave técnica DIAN real
    tip_amb   = "2"      # 2 = habilitación/pruebas, 1 = producción

    cadena = (
        num_fac + fec_fac + hor_fac +
        val_fac +
        "01" + val_imp1 +
        "04" + val_imp2 +
        "03" + val_imp3 +
        val_tot + nit_ofe + num_adq + cl_tec + tip_amb
    )
    return hashlib.sha384(cadena.encode('utf-8')).hexdigest()
