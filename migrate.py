"""
Migraciones de esquema para Siste Soluciones.

    python migrate.py

Cada migración es idempotente: puede ejecutarse las veces que sea sin romper nada.
Lo aplicado queda registrado en la tabla `schema_migrations` para dejar traza.

El proyecto no usa ORM ni una herramienta de migraciones; este script existe para que
los cambios de esquema queden versionados en el repositorio y todo el equipo pueda
aplicarlos con un solo comando en lugar de pasarse ALTERs por chat.
"""
import sys
from datetime import datetime

from database import create_connection


# ── Helpers de introspección ────────────────────────────────────────────────

def _table_exists(cursor, table: str) -> bool:
    cursor.execute(
        "SELECT COUNT(*) FROM information_schema.TABLES "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s",
        (table,),
    )
    return cursor.fetchone()[0] > 0


def _column_exists(cursor, table: str, column: str) -> bool:
    cursor.execute(
        "SELECT COUNT(*) FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s",
        (table, column),
    )
    return cursor.fetchone()[0] > 0


def _ensure_migrations_table(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version     VARCHAR(50)  NOT NULL,
            descripcion VARCHAR(255) NOT NULL,
            aplicada_en DATETIME     NOT NULL,
            PRIMARY KEY (version)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)


def _already_applied(cursor, version: str) -> bool:
    cursor.execute("SELECT COUNT(*) FROM schema_migrations WHERE version = %s", (version,))
    return cursor.fetchone()[0] > 0


