"""
Genera el XML UBL 2.1 de Factura Electrónica según el estándar DIAN Colombia.
Modo pre-producción: sin firma digital real. La firma se agregará cuando se
integre el servicio de tercero con habilitación DIAN.
"""
from datetime import datetime

from services.validaciones import TIPOS_DOCUMENTO


def _fmt(val, decimals=2) -> str:
    return f"{float(val or 0):.{decimals}f}"


def _esc(s: str) -> str:
    if not s:
        return ''
    return (str(s)
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;'))


def generate_invoice_xml(invoice: dict, details: list, empresa: dict) -> str:
    fecha = invoice.get('fecha') or datetime.now()
    if hasattr(fecha, 'strftime'):
        issue_date = fecha.strftime('%Y-%m-%d')
        issue_time = fecha.strftime('%H:%M:%S') + '-05:00'
    else:
        issue_date = str(fecha)[:10]
        issue_time = '00:00:00-05:00'

    cufe         = invoice.get('cufe', '')
    num_factura  = str(invoice.get('numero_factura') or invoice.get('cod_factura', ''))
    prefijo      = empresa.get('prefijo_factura', 'FV')
    nit_empresa  = str(empresa.get('nit', ''))
    dv_empresa   = str(empresa.get('dv', ''))

    # Resolución DIAN
    res_num   = _esc(empresa.get('resolucion_dian', ''))
    res_desde = str(empresa.get('resolucion_fecha_desde', ''))[:10]
    res_hasta = str(empresa.get('resolucion_fecha_hasta', ''))[:10]
    res_from  = str(empresa.get('resolucion_desde', ''))
    res_to    = str(empresa.get('resolucion_hasta', ''))

    # Totales
    subtotal    = _fmt(invoice.get('subtotal', 0))
    total_iva   = _fmt(invoice.get('total_impuestos', 0))
    total_pagar = _fmt(invoice.get('total', 0))

    # Cliente
    cli_nombre = _esc(invoice.get('cliente_nombre', ''))
    cli_doc    = _esc(invoice.get('document_number', ''))
    # `document_type` ya guarda el código del anexo técnico, así que no hay nada que
    # traducir. La traducción a mano que había antes mandaba a un cliente jurídico
    # con esquema 13 (cédula) en lugar de 31 (NIT).
    cli_tipo   = str(invoice.get('document_type') or '13').strip()
    doc_scheme = cli_tipo if cli_tipo in TIPOS_DOCUMENTO else '13'
    cli_dir    = _esc(invoice.get('cliente_address', ''))
    cli_ciudad = _esc(invoice.get('cliente_ciudad', ''))
    cli_correo = _esc(invoice.get('cliente_email', ''))
    cli_cod_mun = str(invoice.get('cliente_cod_municipio', '11001'))

    # Empresa
    emp_nombre = _esc(empresa.get('nombre', ''))
    emp_dir    = _esc(empresa.get('direccion', ''))
    emp_ciudad = _esc(empresa.get('ciudad', ''))
    emp_tel    = _esc(empresa.get('telefono', ''))
    emp_correo = _esc(empresa.get('correo', ''))
    emp_cod_mun = str(empresa.get('cod_municipio') or '76001')
    emp_regimen = empresa.get('regimen_tributario') or 'RESPONSABLE_IVA'
    # «NO_RESPONSABLE_IVA» contiene «RESPONSABLE», así que hay que descartar la
    # negación primero; buscar solo la subcadena clasificaba a los no responsables
    # como responsables.
    tax_level   = 'O-47' if emp_regimen.startswith('NO_RESPONSABLE') else 'O-23'

    # Descuento global de factura (AllowanceCharge a nivel factura)
    desc_factura_val   = float(invoice.get('total_descuentos', 0) or 0)
    desc_factura_label = _esc(invoice.get('descripcion_descuento_factura', '') or 'Descuento comercial')
    subtotal_bruto_xml = float(invoice.get('subtotal', 0)) + desc_factura_val
    allowance_factura_xml = ''
    if desc_factura_val > 0:
        allowance_factura_xml = f"""
    <cac:AllowanceCharge>
        <cbc:ChargeIndicator>false</cbc:ChargeIndicator>
        <cbc:AllowanceChargeReason>{desc_factura_label}</cbc:AllowanceChargeReason>
        <cbc:Amount currencyID="COP">{_fmt(desc_factura_val)}</cbc:Amount>
        <cbc:BaseAmount currencyID="COP">{_fmt(subtotal_bruto_xml)}</cbc:BaseAmount>
    </cac:AllowanceCharge>"""

    # Forma de pago (UBL 2.1 / anexo técnico DIAN)
    #   cac:PaymentMeans/cbc:ID          → 1 contado, 2 crédito
    #   cbc:PaymentMeansCode             → medio de pago (10 efectivo, 20 cheque…)
    #   cbc:PaymentDueDate               → obligatoria cuando la venta es a crédito
    # Antes se ponía siempre ID=1 y el medio de pago se derivaba de forma_pago,
    # que estaba fijo en CONTADO: toda factura se declaraba de contado.
    es_credito = (invoice.get('forma_pago') or 'CONTADO').upper() == 'CREDITO'
    payment_means_id = '2' if es_credito else '1'
    payment_means_code = '20' if es_credito else '10'
    payment_due_date = ''
    if es_credito and invoice.get('fecha_vencimiento'):
        venc = invoice['fecha_vencimiento']
        venc = venc.strftime('%Y-%m-%d') if hasattr(venc, 'strftime') else str(venc)[:10]
        payment_due_date = f"\n        <cbc:PaymentDueDate>{venc}</cbc:PaymentDueDate>"

    # Líneas
    lines_xml = ''
    for i, d in enumerate(details, start=1):
        qty       = _fmt(d.get('cantidad', 1))
        price     = _fmt(d.get('precio_unitario', 0))
        base      = _fmt(d.get('subtotal', 0))
        bruto_lin = _fmt(float(d.get('precio_unitario', 0)) * float(d.get('cantidad', 1)))
        iva_pct   = _fmt(d.get('impuesto_porcentaje', 0))
        iva_val   = _fmt(d.get('impuesto_valor', 0))
        nombre    = _esc(d.get('producto_nombre', ''))
        sku       = _esc(d.get('sku', ''))
        und       = d.get('unidad_medida', 'C62') or 'C62'
        cod_dian  = d.get('impuesto_codigo_dian', '01') or '01'
        desc_val_lin = float(d.get('descuento_valor', 0) or 0)
        desc_desc_lin = _esc(d.get('descripcion_descuento', '') or 'Descuento por producto')

        allowance_line = ''
        if desc_val_lin > 0:
            allowance_line = f"""
            <cac:AllowanceCharge>
                <cbc:ChargeIndicator>false</cbc:ChargeIndicator>
                <cbc:AllowanceChargeReason>{desc_desc_lin}</cbc:AllowanceChargeReason>
                <cbc:Amount currencyID="COP">{_fmt(desc_val_lin)}</cbc:Amount>
                <cbc:BaseAmount currencyID="COP">{bruto_lin}</cbc:BaseAmount>
            </cac:AllowanceCharge>"""

        lines_xml += f"""
        <cac:InvoiceLine>
            <cbc:ID>{i}</cbc:ID>
            <cbc:InvoicedQuantity unitCode="{und}">{qty}</cbc:InvoicedQuantity>
            <cbc:LineExtensionAmount currencyID="COP">{base}</cbc:LineExtensionAmount>
            <cbc:FreeOfChargeIndicator>false</cbc:FreeOfChargeIndicator>{allowance_line}
            <cac:TaxTotal>
                <cbc:TaxAmount currencyID="COP">{iva_val}</cbc:TaxAmount>
                <cac:TaxSubtotal>
                    <cbc:TaxableAmount currencyID="COP">{base}</cbc:TaxableAmount>
                    <cbc:TaxAmount currencyID="COP">{iva_val}</cbc:TaxAmount>
                    <cac:TaxCategory>
                        <cbc:Percent>{iva_pct}</cbc:Percent>
                        <cac:TaxScheme>
                            <cbc:ID>{cod_dian}</cbc:ID>
                            <cbc:Name>IVA</cbc:Name>
                        </cac:TaxScheme>
                    </cac:TaxCategory>
                </cac:TaxSubtotal>
            </cac:TaxTotal>
            <cac:Item>
                <cbc:Description>{nombre}</cbc:Description>
                <cac:StandardItemIdentification>
                    <cbc:ID schemeID="999" schemeName="Estándar de adopción del contribuyente">{sku}</cbc:ID>
                </cac:StandardItemIdentification>
            </cac:Item>
            <cac:Price>
                <cbc:PriceAmount currencyID="COP">{price}</cbc:PriceAmount>
                <cbc:BaseQuantity unitCode="{und}">{qty}</cbc:BaseQuantity>
            </cac:Price>
        </cac:InvoiceLine>"""

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
         xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"
         xmlns:sts="dian:gov:co:facturaelectronica:Structures-2-1">

    <ext:UBLExtensions>
        <ext:UBLExtension>
            <ext:ExtensionContent>
                <sts:DianExtensions>
                    <sts:InvoiceControl>
                        <sts:InvoiceAuthorization>{res_num}</sts:InvoiceAuthorization>
                        <sts:AuthorizationPeriod>
                            <cbc:StartDate>{res_desde}</cbc:StartDate>
                            <cbc:EndDate>{res_hasta}</cbc:EndDate>
                        </sts:AuthorizationPeriod>
                        <sts:AuthorizedInvoices>
                            <sts:Prefix>{prefijo}</sts:Prefix>
                            <sts:From>{res_from}</sts:From>
                            <sts:To>{res_to}</sts:To>
                        </sts:AuthorizedInvoices>
                    </sts:InvoiceControl>
                    <sts:InvoiceSource>
                        <cbc:IdentificationCode listAgencyID="6"
                            listAgencyName="United Nations Economic Commission for Europe"
                            listSchemeURI="urn:oasis:names:specification:ubl:codelist:gc:CountryIdentificationCode-2.1">CO</cbc:IdentificationCode>
                    </sts:InvoiceSource>
                    <sts:QRCode>CUFE:{cufe}</sts:QRCode>
                </sts:DianExtensions>
            </ext:ExtensionContent>
        </ext:UBLExtension>
    </ext:UBLExtensions>

    <cbc:UBLVersionID>UBL 2.1</cbc:UBLVersionID>
    <cbc:CustomizationID>10</cbc:CustomizationID>
    <cbc:ProfileID>DIAN 2.1: Factura Electrónica de Venta</cbc:ProfileID>
    <cbc:ProfileExecutionID>2</cbc:ProfileExecutionID>
    <cbc:ID>{num_factura}</cbc:ID>
    <cbc:UUID schemeID="2" schemeName="CUFE-SHA384">{cufe}</cbc:UUID>
    <cbc:IssueDate>{issue_date}</cbc:IssueDate>
    <cbc:IssueTime>{issue_time}</cbc:IssueTime>
    <cbc:InvoiceTypeCode>01</cbc:InvoiceTypeCode>
    <cbc:DocumentCurrencyCode>COP</cbc:DocumentCurrencyCode>
    <cbc:LineCountNumeric>{len(details)}</cbc:LineCountNumeric>

    <cac:AccountingSupplierParty>
        <cbc:AdditionalAccountID>1</cbc:AdditionalAccountID>
        <cac:Party>
            <cac:PartyName><cbc:Name>{emp_nombre}</cbc:Name></cac:PartyName>
            <cac:PhysicalLocation>
                <cac:Address>
                    <cbc:ID>{emp_cod_mun}</cbc:ID>
                    <cbc:CityName>{emp_ciudad}</cbc:CityName>
                    <cac:AddressLine><cbc:Line>{emp_dir}</cbc:Line></cac:AddressLine>
                    <cac:Country>
                        <cbc:IdentificationCode>CO</cbc:IdentificationCode>
                        <cbc:Name languageID="es">Colombia</cbc:Name>
                    </cac:Country>
                </cac:Address>
            </cac:PhysicalLocation>
            <cac:PartyTaxScheme>
                <cbc:RegistrationName>{emp_nombre}</cbc:RegistrationName>
                <cbc:CompanyID schemeAgencyID="195" schemeID="9" schemeName="31">{nit_empresa}</cbc:CompanyID>
                <cbc:TaxLevelCode>{tax_level}</cbc:TaxLevelCode>
                <cac:TaxScheme><cbc:ID>01</cbc:ID><cbc:Name>IVA</cbc:Name></cac:TaxScheme>
            </cac:PartyTaxScheme>
            <cac:PartyLegalEntity>
                <cbc:RegistrationName>{emp_nombre}</cbc:RegistrationName>
                <cbc:CompanyID schemeAgencyID="195" schemeID="9" schemeName="31">{nit_empresa}</cbc:CompanyID>
                <cac:CorporateRegistrationScheme><cbc:ID>{prefijo}</cbc:ID></cac:CorporateRegistrationScheme>
            </cac:PartyLegalEntity>
            <cac:Contact>
                <cbc:Telephone>{emp_tel}</cbc:Telephone>
                <cbc:ElectronicMail>{emp_correo}</cbc:ElectronicMail>
            </cac:Contact>
        </cac:Party>
    </cac:AccountingSupplierParty>

    <cac:AccountingCustomerParty>
        <cbc:AdditionalAccountID>2</cbc:AdditionalAccountID>
        <cac:Party>
            <cac:PartyName><cbc:Name>{cli_nombre}</cbc:Name></cac:PartyName>
            <cac:PhysicalLocation>
                <cac:Address>
                    <cbc:ID>{cli_cod_mun}</cbc:ID>
                    <cbc:CityName>{cli_ciudad}</cbc:CityName>
                    <cac:AddressLine><cbc:Line>{cli_dir}</cbc:Line></cac:AddressLine>
                    <cac:Country>
                        <cbc:IdentificationCode>CO</cbc:IdentificationCode>
                        <cbc:Name languageID="es">Colombia</cbc:Name>
                    </cac:Country>
                </cac:Address>
            </cac:PhysicalLocation>
            <cac:PartyTaxScheme>
                <cbc:RegistrationName>{cli_nombre}</cbc:RegistrationName>
                <cbc:CompanyID schemeAgencyID="195" schemeName="{doc_scheme}">{cli_doc}</cbc:CompanyID>
                <cac:TaxScheme><cbc:ID>01</cbc:ID><cbc:Name>IVA</cbc:Name></cac:TaxScheme>
            </cac:PartyTaxScheme>
            <cac:PartyLegalEntity>
                <cbc:RegistrationName>{cli_nombre}</cbc:RegistrationName>
                <cbc:CompanyID schemeAgencyID="195" schemeName="{doc_scheme}">{cli_doc}</cbc:CompanyID>
            </cac:PartyLegalEntity>
            <cac:Contact>
                <cbc:ElectronicMail>{cli_correo}</cbc:ElectronicMail>
            </cac:Contact>
        </cac:Party>
    </cac:AccountingCustomerParty>

    <cac:PaymentMeans>
        <cbc:ID>{payment_means_id}</cbc:ID>
        <cbc:PaymentMeansCode>{payment_means_code}</cbc:PaymentMeansCode>{payment_due_date}
    </cac:PaymentMeans>
    {allowance_factura_xml}
    <cac:TaxTotal>
        <cbc:TaxAmount currencyID="COP">{total_iva}</cbc:TaxAmount>
        <cac:TaxSubtotal>
            <cbc:TaxableAmount currencyID="COP">{subtotal}</cbc:TaxableAmount>
            <cbc:TaxAmount currencyID="COP">{total_iva}</cbc:TaxAmount>
            <cac:TaxCategory>
                <cbc:Percent>19.00</cbc:Percent>
                <cac:TaxScheme><cbc:ID>01</cbc:ID><cbc:Name>IVA</cbc:Name></cac:TaxScheme>
            </cac:TaxCategory>
        </cac:TaxSubtotal>
    </cac:TaxTotal>

    <cac:LegalMonetaryTotal>
        <cbc:LineExtensionAmount currencyID="COP">{subtotal}</cbc:LineExtensionAmount>
        <cbc:TaxExclusiveAmount currencyID="COP">{subtotal}</cbc:TaxExclusiveAmount>
        <cbc:TaxInclusiveAmount currencyID="COP">{total_pagar}</cbc:TaxInclusiveAmount>
        <cbc:PayableAmount currencyID="COP">{total_pagar}</cbc:PayableAmount>
    </cac:LegalMonetaryTotal>
    {lines_xml}
</Invoice>"""

    return xml
