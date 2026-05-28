# Modelo de Base de Datos — Sistema POS

## 1. Descripción General

Modelo relacional diseñado para **SQLite** que cubre los 9 módulos del sistema POS offline, más el módulo complementario de **Devoluciones y Cambios**.

### Principios de diseño

- **Normalización** adecuada sin sobre-ingeniería
- **Trazabilidad** completa (auditoría, historial de precios, movimientos)
- **Integridad referencial** con foreign keys
- **Eliminación lógica** (`activo = FALSE`) en lugar de eliminación física
- **Extensibilidad** futura (multi-sucursal, nube)

### Decisiones confirmadas

| Decisión | Resolución |
|----------|------------|
| Folio de venta | `V-YYYYMMDD-NNNN` (prefijo + fecha + consecutivo) |
| Productos sin variantes | No permitidos. Se crea variante "Default" automáticamente |
| Almacenamiento de tickets | No se almacenan. Se generan dinámicamente desde datos de la venta |
| Cajas simultáneas | No. Una sola caja abierta por jornada completa por equipo |
| Descuentos | Opcionales, se aplican en el momento de la venta |
| Devoluciones y cambios | Sí, módulo completo incluido |

### Total de tablas: 28

---

## 2. Diagrama Entidad-Relación

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        DIAGRAMA ENTIDAD-RELACIÓN                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────┐    ┌────────────┐    ┌─────────┐                               │
│  │   Rol   │───▶│ RolPermiso │◀───│ Permiso │                               │
│  └────┬────┘    └────────────┘    └─────────┘                               │
│       │                                                                     │
│       ▼                                                                     │
│  ┌─────────┐    ┌─────────┐    ┌─────────────────────┐                      │
│  │ Usuario │───▶│ Sesión  │    │ BitácoraAutenticación│                      │
│  └────┬────┘    └─────────┘    └─────────────────────┘                      │
│       │                                                                     │
│       ├────────────────────────┬──────────────────────────┐                  │
│       ▼                        ▼                          ▼                  │
│  ┌─────────┐    ┌──────────────────┐    ┌──────────────────┐                │
│  │  Caja   │    │  Autorización    │    │   Venta          │                │
│  └────┬────┘    └──────────────────┘    └───┬──────────┬───┘                │
│       │                                     │          │                     │
│       ▼                                     ▼          ▼                     │
│  ┌──────────────┐    ┌──────────────┐  ┌────────┐  ┌────────┐              │
│  │MovimientoCaja│    │ DetalleVenta │  │  Pago  │  │Devoluci│              │
│  └──────────────┘    └──────┬───────┘  └───┬────┘  │  ón    │              │
│                             │              │       └───┬────┘              │
│                             ▼              ▼           │                     │
│                    ┌────────────────┐ ┌──────────┐     ▼                     │
│                    │VarianteProduct │ │DetallePag│ ┌──────────┐             │
│                    └───┬──────┬─────┘ └──────────┘ │DetalleDev│             │
│                        │      │                    └──────────┘             │
│                        ▼      ▼                                             │
│               ┌──────────┐ ┌──────────────┐                                 │
│               │Inventario│ │PrecioProducto│                                 │
│               └──────┬───┘ └──────────────┘                                 │
│                      ▼                                                      │
│            ┌───────────────────┐                                            │
│            │MovimientoInventari│                                            │
│            └───────────────────┘                                            │
│                                                                             │
│  ┌──────────┐  ┌──────────┐  ┌────────┐                                    │
│  │  Cliente │  │ Producto │  │Config  │                                    │
│  └──────┬───┘  └──────────┘  │General │                                    │
│         │                    └────────┘                                     │
│         ▼                                                                   │
│  ┌────────────────┐                                                         │
│  │MovimientoCrédit│                                                         │
│  └────────────────┘                                                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Definición de Tablas por Módulo

---

### MÓDULO 1 — Autenticación y Usuarios

---

#### Tabla: `rol`

Almacena los roles del sistema (administrador, vendedor).

| Columna | Tipo | Restricción | Descripción |
|---------|------|-------------|-------------|
| id | INTEGER | PK, AUTOINCREMENT | Identificador único |
| nombre | VARCHAR(50) | UNIQUE, NOT NULL | Nombre del rol |
| descripcion | VARCHAR(200) | | Descripción del rol |
| activo | BOOLEAN | DEFAULT TRUE | Eliminación lógica |
| created_at | DATETIME | NOT NULL | Fecha de creación |
| updated_at | DATETIME | NOT NULL | Última modificación |

---

#### Tabla: `permiso`

Almacena permisos predefinidos del sistema. Se pre-cargan con datos semilla.

| Columna | Tipo | Restricción | Descripción |
|---------|------|-------------|-------------|
| id | INTEGER | PK, AUTOINCREMENT | Identificador único |
| codigo | VARCHAR(100) | UNIQUE, NOT NULL | Código del permiso (ej: ventas.crear) |
| nombre | VARCHAR(100) | NOT NULL | Nombre legible |
| modulo | VARCHAR(50) | NOT NULL | Módulo al que pertenece |
| descripcion | VARCHAR(200) | | Descripción del permiso |

---

#### Tabla: `rol_permiso`

Relación N-N entre roles y permisos.

| Columna | Tipo | Restricción | Descripción |
|---------|------|-------------|-------------|
| id | INTEGER | PK, AUTOINCREMENT | Identificador único |
| rol_id | INTEGER | FK → rol.id, NOT NULL | Rol asociado |
| permiso_id | INTEGER | FK → permiso.id, NOT NULL | Permiso asociado |

