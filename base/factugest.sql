-- MariaDB dump 10.19  Distrib 10.4.28-MariaDB, for Win64 (AMD64)
--
-- Host: localhost    Database: factugest
-- ------------------------------------------------------
-- Server version	10.4.28-MariaDB

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `clientes`
--

DROP TABLE IF EXISTS `clientes`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `clientes` (
  `cod_cliente` int(11) NOT NULL AUTO_INCREMENT,
  `nombre` varchar(255) DEFAULT NULL,
  `tipo_documento` varchar(255) DEFAULT NULL,
  `numero_documento` varchar(255) DEFAULT NULL,
  `telefono` varchar(255) DEFAULT NULL,
  `correo` varchar(255) DEFAULT NULL,
  `direccion` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`cod_cliente`),
  UNIQUE KEY `numero_documento` (`numero_documento`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `clientes`
--

LOCK TABLES `clientes` WRITE;
/*!40000 ALTER TABLE `clientes` DISABLE KEYS */;
INSERT INTO `clientes` VALUES (2,'juan perez','V','12345678','0412-1234567','juan@email.com','caracas, venezuela'),(3,'María García','V','87654321','0414-7654321','maria@email.com','Valencia, Venezuela'),(6,'Diana','J','1005066451','3107093720','diana@gmail.com','av10a');
/*!40000 ALTER TABLE `clientes` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `clientes_api`
--

DROP TABLE IF EXISTS `clientes_api`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `clientes_api` (
  `cod_cliente_api` int(11) NOT NULL AUTO_INCREMENT,
  `nombre` varchar(150) NOT NULL COMMENT 'Nombre del negocio o sistema integrado',
  `cod_cliente` int(11) DEFAULT NULL COMMENT 'customers: a quien le facturamos el plan',
  `cod_empresa` int(11) NOT NULL COMMENT 'empresas: con que NIT y resolucion emite',
  `api_key_prefijo` varchar(20) NOT NULL COMMENT 'Parte visible de la llave; permite ubicar la fila sin revelarla',
  `api_key_hash` varchar(255) NOT NULL COMMENT 'Hash de la llave completa; la llave se muestra una sola vez',
  `plan` varchar(20) NOT NULL DEFAULT 'BASICO',
  `limite_mensual` int(11) DEFAULT NULL COMMENT 'Documentos por mes; NULL = sin limite',
  `estado` varchar(20) NOT NULL DEFAULT 'ACTIVO' COMMENT 'ACTIVO | SUSPENDIDO | REVOCADO',
  `creado_en` datetime NOT NULL,
  `ultimo_uso` datetime DEFAULT NULL,
  PRIMARY KEY (`cod_cliente_api`),
  UNIQUE KEY `uq_api_key_prefijo` (`api_key_prefijo`),
  KEY `idx_cliente_api_empresa` (`cod_empresa`),
  KEY `idx_cliente_api_cliente` (`cod_cliente`),
  CONSTRAINT `fk_cliente_api_cliente` FOREIGN KEY (`cod_cliente`) REFERENCES `customers` (`customer_id`) ON DELETE SET NULL,
  CONSTRAINT `fk_cliente_api_empresa` FOREIGN KEY (`cod_empresa`) REFERENCES `empresas` (`cod_empresa`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `clientes_api`
--

LOCK TABLES `clientes_api` WRITE;
/*!40000 ALTER TABLE `clientes_api` DISABLE KEYS */;
/*!40000 ALTER TABLE `clientes_api` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `configuracion`
--

DROP TABLE IF EXISTS `configuracion`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `configuracion` (
  `clave` varchar(255) NOT NULL,
  `valor` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`clave`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `configuracion`
--

LOCK TABLES `configuracion` WRITE;
/*!40000 ALTER TABLE `configuracion` DISABLE KEYS */;
/*!40000 ALTER TABLE `configuracion` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `customers`
--

DROP TABLE IF EXISTS `customers`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `customers` (
  `customer_id` int(11) NOT NULL AUTO_INCREMENT,
  `full_name` varchar(100) NOT NULL,
  `document_type` char(1) NOT NULL COMMENT 'C for National ID, E for Foreign ID',
  `document_number` varchar(20) NOT NULL,
  `phone` varchar(15) DEFAULT NULL,
  `email` varchar(100) DEFAULT NULL,
  `address` varchar(255) DEFAULT NULL,
  `ciudad` varchar(50) NOT NULL,
  `departamento` varchar(50) NOT NULL,
  `pais` varchar(50) NOT NULL,
  `tipo_persona` varchar(20) DEFAULT 'NATURAL',
  `regimen_tributario` varchar(60) DEFAULT 'NO_RESPONSABLE_IVA',
  `cod_municipio` char(5) DEFAULT NULL,
  `activo` tinyint(1) NOT NULL DEFAULT 1,
  PRIMARY KEY (`customer_id`),
  UNIQUE KEY `document_number` (`document_number`),
  KEY `fk_customer_municipio` (`cod_municipio`),
  CONSTRAINT `fk_customer_municipio` FOREIGN KEY (`cod_municipio`) REFERENCES `municipios` (`cod_municipio`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=28 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `customers`
--

LOCK TABLES `customers` WRITE;
/*!40000 ALTER TABLE `customers` DISABLE KEYS */;
INSERT INTO `customers` VALUES (1,'Consumidor Final','C','222222222222','','','','','','','NATURAL','NO_RESPONSABLE_IVA',NULL,1),(2,'Maria Fernanda Ruiz','C','1015432109','3209876543','mafe.ruiz@outlook.com','Libertadores Ave # 11-45','','','','NATURAL','NO_RESPONSABLE_IVA',NULL,1),(3,'Juan Sebastian Gomez','E','E87654321','3156789012','juan.gomez@gmail.com','La Playa Neighborhood, House 4','','','','NATURAL','NO_RESPONSABLE_IVA',NULL,1),(4,'Diana Marcela Rojas','C','1093456789','3004567890','diana.rojas@servicios.co','7N St # 3-12, Los Patios','','','','NATURAL','NO_RESPONSABLE_IVA',NULL,1),(5,'Ricardo Jose Torres','C','1116789456','3112345678','ricardo.torres@empresa.com','0 Avenue # 15-30','','','','NATURAL','NO_RESPONSABLE_IVA',NULL,1),(6,'Elena Patricia Meza','C','1012345987','3189012345','elena.meza@misena.edu.co','Siglo XXI Estate','','','','NATURAL','NO_RESPONSABLE_IVA',NULL,1),(7,'Oscar David Ortiz','E','E12345678','3145678234','oscar.ortiz@flete.net','Industrial Zone, Plot 5','','','','NATURAL','NO_RESPONSABLE_IVA',NULL,1),(8,'Sandra Milena Cano','C','1090123456','3216540987','sandra.cano@yahoo.es','24th St # 12-05, Villa del Rosario','','','','NATURAL','NO_RESPONSABLE_IVA',NULL,1),(9,'Luis Alberto Quintero','C','1115678234','3124567890','luis.quintero@tecnicos.com','5th Ave # 10-10','','','','NATURAL','NO_RESPONSABLE_IVA',NULL,1),(10,'Angela Maria Velez','C','1018907654','3012345678','angela.velez@estudio.edu','15th St # 4-50, Atalaya','Los Patios','Norte De Santander','Colombia','NATURAL','NO_RESPONSABLE_IVA','54405',1),(11,'Brandon Arley Restrepo Gelvez','C','1093789989','3044412657','brandon@gmail.com','Calle 37 # 3-41 La Sabana','Bogotá, D.C.','Bogotá, D.C.','Colombia','NATURAL','NO_RESPONSABLE_IVA','11001',1);
/*!40000 ALTER TABLE `customers` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `departamentos`
--

DROP TABLE IF EXISTS `departamentos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `departamentos` (
  `cod_departamento` char(2) NOT NULL,
  `nombre` varchar(100) NOT NULL,
  PRIMARY KEY (`cod_departamento`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `departamentos`
--

LOCK TABLES `departamentos` WRITE;
/*!40000 ALTER TABLE `departamentos` DISABLE KEYS */;
INSERT INTO `departamentos` VALUES ('05','Antioquia'),('08','Atlántico'),('11','Bogotá, D.C.'),('13','Bolívar'),('15','Boyacá'),('17','Caldas'),('18','Caquetá'),('19','Cauca'),('20','Cesar'),('23','Córdoba'),('25','Cundinamarca'),('27','Chocó'),('41','Huila'),('44','La Guajira'),('47','Magdalena'),('50','Meta'),('52','Nariño'),('54','Norte De Santander'),('63','Quindío'),('66','Risaralda'),('68','Santander'),('70','Sucre'),('73','Tolima'),('76','Valle Del Cauca'),('81','Arauca'),('85','Casanare'),('86','Putumayo'),('88','Archipiélago De San Andrés, Providencia Y Santa Catalina'),('91','Amazonas'),('94','Guainía'),('95','Guaviare'),('97','Vaupés'),('99','Vichada');
/*!40000 ALTER TABLE `departamentos` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `descuentos`
--

DROP TABLE IF EXISTS `descuentos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `descuentos` (
  `cod_descuento` int(11) NOT NULL AUTO_INCREMENT,
  `descripcion` varchar(255) DEFAULT NULL,
  `porcentaje` double NOT NULL,
  `aplica_a_producto` smallint(6) NOT NULL,
  `aplica_a_factura` smallint(6) NOT NULL,
  PRIMARY KEY (`cod_descuento`)
) ENGINE=InnoDB AUTO_INCREMENT=665659 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `descuentos`
--

LOCK TABLES `descuentos` WRITE;
/*!40000 ALTER TABLE `descuentos` DISABLE KEYS */;
INSERT INTO `descuentos` VALUES (55501,'Seasonal Discount',10,1,0),(55502,'Frequent Customer Promotion',5,0,1),(55503,'End of Month Offer',15,0,1),(55504,'Volume Discount',8,1,0),(55505,'Card Promotion',12,0,1),(55506,'Inventory Clearance',20,1,0),(55507,'Special VIP Discount',7,0,1),(55508,'Anniversary Promotion',18,1,0);
/*!40000 ALTER TABLE `descuentos` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `detalle_factura`
--

DROP TABLE IF EXISTS `detalle_factura`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `detalle_factura` (
  `cantidad` int(11) NOT NULL,
  `cod_destalle` int(11) NOT NULL AUTO_INCREMENT,
  `cod_factura` int(11) NOT NULL,
  `cod_producto` int(11) NOT NULL,
  `precio_unitario` double NOT NULL,
  `subtotal` double NOT NULL,
  `descuento_porcentaje` double NOT NULL DEFAULT 0,
  `descuento_valor` double NOT NULL DEFAULT 0,
  `impuesto_porcentaje` double NOT NULL DEFAULT 0,
  `impuesto_valor` double NOT NULL DEFAULT 0,
  `descripcion_descuento` varchar(200) DEFAULT NULL,
  PRIMARY KEY (`cod_destalle`)
) ENGINE=InnoDB AUTO_INCREMENT=1616 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `detalle_factura`
--

LOCK TABLES `detalle_factura` WRITE;
/*!40000 ALTER TABLE `detalle_factura` DISABLE KEYS */;
INSERT INTO `detalle_factura` VALUES (1,12,21,3,650000,585000,10,65000,19,111150,'Seasonal Discount'),(1,13,21,4,95000,95000,0,0,19,18050,NULL),(1,14,22,3,650000,650000,0,0,19,123500,NULL),(1,15,23,3,650000,650000,0,0,19,123500,NULL),(1,16,24,3,650000,585000,10,65000,19,111150,'Seasonal Discount'),(1,17,24,4,95000,95000,0,0,19,18050,NULL),(1,18,25,8,55000,55000,0,0,19,10450,NULL),(1,19,26,4,95000,95000,0,0,19,18050,NULL),(1,20,27,3,650000,650000,0,0,19,123500,NULL),(1,21,28,3,650000,585000,10,65000,19,111150,'Seasonal Discount'),(1,22,29,3,650000,585000,10,65000,19,111150,'Seasonal Discount'),(1,23,30,4,95000,95000,0,0,19,18050,NULL);
/*!40000 ALTER TABLE `detalle_factura` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `documento_eventos`
--

DROP TABLE IF EXISTS `documento_eventos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `documento_eventos` (
  `cod_evento` int(11) NOT NULL AUTO_INCREMENT,
  `cod_documento` int(11) NOT NULL,
  `tipo` varchar(30) NOT NULL COMMENT 'RECIBIDO | TRANSMITIDO | ACEPTADO | RECHAZADO | CORREO_ENVIADO | ERROR',
  `proveedor` varchar(20) DEFAULT NULL,
  `codigo` varchar(20) DEFAULT NULL COMMENT 'Codigo de respuesta del proveedor',
  `mensaje` text DEFAULT NULL,
  `payload` mediumtext DEFAULT NULL,
  `fecha` datetime(6) NOT NULL,
  PRIMARY KEY (`cod_evento`),
  KEY `idx_evento_documento` (`cod_documento`),
  KEY `idx_evento_fecha` (`fecha`),
  CONSTRAINT `fk_evento_documento` FOREIGN KEY (`cod_documento`) REFERENCES `documentos` (`cod_documento`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `documento_eventos`
--

LOCK TABLES `documento_eventos` WRITE;
/*!40000 ALTER TABLE `documento_eventos` DISABLE KEYS */;
/*!40000 ALTER TABLE `documento_eventos` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `documento_lineas`
--

DROP TABLE IF EXISTS `documento_lineas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `documento_lineas` (
  `cod_linea` int(11) NOT NULL AUTO_INCREMENT,
  `cod_documento` int(11) NOT NULL,
  `orden` int(11) NOT NULL DEFAULT 1,
  `codigo` varchar(60) DEFAULT NULL COMMENT 'SKU en el sistema del cliente',
  `descripcion` varchar(300) NOT NULL,
  `unidad_medida` varchar(10) DEFAULT '94',
  `cantidad` decimal(14,3) NOT NULL,
  `precio_unitario` decimal(14,2) NOT NULL,
  `valor_bruto` decimal(14,2) NOT NULL DEFAULT 0.00,
  `descuento_porcentaje` decimal(6,3) NOT NULL DEFAULT 0.000,
  `descuento_valor` decimal(14,2) NOT NULL DEFAULT 0.00,
  `descripcion_descuento` varchar(200) DEFAULT NULL,
  `subtotal` decimal(14,2) NOT NULL DEFAULT 0.00 COMMENT 'Base gravable de la linea',
  `impuesto_codigo_dian` varchar(5) DEFAULT '01',
  `impuesto_porcentaje` decimal(6,3) NOT NULL DEFAULT 0.000,
  `impuesto_valor` decimal(14,2) NOT NULL DEFAULT 0.00,
  PRIMARY KEY (`cod_linea`),
  KEY `idx_linea_documento` (`cod_documento`),
  CONSTRAINT `fk_linea_documento` FOREIGN KEY (`cod_documento`) REFERENCES `documentos` (`cod_documento`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `documento_lineas`
--

LOCK TABLES `documento_lineas` WRITE;
/*!40000 ALTER TABLE `documento_lineas` DISABLE KEYS */;
/*!40000 ALTER TABLE `documento_lineas` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `documentos`
--

DROP TABLE IF EXISTS `documentos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `documentos` (
  `cod_documento` int(11) NOT NULL AUTO_INCREMENT,
  `id_publico` varchar(40) NOT NULL COMMENT 'Identificador que ve el cliente; no exponemos el autoincremental',
  `cod_cliente_api` int(11) NOT NULL,
  `cod_empresa` int(11) NOT NULL COMMENT 'Emisor con cuya resolucion se numero',
  `cod_receptor` int(11) NOT NULL,
  `tipo` varchar(5) NOT NULL DEFAULT 'FV' COMMENT 'FV | NC | ND',
  `prefijo` varchar(10) DEFAULT NULL,
  `consecutivo` bigint(20) DEFAULT NULL,
  `numero` varchar(50) DEFAULT NULL,
  `cufe` varchar(200) DEFAULT NULL,
  `fecha_emision` datetime(6) NOT NULL,
  `fecha_vencimiento` date DEFAULT NULL,
  `forma_pago` varchar(20) NOT NULL DEFAULT 'CONTADO',
  `subtotal_bruto` decimal(14,2) NOT NULL DEFAULT 0.00,
  `total_descuentos` decimal(14,2) NOT NULL DEFAULT 0.00,
  `subtotal` decimal(14,2) NOT NULL DEFAULT 0.00 COMMENT 'Base gravable neta',
  `total_impuestos` decimal(14,2) NOT NULL DEFAULT 0.00,
  `total` decimal(14,2) NOT NULL DEFAULT 0.00,
  `estado` varchar(20) NOT NULL DEFAULT 'PENDIENTE' COMMENT 'PENDIENTE | ACEPTADO | RECHAZADO | ERROR',
  `referencia_externa` varchar(80) DEFAULT NULL COMMENT 'Identificador de la venta en el sistema del cliente',
  `cod_documento_referencia` int(11) DEFAULT NULL COMMENT 'La FV que origina una NC o ND',
  `motivo_nota` text DEFAULT NULL,
  `observaciones` text DEFAULT NULL,
  `orden_compra` varchar(100) DEFAULT NULL,
  `proveedor_dian` varchar(20) DEFAULT NULL COMMENT 'simulado | factus',
  `xml` mediumtext DEFAULT NULL,
  `creado_en` datetime NOT NULL,
  PRIMARY KEY (`cod_documento`),
  UNIQUE KEY `uq_documento_publico` (`id_publico`),
  UNIQUE KEY `uq_referencia_del_cliente` (`cod_cliente_api`,`referencia_externa`),
  UNIQUE KEY `uq_numero_del_emisor` (`cod_empresa`,`tipo`,`numero`),
  KEY `idx_documento_cliente` (`cod_cliente_api`),
  KEY `idx_documento_fecha` (`fecha_emision`),
  KEY `idx_documento_estado` (`estado`),
  KEY `idx_documento_referencia` (`cod_documento_referencia`),
  KEY `fk_documento_receptor` (`cod_receptor`),
  CONSTRAINT `fk_documento_cliente_api` FOREIGN KEY (`cod_cliente_api`) REFERENCES `clientes_api` (`cod_cliente_api`),
  CONSTRAINT `fk_documento_empresa` FOREIGN KEY (`cod_empresa`) REFERENCES `empresas` (`cod_empresa`),
  CONSTRAINT `fk_documento_receptor` FOREIGN KEY (`cod_receptor`) REFERENCES `receptores` (`cod_receptor`),
  CONSTRAINT `fk_documento_referencia` FOREIGN KEY (`cod_documento_referencia`) REFERENCES `documentos` (`cod_documento`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `documentos`
--

LOCK TABLES `documentos` WRITE;
/*!40000 ALTER TABLE `documentos` DISABLE KEYS */;
/*!40000 ALTER TABLE `documentos` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `empresas`
--

DROP TABLE IF EXISTS `empresas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `empresas` (
  `cod_empresa` int(11) NOT NULL AUTO_INCREMENT,
  `nombre` varchar(255) DEFAULT NULL,
  `nit` varchar(255) DEFAULT NULL,
  `direccion` varchar(255) DEFAULT NULL,
  `ciudad` varchar(50) NOT NULL,
  `telefono` varchar(255) DEFAULT NULL,
  `correo` varchar(255) DEFAULT NULL,
  `dv` varchar(5) DEFAULT NULL,
  `regimen_tributario` varchar(60) DEFAULT 'RESPONSABLE_IVA',
  `actividad_economica` varchar(10) DEFAULT NULL,
  `tipo_documento` varchar(20) DEFAULT 'NIT',
  `cod_municipio` char(5) DEFAULT NULL,
  `website` varchar(255) DEFAULT NULL,
  `tarifa_ica` decimal(10,4) DEFAULT 0.0000,
  `autoretenedor` tinyint(1) DEFAULT 0,
  `gran_contribuyente` tinyint(1) DEFAULT 0,
  `prefijo_factura` varchar(10) DEFAULT 'FV',
  `resolucion_dian` varchar(50) DEFAULT NULL,
  `resolucion_fecha_desde` date DEFAULT NULL,
  `resolucion_fecha_hasta` date DEFAULT NULL,
  `resolucion_desde` bigint(20) DEFAULT NULL,
  `resolucion_hasta` bigint(20) DEFAULT NULL,
  `consecutivo_actual` bigint(20) DEFAULT 1,
  `consecutivo_nc` bigint(20) DEFAULT 1,
  `consecutivo_nd` bigint(20) DEFAULT 1,
  PRIMARY KEY (`cod_empresa`),
  UNIQUE KEY `nit` (`nit`),
  KEY `fk_empresa_municipio` (`cod_municipio`),
  CONSTRAINT `fk_empresa_municipio` FOREIGN KEY (`cod_municipio`) REFERENCES `municipios` (`cod_municipio`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `empresas`
--

LOCK TABLES `empresas` WRITE;
/*!40000 ALTER TABLE `empresas` DISABLE KEYS */;
INSERT INTO `empresas` VALUES (1,'Verdad y Reconciliacion','980256314','Cll 28 # 9-47','Cali','3206841435','verdadyreconciliacion@factugest.com',NULL,'RESPONSABLE_IVA',NULL,'NIT','76001',NULL,0.0000,0,0,'FV',NULL,NULL,NULL,NULL,NULL,1,1,1),(2,'Pillar of Autumn','987654321','Av Caracas # 2-56','San José De Cúcuta','3132156472','pillarofautumn@factugest.com',NULL,'RESPONSABLE_IVA',NULL,'NIT','54001',NULL,NULL,0,0,'PA','23456','2026-04-20','2026-07-20',NULL,NULL,6,1,1),(6,'Gran Caridad','890345555','AV 10  # 3-21','Bogotá, D.C.','312398888','grancaridad@factugest.com',NULL,'RESPONSABLE_IVA',NULL,'NIT','11001',NULL,NULL,0,0,'FV','1234575432','2026-04-16','2026-06-16',1,5000,6,1,1);
/*!40000 ALTER TABLE `empresas` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `factura_descuento`
--

DROP TABLE IF EXISTS `factura_descuento`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `factura_descuento` (
  `cod_descuento` int(11) NOT NULL,
  `cod_factura` int(11) NOT NULL,
  `valor_descuento` float NOT NULL,
  PRIMARY KEY (`cod_descuento`,`cod_factura`),
  KEY `FKn9t3efsp0sk3egm9386gv9v7f` (`cod_factura`),
  CONSTRAINT `FKn9t3efsp0sk3egm9386gv9v7f` FOREIGN KEY (`cod_factura`) REFERENCES `facturas` (`cod_factura`),
  CONSTRAINT `FKqum49fhp3hw13koeag0pcf564` FOREIGN KEY (`cod_descuento`) REFERENCES `descuentos` (`cod_descuento`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `factura_descuento`
--

LOCK TABLES `factura_descuento` WRITE;
/*!40000 ALTER TABLE `factura_descuento` DISABLE KEYS */;
/*!40000 ALTER TABLE `factura_descuento` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `factura_impuesto`
--

DROP TABLE IF EXISTS `factura_impuesto`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `factura_impuesto` (
  `cod_factura` int(11) DEFAULT NULL,
  `cod_impuesto` int(11) DEFAULT NULL,
  `id_factura_impuesto` int(11) NOT NULL AUTO_INCREMENT,
  `valor_impuesto` float NOT NULL,
  PRIMARY KEY (`id_factura_impuesto`),
  KEY `FKa6ckq6lco6pjwp46oyx29v620` (`cod_factura`),
  KEY `FKb3kag5880t417tnrsbop0mrrd` (`cod_impuesto`),
  CONSTRAINT `FKa6ckq6lco6pjwp46oyx29v620` FOREIGN KEY (`cod_factura`) REFERENCES `facturas` (`cod_factura`),
  CONSTRAINT `FKb3kag5880t417tnrsbop0mrrd` FOREIGN KEY (`cod_impuesto`) REFERENCES `impuestos` (`cod_impuesto`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `factura_impuesto`
--

LOCK TABLES `factura_impuesto` WRITE;
/*!40000 ALTER TABLE `factura_impuesto` DISABLE KEYS */;
/*!40000 ALTER TABLE `factura_impuesto` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `facturas`
--

DROP TABLE IF EXISTS `facturas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `facturas` (
  `cod_factura` int(11) NOT NULL AUTO_INCREMENT,
  `fecha` datetime(6) NOT NULL,
  `cod_cliente` int(11) DEFAULT NULL,
  `cod_usuario` int(11) DEFAULT NULL,
  `cod_pago` int(11) DEFAULT NULL,
  `total` double NOT NULL,
  `cod_empresa` int(11) DEFAULT NULL,
  `cod_metodo_pago` int(11) DEFAULT NULL,
  `fecha_vencimiento` date DEFAULT NULL,
  `subtotal` double NOT NULL DEFAULT 0,
  `total_descuentos` double NOT NULL DEFAULT 0,
  `total_impuestos` double NOT NULL DEFAULT 0,
  `tipo_factura` varchar(5) NOT NULL DEFAULT 'FV',
  `observaciones` text DEFAULT NULL,
  `cufe` varchar(200) DEFAULT NULL,
  `numero_factura` varchar(50) DEFAULT NULL,
  `forma_pago` varchar(20) DEFAULT 'CONTADO',
  `orden_compra` varchar(100) DEFAULT NULL,
  `nombre_vendedor` varchar(100) DEFAULT NULL,
  `cod_descuento_factura` int(11) DEFAULT NULL,
  `descripcion_descuento_factura` varchar(200) DEFAULT NULL,
  `cod_factura_referencia` int(11) DEFAULT NULL,
  `motivo_nota` text DEFAULT NULL,
  PRIMARY KEY (`cod_factura`),
  KEY `cod_usuario` (`cod_usuario`),
  KEY `cod_empresa` (`cod_empresa`),
  KEY `cod_pago` (`cod_pago`),
  KEY `FKcxx7trc0b0xhuawwapbr4ogco` (`cod_metodo_pago`),
  KEY `facturas_ibfk_1` (`cod_cliente`),
  CONSTRAINT `FKcxx7trc0b0xhuawwapbr4ogco` FOREIGN KEY (`cod_metodo_pago`) REFERENCES `metodos_pago` (`cod_pago`),
  CONSTRAINT `facturas_ibfk_1` FOREIGN KEY (`cod_cliente`) REFERENCES `customers` (`customer_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `facturas_ibfk_2` FOREIGN KEY (`cod_usuario`) REFERENCES `usuarios` (`cod_usuario`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `facturas_ibfk_3` FOREIGN KEY (`cod_empresa`) REFERENCES `empresas` (`cod_empresa`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `facturas_ibfk_4` FOREIGN KEY (`cod_pago`) REFERENCES `pagos_factura` (`cod_pago_factura`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=909 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `facturas`
--

LOCK TABLES `facturas` WRITE;
/*!40000 ALTER TABLE `facturas` DISABLE KEYS */;
INSERT INTO `facturas` VALUES (21,'2026-04-17 00:08:37.000000',10,2,1,752556,6,1,'2026-04-17',632400,112600,120156,'FV',NULL,'4d8b571867ac8452312b4ca3c741b19a588cd69408cf4b9e6d9cfcf5d7506cd4cd809761cf88374c0732e113ccf26fce','FV1','CONTADO',NULL,NULL,55507,'Special VIP Discount',NULL,NULL),(22,'2026-04-20 18:58:00.000000',8,3,1,773500,2,1,'2026-04-20',650000,0,123500,'FV',NULL,'8f49b4d0311650e848f604b5161af714859cad305478f0d216b8c3e5cf9d8b7da90a10466a298aea532baeff254dc230','FV1','CONTADO',NULL,NULL,NULL,NULL,NULL,NULL),(23,'2026-04-20 18:59:41.000000',8,3,1,773500,2,1,'2026-04-20',650000,0,123500,'FV',NULL,'cdc8bf5209c0105adcaf0d33cb59c2b27aca490f865143590592175b4eec8ad98172936e0e32865d318750a98676f5ef','PA2','CONTADO',NULL,NULL,NULL,NULL,NULL,NULL),(24,'2026-04-20 19:13:20.000000',8,3,1,768740,2,1,'2026-04-20',646000,99000,122740,'FV',NULL,'93ee86e2453b5b4ae4f595e5d7fa666d93826a6225901045dcb0e117a0b1f866f79ca0a4c865d219b5d4353b749ce67f','PA3','CONTADO',NULL,NULL,55502,'Frequent Customer Promotion',NULL,NULL),(25,'2026-04-20 19:16:05.000000',8,3,1,65450,2,1,'2026-04-20',55000,0,10450,'FV',NULL,'df2a2eb61d73cdb336988d7571a7d790885412401742608f81009b6dc2d5963d5596133ac3a490a310b27de66907a03e','PA4','CONTADO',NULL,NULL,NULL,NULL,NULL,NULL),(26,'2026-04-25 20:02:41.000000',8,3,1,113050,2,1,'2026-04-25',95000,0,18050,'FV','asdas','06cd2a2005aea6b428f35e2d56f2b25985463ffbf39a4b3de2fd33ffed74efeadfa23e65d0c17d2720bd929290f4e834','PA5','CONTADO',NULL,NULL,NULL,NULL,NULL,NULL),(27,'2026-04-27 19:11:34.000000',10,2,1,773500,6,1,'2026-04-27',650000,0,123500,'FV',NULL,'33a9265186eebc425265d529cedebcfde658d026ba4db5360c7dfaa044f8855c57b2bed806bdb4c2d97f16f196baac09','FV2','CONTADO',NULL,NULL,NULL,NULL,NULL,NULL),(28,'2026-04-27 19:36:29.000000',9,2,1,696150,6,1,'2026-04-27',585000,65000,111150,'FV',NULL,'a820c2a42531550df857fc8bd3b88428fcafe697c863ca2923b11a5f48ed030e207561d9952b711eae083abceb587810','FV3','CONTADO',NULL,NULL,NULL,NULL,NULL,NULL),(29,'2026-05-07 10:49:51.000000',4,2,1,612612,6,1,'2026-05-07',514800,135200,97812,'FV',NULL,'4576811f5ea75a21264023de70face1a44d5e3ffda0673d3121efddaa3f8f2805b49ec3057c88591945ad0d50bdfa556','FV4','CONTADO',NULL,NULL,55505,'Card Promotion',NULL,NULL),(30,'2026-07-28 10:13:10.000000',4,2,1,113050,6,1,'2026-07-28',95000,0,18050,'FV',NULL,'d85f675471f49273756d75c186db55082fe20876d43dbb13b81e11c9b822f98bfa194bf5c93e440ce6591033d3dedff0','FV5','CONTADO',NULL,NULL,NULL,NULL,NULL,NULL);
/*!40000 ALTER TABLE `facturas` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `impuestos`
--

DROP TABLE IF EXISTS `impuestos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `impuestos` (
  `cod_impuesto` int(11) NOT NULL AUTO_INCREMENT,
  `porcentaje` double NOT NULL,
  `descripcion` varchar(255) NOT NULL,
  `codigo_dian` varchar(5) DEFAULT NULL,
  PRIMARY KEY (`cod_impuesto`)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `impuestos`
--

LOCK TABLES `impuestos` WRITE;
/*!40000 ALTER TABLE `impuestos` DISABLE KEYS */;
INSERT INTO `impuestos` VALUES (1,19,'IVA',NULL),(2,2,'RETEFUENTE',NULL),(3,1,'RETEICA',NULL),(6,15,'RETEIVA',NULL),(7,0.8,'RETECREE',NULL),(8,0,'EXENTO',NULL);
/*!40000 ALTER TABLE `impuestos` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `logs`
--

DROP TABLE IF EXISTS `logs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `logs` (
  `cod_usuario` int(11) NOT NULL,
  `id_log` int(11) NOT NULL AUTO_INCREMENT,
  `fecha` datetime(6) NOT NULL,
  `accion` varchar(100) NOT NULL,
  `descripcion` varchar(255) NOT NULL,
  PRIMARY KEY (`id_log`),
  KEY `FKedv0n646ie560v5r7nqtbs9d5` (`cod_usuario`),
  CONSTRAINT `FKedv0n646ie560v5r7nqtbs9d5` FOREIGN KEY (`cod_usuario`) REFERENCES `usuarios` (`cod_usuario`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `logs`
--

LOCK TABLES `logs` WRITE;
/*!40000 ALTER TABLE `logs` DISABLE KEYS */;
INSERT INTO `logs` VALUES (1,1,'2026-03-01 08:00:15.000000','LOGIN','User logged in'),(2,2,'2026-03-01 08:10:32.000000','VIEW','Accessed the main dashboard'),(1,3,'2026-03-01 08:15:10.000000','CREATE','Created a new record'),(3,4,'2026-03-01 09:02:55.000000','LOGIN','Successful login'),(2,5,'2026-03-01 09:15:45.000000','UPDATE','Updated information');
/*!40000 ALTER TABLE `logs` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `metodos_pago`
--

DROP TABLE IF EXISTS `metodos_pago`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `metodos_pago` (
  `cod_pago` int(11) NOT NULL AUTO_INCREMENT,
  `descripcion` varchar(255) DEFAULT NULL,
  `nombre` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`cod_pago`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `metodos_pago`
--

LOCK TABLES `metodos_pago` WRITE;
/*!40000 ALTER TABLE `metodos_pago` DISABLE KEYS */;
INSERT INTO `metodos_pago` VALUES (1,'CASH',NULL),(2,'DEBIT CARD',NULL),(3,'CREDIT CARD',NULL),(4,'BANK TRANSFER',NULL);
/*!40000 ALTER TABLE `metodos_pago` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `movimientos_inventario`
--

DROP TABLE IF EXISTS `movimientos_inventario`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `movimientos_inventario` (
  `cod_movimiento` int(11) NOT NULL AUTO_INCREMENT,
  `cod_producto` int(11) NOT NULL,
  `tipo` varchar(10) NOT NULL COMMENT 'ENTRADA | SALIDA | AJUSTE',
  `motivo` varchar(30) NOT NULL COMMENT 'VENTA, COMPRA, DEVOLUCION, AJUSTE_MANUAL, MERMA, INICIAL, ANULACION',
  `cantidad` int(11) NOT NULL COMMENT 'Siempre positivo; el signo lo determina el tipo',
  `stock_anterior` int(11) NOT NULL,
  `stock_nuevo` int(11) NOT NULL,
  `costo_unitario` decimal(12,2) DEFAULT NULL,
  `cod_factura` int(11) DEFAULT NULL,
  `cod_usuario` int(11) DEFAULT NULL,
  `observaciones` varchar(255) DEFAULT NULL,
  `fecha` datetime(6) NOT NULL,
  PRIMARY KEY (`cod_movimiento`),
  KEY `idx_mov_producto` (`cod_producto`),
  KEY `idx_mov_fecha` (`fecha`),
  KEY `idx_mov_factura` (`cod_factura`),
  KEY `fk_mov_usuario` (`cod_usuario`),
  CONSTRAINT `fk_mov_producto` FOREIGN KEY (`cod_producto`) REFERENCES `productos` (`cod_producto`) ON DELETE CASCADE,
  CONSTRAINT `fk_mov_usuario` FOREIGN KEY (`cod_usuario`) REFERENCES `usuarios` (`cod_usuario`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=1605 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `movimientos_inventario`
--

LOCK TABLES `movimientos_inventario` WRITE;
/*!40000 ALTER TABLE `movimientos_inventario` DISABLE KEYS */;
INSERT INTO `movimientos_inventario` VALUES (1,1,'ENTRADA','INICIAL',50,0,50,45000.00,NULL,NULL,'Saldo de apertura al implementar el kardex','2026-08-09 18:29:28.000000'),(2,2,'ENTRADA','INICIAL',20,0,20,180000.00,NULL,NULL,'Saldo de apertura al implementar el kardex','2026-08-09 18:29:28.000000'),(3,3,'ENTRADA','INICIAL',2,0,2,650000.00,NULL,NULL,'Saldo de apertura al implementar el kardex','2026-08-09 18:29:28.000000'),(4,4,'ENTRADA','INICIAL',30,0,30,95000.00,NULL,NULL,'Saldo de apertura al implementar el kardex','2026-08-09 18:29:28.000000'),(5,6,'ENTRADA','INICIAL',40,0,40,120000.00,NULL,NULL,'Saldo de apertura al implementar el kardex','2026-08-09 18:29:28.000000'),(6,7,'ENTRADA','INICIAL',15,0,15,15000.00,NULL,NULL,'Saldo de apertura al implementar el kardex','2026-08-09 18:29:28.000000'),(7,9,'ENTRADA','INICIAL',25,0,25,110000.00,NULL,NULL,'Saldo de apertura al implementar el kardex','2026-08-09 18:29:28.000000'),(8,10,'ENTRADA','INICIAL',0,0,0,18500.00,NULL,NULL,'Saldo de apertura al implementar el kardex','2026-08-09 18:29:28.000000');
/*!40000 ALTER TABLE `movimientos_inventario` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `municipios`
--

DROP TABLE IF EXISTS `municipios`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `municipios` (
  `cod_municipio` char(5) NOT NULL,
  `nombre` varchar(150) NOT NULL,
  `cod_departamento` char(2) NOT NULL,
  PRIMARY KEY (`cod_municipio`),
  KEY `cod_departamento` (`cod_departamento`),
  CONSTRAINT `municipios_ibfk_1` FOREIGN KEY (`cod_departamento`) REFERENCES `departamentos` (`cod_departamento`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `municipios`
--

LOCK TABLES `municipios` WRITE;
/*!40000 ALTER TABLE `municipios` DISABLE KEYS */;
INSERT INTO `municipios` VALUES ('05001','Medellín','05'),('05002','Abejorral','05'),('05004','Abriaquí','05'),('05021','Alejandría','05'),('05030','Amagá','05'),('05031','Amalfi','05'),('05034','Andes','05'),('05036','Angelópolis','05'),('05038','Angostura','05'),('05040','Anorí','05'),('05042','Santa Fé De Antioquia','05'),('05044','Anzá','05'),('05045','Apartadó','05'),('05051','Arboletes','05'),('05055','Argelia','05'),('05059','Armenia','05'),('05079','Barbosa','05'),('05086','Belmira','05'),('05088','Bello','05'),('05091','Betania','05'),('05093','Betulia','05'),('05101','Ciudad Bolívar','05'),('05107','Briceño','05'),('05113','Buriticá','05'),('05120','Cáceres','05'),('05125','Caicedo','05'),('05129','Caldas','05'),('05134','Campamento','05'),('05138','Cañasgordas','05'),('05142','Caracolí','05'),('05145','Caramanta','05'),('05147','Carepa','05'),('05148','El Carmen De Viboral','05'),('05150','Carolina','05'),('05154','Caucasia','05'),('05172','Chigorodó','05'),('05190','Cisneros','05'),('05197','Cocorná','05'),('05206','Concepción','05'),('05209','Concordia','05'),('05212','Copacabana','05'),('05234','Dabeiba','05'),('05237','Donmatías','05'),('05240','Ebéjico','05'),('05250','El Bagre','05'),('05264','Entrerríos','05'),('05266','Envigado','05'),('05282','Fredonia','05'),('05284','Frontino','05'),('05306','Giraldo','05'),('05308','Girardota','05'),('05310','Gómez Plata','05'),('05313','Granada','05'),('05315','Guadalupe','05'),('05318','Guarne','05'),('05321','Guatapé','05'),('05347','Heliconia','05'),('05353','Hispania','05'),('05360','Itagüí','05'),('05361','Ituango','05'),('05364','Jardín','05'),('05368','Jericó','05'),('05376','La Ceja','05'),('05380','La Estrella','05'),('05390','La Pintada','05'),('05400','La Unión','05'),('05411','Liborina','05'),('05425','Maceo','05'),('05440','Marinilla','05'),('05467','Montebello','05'),('05475','Murindó','05'),('05480','Mutatá','05'),('05483','Nariño','05'),('05490','Necoclí','05'),('05495','Nechí','05'),('05501','Olaya','05'),('05541','Peñol','05'),('05543','Peque','05'),('05576','Pueblorrico','05'),('05579','Puerto Berrío','05'),('05585','Puerto Nare','05'),('05591','Puerto Triunfo','05'),('05604','Remedios','05'),('05607','Retiro','05'),('05615','Rionegro','05'),('05628','Sabanalarga','05'),('05631','Sabaneta','05'),('05642','Salgar','05'),('05647','San Andrés De Cuerquía','05'),('05649','San Carlos','05'),('05652','San Francisco','05'),('05656','San Jerónimo','05'),('05658','San José De La Montaña','05'),('05659','San Juan De Urabá','05'),('05660','San Luis','05'),('05664','San Pedro De Los Milagros','05'),('05665','San Pedro De Urabá','05'),('05667','San Rafael','05'),('05670','San Roque','05'),('05674','San Vicente Ferrer','05'),('05679','Santa Bárbara','05'),('05686','Santa Rosa De Osos','05'),('05690','Santo Domingo','05'),('05697','El Santuario','05'),('05736','Segovia','05'),('05756','Sonsón','05'),('05761','Sopetrán','05'),('05789','Támesis','05'),('05790','Tarazá','05'),('05792','Tarso','05'),('05809','Titiribí','05'),('05819','Toledo','05'),('05837','Turbo','05'),('05842','Uramita','05'),('05847','Urrao','05'),('05854','Valdivia','05'),('05856','Valparaíso','05'),('05858','Vegachí','05'),('05861','Venecia','05'),('05873','Vigía Del Fuerte','05'),('05885','Yalí','05'),('05887','Yarumal','05'),('05890','Yolombó','05'),('05893','Yondó','05'),('05895','Zaragoza','05'),('08001','Barranquilla','08'),('08078','Baranoa','08'),('08137','Campo De La Cruz','08'),('08141','Candelaria','08'),('08296','Galapa','08'),('08372','Juan De Acosta','08'),('08421','Luruaco','08'),('08433','Malambo','08'),('08436','Manatí','08'),('08520','Palmar De Varela','08'),('08549','Piojó','08'),('08558','Polonuevo','08'),('08560','Ponedera','08'),('08573','Puerto Colombia','08'),('08606','Repelón','08'),('08634','Sabanagrande','08'),('08638','Sabanalarga','08'),('08675','Santa Lucía','08'),('08685','Santo Tomás','08'),('08758','Soledad','08'),('08770','Suan','08'),('08832','Tubará','08'),('08849','Usiacurí','08'),('11001','Bogotá, D.C.','11'),('13001','Cartagena De Indias','13'),('13006','Achí','13'),('13030','Altos Del Rosario','13'),('13042','Arenal','13'),('13052','Arjona','13'),('13062','Arroyohondo','13'),('13074','Barranco De Loba','13'),('13140','Calamar','13'),('13160','Cantagallo','13'),('13188','Cicuco','13'),('13212','Córdoba','13'),('13222','Clemencia','13'),('13244','El Carmen De Bolívar','13'),('13248','El Guamo','13'),('13268','El Peñón','13'),('13300','Hatillo De Loba','13'),('13430','Magangué','13'),('13433','Mahates','13'),('13440','Margarita','13'),('13442','María La Baja','13'),('13458','Montecristo','13'),('13468','Santa Cruz De Mompox','13'),('13473','Morales','13'),('13490','Norosí','13'),('13549','Pinillos','13'),('13580','Regidor','13'),('13600','Río Viejo','13'),('13620','San Cristóbal','13'),('13647','San Estanislao','13'),('13650','San Fernando','13'),('13654','San Jacinto','13'),('13655','San Jacinto Del Cauca','13'),('13657','San Juan Nepomuceno','13'),('13667','San Martín De Loba','13'),('13670','San Pablo','13'),('13673','Santa Catalina','13'),('13683','Santa Rosa','13'),('13688','Santa Rosa Del Sur','13'),('13744','Simití','13'),('13760','Soplaviento','13'),('13780','Talaigua Nuevo','13'),('13810','Tiquisio','13'),('13836','Turbaco','13'),('13838','Turbaná','13'),('13873','Villanueva','13'),('13894','Zambrano','13'),('15001','Tunja','15'),('15022','Almeida','15'),('15047','Aquitania','15'),('15051','Arcabuco','15'),('15087','Belén','15'),('15090','Berbeo','15'),('15092','Betéitiva','15'),('15097','Boavita','15'),('15104','Boyacá','15'),('15106','Briceño','15'),('15109','Buenavista','15'),('15114','Busbanzá','15'),('15131','Caldas','15'),('15135','Campohermoso','15'),('15162','Cerinza','15'),('15172','Chinavita','15'),('15176','Chiquinquirá','15'),('15180','Chiscas','15'),('15183','Chita','15'),('15185','Chitaraque','15'),('15187','Chivatá','15'),('15189','Ciénega','15'),('15204','Cómbita','15'),('15212','Coper','15'),('15215','Corrales','15'),('15218','Covarachía','15'),('15223','Cubará','15'),('15224','Cucaita','15'),('15226','Cuítiva','15'),('15232','Chíquiza','15'),('15236','Chivor','15'),('15238','Duitama','15'),('15244','El Cocuy','15'),('15248','El Espino','15'),('15272','Firavitoba','15'),('15276','Floresta','15'),('15293','Gachantivá','15'),('15296','Gámeza','15'),('15299','Garagoa','15'),('15317','Guacamayas','15'),('15322','Guateque','15'),('15325','Guayatá','15'),('15332','Güicán De La Sierra','15'),('15362','Iza','15'),('15367','Jenesano','15'),('15368','Jericó','15'),('15377','Labranzagrande','15'),('15380','La Capilla','15'),('15401','La Victoria','15'),('15403','La Uvita','15'),('15407','Villa De Leyva','15'),('15425','Macanal','15'),('15442','Maripí','15'),('15455','Miraflores','15'),('15464','Mongua','15'),('15466','Monguí','15'),('15469','Moniquirá','15'),('15476','Motavita','15'),('15480','Muzo','15'),('15491','Nobsa','15'),('15494','Nuevo Colón','15'),('15500','Oicatá','15'),('15507','Otanche','15'),('15511','Pachavita','15'),('15514','Páez','15'),('15516','Paipa','15'),('15518','Pajarito','15'),('15522','Panqueba','15'),('15531','Pauna','15'),('15533','Paya','15'),('15537','Paz De Río','15'),('15542','Pesca','15'),('15550','Pisba','15'),('15572','Puerto Boyacá','15'),('15580','Quípama','15'),('15599','Ramiriquí','15'),('15600','Ráquira','15'),('15621','Rondón','15'),('15632','Saboyá','15'),('15638','Sáchica','15'),('15646','Samacá','15'),('15660','San Eduardo','15'),('15664','San José De Pare','15'),('15667','San Luis De Gaceno','15'),('15673','San Mateo','15'),('15676','San Miguel De Sema','15'),('15681','San Pablo De Borbur','15'),('15686','Santana','15'),('15690','Santa María','15'),('15693','Santa Rosa De Viterbo','15'),('15696','Santa Sofía','15'),('15720','Sativanorte','15'),('15723','Sativasur','15'),('15740','Siachoque','15'),('15753','Soatá','15'),('15755','Socotá','15'),('15757','Socha','15'),('15759','Sogamoso','15'),('15761','Somondoco','15'),('15762','Sora','15'),('15763','Sotaquirá','15'),('15764','Soracá','15'),('15774','Susacón','15'),('15776','Sutamarchán','15'),('15778','Sutatenza','15'),('15790','Tasco','15'),('15798','Tenza','15'),('15804','Tibaná','15'),('15806','Tibasosa','15'),('15808','Tinjacá','15'),('15810','Tipacoque','15'),('15814','Toca','15'),('15816','Togüí','15'),('15820','Tópaga','15'),('15822','Tota','15'),('15832','Tununguá','15'),('15835','Turmequé','15'),('15837','Tuta','15'),('15839','Tutazá','15'),('15842','Úmbita','15'),('15861','Ventaquemada','15'),('15879','Viracachá','15'),('15897','Zetaquira','15'),('17001','Manizales','17'),('17013','Aguadas','17'),('17042','Anserma','17'),('17050','Aranzazu','17'),('17088','Belalcázar','17'),('17174','Chinchiná','17'),('17272','Filadelfia','17'),('17380','La Dorada','17'),('17388','La Merced','17'),('17433','Manzanares','17'),('17442','Marmato','17'),('17444','Marquetalia','17'),('17446','Marulanda','17'),('17486','Neira','17'),('17495','Norcasia','17'),('17513','Pácora','17'),('17524','Palestina','17'),('17541','Pensilvania','17'),('17614','Riosucio','17'),('17616','Risaralda','17'),('17653','Salamina','17'),('17662','Samaná','17'),('17665','San José','17'),('17777','Supía','17'),('17867','Victoria','17'),('17873','Villamaría','17'),('17877','Viterbo','17'),('18001','Florencia','18'),('18029','Albania','18'),('18094','Belén De Los Andaquíes','18'),('18150','Cartagena Del Chairá','18'),('18205','Curillo','18'),('18247','El Doncello','18'),('18256','El Paujíl','18'),('18410','La Montañita','18'),('18460','Milán','18'),('18479','Morelia','18'),('18592','Puerto Rico','18'),('18610','San José Del Fragua','18'),('18753','San Vicente Del Caguán','18'),('18756','Solano','18'),('18785','Solita','18'),('18860','Valparaíso','18'),('19001','Popayán','19'),('19022','Almaguer','19'),('19050','Argelia','19'),('19075','Balboa','19'),('19100','Bolívar','19'),('19110','Buenos Aires','19'),('19130','Cajibío','19'),('19137','Caldono','19'),('19142','Caloto','19'),('19212','Corinto','19'),('19256','El Tambo','19'),('19290','Florencia','19'),('19300','Guachené','19'),('19318','Guapi','19'),('19355','Inzá','19'),('19364','Jambaló','19'),('19392','La Sierra','19'),('19397','La Vega','19'),('19418','López De Micay','19'),('19450','Mercaderes','19'),('19455','Miranda','19'),('19473','Morales','19'),('19513','Padilla','19'),('19517','Páez','19'),('19532','Patía','19'),('19533','Piamonte','19'),('19548','Piendamó - Tunía','19'),('19573','Puerto Tejada','19'),('19585','Puracé','19'),('19622','Rosas','19'),('19693','San Sebastián','19'),('19698','Santander De Quilichao','19'),('19701','Santa Rosa','19'),('19743','Silvia','19'),('19760','Sotará - Paispamba','19'),('19780','Suárez','19'),('19785','Sucre','19'),('19807','Timbío','19'),('19809','Timbiquí','19'),('19821','Toribío','19'),('19824','Totoró','19'),('19845','Villa Rica','19'),('20001','Valledupar','20'),('20011','Aguachica','20'),('20013','Agustín Codazzi','20'),('20032','Astrea','20'),('20045','Becerril','20'),('20060','Bosconia','20'),('20175','Chimichagua','20'),('20178','Chiriguaná','20'),('20228','Curumaní','20'),('20238','El Copey','20'),('20250','El Paso','20'),('20295','Gamarra','20'),('20310','González','20'),('20383','La Gloria','20'),('20400','La Jagua De Ibirico','20'),('20443','Manaure Balcón Del Cesar','20'),('20517','Pailitas','20'),('20550','Pelaya','20'),('20570','Pueblo Bello','20'),('20614','Río De Oro','20'),('20621','La Paz','20'),('20710','San Alberto','20'),('20750','San Diego','20'),('20770','San Martín','20'),('20787','Tamalameque','20'),('23001','Montería','23'),('23068','Ayapel','23'),('23079','Buenavista','23'),('23090','Canalete','23'),('23162','Cereté','23'),('23168','Chimá','23'),('23182','Chinú','23'),('23189','Ciénaga De Oro','23'),('23300','Cotorra','23'),('23350','La Apartada','23'),('23417','Lorica','23'),('23419','Los Córdobas','23'),('23464','Momil','23'),('23466','Montelíbano','23'),('23500','Moñitos','23'),('23555','Planeta Rica','23'),('23570','Pueblo Nuevo','23'),('23574','Puerto Escondido','23'),('23580','Puerto Libertador','23'),('23586','Purísima De La Concepción','23'),('23660','Sahagún','23'),('23670','San Andrés De Sotavento','23'),('23672','San Antero','23'),('23675','San Bernardo Del Viento','23'),('23678','San Carlos','23'),('23682','San José De Uré','23'),('23686','San Pelayo','23'),('23807','Tierralta','23'),('23815','Tuchín','23'),('23855','Valencia','23'),('25001','Agua De Dios','25'),('25019','Albán','25'),('25035','Anapoima','25'),('25040','Anolaima','25'),('25053','Arbeláez','25'),('25086','Beltrán','25'),('25095','Bituima','25'),('25099','Bojacá','25'),('25120','Cabrera','25'),('25123','Cachipay','25'),('25126','Cajicá','25'),('25148','Caparrapí','25'),('25151','Cáqueza','25'),('25154','Carmen De Carupa','25'),('25168','Chaguaní','25'),('25175','Chía','25'),('25178','Chipaque','25'),('25181','Choachí','25'),('25183','Chocontá','25'),('25200','Cogua','25'),('25214','Cota','25'),('25224','Cucunubá','25'),('25245','El Colegio','25'),('25258','El Peñón','25'),('25260','El Rosal','25'),('25269','Facatativá','25'),('25279','Fómeque','25'),('25281','Fosca','25'),('25286','Funza','25'),('25288','Fúquene','25'),('25290','Fusagasugá','25'),('25293','Gachalá','25'),('25295','Gachancipá','25'),('25297','Gachetá','25'),('25299','Gama','25'),('25307','Girardot','25'),('25312','Granada','25'),('25317','Guachetá','25'),('25320','Guaduas','25'),('25322','Guasca','25'),('25324','Guataquí','25'),('25326','Guatavita','25'),('25328','Guayabal De Síquima','25'),('25335','Guayabetal','25'),('25339','Gutiérrez','25'),('25368','Jerusalén','25'),('25372','Junín','25'),('25377','La Calera','25'),('25386','La Mesa','25'),('25394','La Palma','25'),('25398','La Peña','25'),('25402','La Vega','25'),('25407','Lenguazaque','25'),('25426','Machetá','25'),('25430','Madrid','25'),('25436','Manta','25'),('25438','Medina','25'),('25473','Mosquera','25'),('25483','Nariño','25'),('25486','Nemocón','25'),('25488','Nilo','25'),('25489','Nimaima','25'),('25491','Nocaima','25'),('25506','Venecia','25'),('25513','Pacho','25'),('25518','Paime','25'),('25524','Pandi','25'),('25530','Paratebueno','25'),('25535','Pasca','25'),('25572','Puerto Salgar','25'),('25580','Pulí','25'),('25592','Quebradanegra','25'),('25594','Quetame','25'),('25596','Quipile','25'),('25599','Apulo','25'),('25612','Ricaurte','25'),('25645','San Antonio Del Tequendama','25'),('25649','San Bernardo','25'),('25653','San Cayetano','25'),('25658','San Francisco','25'),('25662','San Juan De Rioseco','25'),('25718','Sasaima','25'),('25736','Sesquilé','25'),('25740','Sibaté','25'),('25743','Silvania','25'),('25745','Simijaca','25'),('25754','Soacha','25'),('25758','Sopó','25'),('25769','Subachoque','25'),('25772','Suesca','25'),('25777','Supatá','25'),('25779','Susa','25'),('25781','Sutatausa','25'),('25785','Tabio','25'),('25793','Tausa','25'),('25797','Tena','25'),('25799','Tenjo','25'),('25805','Tibacuy','25'),('25807','Tibirita','25'),('25815','Tocaima','25'),('25817','Tocancipá','25'),('25823','Topaipí','25'),('25839','Ubalá','25'),('25841','Ubaque','25'),('25843','Villa De San Diego De Ubaté','25'),('25845','Une','25'),('25851','Útica','25'),('25862','Vergara','25'),('25867','Vianí','25'),('25871','Villagómez','25'),('25873','Villapinzón','25'),('25875','Villeta','25'),('25878','Viotá','25'),('25885','Yacopí','25'),('25898','Zipacón','25'),('25899','Zipaquirá','25'),('27001','Quibdó','27'),('27006','Acandí','27'),('27025','Alto Baudó','27'),('27050','Atrato','27'),('27073','Bagadó','27'),('27075','Bahía Solano','27'),('27077','Bajo Baudó','27'),('27099','Bojayá','27'),('27135','El Cantón Del San Pablo','27'),('27150','Carmen Del Darién','27'),('27160','Cértegui','27'),('27205','Condoto','27'),('27245','El Carmen De Atrato','27'),('27250','El Litoral Del San Juan','27'),('27361','Istmina','27'),('27372','Juradó','27'),('27413','Lloró','27'),('27425','Medio Atrato','27'),('27430','Medio Baudó','27'),('27450','Medio San Juan','27'),('27491','Nóvita','27'),('27493','Nuevo Belén De Bajirá','27'),('27495','Nuquí','27'),('27580','Río Iró','27'),('27600','Río Quito','27'),('27615','Riosucio','27'),('27660','San José Del Palmar','27'),('27745','Sipí','27'),('27787','Tadó','27'),('27800','Unguía','27'),('27810','Unión Panamericana','27'),('41001','Neiva','41'),('41006','Acevedo','41'),('41013','Agrado','41'),('41016','Aipe','41'),('41020','Algeciras','41'),('41026','Altamira','41'),('41078','Baraya','41'),('41132','Campoalegre','41'),('41206','Colombia','41'),('41244','Elías','41'),('41298','Garzón','41'),('41306','Gigante','41'),('41319','Guadalupe','41'),('41349','Hobo','41'),('41357','Íquira','41'),('41359','Isnos','41'),('41378','La Argentina','41'),('41396','La Plata','41'),('41483','Nátaga','41'),('41503','Oporapa','41'),('41518','Paicol','41'),('41524','Palermo','41'),('41530','Palestina','41'),('41548','Pital','41'),('41551','Pitalito','41'),('41615','Rivera','41'),('41660','Saladoblanco','41'),('41668','San Agustín','41'),('41676','Santa María','41'),('41770','Suaza','41'),('41791','Tarqui','41'),('41797','Tesalia','41'),('41799','Tello','41'),('41801','Teruel','41'),('41807','Timaná','41'),('41872','Villavieja','41'),('41885','Yaguará','41'),('44001','Riohacha','44'),('44035','Albania','44'),('44078','Barrancas','44'),('44090','Dibulla','44'),('44098','Distracción','44'),('44110','El Molino','44'),('44279','Fonseca','44'),('44378','Hatonuevo','44'),('44420','La Jagua Del Pilar','44'),('44430','Maicao','44'),('44560','Manaure','44'),('44650','San Juan Del Cesar','44'),('44847','Uribia','44'),('44855','Urumita','44'),('44874','Villanueva','44'),('47001','Santa Marta','47'),('47030','Algarrobo','47'),('47053','Aracataca','47'),('47058','Ariguaní','47'),('47161','Cerro De San Antonio','47'),('47170','Chivolo','47'),('47189','Ciénaga','47'),('47205','Concordia','47'),('47245','El Banco','47'),('47258','El Piñón','47'),('47268','El Retén','47'),('47288','Fundación','47'),('47318','Guamal','47'),('47460','Nueva Granada','47'),('47541','Pedraza','47'),('47545','Pijiño Del Carmen','47'),('47551','Pivijay','47'),('47555','Plato','47'),('47570','Puebloviejo','47'),('47605','Remolino','47'),('47660','Sabanas De San Ángel','47'),('47675','Salamina','47'),('47692','San Sebastián De Buenavista','47'),('47703','San Zenón','47'),('47707','Santa Ana','47'),('47720','Santa Bárbara De Pinto','47'),('47745','Sitionuevo','47'),('47798','Tenerife','47'),('47960','Zapayán','47'),('47980','Zona Bananera','47'),('50001','Villavicencio','50'),('50006','Acacías','50'),('50110','Barranca De Upía','50'),('50124','Cabuyaro','50'),('50150','Castilla La Nueva','50'),('50223','Cubarral','50'),('50226','Cumaral','50'),('50245','El Calvario','50'),('50251','El Castillo','50'),('50270','El Dorado','50'),('50287','Fuente De Oro','50'),('50313','Granada','50'),('50318','Guamal','50'),('50325','Mapiripán','50'),('50330','Mesetas','50'),('50350','La Macarena','50'),('50370','Uribe','50'),('50400','Lejanías','50'),('50450','Puerto Concordia','50'),('50568','Puerto Gaitán','50'),('50573','Puerto López','50'),('50577','Puerto Lleras','50'),('50590','Puerto Rico','50'),('50606','Restrepo','50'),('50680','San Carlos De Guaroa','50'),('50683','San Juan De Arama','50'),('50686','San Juanito','50'),('50689','San Martín','50'),('50711','Vistahermosa','50'),('52001','Pasto','52'),('52019','Albán','52'),('52022','Aldana','52'),('52036','Ancuya','52'),('52051','Arboleda','52'),('52079','Barbacoas','52'),('52083','Belén','52'),('52110','Buesaco','52'),('52203','Colón','52'),('52207','Consacá','52'),('52210','Contadero','52'),('52215','Córdoba','52'),('52224','Cuaspud Carlosama','52'),('52227','Cumbal','52'),('52233','Cumbitara','52'),('52240','Chachagüí','52'),('52250','El Charco','52'),('52254','El Peñol','52'),('52256','El Rosario','52'),('52258','El Tablón De Gómez','52'),('52260','El Tambo','52'),('52287','Funes','52'),('52317','Guachucal','52'),('52320','Guaitarilla','52'),('52323','Gualmatán','52'),('52352','Iles','52'),('52354','Imués','52'),('52356','Ipiales','52'),('52378','La Cruz','52'),('52381','La Florida','52'),('52385','La Llanada','52'),('52390','La Tola','52'),('52399','La Unión','52'),('52405','Leiva','52'),('52411','Linares','52'),('52418','Los Andes','52'),('52427','Magüí','52'),('52435','Mallama','52'),('52473','Mosquera','52'),('52480','Nariño','52'),('52490','Olaya Herrera','52'),('52506','Ospina','52'),('52520','Francisco Pizarro','52'),('52540','Policarpa','52'),('52560','Potosí','52'),('52565','Providencia','52'),('52573','Puerres','52'),('52585','Pupiales','52'),('52612','Ricaurte','52'),('52621','Roberto Payán','52'),('52678','Samaniego','52'),('52683','Sandoná','52'),('52685','San Bernardo','52'),('52687','San Lorenzo','52'),('52693','San Pablo','52'),('52694','San Pedro De Cartago','52'),('52696','Santa Bárbara','52'),('52699','Santacruz','52'),('52720','Sapuyes','52'),('52786','Taminango','52'),('52788','Tangua','52'),('52835','San Andrés De Tumaco','52'),('52838','Túquerres','52'),('52885','Yacuanquer','52'),('54001','San José De Cúcuta','54'),('54003','Ábrego','54'),('54051','Arboledas','54'),('54099','Bochalema','54'),('54109','Bucarasica','54'),('54125','Cácota','54'),('54128','Cáchira','54'),('54172','Chinácota','54'),('54174','Chitagá','54'),('54206','Convención','54'),('54223','Cucutilla','54'),('54239','Durania','54'),('54245','El Carmen','54'),('54250','El Tarra','54'),('54261','El Zulia','54'),('54313','Gramalote','54'),('54344','Hacarí','54'),('54347','Herrán','54'),('54377','Labateca','54'),('54385','La Esperanza','54'),('54398','La Playa','54'),('54405','Los Patios','54'),('54418','Lourdes','54'),('54480','Mutiscua','54'),('54498','Ocaña','54'),('54518','Pamplona','54'),('54520','Pamplonita','54'),('54553','Puerto Santander','54'),('54599','Ragonvalia','54'),('54660','Salazar','54'),('54670','San Calixto','54'),('54673','San Cayetano','54'),('54680','Santiago','54'),('54720','Sardinata','54'),('54743','Silos','54'),('54800','Teorama','54'),('54810','Tibú','54'),('54820','Toledo','54'),('54871','Villa Caro','54'),('54874','Villa Del Rosario','54'),('63001','Armenia','63'),('63111','Buenavista','63'),('63130','Calarcá','63'),('63190','Circasia','63'),('63212','Córdoba','63'),('63272','Filandia','63'),('63302','Génova','63'),('63401','La Tebaida','63'),('63470','Montenegro','63'),('63548','Pijao','63'),('63594','Quimbaya','63'),('63690','Salento','63'),('66001','Pereira','66'),('66045','Apía','66'),('66075','Balboa','66'),('66088','Belén De Umbría','66'),('66170','Dosquebradas','66'),('66318','Guática','66'),('66383','La Celia','66'),('66400','La Virginia','66'),('66440','Marsella','66'),('66456','Mistrató','66'),('66572','Pueblo Rico','66'),('66594','Quinchía','66'),('66682','Santa Rosa De Cabal','66'),('66687','Santuario','66'),('68001','Bucaramanga','68'),('68013','Aguada','68'),('68020','Albania','68'),('68051','Aratoca','68'),('68077','Barbosa','68'),('68079','Barichara','68'),('68081','Barrancabermeja','68'),('68092','Betulia','68'),('68101','Bolívar','68'),('68121','Cabrera','68'),('68132','California','68'),('68147','Capitanejo','68'),('68152','Carcasí','68'),('68160','Cepitá','68'),('68162','Cerrito','68'),('68167','Charalá','68'),('68169','Charta','68'),('68176','Chima','68'),('68179','Chipatá','68'),('68190','Cimitarra','68'),('68207','Concepción','68'),('68209','Confines','68'),('68211','Contratación','68'),('68217','Coromoro','68'),('68229','Curití','68'),('68235','El Carmen De Chucurí','68'),('68245','El Guacamayo','68'),('68250','El Peñón','68'),('68255','El Playón','68'),('68264','Encino','68'),('68266','Enciso','68'),('68271','Florián','68'),('68276','Floridablanca','68'),('68296','Galán','68'),('68298','Gámbita','68'),('68307','Girón','68'),('68318','Guaca','68'),('68320','Guadalupe','68'),('68322','Guapotá','68'),('68324','Guavatá','68'),('68327','Güepsa','68'),('68344','Hato','68'),('68368','Jesús María','68'),('68370','Jordán','68'),('68377','La Belleza','68'),('68385','Landázuri','68'),('68397','La Paz','68'),('68406','Lebrija','68'),('68418','Los Santos','68'),('68425','Macaravita','68'),('68432','Málaga','68'),('68444','Matanza','68'),('68464','Mogotes','68'),('68468','Molagavita','68'),('68498','Ocamonte','68'),('68500','Oiba','68'),('68502','Onzaga','68'),('68522','Palmar','68'),('68524','Palmas Del Socorro','68'),('68533','Páramo','68'),('68547','Piedecuesta','68'),('68549','Pinchote','68'),('68572','Puente Nacional','68'),('68573','Puerto Parra','68'),('68575','Puerto Wilches','68'),('68615','Rionegro','68'),('68655','Sabana De Torres','68'),('68669','San Andrés','68'),('68673','San Benito','68'),('68679','San Gil','68'),('68682','San Joaquín','68'),('68684','San José De Miranda','68'),('68686','San Miguel','68'),('68689','San Vicente De Chucurí','68'),('68705','Santa Bárbara','68'),('68720','Santa Helena Del Opón','68'),('68745','Simacota','68'),('68755','Socorro','68'),('68770','Suaita','68'),('68773','Sucre','68'),('68780','Suratá','68'),('68820','Tona','68'),('68855','Valle De San José','68'),('68861','Vélez','68'),('68867','Vetas','68'),('68872','Villanueva','68'),('68895','Zapatoca','68'),('70001','Sincelejo','70'),('70110','Buenavista','70'),('70124','Caimito','70'),('70204','Colosó','70'),('70215','Corozal','70'),('70221','Coveñas','70'),('70230','Chalán','70'),('70233','El Roble','70'),('70235','Galeras','70'),('70265','Guaranda','70'),('70400','La Unión','70'),('70418','Los Palmitos','70'),('70429','Majagual','70'),('70473','Morroa','70'),('70508','Ovejas','70'),('70523','Palmito','70'),('70670','Sampués','70'),('70678','San Benito Abad','70'),('70702','San Juan De Betulia','70'),('70708','San Marcos','70'),('70713','San Onofre','70'),('70717','San Pedro','70'),('70742','San Luis De Sincé','70'),('70771','Sucre','70'),('70820','Santiago De Tolú','70'),('70823','San José De Toluviejo','70'),('73001','Ibagué','73'),('73024','Alpujarra','73'),('73026','Alvarado','73'),('73030','Ambalema','73'),('73043','Anzoátegui','73'),('73055','Armero','73'),('73067','Ataco','73'),('73124','Cajamarca','73'),('73148','Carmen De Apicalá','73'),('73152','Casabianca','73'),('73168','Chaparral','73'),('73200','Coello','73'),('73217','Coyaima','73'),('73226','Cunday','73'),('73236','Dolores','73'),('73268','Espinal','73'),('73270','Falan','73'),('73275','Flandes','73'),('73283','Fresno','73'),('73319','Guamo','73'),('73347','Herveo','73'),('73349','Honda','73'),('73352','Icononzo','73'),('73408','Lérida','73'),('73411','Líbano','73'),('73443','San Sebastián De Mariquita','73'),('73449','Melgar','73'),('73461','Murillo','73'),('73483','Natagaima','73'),('73504','Ortega','73'),('73520','Palocabildo','73'),('73547','Piedras','73'),('73555','Planadas','73'),('73563','Prado','73'),('73585','Purificación','73'),('73616','Rioblanco','73'),('73622','Roncesvalles','73'),('73624','Rovira','73'),('73671','Saldaña','73'),('73675','San Antonio','73'),('73678','San Luis','73'),('73686','Santa Isabel','73'),('73770','Suárez','73'),('73854','Valle De San Juan','73'),('73861','Venadillo','73'),('73870','Villahermosa','73'),('73873','Villarrica','73'),('76001','Santiago De Cali','76'),('76020','Alcalá','76'),('76036','Andalucía','76'),('76041','Ansermanuevo','76'),('76054','Argelia','76'),('76100','Bolívar','76'),('76109','Buenaventura','76'),('76111','Guadalajara De Buga','76'),('76113','Bugalagrande','76'),('76122','Caicedonia','76'),('76126','Calima','76'),('76130','Candelaria','76'),('76147','Cartago','76'),('76233','Dagua','76'),('76243','El Águila','76'),('76246','El Cairo','76'),('76248','El Cerrito','76'),('76250','El Dovio','76'),('76275','Florida','76'),('76306','Ginebra','76'),('76318','Guacarí','76'),('76364','Jamundí','76'),('76377','La Cumbre','76'),('76400','La Unión','76'),('76403','La Victoria','76'),('76497','Obando','76'),('76520','Palmira','76'),('76563','Pradera','76'),('76606','Restrepo','76'),('76616','Riofrío','76'),('76622','Roldanillo','76'),('76670','San Pedro','76'),('76736','Sevilla','76'),('76823','Toro','76'),('76828','Trujillo','76'),('76834','Tuluá','76'),('76845','Ulloa','76'),('76863','Versalles','76'),('76869','Vijes','76'),('76890','Yotoco','76'),('76892','Yumbo','76'),('76895','Zarzal','76'),('81001','Arauca','81'),('81065','Arauquita','81'),('81220','Cravo Norte','81'),('81300','Fortul','81'),('81591','Puerto Rondón','81'),('81736','Saravena','81'),('81794','Tame','81'),('85001','Yopal','85'),('85010','Aguazul','85'),('85015','Chámeza','85'),('85125','Hato Corozal','85'),('85136','La Salina','85'),('85139','Maní','85'),('85162','Monterrey','85'),('85225','Nunchía','85'),('85230','Orocué','85'),('85250','Paz De Ariporo','85'),('85263','Pore','85'),('85279','Recetor','85'),('85300','Sabanalarga','85'),('85315','Sácama','85'),('85325','San Luis De Palenque','85'),('85400','Támara','85'),('85410','Tauramena','85'),('85430','Trinidad','85'),('85440','Villanueva','85'),('86001','Mocoa','86'),('86219','Colón','86'),('86320','Orito','86'),('86568','Puerto Asís','86'),('86569','Puerto Caicedo','86'),('86571','Puerto Guzmán','86'),('86573','Puerto Leguízamo','86'),('86749','Sibundoy','86'),('86755','San Francisco','86'),('86757','San Miguel','86'),('86760','Santiago','86'),('86865','Valle Del Guamuez','86'),('86885','Villagarzón','86'),('88001','San Andrés','88'),('88564','Providencia','88'),('91001','Leticia','91'),('91263','El Encanto','91'),('91405','La Chorrera','91'),('91407','La Pedrera','91'),('91430','La Victoria','91'),('91460','Mirití - Paraná','91'),('91530','Puerto Alegría','91'),('91536','Puerto Arica','91'),('91540','Puerto Nariño','91'),('91669','Puerto Santander','91'),('91798','Tarapacá','91'),('94001','Inírida','94'),('94343','Barrancominas','94'),('94883','San Felipe','94'),('94884','Puerto Colombia','94'),('94885','La Guadalupe','94'),('94886','Cacahual','94'),('94887','Pana Pana','94'),('94888','Morichal','94'),('95001','San José Del Guaviare','95'),('95015','Calamar','95'),('95025','El Retorno','95'),('95200','Miraflores','95'),('97001','Mitú','97'),('97161','Carurú','97'),('97511','Pacoa','97'),('97666','Taraira','97'),('97777','Papunahua','97'),('97889','Yavaraté','97'),('99001','Puerto Carreño','99'),('99524','La Primavera','99'),('99624','Santa Rosalía','99'),('99773','Cumaribo','99');
/*!40000 ALTER TABLE `municipios` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `pagos_factura`
--

DROP TABLE IF EXISTS `pagos_factura`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `pagos_factura` (
  `status` varchar(20) NOT NULL,
  `cod_pago_factura` int(11) NOT NULL AUTO_INCREMENT,
  PRIMARY KEY (`cod_pago_factura`)
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `pagos_factura`
--

LOCK TABLES `pagos_factura` WRITE;
/*!40000 ALTER TABLE `pagos_factura` DISABLE KEYS */;
INSERT INTO `pagos_factura` VALUES ('paid',1),('pending',2),('partially paid',3),('overdue',4),('cancelled',5),('disputed',6),('refunded',7),('Anulada',8),('Parcialmente Anulada',9);
/*!40000 ALTER TABLE `pagos_factura` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `producto_descuento`
--

DROP TABLE IF EXISTS `producto_descuento`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `producto_descuento` (
  `cod_producto` int(11) NOT NULL,
  `cod_descuento` int(11) NOT NULL,
  PRIMARY KEY (`cod_producto`,`cod_descuento`),
  KEY `cod_descuento` (`cod_descuento`),
  CONSTRAINT `producto_descuento_ibfk_2` FOREIGN KEY (`cod_descuento`) REFERENCES `descuentos` (`cod_descuento`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `producto_descuento`
--

LOCK TABLES `producto_descuento` WRITE;
/*!40000 ALTER TABLE `producto_descuento` DISABLE KEYS */;
INSERT INTO `producto_descuento` VALUES (1,55504),(2,55506),(3,55501),(6,55508);
/*!40000 ALTER TABLE `producto_descuento` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `productos`
--

DROP TABLE IF EXISTS `productos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `productos` (
  `cod_producto` int(11) NOT NULL AUTO_INCREMENT,
  `sku` varchar(50) NOT NULL COMMENT 'Código interno único para el negocio',
  `nombre` varchar(255) NOT NULL,
  `descripcion` text DEFAULT NULL,
  `precio_unitario` decimal(12,2) NOT NULL COMMENT 'Decimal para precisión monetaria',
  `stock` int(11) DEFAULT 0,
  `stock_minimo` int(11) DEFAULT 5 COMMENT 'Alerta para reabastecimiento',
  `controla_stock` tinyint(1) NOT NULL DEFAULT 1 COMMENT '0 = servicio o intangible: no descuenta inventario',
  `cod_impuesto` int(11) NOT NULL DEFAULT 1 COMMENT 'FK a tabla impuestos. 1 = IVA 19% por defecto',
  `unidad_medida` varchar(20) DEFAULT '94' COMMENT 'Código estándar (ej. C62=Unidad, WSD=servicios, KGM=Kilogramo)',
  `codigo_barras` varchar(50) DEFAULT NULL,
  `activo` tinyint(1) DEFAULT 1,
  `tipo_item` varchar(5) DEFAULT 'IP',
  PRIMARY KEY (`cod_producto`),
  UNIQUE KEY `sku` (`sku`),
  KEY `fk_producto_impuesto` (`cod_impuesto`),
  CONSTRAINT `fk_producto_impuesto` FOREIGN KEY (`cod_impuesto`) REFERENCES `impuestos` (`cod_impuesto`)
) ENGINE=InnoDB AUTO_INCREMENT=41 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `productos`
--

LOCK TABLES `productos` WRITE;
/*!40000 ALTER TABLE `productos` DISABLE KEYS */;
INSERT INTO `productos` VALUES (1,'TEC-001','Logitech Wireless Mouse','Ergonomic black mouse, AA battery included',45000.00,50,10,1,1,'C62',NULL,1,'IP'),(2,'TEC-002','RGB Mechanical Keyboard','Gaming keyboard with blue switches, backlit',180000.00,20,5,1,1,'C62',NULL,1,'IP'),(3,'TEC-003','Samsung 24\" Monitor','LED IPS 75Hz display, HDMI/VGA',650000.00,2,3,1,1,'C62',NULL,1,'IP'),(4,'ACC-001','Laptop Backpack','Waterproof backpack for laptops up to 15.6\"',95000.00,30,5,1,1,'C62',NULL,1,'IP'),(5,'SER-001','Preventive Maintenance','PC cleaning and optimization technical service',80000.00,999,0,0,1,'WSD',NULL,1,'IP'),(6,'TEC-004','480GB SSD Solid State Drive','Kingston SATA III solid state drive',120000.00,40,8,1,1,'C62',NULL,1,'IP'),(7,'TEC-005','2 Meter HDMI Cable','Reinforced 4K high-speed cable',15000.00,15,20,1,1,'C62',NULL,1,'IP'),(8,'LIC-001','1 Year Antivirus License','Digital activation code sent via email',55000.00,999,0,0,1,'WSD',NULL,1,'IP'),(9,'TEC-006','8GB DDR4 RAM Memory','Laptop memory module 2666MHz',110000.00,25,5,1,1,'C62',NULL,1,'IP'),(10,'PAP-001','Letter Size Bond Paper Ream','White paper box 75g x 500 sheets',18500.00,0,0,1,1,'C62',NULL,0,'IP');
/*!40000 ALTER TABLE `productos` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `productos_descuentos`
--

DROP TABLE IF EXISTS `productos_descuentos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `productos_descuentos` (
  `cod_descuento` int(11) NOT NULL AUTO_INCREMENT,
  `cod_producto` int(11) NOT NULL,
  PRIMARY KEY (`cod_descuento`)
) ENGINE=InnoDB AUTO_INCREMENT=21 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `productos_descuentos`
--

LOCK TABLES `productos_descuentos` WRITE;
/*!40000 ALTER TABLE `productos_descuentos` DISABLE KEYS */;
INSERT INTO `productos_descuentos` VALUES (15,3),(20,1);
/*!40000 ALTER TABLE `productos_descuentos` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `receptores`
--

DROP TABLE IF EXISTS `receptores`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `receptores` (
  `cod_receptor` int(11) NOT NULL AUTO_INCREMENT,
  `cod_cliente_api` int(11) NOT NULL,
  `tipo_documento` varchar(4) NOT NULL COMMENT 'Codigo DIAN: 13 CC, 22 CE, 31 NIT, 41 Pasaporte',
  `numero_documento` varchar(30) NOT NULL,
  `dv` char(1) DEFAULT NULL,
  `nombre` varchar(200) NOT NULL,
  `tipo_persona` varchar(20) DEFAULT 'NATURAL',
  `regimen_tributario` varchar(60) DEFAULT 'NO_RESPONSABLE_IVA',
  `email` varchar(150) DEFAULT NULL,
  `telefono` varchar(40) DEFAULT NULL,
  `direccion` varchar(200) DEFAULT NULL,
  `cod_municipio` char(5) DEFAULT NULL,
  `creado_en` datetime NOT NULL,
  PRIMARY KEY (`cod_receptor`),
  UNIQUE KEY `uq_receptor_del_cliente` (`cod_cliente_api`,`tipo_documento`,`numero_documento`),
  CONSTRAINT `fk_receptor_cliente_api` FOREIGN KEY (`cod_cliente_api`) REFERENCES `clientes_api` (`cod_cliente_api`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `receptores`
--

LOCK TABLES `receptores` WRITE;
/*!40000 ALTER TABLE `receptores` DISABLE KEYS */;
/*!40000 ALTER TABLE `receptores` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `schema_migrations`
--

DROP TABLE IF EXISTS `schema_migrations`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `schema_migrations` (
  `version` varchar(50) NOT NULL,
  `descripcion` varchar(255) NOT NULL,
  `aplicada_en` datetime NOT NULL,
  PRIMARY KEY (`version`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `schema_migrations`
--

LOCK TABLES `schema_migrations` WRITE;
/*!40000 ALTER TABLE `schema_migrations` DISABLE KEYS */;
INSERT INTO `schema_migrations` VALUES ('001','Módulo de inventario: kardex de movimientos y flag controla_stock','2026-08-09 18:29:28'),('002','Foto de perfil de usuario','2026-08-09 19:55:12'),('003','API middleware DIAN: clientes API, receptores, documentos, líneas y eventos','2026-08-18 09:12:00');
/*!40000 ALTER TABLE `schema_migrations` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `usuarios`
--

DROP TABLE IF EXISTS `usuarios`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `usuarios` (
  `cod_usuario` int(11) NOT NULL AUTO_INCREMENT,
  `nombre` varchar(255) DEFAULT NULL,
  `correo` varchar(255) DEFAULT NULL,
  `contrasena` varchar(255) DEFAULT NULL,
  `rol` varchar(255) DEFAULT NULL,
  `foto` varchar(255) DEFAULT NULL COMMENT 'Nombre del archivo dentro de static/img/perfiles; NULL = avatar genérico',
  `cod_empresa` int(11) DEFAULT NULL,
  `activo` tinyint(1) NOT NULL DEFAULT 1,
  PRIMARY KEY (`cod_usuario`),
  UNIQUE KEY `correo` (`correo`),
  KEY `fk_usuario_empresa` (`cod_empresa`),
  CONSTRAINT `fk_usuario_empresa` FOREIGN KEY (`cod_empresa`) REFERENCES `empresas` (`cod_empresa`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=101 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `usuarios`
--

LOCK TABLES `usuarios` WRITE;
/*!40000 ALTER TABLE `usuarios` DISABLE KEYS */;
INSERT INTO `usuarios` VALUES (1,'Administrator','administrador@factugest.com','$2b$12$Pg7Xv8AuOi7Zjmg2DIjM4OvAcoOFF3CLidz6VMAEUM7KAXNN8uPDm','ADMIN',NULL,6,1),(2,'Brandon','brandon@factugest.com','$2b$12$nrHaD3rYzV7S8CKrHM3FPevndd5fuFlIxTYIQsQ2VQuFKTf/SAf5m','ADMIN',NULL,6,1),(3,'Johan','johan@factugest.com','$2b$12$NqQnvTFgb4fR5Olhvd5W4uXue0rjco5O3fm7jf6ZonbOGCf.AMdyq','ADMIN',NULL,2,1),(4,'Wilmer','wilmer@factugest.com','$2b$12$JJPYM1JMt2bgk5xX121AdOEQiUzShPYT1iQfbqKGukNxv6MpwD7Di','ADMIN',NULL,1,1),(5,'Yuliana','yuliana@factugest.com','$2b$12$56M/ZdFU6v.L1CnTW9QyqeVWbmMYke9X18vaUL4I34Av5.7oXx/6u','CAJERO',NULL,6,1),(6,'Diana Pedraza','diana@factugest.com','$2b$12$xeLuVjKbtnBzCgYBiEZPf.QwVl7pPBKpRfBhnt0N6.8iZKqj1LvI.','SUPERVISOR',NULL,2,0),(7,'Valeria Padraza','valeria@factugest.com','$2b$12$JdVCOVXjFYTjevFGeFlileL.39oYNW0c0EAvUwSrxDMRz/.1BwMTa','JEFE_TIENDA',NULL,1,1),(8,'juan','juan@factugest.com','$2b$12$kJhBVgt/pQ9/6g8LNfkFQ.CrzVq3JnS8Hq38hK/6rcX2d3rr6S5n.','SUPERVISOR',NULL,1,1);
/*!40000 ALTER TABLE `usuarios` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping events for database 'factugest'
--

--
-- Dumping routines for database 'factugest'
--
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-08-09 20:27:19
