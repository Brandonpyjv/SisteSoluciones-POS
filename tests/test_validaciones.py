"""Pruebas de las reglas de validación del dominio."""
import pytest

from services.validaciones import (ErrorValidacion, Validador, calcular_dv, cantidad,
                                   correo, decimal, dinero, dv, entero, fecha,
                                   fechas_ordenadas, nombre_persona, numero_documento,
                                   opcion, porcentaje, precio, rango, razon_social, sku,
                                   telefono, texto, tipo_documento)


def error(funcion, *args, **kwargs) -> str:
    """Ejecuta la validación esperando que falle y devuelve el mensaje."""
    with pytest.raises(ErrorValidacion) as capturado:
        funcion(*args, **kwargs)
    return capturado.value.mensaje


# ── Números ─────────────────────────────────────────────────────────────────

def test_entero_acepta_cero_y_positivos():
    assert entero(0) == 0
    assert entero("15") == 15
    assert entero(7.0) == 7


def test_entero_rechaza_negativos():
    assert error(entero, -1) == "No puede ser negativo"
    assert error(entero, "-40") == "No puede ser negativo"


def test_entero_rechaza_decimales_y_texto():
    assert error(entero, 2.5) == "Debe ser un número entero, sin decimales"
    assert error(entero, "abc") == "Debe ser un número"
    assert error(entero, "") == "Es obligatorio"
    assert error(entero, None) == "Es obligatorio"


def test_entero_respeta_el_maximo():
    assert entero(365, maximo=365) == 365
    assert error(entero, 366, maximo=365) == "No puede ser mayor que 365"


def test_los_numeros_admiten_coma_decimal_y_espacios():
    assert decimal("1234,50") == 1234.5
    assert decimal(" 99.9 ") == 99.9


def test_el_dinero_no_puede_ser_negativo_pero_si_cero():
    assert dinero(0) == 0
    assert dinero("189000") == 189000.0
    assert error(dinero, -0.01) == "No puede ser negativo"


def test_el_precio_debe_ser_mayor_que_cero():
    assert precio(1) == 1
    assert error(precio, 0) == "Debe ser mayor que cero"
    assert error(precio, -5) == "No puede ser negativo"


def test_la_cantidad_arranca_en_uno():
    assert cantidad(1) == 1
    assert error(cantidad, 0) == "No puede ser menor que 1"
    assert error(cantidad, -3) == "No puede ser menor que 1"


def test_la_cantidad_fraccionaria_es_opcional():
    assert cantidad(2.5, fraccionaria=True) == 2.5
    assert error(cantidad, 2.5) == "Debe ser un número entero, sin decimales"


def test_el_porcentaje_va_de_cero_a_cien():
    assert porcentaje(0) == 0
    assert porcentaje(19) == 19
    assert porcentaje(100) == 100
    assert error(porcentaje, 150) == "No puede ser mayor que 100"
    assert error(porcentaje, -1) == "No puede ser negativo"


def test_infinito_y_nan_no_pasan_por_numero():
    assert error(decimal, "inf") == "Debe ser un número"
    assert error(decimal, "nan") == "Debe ser un número"


# ── Texto ───────────────────────────────────────────────────────────────────

def test_el_nombre_de_persona_admite_tildes_y_apostrofos():
    assert nombre_persona("María Fernanda Ospina") == "María Fernanda Ospina"
    assert nombre_persona("  Iván Muñoz  ") == "Iván Muñoz"
    assert nombre_persona("Jean-Luc D'Alembert") == "Jean-Luc D'Alembert"


def test_el_nombre_de_persona_rechaza_numeros_y_simbolos():
    assert error(nombre_persona, "Juan 3ro") == "No puede contener números"
    assert "letras" in error(nombre_persona, "Pedro <script>")


def test_la_razon_social_si_admite_numeros():
    """Esta es la razón por la que no se puede usar la misma regla que para personas."""
    assert razon_social("Comercial 3M S.A.S.") == "Comercial 3M S.A.S."
    assert razon_social("Siste Soluciones & Cía.") == "Siste Soluciones & Cía."
    assert error(nombre_persona, "Comercial 3M S.A.S.") == "No puede contener números"


def test_la_razon_social_necesita_al_menos_una_letra():
    assert error(razon_social, "123456") == "Debe contener letras"


def test_el_texto_respeta_el_largo():
    assert texto("hola", maximo=10) == "hola"
    assert error(texto, "x" * 11, maximo=10) == "No puede pasar de 10 caracteres"
    assert texto("", requerido=False) == ""