Restricción: UNIQUE(rol_id, permiso_id)

---

#### Tabla: `usuario`

Usuarios del sistema con credenciales y rol asignado.

| Columna | Tipo | Restricción | Descripción |
|---------|------|-------------|-------------|
| id | INTEGER | PK, AUTOINCREMENT | Identificador único |
| username | VARCHAR(50) | UNIQUE, NOT NULL | Nombre de usuario |
| password_hash | VARCHAR(255) | NOT NULL | Contraseña cifrada (bcrypt) |
| nombre_completo | VARCHAR(150) | NOT NULL | Nombre del usuario |
| rol_id | INTEGER | FK → rol.id, NOT NULL | Rol asignado |
| activo | BOOLEAN | DEFAULT TRUE | Estado del usuario |
| forzar_cambio_password | BOOLEAN | DEFAULT FALSE | Obliga cambio al siguiente login |
| created_at | DATETIME | NOT NULL | Fecha de creación |
| updated_at | DATETIME | NOT NULL | Última modificación |

---

#### Tabla: `sesion`

Registro de sesiones activas y cerradas.

| Columna | Tipo | Restricción | Descripción |
|---------|------|-------------|-------------|
| id | INTEGER | PK, AUTOINCREMENT | Identificador único |
| usuario_id | INTEGER | FK → usuario.id, NOT NULL | Usuario de la sesión |
| fecha_inicio | DATETIME | NOT NULL | Inicio de sesión |
| fecha_fin | DATETIME | NULL | NULL = sesión activa |
| activa | BOOLEAN | DEFAULT TRUE | Estado de la sesión |

---

#### Tabla: `bitacora_autenticacion`

Registro de eventos de seguridad y acceso.

| Columna | Tipo | Restricción | Descripción |
|---------|------|-------------|-------------|
| id | INTEGER | PK, AUTOINCREMENT | Identificador único |
| usuario_id | INTEGER | FK → usuario.id, NOT NULL | Usuario involucrado |
| evento | VARCHAR(50) | NOT NULL | login, logout, cambio_password, reset_password, login_fallido |
| detalle | TEXT | | Información adicional |
| fecha | DATETIME | NOT NULL | Fecha del evento |

---

### MÓDULO 2 — Clientes

---

#### Tabla: `cliente`

Información de clientes con control de crédito.

| Columna | Tipo | Restricción | Descripción |
|---------|------|-------------|-------------|
| id | INTEGER | PK, AUTOINCREMENT | Identificador único |
| nombre | VARCHAR(150) | NOT NULL | Nombre del cliente |
| telefono | VARCHAR(20) | | Teléfono de contacto |
| email | VARCHAR(100) | | Correo electrónico |
| direccion | TEXT | | Dirección |
| tipo_cliente | VARCHAR(50) | DEFAULT 'general' | general, mayorista, etc. |
| limite_credito | DECIMAL(12,2) | DEFAULT 0.00 | Límite de crédito asignado. 0 = sin crédito |
| saldo_credito | DECIMAL(12,2) | DEFAULT 0.00 | Saldo pendiente actual (campo desnormalizado) |
| activo | BOOLEAN | DEFAULT TRUE | Eliminación lógica |
| notas | TEXT | | Observaciones |
| created_at | DATETIME | NOT NULL | Fecha de registro |
| updated_at | DATETIME | NOT NULL | Última modificación |

**NOTA IMPORTANTE:** `saldo_credito` es un campo desnormalizado que se actualiza automáticamente con cada venta a crédito, pago o cancelación. Siempre debe ser recalculable a partir de `movimiento_credito`.

---

#### Tabla: `movimiento_credito`

Historial completo de movimientos de crédito del cliente.

| Columna | Tipo | Restricción | Descripción |
|---------|------|-------------|-------------|
| id | INTEGER | PK, AUTOINCREMENT | Identificador único |
| cliente_id | INTEGER | FK → cliente.id, NOT NULL | Cliente asociado |
| venta_id | INTEGER | FK → venta.id, NULL | Venta que originó el movimiento |
| pago_id | INTEGER | FK → pago.id, NULL | Pago asociado (si es abono) |
| devolucion_id | INTEGER | FK → devolucion.id, NULL | Devolución asociada |
| tipo | VARCHAR(30) | NOT NULL | cargo, abono, anticipo, cancelacion, devolucion |
| monto | DECIMAL(12,2) | NOT NULL | Monto del movimiento (siempre positivo) |
| saldo_anterior | DECIMAL(12,2) | NOT NULL | Saldo antes del movimiento |
| saldo_nuevo | DECIMAL(12,2) | NOT NULL | Saldo después del movimiento |
| descripcion | VARCHAR(200) | | Descripción del movimiento |
| usuario_id | INTEGER | FK → usuario.id, NOT NULL | Quién registró el movimiento |
| fecha | DATETIME | NOT NULL | Fecha del movimiento |

---

### MÓDULO 3 — Productos

---

#### Tabla: `tipo_producto`

Tipos genéricos de producto (ropa, alimento, perfume, etc.).

| Columna | Tipo | Restricción | Descripción |
|---------|------|-------------|-------------|
| id | INTEGER | PK, AUTOINCREMENT | Identificador único |
| nombre | VARCHAR(100) | UNIQUE, NOT NULL | Nombre del tipo |
| activo | BOOLEAN | DEFAULT TRUE | Estado |

---

#### Tabla: `categoria`

Categorías de producto (camisas, pantalones, abarrotes, etc.).