def _mark_applied(cursor, version: str, descripcion: str):
    cursor.execute(
        "INSERT INTO schema_migrations (version, descripcion, aplicada_en) VALUES (%s, %s, %s)",
        (version, descripcion, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )


# ── 001 · Módulo de inventario ──────────────────────────────────────────────

def migracion_001_inventario(cursor):
    """Kardex de movimientos y control de qué productos manejan stock."""
    pasos = []

    if not _table_exists(cursor, "movimientos_inventario"):
        cursor.execute("""
            CREATE TABLE movimientos_inventario (
                cod_movimiento  INT(11)       NOT NULL AUTO_INCREMENT,
                cod_producto    INT(11)       NOT NULL,
                tipo            VARCHAR(10)   NOT NULL COMMENT 'ENTRADA | SALIDA | AJUSTE',
                motivo          VARCHAR(30)   NOT NULL COMMENT 'VENTA, COMPRA, DEVOLUCION, AJUSTE_MANUAL, MERMA, INICIAL, ANULACION',
                cantidad        INT(11)       NOT NULL COMMENT 'Siempre positivo; el signo lo determina el tipo',
                stock_anterior  INT(11)       NOT NULL,
                stock_nuevo     INT(11)       NOT NULL,
                costo_unitario  DECIMAL(12,2)          DEFAULT NULL,
                cod_factura     INT(11)                DEFAULT NULL,
                cod_usuario     INT(11)                DEFAULT NULL,
                observaciones   VARCHAR(255)           DEFAULT NULL,
                fecha           DATETIME(6)   NOT NULL,
                PRIMARY KEY (cod_movimiento),
                KEY idx_mov_producto (cod_producto),
                KEY idx_mov_fecha    (fecha),
                KEY idx_mov_factura  (cod_factura),
                CONSTRAINT fk_mov_producto FOREIGN KEY (cod_producto)
                    REFERENCES productos (cod_producto) ON DELETE CASCADE,
                CONSTRAINT fk_mov_usuario  FOREIGN KEY (cod_usuario)
                    REFERENCES usuarios (cod_usuario)  ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        pasos.append("tabla movimientos_inventario creada")

    if not _column_exists(cursor, "productos", "controla_stock"):
        cursor.execute(
            "ALTER TABLE productos ADD COLUMN controla_stock TINYINT(1) NOT NULL DEFAULT 1 "
            "COMMENT '0 = servicio o intangible: no descuenta inventario' AFTER stock_minimo"
        )
        # WSD es la unidad DIAN de servicio: no tiene sentido llevarle inventario.
        cursor.execute("UPDATE productos SET controla_stock = 0 WHERE unidad_medida = 'WSD'")
        pasos.append("columna productos.controla_stock creada")

    # Saldo de apertura: sin esto el kardex arranca vacío y no cuadraría con el stock actual.
    cursor.execute("SELECT COUNT(*) FROM movimientos_inventario WHERE motivo = 'INICIAL'")
    if cursor.fetchone()[0] == 0:
        ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO movimientos_inventario
                (cod_producto, tipo, motivo, cantidad, stock_anterior, stock_nuevo,
                 costo_unitario, observaciones, fecha)
            SELECT cod_producto, 'ENTRADA', 'INICIAL', COALESCE(stock, 0), 0, COALESCE(stock, 0),
                   precio_unitario, 'Saldo de apertura al implementar el kardex', %s
            FROM productos
            WHERE controla_stock = 1
        """, (ahora,))
        pasos.append(f"{cursor.rowcount} saldos de apertura registrados")

    return pasos


# ── 002 · Foto de perfil ────────────────────────────────────────────────────

def migracion_002_foto_perfil(cursor):
    """Foto de perfil del usuario, mostrada en el navbar y el listado."""
    pasos = []

    if not _column_exists(cursor, "usuarios", "foto"):
        cursor.execute(
            "ALTER TABLE usuarios ADD COLUMN foto VARCHAR(255) DEFAULT NULL "
            "COMMENT 'Nombre del archivo dentro de static/img/perfiles; NULL = avatar genérico' "
            "AFTER rol"
        )
        pasos.append("columna usuarios.foto creada")

    return pasos


# ── 003 · API middleware DIAN ───────────────────────────────────────────────

def migracion_003_api_middleware(cursor):
    """Tablas de los documentos que emitimos por cuenta de terceros.

    Están separadas de `facturas` a propósito: ahí van nuestras ventas de planes,
    y meter las facturas de nuestros clientes las contaría como ingresos propios
    en el tablero y en los reportes.
    """
    pasos = []

    if not _table_exists(cursor, "clientes_api"):
        cursor.execute("""
            CREATE TABLE clientes_api (
                cod_cliente_api INT(11)      NOT NULL AUTO_INCREMENT,
                nombre          VARCHAR(150) NOT NULL COMMENT 'Nombre del negocio o sistema integrado',
                cod_cliente     INT(11)               DEFAULT NULL COMMENT 'customers: a quien le facturamos el plan',
                cod_empresa     INT(11)      NOT NULL COMMENT 'empresas: con que NIT y resolucion emite',
                api_key_prefijo VARCHAR(20)  NOT NULL COMMENT 'Parte visible de la llave; permite ubicar la fila sin revelarla',
                api_key_hash    VARCHAR(255) NOT NULL COMMENT 'Hash de la llave completa; la llave se muestra una sola vez',
                plan            VARCHAR(20)  NOT NULL DEFAULT 'BASICO',
                limite_mensual  INT(11)               DEFAULT NULL COMMENT 'Documentos por mes; NULL = sin limite',
                estado          VARCHAR(20)  NOT NULL DEFAULT 'ACTIVO' COMMENT 'ACTIVO | SUSPENDIDO | REVOCADO',
                creado_en       DATETIME     NOT NULL,
                ultimo_uso      DATETIME              DEFAULT NULL,
                PRIMARY KEY (cod_cliente_api),
                UNIQUE KEY uq_api_key_prefijo (api_key_prefijo),
                KEY idx_cliente_api_empresa (cod_empresa),
                KEY idx_cliente_api_cliente (cod_cliente),
                CONSTRAINT fk_cliente_api_empresa FOREIGN KEY (cod_empresa)
                    REFERENCES empresas (cod_empresa),
                CONSTRAINT fk_cliente_api_cliente FOREIGN KEY (cod_cliente)
                    REFERENCES customers (customer_id) ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        pasos.append("tabla clientes_api creada")

    if not _table_exists(cursor, "receptores"):
        cursor.execute("""
            CREATE TABLE receptores (
                cod_receptor       INT(11)      NOT NULL AUTO_INCREMENT,
                cod_cliente_api    INT(11)      NOT NULL,
                tipo_documento     VARCHAR(4)   NOT NULL COMMENT 'Codigo DIAN: 13 CC, 22 CE, 31 NIT, 41 Pasaporte',
                numero_documento   VARCHAR(30)  NOT NULL,
                dv                 CHAR(1)               DEFAULT NULL,
                nombre             VARCHAR(200) NOT NULL,
                tipo_persona       VARCHAR(20)           DEFAULT 'NATURAL',
                regimen_tributario VARCHAR(60)           DEFAULT 'NO_RESPONSABLE_IVA',
                email              VARCHAR(150)          DEFAULT NULL,
                telefono           VARCHAR(40)           DEFAULT NULL,
                direccion          VARCHAR(200)          DEFAULT NULL,
                cod_municipio      CHAR(5)               DEFAULT NULL,
                creado_en          DATETIME     NOT NULL,
                PRIMARY KEY (cod_receptor),
                -- El mismo comprador enviado dos veces se reutiliza en lugar de duplicarse,
                -- y cada cliente API ve solo su propio padron.
                UNIQUE KEY uq_receptor_del_cliente (cod_cliente_api, tipo_documento, numero_documento),
                CONSTRAINT fk_receptor_cliente_api FOREIGN KEY (cod_cliente_api)
                    REFERENCES clientes_api (cod_cliente_api) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        pasos.append("tabla receptores creada")

    if not _table_exists(cursor, "documentos"):
        cursor.execute("""
            CREATE TABLE documentos (
                cod_documento      INT(11)       NOT NULL AUTO_INCREMENT,
                id_publico         VARCHAR(40)   NOT NULL COMMENT 'Identificador que ve el cliente; no exponemos el autoincremental',
                cod_cliente_api    INT(11)       NOT NULL,
                cod_empresa        INT(11)       NOT NULL COMMENT 'Emisor con cuya resolucion se numero',
                cod_receptor       INT(11)       NOT NULL,
                tipo               VARCHAR(5)    NOT NULL DEFAULT 'FV' COMMENT 'FV | NC | ND',
                prefijo            VARCHAR(10)            DEFAULT NULL,
                consecutivo        BIGINT(20)             DEFAULT NULL,
                numero             VARCHAR(50)            DEFAULT NULL,
                cufe               VARCHAR(200)           DEFAULT NULL,
                fecha_emision      DATETIME(6)   NOT NULL,
                fecha_vencimiento  DATE                   DEFAULT NULL,
                forma_pago         VARCHAR(20)   NOT NULL DEFAULT 'CONTADO',
                subtotal_bruto     DECIMAL(14,2) NOT NULL DEFAULT 0,
                total_descuentos   DECIMAL(14,2) NOT NULL DEFAULT 0,
                subtotal           DECIMAL(14,2) NOT NULL DEFAULT 0 COMMENT 'Base gravable neta',
                total_impuestos    DECIMAL(14,2) NOT NULL DEFAULT 0,
                total              DECIMAL(14,2) NOT NULL DEFAULT 0,
                estado             VARCHAR(20)   NOT NULL DEFAULT 'PENDIENTE' COMMENT 'PENDIENTE | ACEPTADO | RECHAZADO | ERROR',
                referencia_externa VARCHAR(80)            DEFAULT NULL COMMENT 'Identificador de la venta en el sistema del cliente',
                cod_documento_referencia INT(11)          DEFAULT NULL COMMENT 'La FV que origina una NC o ND',
                motivo_nota        TEXT                   DEFAULT NULL,
                observaciones      TEXT                   DEFAULT NULL,
                orden_compra       VARCHAR(100)           DEFAULT NULL,
                proveedor_dian     VARCHAR(20)            DEFAULT NULL COMMENT 'simulado | factus',
                -- Se guarda el XML y no el PDF: el XML es lo que se firma y valida, y hay
                -- deber de conservarlo. La representacion grafica se regenera de estos datos.
                xml                MEDIUMTEXT             DEFAULT NULL,
                creado_en          DATETIME      NOT NULL,
                PRIMARY KEY (cod_documento),
                UNIQUE KEY uq_documento_publico (id_publico),
                -- Idempotencia: reintentar la misma venta no emite un segundo documento.
                -- MySQL admite varios NULL en un indice unico, asi que quien no manda
                -- referencia no queda bloqueado.
                UNIQUE KEY uq_referencia_del_cliente (cod_cliente_api, referencia_externa),
                -- Red de seguridad sobre la reserva atomica del consecutivo: aunque la
                -- aplicacion se equivoque, la base no acepta dos veces el mismo numero.
                UNIQUE KEY uq_numero_del_emisor (cod_empresa, tipo, numero),
                KEY idx_documento_cliente (cod_cliente_api),
                KEY idx_documento_fecha (fecha_emision),
                KEY idx_documento_estado (estado),
                KEY idx_documento_referencia (cod_documento_referencia),
                CONSTRAINT fk_documento_cliente_api FOREIGN KEY (cod_cliente_api)
                    REFERENCES clientes_api (cod_cliente_api),
                CONSTRAINT fk_documento_empresa FOREIGN KEY (cod_empresa)
                    REFERENCES empresas (cod_empresa),
                CONSTRAINT fk_documento_receptor FOREIGN KEY (cod_receptor)
                    REFERENCES receptores (cod_receptor),
                CONSTRAINT fk_documento_referencia FOREIGN KEY (cod_documento_referencia)
                    REFERENCES documentos (cod_documento) ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        pasos.append("tabla documentos creada")

    if not _table_exists(cursor, "documento_lineas"):
        cursor.execute("""
            CREATE TABLE documento_lineas (
                cod_linea             INT(11)       NOT NULL AUTO_INCREMENT,
                cod_documento         INT(11)       NOT NULL,
                orden                 INT(11)       NOT NULL DEFAULT 1,
                -- No es FK a productos: el catalogo es del sistema del cliente, no nuestro.
                codigo                VARCHAR(60)            DEFAULT NULL COMMENT 'SKU en el sistema del cliente',
                descripcion           VARCHAR(300)  NOT NULL,
                unidad_medida         VARCHAR(10)            DEFAULT '94',
                -- Con decimales porque la DIAN admite unidades fraccionarias (kilos, horas);
                -- nuestro detalle_factura interno solo maneja enteros.
                cantidad              DECIMAL(14,3) NOT NULL,
                precio_unitario       DECIMAL(14,2) NOT NULL,
                valor_bruto           DECIMAL(14,2) NOT NULL DEFAULT 0,
                descuento_porcentaje  DECIMAL(6,3)  NOT NULL DEFAULT 0,
                descuento_valor       DECIMAL(14,2) NOT NULL DEFAULT 0,
                descripcion_descuento VARCHAR(200)           DEFAULT NULL,
                subtotal              DECIMAL(14,2) NOT NULL DEFAULT 0 COMMENT 'Base gravable de la linea',
                impuesto_codigo_dian  VARCHAR(5)             DEFAULT '01',
                impuesto_porcentaje   DECIMAL(6,3)  NOT NULL DEFAULT 0,
                impuesto_valor        DECIMAL(14,2) NOT NULL DEFAULT 0,
                PRIMARY KEY (cod_linea),
                KEY idx_linea_documento (cod_documento),
                CONSTRAINT fk_linea_documento FOREIGN KEY (cod_documento)
                    REFERENCES documentos (cod_documento) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        pasos.append("tabla documento_lineas creada")

    if not _table_exists(cursor, "documento_eventos"):
        cursor.execute("""
            CREATE TABLE documento_eventos (
                cod_evento    INT(11)     NOT NULL AUTO_INCREMENT,
                cod_documento INT(11)     NOT NULL,
                tipo          VARCHAR(30) NOT NULL COMMENT 'RECIBIDO | TRANSMITIDO | ACEPTADO | RECHAZADO | CORREO_ENVIADO | ERROR',
                proveedor     VARCHAR(20)          DEFAULT NULL,
                codigo        VARCHAR(20)          DEFAULT NULL COMMENT 'Codigo de respuesta del proveedor',
                mensaje       TEXT                 DEFAULT NULL,
                -- Respuesta cruda del proveedor: si la DIAN rechaza, hay que poder mostrar
                -- exactamente que contesto y no una interpretacion nuestra.
                payload       MEDIUMTEXT           DEFAULT NULL,
                fecha         DATETIME(6) NOT NULL,
                PRIMARY KEY (cod_evento),
                KEY idx_evento_documento (cod_documento),
                KEY idx_evento_fecha (fecha),
                CONSTRAINT fk_evento_documento FOREIGN KEY (cod_documento)
                    REFERENCES documentos (cod_documento) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        pasos.append("tabla documento_eventos creada")

    # No hay tabla de consumo: los documentos por cliente y por mes se cuentan de
    # `documentos`, de modo que el contador nunca puede desviarse de la realidad.

    return pasos


# ── 004 · Tipos de documento con los códigos de la DIAN ─────────────────────

# El catálogo anterior era propio (C, E, J, G) y no correspondía al del anexo
# técnico, así que `xml_service` traducía a mano y se equivocaba: mandaba un
# cliente jurídico con esquema 13 (cédula) en lugar de 31 (NIT). Las entidades
# públicas —la «G» de gobierno— también se identifican con NIT; la DIAN no tiene
# un código aparte para ellas.
_MAPEO_TIPOS = {
    "C": "13",   # Cédula de ciudadanía
    "E": "22",   # Cédula de extranjería
    "J": "31",   # NIT
    "N": "31",   # NIT (lo que xml_service ya trataba como NIT)
    "G": "31",   # Gobierno → NIT
}


def migracion_004_tipos_documento_dian(cursor):
    """Convierte customers.document_type al código DIAN."""
    pasos = []

    cursor.execute(
        "SELECT COLUMN_TYPE FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'customers' "
        "AND COLUMN_NAME = 'document_type'"
    )
    fila = cursor.fetchone()
    tipo_actual = (fila[0] if fila else "").lower()

    # Un char(1) no alcanza para un código de dos dígitos: hay que ensanchar antes
    # de convertir, o el UPDATE truncaría los valores.
    if tipo_actual != "varchar(4)":
        cursor.execute(
            "ALTER TABLE customers MODIFY document_type VARCHAR(4) NOT NULL DEFAULT '13' "
            "COMMENT 'Código DIAN: 13 CC, 22 CE, 31 NIT, 41 Pasaporte'"
        )
        pasos.append("columna customers.document_type ensanchada a VARCHAR(4)")

    for viejo, nuevo in _MAPEO_TIPOS.items():
        cursor.execute(
            "UPDATE customers SET document_type = %s WHERE document_type = %s",
            (nuevo, viejo),
        )
        if cursor.rowcount:
            pasos.append(f"{cursor.rowcount} cliente(s) con '{viejo}' pasan a '{nuevo}'")

    # Lo que no estaba en el catálogo viejo ni es un código válido se deja como
    # cédula, que es el caso mayoritario, pero se reporta para poder revisarlo.
    codigos = ", ".join(f"'{c}'" for c in
                        ("11", "12", "13", "21", "22", "31", "41", "42", "50", "91"))
    cursor.execute(f"SELECT COUNT(*) FROM customers WHERE document_type NOT IN ({codigos})")
    sueltos = cursor.fetchone()[0]
    if sueltos:
        cursor.execute(f"UPDATE customers SET document_type = '13' "
                       f"WHERE document_type NOT IN ({codigos})")
        pasos.append(f"ATENCION: {sueltos} cliente(s) con un tipo desconocido quedaron en '13'")

    return pasos


# ── 005 · Líneas de concepto en el detalle ──────────────────────────────────

def migracion_005_lineas_de_concepto(cursor):
    """Permite que una línea describa un concepto y no un producto del catálogo.

    Una nota débito ajusta un flete, un interés o un cargo: no hay un producto
    al que apuntar. Se emitían sin ninguna línea, así que su XML salía sin
    InvoiceLine y la DIAN lo habría rechazado.
    """
    pasos = []

    cursor.execute(
        "SELECT IS_NULLABLE FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'detalle_factura' "
        "AND COLUMN_NAME = 'cod_producto'"
    )
    fila = cursor.fetchone()
    if fila and fila[0] == "NO":
        cursor.execute(
            "ALTER TABLE detalle_factura MODIFY cod_producto INT(11) DEFAULT NULL "
            "COMMENT 'NULL cuando la linea es un concepto y no un producto'"
        )
        pasos.append("detalle_factura.cod_producto ahora admite NULL")

    if not _column_exists(cursor, "detalle_factura", "descripcion"):
        cursor.execute(
            "ALTER TABLE detalle_factura ADD COLUMN descripcion VARCHAR(300) DEFAULT NULL "
            "COMMENT 'Texto de la linea cuando no hay producto; si hay, manda el del producto' "
            "AFTER cod_producto"
        )
        pasos.append("columna detalle_factura.descripcion creada")

    # Las notas débito ya emitidas no tienen líneas. Se reconstruye la suya a
    # partir de la cabecera, que es donde quedó el ajuste, para que dejen de ser
    # documentos que ningún proveedor aceptaría.
    cursor.execute("""
        SELECT f.cod_factura, f.subtotal, f.total_impuestos, f.motivo_nota
        FROM facturas f
        LEFT JOIN detalle_factura d ON f.cod_factura = d.cod_factura
        WHERE f.tipo_factura = 'ND'
        GROUP BY f.cod_factura, f.subtotal, f.total_impuestos, f.motivo_nota
        HAVING COUNT(d.cod_destalle) = 0
    """)
    huerfanas = cursor.fetchall()
    for cod_factura, subtotal, impuestos, motivo in huerfanas:
        subtotal = float(subtotal or 0)
        impuestos = float(impuestos or 0)
        tasa = round(impuestos / subtotal * 100, 2) if subtotal else 0
        cursor.execute(
            "INSERT INTO detalle_factura "
            "  (cod_factura, cod_producto, descripcion, cantidad, precio_unitario, "
            "   subtotal, descuento_porcentaje, descuento_valor, "
            "   impuesto_porcentaje, impuesto_valor) "
            "VALUES (%s, NULL, %s, 1, %s, %s, 0, 0, %s, %s)",
            (cod_factura, (motivo or "Ajuste")[:300], subtotal, subtotal, tasa, impuestos),
        )
    if huerfanas:
        pasos.append(f"{len(huerfanas)} nota(s) debito sin lineas: linea reconstruida")

    return pasos


# ── 006 · Emisión electrónica a través de FactuGest ─────────────────────────

def migracion_006_emision_factugest(cursor):
    """Guarda lo que devuelve FactuGest al emitir electrónicamente una venta.

    Va en columnas aparte y no encima de `numero_factura` y `cufe`: la venta
    tiene su propio número interno desde que se registra, y la emisión
    electrónica es un hecho posterior que puede no haber ocurrido todavía, haber
    fallado, o haberse reintentado. Mezclarlos impediría distinguir «esta venta
    aún no se ha facturado» de «esta venta se facturó».
    """
    columnas = [
        ("factugest_id", "VARCHAR(40) DEFAULT NULL "
                         "COMMENT 'Identificador del documento en FactuGest'"),
        ("factugest_numero", "VARCHAR(50) DEFAULT NULL "
                             "COMMENT 'Numero con el prefijo de la resolucion DIAN'"),
        ("factugest_cufe", "VARCHAR(200) DEFAULT NULL"),
        ("factugest_estado", "VARCHAR(20) DEFAULT NULL "
                             "COMMENT 'ACEPTADO | RECHAZADO | PENDIENTE | ERROR'"),
        ("factugest_qr", "VARCHAR(255) DEFAULT NULL"),
        ("factugest_emitida_en", "DATETIME DEFAULT NULL"),
        ("factugest_error", "TEXT DEFAULT NULL "
                            "COMMENT 'Ultimo error, para poder reintentar sabiendo por que fallo'"),
    ]
    pasos = []
    for nombre, definicion in columnas:
        if not _column_exists(cursor, "facturas", nombre):
            cursor.execute(f"ALTER TABLE facturas ADD COLUMN {nombre} {definicion}")
            pasos.append(f"columna facturas.{nombre} creada")

    if pasos:
        cursor.execute("CREATE INDEX idx_factugest_estado ON facturas (factugest_estado)")
        pasos.append("indice por estado de emision creado")

    return pasos


# ── 007 · Quitar las tablas heredadas de FactuGest ──────────────────────────

def migracion_007_quitar_tablas_de_factugest(cursor):
    """Este sistema es cliente de la API de FactuGest, no proveedor.

    Las tablas del middleware llegaron con el fork y aquí no significan nada: un
    punto de venta no tiene clientes API a los que emitirles. Se borran solo si
    están vacías, por si alguien alcanzó a usarlas.
    """
    pasos = []
    # En orden inverso a las dependencias.
    for tabla in ("documento_eventos", "documento_lineas", "documentos",
                  "receptores", "clientes_api"):
        if not _table_exists(cursor, tabla):
            continue
        cursor.execute(f"SELECT COUNT(*) FROM {tabla}")
        if cursor.fetchone()[0]:
            pasos.append(f"ATENCION: {tabla} tiene datos y se conserva")
            continue
        cursor.execute(f"DROP TABLE {tabla}")
        pasos.append(f"tabla {tabla} eliminada")
    return pasos


# ── 010 · Auditoría ─────────────────────────────────────────────────────────

def migracion_010_auditoria(cursor):
    """Quién hizo qué, cuándo y desde dónde.

    Había una tabla `logs` con cinco columnas en la que nunca se escribió: sin
    quién, sin sobre qué, sin desde dónde. Un registro que no se llena no es un
    registro; era un lugar donde algún día se iba a escribir algo.

    Tres decisiones que conviene entender antes de tocar esto:

    **Una sola tabla y no una por módulo.** La auditoría se lee en orden
    cronológico y se filtra —qué hizo Yuliana ayer, qué le pasó a la factura
    FG60—. Repartida en ocho tablas, cada una de esas preguntas sería una unión
    de ocho consultas.

    **Se guarda el nombre del usuario, no solo su código.** Si mañana se borra o
    se renombra, el registro tiene que seguir diciendo quién fue. Una auditoría
    que cambia cuando cambian los datos que audita no sirve de prueba.

    **La descripción se escribe en el momento.** No se reconstruye después
    leyendo la factura, porque la factura pudo anularse, cambiar o desaparecer.
    Lo que quedó escrito es lo que pasó ese día.
    """
    pasos = []

    if not _table_exists(cursor, "auditoria"):
        cursor.execute("""
            CREATE TABLE auditoria (
                cod_auditoria  BIGINT       NOT NULL AUTO_INCREMENT,
                fecha          DATETIME(6)  NOT NULL,
                cod_usuario    INT(11)               DEFAULT NULL,
                usuario_nombre VARCHAR(120)          DEFAULT NULL COMMENT 'Copia del nombre: el registro sobrevive al usuario',
                usuario_rol    VARCHAR(20)           DEFAULT NULL,
                accion         VARCHAR(30)  NOT NULL COMMENT 'INGRESO | SALIDA | CREO | ACTUALIZO | ELIMINO | EMITIO | ANULO | ...',
                entidad        VARCHAR(40)           DEFAULT NULL COMMENT 'Sobre que se actuo: factura, cliente, producto...',
                entidad_id     VARCHAR(60)           DEFAULT NULL COMMENT 'Su identificador, como texto: hay codigos y numeros de factura',
                descripcion    VARCHAR(300) NOT NULL COMMENT 'Una frase legible, escrita en el momento',
                cambios        MEDIUMTEXT            DEFAULT NULL COMMENT 'JSON con el antes y el despues, solo en modificaciones',
                ip             VARCHAR(45)           DEFAULT NULL,
                PRIMARY KEY (cod_auditoria),
                KEY idx_auditoria_fecha (fecha),
                KEY idx_auditoria_usuario (cod_usuario),
                KEY idx_auditoria_entidad (entidad, entidad_id),
                KEY idx_auditoria_accion (accion),
                -- ON DELETE SET NULL y no CASCADE: borrar un usuario no puede
                -- borrar el rastro de lo que hizo. Para eso queda su nombre.
                CONSTRAINT fk_auditoria_usuario FOREIGN KEY (cod_usuario)
                    REFERENCES usuarios (cod_usuario) ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        pasos.append("tabla auditoria creada")

    # La tabla vieja se va: nunca se escribió en ella y mantenerla al lado de la
    # nueva solo invita a que alguien escriba en la equivocada.
    if _table_exists(cursor, "logs"):
        cursor.execute("SELECT COUNT(*) FROM logs")
        cuantos = cursor.fetchall()[0]
        cuantos = list(cuantos.values())[0] if isinstance(cuantos, dict) else cuantos[0]
        if cuantos:
            pasos.append(f"tabla logs conservada: tiene {cuantos} fila(s) que revisar")
        else:
            cursor.execute("DROP TABLE logs")
            pasos.append("tabla logs eliminada (estaba vacía)")

    return pasos


MIGRACIONES = [
    ("001", "Módulo de inventario: kardex de movimientos y flag controla_stock",
     migracion_001_inventario),
    ("002", "Foto de perfil de usuario",
     migracion_002_foto_perfil),
    ("003", "API middleware DIAN: clientes API, receptores, documentos, líneas y eventos",
     migracion_003_api_middleware),
    ("004", "Tipos de documento de cliente con los códigos de la DIAN",
     migracion_004_tipos_documento_dian),
    ("005", "Líneas de concepto en detalle_factura y reconstrucción de las notas débito",
     migracion_005_lineas_de_concepto),
    ("006", "Emisión electrónica a través de FactuGest",
     migracion_006_emision_factugest),
    ("007", "Quitar las tablas del middleware heredadas del fork",
     migracion_007_quitar_tablas_de_factugest),
    ("010", "Auditoría: quién hizo qué, cuándo y desde dónde",
     migracion_010_auditoria),
]


def run():
    # La consola de Windows usa cp1252 y un acento o una flecha en el mensaje de una
    # migración bastaba para tumbarla a mitad de camino. El texto que se imprime no
    # debería poder abortar un cambio de esquema.
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass

    db = create_connection()
    cursor = db.cursor()
    try:
        _ensure_migrations_table(cursor)
        db.commit()

        for version, descripcion, funcion in MIGRACIONES:
            if _already_applied(cursor, version):
                print(f"  [=] {version} ya aplicada — se omite")
                continue

            print(f"  [>] Aplicando {version}: {descripcion}")
            for paso in funcion(cursor):
                print(f"      · {paso}")
            _mark_applied(cursor, version, descripcion)
            db.commit()
            print(f"  [OK] {version} aplicada")
    except Exception:
        db.rollback()
        raise
    finally:
        cursor.close()
        db.close()


if __name__ == "__main__":
    print("Siste Soluciones — migraciones de esquema")
    run()
    print("Listo.")