def test_el_sku_se_normaliza_en_mayusculas():
    assert sku("tec-014") == "TEC-014"
    assert "letras" in error(sku, "tec 014!")


def test_el_correo_valida_forma_y_se_normaliza():
    assert correo("MOspina@Correo.com") == "mospina@correo.com"
    assert correo("", requerido=False) == ""
    assert error(correo, "sin-arroba") == "No parece un correo válido"
    assert error(correo, "doble@@correo.com") == "No parece un correo válido"
    assert error(correo, "sin@dominio") == "No parece un correo válido"


def test_el_telefono_cuenta_digitos():
    assert telefono("+57 300 123 4567") == "+57 300 123 4567"
    assert error(telefono, "123") == "Debe tener entre 7 y 15 dígitos"
    assert "números" in error(telefono, "300-ABC-4567")


# ── Identificación ──────────────────────────────────────────────────────────

def test_la_cedula_solo_admite_numeros():
    assert numero_documento("1090234567", "13") == "1090234567"
    assert error(numero_documento, "AB1234", "13") == \
        "El Cédula de ciudadanía solo admite números"


def test_el_pasaporte_admite_letras():
    """El caso que mencionó la instructora: depende del tipo de documento."""
    assert numero_documento("AV123456", "41") == "AV123456"
    assert numero_documento("123456", "41") == "123456"


def test_la_identificacion_ignora_puntos_y_guiones_de_separacion():
    assert numero_documento("1.090.234.567", "13") == "1090234567"


def test_la_identificacion_respeta_el_largo_de_su_tipo():
    assert "entre 8 y 10" in error(numero_documento, "123", "31")


def test_las_etiquetas_traducen_el_codigo_para_las_personas():
    from services.validaciones import (abreviatura_documento, nombre_documento,
                                       tipos_documento_ordenados)
    assert abreviatura_documento("13") == "CC"
    assert abreviatura_documento("31") == "NIT"
    assert abreviatura_documento("41") == "PA"
    assert nombre_documento("31") == "NIT"
    assert nombre_documento("13") == "Cédula de ciudadanía"
    # Un valor desconocido se muestra tal cual en lugar de desaparecer.
    assert abreviatura_documento("ZZ") == "ZZ"
    assert abreviatura_documento(None) == ""

    tipos = tipos_documento_ordenados()
    assert tipos[0] == ("13", "CC - Cédula de ciudadanía")
    assert ("41", "PA - Pasaporte") in tipos
    # Cuando la abreviatura y el nombre coinciden no se repite el texto.
    assert ("31", "NIT") in tipos
    assert len(tipos) == 10


def test_el_tipo_de_documento_debe_ser_del_catalogo_dian():
    assert tipo_documento("13") == "13"
    assert tipo_documento("31") == "31"
    # El catálogo viejo del formulario ya no pasa.
    assert error(tipo_documento, "C") == "No es un tipo de documento válido"
    assert error(tipo_documento, "J") == "No es un tipo de documento válido"


@pytest.mark.parametrize("nit,esperado", [
    # NIT de conocimiento público, con su dígito real.
    ("890903938", 8),   # Bancolombia
    ("800197268", 4),   # DIAN
    # Calculado a mano: 5·3+1·7+1·13+3·17+7·19+3·23+0+0+9·41 = 657; 657 % 11 = 8; 11−8 = 3.
    ("900373115", 3),
])
def test_el_digito_de_verificacion_sigue_el_algoritmo_dian(nit, esperado):
    assert calcular_dv(nit) == esperado


def test_el_dv_calculado_siempre_se_verifica_contra_su_propio_nit():
    """Propiedad que no depende de conocer dígitos reales: lo calculado se acepta."""
    for base in range(900000000, 900000200):
        nit = str(base)
        assert dv(str(calcular_dv(nit)), nit) == str(calcular_dv(nit))


def test_el_dv_siempre_queda_entre_cero_y_nueve():
    for base in range(890000000, 890000300):
        assert 0 <= calcular_dv(str(base)) <= 9


def test_el_dv_se_calcula_si_viene_vacio_y_se_verifica_si_viene():
    assert dv("", "890903938") == "8"
    assert dv("8", "890903938") == "8"
    assert "debería ser 8" in error(dv, "1", "890903938")


# ── Rangos y fechas ─────────────────────────────────────────────────────────