| Columna | Tipo | Restricción | Descripción |
|---------|------|-------------|-------------|
| id | INTEGER | PK, AUTOINCREMENT | Identificador único |
| nombre | VARCHAR(100) | UNIQUE, NOT NULL | Nombre de la categoría |
| activo | BOOLEAN | DEFAULT TRUE | Estado |

---

#### Tabla: `marca`

Marcas de producto (Nike, Adidas, etc.).

| Columna | Tipo | Restricción | Descripción |
|---------|------|-------------|-------------|
| id | INTEGER | PK, AUTOINCREMENT | Identificador único |
| nombre | VARCHAR(100) | UNIQUE, NOT NULL | Nombre de la marca |
| activo | BOOLEAN | DEFAULT TRUE | Estado |

---

#### Tabla: `producto`

Definición general de productos.

| Columna | Tipo | Restricción | Descripción |
|---------|------|-------------|-------------|
| id | INTEGER | PK, AUTOINCREMENT | Identificador único |
| nombre | VARCHAR(200) | NOT NULL | Nombre del producto |
| descripcion | TEXT | | Descripción del producto |
| codigo_interno | VARCHAR(50) | UNIQUE, NOT NULL | Código interno (generado o manual) |
| tipo_producto_id | INTEGER | FK → tipo_producto.id, NULL | Tipo de producto |
| categoria_id | INTEGER | FK → categoria.id, NULL | Categoría |
| marca_id | INTEGER | FK → marca.id, NULL | Marca |
| activo | BOOLEAN | DEFAULT TRUE | Eliminación lógica |
| created_at | DATETIME | NOT NULL | Fecha de creación |
| updated_at | DATETIME | NOT NULL | Última modificación |

---

#### Tabla: `variante_producto`

Variantes específicas de un producto. Todo producto debe tener al menos una variante "Default".

| Columna | Tipo | Restricción | Descripción |
|---------|------|-------------|-------------|
| id | INTEGER | PK, AUTOINCREMENT | Identificador único |
| producto_id | INTEGER | FK → producto.id, NOT NULL | Producto padre |
| nombre | VARCHAR(200) | NOT NULL | Nombre de la variante (ej: "Talla S Negra", "Default") |
| sku | VARCHAR(50) | UNIQUE, NULL | Stock Keeping Unit |
| atributos | JSON | | Atributos flexibles: {"talla": "S", "color": "Negro"} |
| es_default | BOOLEAN | DEFAULT FALSE | TRUE si es la variante por defecto |
| activo | BOOLEAN | DEFAULT TRUE | Estado |
| created_at | DATETIME | NOT NULL | Fecha de creación |
| updated_at | DATETIME | NOT NULL | Última modificación |

Restricción: UNIQUE(producto_id, nombre)

**NOTA:** La columna `atributos` (JSON) permite flexibilidad para distintos rubros: tallas para ropa, medidas para llantas, presentaciones para abarrotes, etc. SQLite soporta JSON nativo desde v3.38. Al crear un producto se genera automáticamente una variante con `nombre = "Default"` y `es_default = TRUE`.

---

#### Tabla: `codigo_barras`

Códigos de barras asociados a variantes. Un producto puede tener múltiples códigos.

| Columna | Tipo | Restricción | Descripción |
|---------|------|-------------|-------------|
| id | INTEGER | PK, AUTOINCREMENT | Identificador único |
| variante_id | INTEGER | FK → variante_producto.id, NOT NULL | Variante asociada |
| codigo | VARCHAR(100) | UNIQUE, NOT NULL | Código de barras |
| principal | BOOLEAN | DEFAULT FALSE | Código principal de la variante |
| created_at | DATETIME | NOT NULL | Fecha de registro |

---

#### Tabla: `precio_producto`

Precios versionados por variante. Cada cambio crea un nuevo registro.

| Columna | Tipo | Restricción | Descripción |
|---------|------|-------------|-------------|
| id | INTEGER | PK, AUTOINCREMENT | Identificador único |
| variante_id | INTEGER | FK → variante_producto.id, NOT NULL | Variante asociada |
| precio_compra | DECIMAL(12,2) | NULL | Solo visible para administrador |
| precio_contado | DECIMAL(12,2) | NOT NULL | Precio de venta de contado |
| precio_credito | DECIMAL(12,2) | NULL | Precio de venta a crédito |
| porcentaje_ganancia | DECIMAL(5,2) | NULL | Porcentaje usado para calcular precio |
| vigente | BOOLEAN | DEFAULT TRUE | Solo uno vigente por variante |
| usuario_id | INTEGER | FK → usuario.id, NOT NULL | Quién registró el precio |
| motivo_cambio | VARCHAR(200) | | Motivo de la modificación |
| created_at | DATETIME | NOT NULL | Fecha de registro |

**NOTA:** Al crear un nuevo registro de precio, el anterior se marca como `vigente = FALSE`. Esto genera el historial de precios automáticamente sin tabla adicional.

---

### MÓDULO 4 — Inventario

---

#### Tabla: `inventario`

Stock actual por variante. Un registro por variante de producto.

| Columna | Tipo | Restricción | Descripción |
|---------|------|-------------|-------------|
| id | INTEGER | PK, AUTOINCREMENT | Identificador único |
| variante_id | INTEGER | FK → variante_producto.id, UNIQUE, NOT NULL | Variante asociada (1:1) |
| stock_actual | INTEGER | NOT NULL, DEFAULT 0 | Cantidad en existencia |
| stock_minimo | INTEGER | DEFAULT 0 | Umbral para alerta de stock bajo |
| updated_at | DATETIME | NOT NULL | Última actualización |

---

#### Tabla: `movimiento_inventario`

Historial completo de entradas, salidas y ajustes de inventario.

| Columna | Tipo | Restricción | Descripción |
|---------|------|-------------|-------------|
| id | INTEGER | PK, AUTOINCREMENT | Identificador único |
| inventario_id | INTEGER | FK → inventario.id, NOT NULL | Inventario afectado |
| variante_id | INTEGER | FK → variante_producto.id, NOT NULL | Variante (redundancia para consultas rápidas) |
| tipo_movimiento | VARCHAR(30) | NOT NULL | entrada_compra, entrada_ajuste, salida_venta, salida_merma, salida_sin_stock, ajuste_manual, entrada_devolucion |
| cantidad | INTEGER | NOT NULL | Positivo = entrada, Negativo = salida |
| stock_anterior | INTEGER | NOT NULL | Stock antes del movimiento |
| stock_nuevo | INTEGER | NOT NULL | Stock después del movimiento |
| referencia_id | INTEGER | NULL | ID de venta/ajuste/devolución que originó |
| referencia_tipo | VARCHAR(30) | NULL | venta, ajuste, merma, devolucion |
| motivo | VARCHAR(200) | | Obligatorio en ajustes y mermas |
| usuario_id | INTEGER | FK → usuario.id, NOT NULL | Usuario responsable |
| autorizacion_id | INTEGER | FK → autorizacion.id, NULL | Si requirió autorización |
| fecha | DATETIME | NOT NULL | Fecha del movimiento |

---

### MÓDULO 5 — Ventas (POS)

---

#### Tabla: `venta`

Registro principal de ventas con soporte para contado y crédito.

| Columna | Tipo | Restricción | Descripción |
|---------|------|-------------|-------------|
| id | INTEGER | PK, AUTOINCREMENT | Identificador único |
| folio | VARCHAR(30) | UNIQUE, NOT NULL | Folio de venta: V-YYYYMMDD-NNNN |
| usuario_id | INTEGER | FK → usuario.id, NOT NULL | Vendedor que realiza la venta |
| cliente_id | INTEGER | FK → cliente.id, NULL | Cliente. Obligatorio si tipo = crédito |
| caja_id | INTEGER | FK → caja.id, NOT NULL | Caja donde se realizó la venta |
| tipo_venta | VARCHAR(20) | NOT NULL | contado, credito |
| estado | VARCHAR(20) | NOT NULL, DEFAULT 'en_proceso' | en_proceso, completada, parcial, liquidada, cancelada |
| subtotal | DECIMAL(12,2) | NOT NULL, DEFAULT 0 | Suma antes de descuento |
| descuento_tipo | VARCHAR(20) | NULL | porcentaje, monto_fijo |
| descuento_valor | DECIMAL(12,2) | NULL | Valor del descuento aplicado |
| descuento_monto | DECIMAL(12,2) | DEFAULT 0 | Monto real descontado (calculado) |
| total | DECIMAL(12,2) | NOT NULL, DEFAULT 0 | subtotal - descuento_monto |
| notas | TEXT | | Observaciones |
| motivo_cancelacion | VARCHAR(200) | NULL | Motivo si fue cancelada |
| fecha | DATETIME | NOT NULL | Fecha de la venta |
| created_at | DATETIME | NOT NULL | Fecha de creación |
| updated_at | DATETIME | NOT NULL | Última modificación |

**NOTA sobre folio:** El formato es `V-YYYYMMDD-NNNN`. Ejemplo: V-20250211-0001, V-20250211-0002. El consecutivo se reinicia por día.

**NOTA sobre descuentos:** Los descuentos son opcionales y se aplican al total de la venta. `descuento_tipo` indica si es porcentaje o monto fijo. `descuento_monto` almacena el monto real que se descuenta (para que no haya ambigüedad). Si no hay descuento, los campos quedan NULL/0.

---

#### Tabla: `detalle_venta`

Productos incluidos en cada venta (relación N-N entre venta y variante).

| Columna | Tipo | Restricción | Descripción |
|---------|------|-------------|-------------|
| id | INTEGER | PK, AUTOINCREMENT | Identificador único |
| venta_id | INTEGER | FK → venta.id, NOT NULL | Venta asociada |
| variante_id | INTEGER | FK → variante_producto.id, NOT NULL | Variante vendida |
| cantidad | INTEGER | NOT NULL, CHECK > 0 | Cantidad vendida |
| precio_unitario | DECIMAL(12,2) | NOT NULL | Precio al momento de la venta (congelado) |
| descuento_linea_tipo | VARCHAR(20) | NULL | porcentaje, monto_fijo (descuento por línea) |
| descuento_linea_valor | DECIMAL(12,2) | NULL | Valor del descuento por línea |
| descuento_linea_monto | DECIMAL(12,2) | DEFAULT 0 | Monto real descontado en esta línea |
| subtotal | DECIMAL(12,2) | NOT NULL | (cantidad × precio_unitario) - descuento_linea_monto |
| precio_modificado | BOOLEAN | DEFAULT FALSE | TRUE si el precio fue editado manualmente |
| sin_stock | BOOLEAN | DEFAULT FALSE | TRUE si se vendió sin stock disponible |

**NOTA:** `precio_unitario` se congela al momento de la venta. Si el precio del producto cambia después, las ventas anteriores conservan el precio original.

**NOTA sobre descuentos por línea:** Opcionalmente el vendedor puede aplicar un descuento a un producto específico dentro de la venta. Esto es independiente del descuento general de la venta.