def test_el_rango_de_numeracion_exige_desde_menor_o_igual_que_hasta():
    assert rango(1, 5000) == (1, 5000)
    assert rango(7, 7) == (7, 7)
    assert error(rango, 5000, 1) == "No puede ser menor que el valor inicial"


def test_el_rango_no_admite_negativos_ni_cero():
    assert error(rango, 0, 100) == "No puede ser menor que 1"
    assert error(rango, -10, 100) == "No puede ser menor que 1"


def test_el_rango_puede_quedar_vacio_si_no_es_obligatorio():
    assert rango("", "", requerido=False) == (None, None)
    assert error(rango, "", "") == "Es obligatorio"


def test_las_fechas_de_vigencia_deben_ir_en_orden():
    inicio, fin = fechas_ordenadas("2026-01-01", "2026-12-31")
    assert (inicio.year, fin.month) == (2026, 12)
    assert error(fechas_ordenadas, "2026-12-31", "2026-01-01") == \
        "No puede ser anterior a la fecha inicial"


def test_una_fecha_mal_escrita_se_rechaza():
    assert error(fecha, "31/12/2026") == "No es una fecha válida"
    assert error(fecha, "2026-13-45") == "No es una fecha válida"


# ── Identidad de la empresa emisora ─────────────────────────────────────────

def test_el_nit_solo_admite_digitos_y_de_8_a_10():
    from services.validaciones import nit
    assert nit("901555444") == "901555444"
    assert nit("901.555.444") == "901555444"
    assert error(nit, "90A555444") == "El NIT solo admite números"
    assert "entre 8 y 10" in error(nit, "123")


def test_el_ciiu_son_cuatro_digitos():
    from services.validaciones import codigo_ciiu
    assert codigo_ciiu("4741") == "4741"
    assert codigo_ciiu("") == ""
    assert error(codigo_ciiu, "47") == "El código CIIU son cuatro dígitos"
    assert error(codigo_ciiu, "47A1") == "El código CIIU son cuatro dígitos"


def test_el_prefijo_se_normaliza_y_no_admite_simbolos():
    from services.validaciones import prefijo
    assert prefijo("setp") == "SETP"
    assert error(prefijo, "SE-TP") == "Solo puede contener letras y números"
    assert error(prefijo, "") == "Es obligatorio"


def test_la_contrasena_exige_largo_minimo_salvo_al_editar():
    from services.validaciones import contrasena
    assert contrasena("clave-segura-1") == "clave-segura-1"
    assert error(contrasena, "123") == "Debe tener al menos 8 caracteres"
    assert error(contrasena, "") == "Es obligatoria"
    # Al editar, vacía significa «déjala como está».
    assert contrasena("", requerido=False) == ""


def test_el_sitio_web_rechaza_lo_que_no_parece_dominio():
    from services.validaciones import sitio_web
    assert sitio_web("siste.co") == "siste.co"
    assert sitio_web("") == ""
    assert error(sitio_web, "sin punto") == "No parece una dirección web válida"


def test_la_pareja_asigna_los_dos_campos_o_marca_el_que_falla():
    from services.validaciones import rango
    v = Validador()
    v.pareja(("desde", "hasta"), rango, 1, 5000, "desde", "hasta")
    assert v.valido and v.datos == {"desde": 1, "hasta": 5000}

    v = Validador()
    v.pareja(("desde", "hasta"), rango, 5000, 1, "desde", "hasta")
    assert not v.valido
    assert list(v.errores) == ["hasta"]


# ── Catálogos ───────────────────────────────────────────────────────────────

def test_la_opcion_debe_estar_en_la_lista_blanca():
    assert opcion("FV", ("FV", "NC", "ND")) == "FV"
    assert error(opcion, "XX", ("FV", "NC", "ND")) == "No es una opción válida"


# ── Acumulador para formularios ─────────────────────────────────────────────

def test_el_validador_acumula_todos_los_errores_del_formulario():
    v = Validador()
    v.campo("nombre", nombre_persona, "Juan 3ro")
    v.campo("precio", precio, -100)
    v.campo("correo", correo, "roto@")
    v.campo("stock", entero, "40")

    assert not v.valido
    assert set(v.errores) == {"nombre", "precio", "correo"}
    assert v.datos["stock"] == 40
    assert "·" in v.resumen()


def test_el_validador_queda_valido_cuando_todo_pasa():
    v = Validador()
    v.campo("nombre", nombre_persona, "María Ospina")
    v.campo("precio", precio, "189000")

    assert v.valido
    assert v.errores == {}
    assert v.datos == {"nombre": "María Ospina", "precio": 189000.0}