---

### MÓDULO 6 — Pagos

---

#### Tabla: `pago`

Registro de pagos realizados. Un pago puede asociarse a una venta o ser un abono a crédito.

| Columna | Tipo | Restricción | Descripción |
|---------|------|-------------|-------------|
| id | INTEGER | PK, AUTOINCREMENT | Identificador único |
| venta_id | INTEGER | FK → venta.id, NOT NULL | Venta asociada |
| cliente_id | INTEGER | FK → cliente.id, NULL | Cliente (para abonos a crédito) |
| caja_id | INTEGER | FK → caja.id, NOT NULL | Caja donde se registró |
| tipo_pago | VARCHAR(30) | NOT NULL | pago_total, anticipo, abono |
| monto_base | DECIMAL(12,2) | NOT NULL | Monto del pago sin cargos |
| cargo_tarjeta | DECIMAL(12,2) | DEFAULT 0 | Cargo financiero por tarjeta |
| monto_total | DECIMAL(12,2) | NOT NULL | monto_base + cargo_tarjeta |
| usuario_id | INTEGER | FK → usuario.id, NOT NULL | Usuario que registró |
| fecha | DATETIME | NOT NULL | Fecha del pago |
| created_at | DATETIME | NOT NULL | Fecha de creación |

---

#### Tabla: `detalle_pago`

Desglose del pago por método. Soporta pagos mixtos.

| Columna | Tipo | Restricción | Descripción |
|---------|------|-------------|-------------|
| id | INTEGER | PK, AUTOINCREMENT | Identificador único |
| pago_id | INTEGER | FK → pago.id, NOT NULL | Pago asociado |
| metodo_pago | VARCHAR(20) | NOT NULL | efectivo, tarjeta, transferencia |
| monto | DECIMAL(12,2) | NOT NULL | Monto pagado con este método |
| con_intereses | BOOLEAN | DEFAULT FALSE | Solo aplica si método = tarjeta |
| porcentaje_cargo | DECIMAL(5,2) | NULL | Porcentaje aplicado (ej: 4.5) |
| monto_cargo | DECIMAL(12,2) | DEFAULT 0 | Cargo financiero calculado |

**NOTA sobre pago mixto:** Una venta puede tener un `pago` con múltiples registros en `detalle_pago`. Ejemplo: $500 en efectivo + $500 en tarjeta con intereses (cargo de $22.50). El cargo por tarjeta NUNCA modifica precios de productos ni saldo de crédito. Se registra como cargo financiero separado.

---

### MÓDULO 7 — Caja

---

#### Tabla: `caja`

Registro de apertura y cierre de caja. Una sola caja abierta por equipo durante la jornada.

| Columna | Tipo | Restricción | Descripción |
|---------|------|-------------|-------------|
| id | INTEGER | PK, AUTOINCREMENT | Identificador único |
| usuario_apertura_id | INTEGER | FK → usuario.id, NOT NULL | Usuario que abrió la caja |
| usuario_cierre_id | INTEGER | FK → usuario.id, NULL | Usuario que cerró la caja |
| monto_inicial | DECIMAL(12,2) | NOT NULL | Efectivo al momento de abrir |
| estado | VARCHAR(20) | NOT NULL, DEFAULT 'abierta' | abierta, cerrada |
| fecha_apertura | DATETIME | NOT NULL | Fecha y hora de apertura |
| fecha_cierre | DATETIME | NULL | Fecha y hora de cierre |
| total_efectivo_esperado | DECIMAL(12,2) | NULL | Calculado por el sistema al cierre |
| total_tarjeta_esperado | DECIMAL(12,2) | NULL | Calculado por el sistema al cierre |
| total_transferencia_esperado | DECIMAL(12,2) | NULL | Calculado por el sistema al cierre |
| total_efectivo_contado | DECIMAL(12,2) | NULL | Declarado por el usuario al cierre |
| total_tarjeta_declarado | DECIMAL(12,2) | NULL | Declarado por el usuario al cierre |
| total_transferencia_declarado | DECIMAL(12,2) | NULL | Declarado por el usuario al cierre |
| diferencia_efectivo | DECIMAL(12,2) | NULL | Sobrante (+) o Faltante (-) |
| diferencia_tarjeta | DECIMAL(12,2) | NULL | Sobrante (+) o Faltante (-) |
| diferencia_transferencia | DECIMAL(12,2) | NULL | Sobrante (+) o Faltante (-) |
| observaciones_cierre | TEXT | NULL | Notas del cierre |

**NOTA:** Solo se permite una caja abierta a la vez por equipo. El sistema debe validar que no exista otra caja con `estado = 'abierta'` antes de permitir una nueva apertura. La caja permanece abierta durante toda la jornada laboral.

---

#### Tabla: `movimiento_caja`

Registro de entradas y salidas de dinero asociadas a la caja.

| Columna | Tipo | Restricción | Descripción |
|---------|------|-------------|-------------|
| id | INTEGER | PK, AUTOINCREMENT | Identificador único |
| caja_id | INTEGER | FK → caja.id, NOT NULL | Caja asociada |
| tipo | VARCHAR(20) | NOT NULL | entrada, salida |
| metodo_pago | VARCHAR(20) | NOT NULL | efectivo, tarjeta, transferencia |
| monto | DECIMAL(12,2) | NOT NULL | Monto del movimiento |
| concepto | VARCHAR(200) | NOT NULL | Descripción del movimiento |
| origen | VARCHAR(30) | NULL | venta, abono, manual, devolucion |
| referencia_id | INTEGER | NULL | ID del pago/venta/devolución que originó |
| usuario_id | INTEGER | FK → usuario.id, NOT NULL | Usuario responsable |
| fecha | DATETIME | NOT NULL | Fecha del movimiento |

---

### MÓDULO COMPLEMENTARIO — Devoluciones y Cambios

---

#### Tabla: `devolucion`

Registro de devoluciones de productos y cambios.

| Columna | Tipo | Restricción | Descripción |
|---------|------|-------------|-------------|
| id | INTEGER | PK, AUTOINCREMENT | Identificador único |
| folio | VARCHAR(30) | UNIQUE, NOT NULL | Folio: D-YYYYMMDD-NNNN |
| venta_id | INTEGER | FK → venta.id, NOT NULL | Venta original de los productos |
| cliente_id | INTEGER | FK → cliente.id, NULL | Cliente asociado |
| caja_id | INTEGER | FK → caja.id, NOT NULL | Caja donde se procesa |
| usuario_id | INTEGER | FK → usuario.id, NOT NULL | Usuario que procesa |
| tipo | VARCHAR(20) | NOT NULL | devolucion, cambio |
| estado | VARCHAR(20) | NOT NULL, DEFAULT 'completada' | completada, cancelada |
| monto_devuelto | DECIMAL(12,2) | NOT NULL, DEFAULT 0 | Monto total devuelto al cliente |
| monto_diferencia | DECIMAL(12,2) | DEFAULT 0 | Diferencia a favor/en contra en cambios |
| metodo_reembolso | VARCHAR(20) | NULL | efectivo, credito, nota_credito |
| motivo | VARCHAR(300) | NOT NULL | Motivo de la devolución o cambio |
| autorizacion_id | INTEGER | FK → autorizacion.id, NULL | Si requirió autorización |
| notas | TEXT | | Observaciones |
| fecha | DATETIME | NOT NULL | Fecha de la operación |
| created_at | DATETIME | NOT NULL | Fecha de creación |

**NOTA sobre tipo de movimiento:**
- `devolucion`: El cliente regresa productos y recibe reembolso (efectivo, crédito o nota de crédito).
- `cambio`: El cliente regresa productos y los intercambia por otros. Si hay diferencia de precio, se gestiona el saldo.

---

#### Tabla: `detalle_devolucion`

Productos devueltos o intercambiados.

| Columna | Tipo | Restricción | Descripción |
|---------|------|-------------|-------------|
| id | INTEGER | PK, AUTOINCREMENT | Identificador único |
| devolucion_id | INTEGER | FK → devolucion.id, NOT NULL | Devolución asociada |
| detalle_venta_id | INTEGER | FK → detalle_venta.id, NOT NULL | Línea de venta original |
| variante_id | INTEGER | FK → variante_producto.id, NOT NULL | Variante devuelta |
| cantidad | INTEGER | NOT NULL, CHECK > 0 | Cantidad devuelta |
| precio_unitario | DECIMAL(12,2) | NOT NULL | Precio al que se vendió (para calcular reembolso) |
| subtotal_devolucion | DECIMAL(12,2) | NOT NULL | cantidad × precio_unitario |
| tipo_linea | VARCHAR(20) | NOT NULL | salida (producto devuelto), entrada (producto recibido en cambio) |
| reingresa_inventario | BOOLEAN | DEFAULT TRUE | TRUE si el producto reingresa al stock |

**NOTA sobre `tipo_linea`:**
- `salida`: Producto que SALE del cliente (lo devuelve). Reingresa al inventario.
- `entrada`: Producto que ENTRA al cliente (lo recibe como cambio). Sale del inventario. Esta línea NO tiene `detalle_venta_id` ya que es un producto nuevo.

---

### MÓDULO TRANSVERSAL — Autorizaciones

---

#### Tabla: `autorizacion`

Registro formal de autorizaciones administrativas para operaciones sensibles.

| Columna | Tipo | Restricción | Descripción |
|---------|------|-------------|-------------|
| id | INTEGER | PK, AUTOINCREMENT | Identificador único |
| tipo | VARCHAR(50) | NOT NULL | exceso_credito, venta_sin_stock, cancelacion_venta, ajuste_inventario, modificacion_precio, devolucion, cambio |
| usuario_solicitante_id | INTEGER | FK → usuario.id, NOT NULL | Quién solicita |
| usuario_autorizador_id | INTEGER | FK → usuario.id, NOT NULL | Quién autoriza |
| entidad_tipo | VARCHAR(50) | NOT NULL | venta, inventario, cliente, producto, devolucion |
| entidad_id | INTEGER | NOT NULL | ID de la entidad afectada |
| motivo | VARCHAR(300) | NOT NULL | Motivo de la autorización |
| estado | VARCHAR(20) | NOT NULL | aprobada, rechazada |
| fecha | DATETIME | NOT NULL | Fecha de la autorización |

---

### MÓDULO 9 — Configuración

---

#### Tabla: `configuracion_general`

Tabla de un solo registro con la configuración global del sistema.

| Columna | Tipo | Restricción | Descripción |
|---------|------|-------------|-------------|
| id | INTEGER | PK, AUTOINCREMENT | Siempre 1 registro |
| nombre_negocio | VARCHAR(200) | NOT NULL | Nombre del negocio |
| direccion | TEXT | | Dirección del negocio |
| telefono | VARCHAR(20) | | Teléfono |
| rfc | VARCHAR(20) | NULL | RFC (opcional) |
| logo_path | VARCHAR(500) | NULL | Ruta al archivo de logo |
| mensaje_ticket | TEXT | | Leyenda que aparece en tickets |
| porcentaje_cargo_tarjeta | DECIMAL(5,2) | DEFAULT 4.50 | Porcentaje de cargo por tarjeta |
| cargo_tarjeta_activo | BOOLEAN | DEFAULT TRUE | Habilita/deshabilita cargo tarjeta |
| permitir_exceder_credito | BOOLEAN | DEFAULT TRUE | Permite exceder crédito con autorización |
| limite_credito_defecto | DECIMAL(12,2) | DEFAULT 0 | Límite de crédito por defecto |
| anticipo_minimo | DECIMAL(12,2) | NULL | Anticipo mínimo obligatorio (opcional) |
| permitir_stock_negativo | BOOLEAN | DEFAULT FALSE | Permite stock negativo |
| permitir_inventario_desde_pos | BOOLEAN | DEFAULT TRUE | Permite agregar inventario desde POS |
| requerir_autorizacion_sin_stock | BOOLEAN | DEFAULT TRUE | Requiere autorización para vender sin stock |
| permitir_descuento_venta | BOOLEAN | DEFAULT TRUE | Habilita descuentos en ventas |
| descuento_maximo_porcentaje | DECIMAL(5,2) | NULL | Límite máximo de descuento (%) |
| permitir_devoluciones | BOOLEAN | DEFAULT TRUE | Habilita devoluciones |
| dias_limite_devolucion | INTEGER | NULL | Días máximos para aceptar devolución |
| version_db | VARCHAR(20) | NOT NULL | Versión de la BD (compatibilidad de respaldos) |
| updated_at | DATETIME | NOT NULL | Última modificación |

---

## 4. Índices Recomendados

### Búsquedas frecuentes
```sql
CREATE INDEX idx_producto_codigo ON producto(codigo_interno);
CREATE INDEX idx_variante_sku ON variante_producto(sku);
CREATE INDEX idx_variante_producto ON variante_producto(producto_id);
CREATE INDEX idx_codigo_barras ON codigo_barras(codigo);
CREATE INDEX idx_cliente_nombre ON cliente(nombre);
CREATE INDEX idx_cliente_telefono ON cliente(telefono);
```

### Filtros de reportes
```sql
CREATE INDEX idx_venta_fecha ON venta(fecha);
CREATE INDEX idx_venta_estado ON venta(estado);
CREATE INDEX idx_venta_tipo ON venta(tipo_venta);
CREATE INDEX idx_venta_cliente ON venta(cliente_id);
CREATE INDEX idx_venta_folio ON venta(folio);
CREATE INDEX idx_pago_fecha ON pago(fecha);
CREATE INDEX idx_pago_venta ON pago(venta_id);
CREATE INDEX idx_mov_inventario_fecha ON movimiento_inventario(fecha);
CREATE INDEX idx_mov_inventario_tipo ON movimiento_inventario(tipo_movimiento);
CREATE INDEX idx_mov_inventario_variante ON movimiento_inventario(variante_id);
CREATE INDEX idx_mov_credito_cliente ON movimiento_credito(cliente_id);
CREATE INDEX idx_mov_caja_caja ON movimiento_caja(caja_id);
```

### Precio vigente
```sql
CREATE INDEX idx_precio_vigente ON precio_producto(variante_id, vigente);
```

### Inventario
```sql
CREATE INDEX idx_inventario_stock ON inventario(stock_actual);
CREATE INDEX idx_inventario_variante ON inventario(variante_id);
```

### Devoluciones
```sql
CREATE INDEX idx_devolucion_venta ON devolucion(venta_id);
CREATE INDEX idx_devolucion_fecha ON devolucion(fecha);
CREATE INDEX idx_devolucion_folio ON devolucion(folio);
CREATE INDEX idx_detalle_devolucion ON detalle_devolucion(devolucion_id);
```

---

## 5. Flujos de Datos Principales

### 5.1 Flujo de Venta de Contado

```
1. Crear venta (estado: en_proceso, tipo: contado)
2. Agregar productos → detalle_venta (precio congelado)
3. Aplicar descuento (opcional) → actualizar venta
4. Registrar pago → pago + detalle_pago
5. Finalizar venta → estado: completada
6. Generar movimientos:
   → movimiento_inventario (salida_venta por cada línea)
   → movimiento_caja (entrada por pago)
   → Actualizar inventario.stock_actual
7. Generar ticket dinámico (no se almacena)
```

### 5.2 Flujo de Venta a Crédito

```
1. Crear venta (estado: en_proceso, tipo: credito)
2. Asociar cliente (obligatorio)
3. Validar crédito disponible
   → Si excede: solicitar autorización → tabla autorizacion
4. Agregar productos → detalle_venta
5. Registrar anticipo (opcional) → pago + movimiento_credito
6. Finalizar venta → estado: completada
7. Generar movimientos:
   → movimiento_credito (cargo al cliente)
   → movimiento_inventario (salida_venta)
   → movimiento_caja (si hubo anticipo)
   → Actualizar cliente.saldo_credito
   → Actualizar inventario.stock_actual
```

### 5.3 Flujo de Devolución

```
1. Buscar venta original por folio
2. Crear devolución (tipo: devolucion)
3. Seleccionar productos a devolver → detalle_devolucion (tipo_linea: salida)
4. Calcular monto a devolver
5. Registrar reembolso:
   → Si efectivo: movimiento_caja (salida)
   → Si crédito: movimiento_credito (abono al cliente)
6. Reingresar productos al inventario:
   → movimiento_inventario (entrada_devolucion)
   → Actualizar inventario.stock_actual
```

### 5.4 Flujo de Cambio

```
1. Buscar venta original por folio
2. Crear devolución (tipo: cambio)
3. Registrar productos devueltos → detalle_devolucion (tipo_linea: salida)
4. Registrar productos nuevos → detalle_devolucion (tipo_linea: entrada)
5. Calcular diferencia:
   → A favor del cliente: reembolsar diferencia
   → En contra: cobrar diferencia → pago adicional
6. Actualizar inventario:
   → entrada_devolucion (productos devueltos)
   → salida_venta (productos nuevos entregados)
```

### 5.5 Flujo de Caja

```
1. Abrir caja → monto_inicial (estado: abierta)
2. Durante la jornada:
   → Ventas generan entradas automáticas
   → Abonos generan entradas automáticas
   → Devoluciones generan salidas
   → Retiros/gastos: salidas manuales
3. Cuadre:
   → Sistema calcula esperados por método
   → Usuario declara conteo real
   → Calcular diferencias
4. Cerrar caja → estado: cerrada
```

---

## 6. Resumen de Tablas

| # | Tabla | Módulo | Registros Estimados |
|---|-------|--------|---------------------|
| 1 | rol | Auth | 2-5 (semilla) |
| 2 | permiso | Auth | 20-40 (semilla) |
| 3 | rol_permiso | Auth | 40-100 (semilla) |
| 4 | usuario | Auth | 2-10 |
| 5 | sesion | Auth | Crecimiento diario |
| 6 | bitacora_autenticacion | Auth | Crecimiento diario |
| 7 | cliente | Clientes | 50-5,000 |
| 8 | movimiento_credito | Clientes | Alto volumen |
| 9 | tipo_producto | Productos | 5-20 |
| 10 | categoria | Productos | 10-50 |
| 11 | marca | Productos | 10-100 |
| 12 | producto | Productos | 50-10,000 |
| 13 | variante_producto | Productos | 100-50,000 |
| 14 | codigo_barras | Productos | 100-50,000 |
| 15 | precio_producto | Productos | Alto (histórico) |
| 16 | inventario | Inventario | = número de variantes |
| 17 | movimiento_inventario | Inventario | Muy alto volumen |
| 18 | venta | Ventas | Alto volumen |
| 19 | detalle_venta | Ventas | Muy alto volumen |
| 20 | pago | Pagos | = ventas + abonos |
| 21 | detalle_pago | Pagos | >= pagos |
| 22 | caja | Caja | 1-2 por día |
| 23 | movimiento_caja | Caja | Alto volumen |
| 24 | devolucion | Devoluciones | Moderado |
| 25 | detalle_devolucion | Devoluciones | Moderado |
| 26 | autorizacion | Transversal | Moderado |
| 27 | configuracion_general | Config | 1 registro |

**Total: 27 tablas**

---

## 7. Decisiones de Diseño

### 7.1 Inventario a nivel de Variante
El stock se gestiona por variante, no por producto general. Esto permite que un producto como "Playera Nike" tenga stock independiente para "Talla S Negra" y "Talla M Blanca".

### 7.2 Variante "Default" obligatoria
Todo producto tiene al menos una variante con `nombre = "Default"` y `es_default = TRUE`. Esto simplifica las consultas ya que todas las operaciones (precios, inventario, ventas) siempre apuntan a una variante.

### 7.3 Precios versionados
Cada cambio de precio crea un nuevo registro en `precio_producto` y desactiva el anterior (`vigente = FALSE`). Esto genera historial automáticamente.

### 7.4 Saldo de crédito desnormalizado
`cliente.saldo_credito` es un campo calculado almacenado. Se actualiza con cada venta a crédito, pago, devolución o cancelación. Siempre es recalculable desde `movimiento_credito`.

### 7.5 Cargo por tarjeta separado
El cargo por tarjeta NUNCA modifica precios de productos ni saldo de crédito. Se registra como cargo financiero en `detalle_pago.monto_cargo`.

### 7.6 Descuentos duales (venta y línea)
Se soportan dos niveles de descuento: a nivel de venta (descuento global) y a nivel de línea (descuento por producto). Ambos son opcionales y configurables.

### 7.7 Caja única por jornada
Solo una caja puede estar abierta a la vez. La caja permanece abierta durante toda la jornada y es operada por una sola persona.

### 7.8 Tickets dinámicos
Los tickets no se almacenan en la base de datos. Se generan dinámicamente a partir de los datos de la venta, permitiendo reimprimir en cualquier momento.

### 7.9 Devoluciones y cambios unificados
Se usa una sola tabla `devolucion` con campo `tipo` que distingue entre devolución (reembolso) y cambio (intercambio). El `detalle_devolucion` usa `tipo_linea` para diferenciar productos que salen del cliente vs productos que entran como reemplazo.

### 7.10 Autorizaciones polimórficas
Una sola tabla `autorizacion` cubre todos los tipos usando `tipo` + `entidad_tipo` + `entidad_id` como referencia polimórfica.

### 7.11 Atributos JSON en variantes
Permite flexibilidad para distintos rubros sin crear tablas específicas por tipo de negocio (tallas, medidas, presentaciones, etc.).

### 7.12 Folio con formato estándar
Formato V-YYYYMMDD-NNNN para ventas y D-YYYYMMDD-NNNN para devoluciones, con consecutivo que reinicia diariamente.
