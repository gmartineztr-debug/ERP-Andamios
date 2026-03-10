# utils/database.py
# Conexión centralizada a Supabase

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
import os

load_dotenv()


def get_connection():
    """Retorna una conexión a la base de datos"""
    return psycopg2.connect(
        host=os.getenv('SUPABASE_HOST'),
        port=os.getenv('SUPABASE_PORT'),
        database=os.getenv('SUPABASE_DB'),
        user=os.getenv('SUPABASE_USER'),
        password=os.getenv('SUPABASE_PASSWORD')
    )


# ================================================
# CLIENTES
# ================================================

def get_clientes(solo_activos=True):
    """Retorna lista de clientes"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    query = "SELECT * FROM crm_clientes"
    if solo_activos:
        query += " WHERE activo = TRUE"
    query += " ORDER BY razon_social"

    cur.execute(query)
    clientes = cur.fetchall()
    cur.close()
    conn.close()
    return clientes


def get_cliente_by_id(cliente_id):
    """Retorna un cliente por su ID"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM crm_clientes WHERE id = %s", (cliente_id,))
    cliente = cur.fetchone()
    cur.close()
    conn.close()
    return cliente


def crear_cliente(datos):
    """Crea un nuevo cliente"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO crm_clientes
        (razon_social, rfc, contacto, telefono, email, direccion, tipo_cliente, limite_credito)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (
        datos['razon_social'],
        datos['rfc'],
        datos['contacto'],
        datos['telefono'],
        datos['email'],
        datos['direccion'],
        datos['tipo_cliente'],
        datos['limite_credito']
    ))
    nuevo_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return nuevo_id


def actualizar_cliente(cliente_id, datos):
    """Actualiza un cliente existente"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE crm_clientes SET
            razon_social   = %s,
            rfc            = %s,
            contacto       = %s,
            telefono       = %s,
            email          = %s,
            direccion      = %s,
            tipo_cliente   = %s,
            limite_credito = %s
        WHERE id = %s
    """, (
        datos['razon_social'],
        datos['rfc'],
        datos['contacto'],
        datos['telefono'],
        datos['email'],
        datos['direccion'],
        datos['tipo_cliente'],
        datos['limite_credito'],
        cliente_id
    ))
    conn.commit()
    cur.close()
    conn.close()


# ================================================
# PRODUCTOS
# ================================================

def get_productos(solo_activos=True):
    """Retorna lista de productos"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    query = """
        SELECT p.*, 
               COALESCE(i.cantidad_disponible, 0) as cantidad_disponible,
               COALESCE(i.cantidad_rentada, 0) as cantidad_rentada,
               COALESCE(i.cantidad_mantenimiento, 0) as cantidad_mantenimiento,
               COALESCE(i.cantidad_chatarra, 0) as cantidad_chatarra,
               COALESCE(i.stock_minimo, 0) as stock_minimo
        FROM cat_productos p
        LEFT JOIN inv_master i ON p.id = i.producto_id
    """
    if solo_activos:
        query += " WHERE p.activo = TRUE"
    query += " ORDER BY p.nombre"

    cur.execute(query)
    productos = cur.fetchall()
    cur.close()
    conn.close()
    return productos

# ================================================
# PRODUCTOS - CRUD
# ================================================

def get_producto_by_id(producto_id):
    """Retorna un producto por su ID"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT p.*, i.cantidad_disponible, i.cantidad_rentada,
               i.cantidad_mantenimiento, i.cantidad_chatarra, i.stock_minimo
        FROM cat_productos p
        LEFT JOIN inv_master i ON p.id = i.producto_id
        WHERE p.id = %s
    """, (producto_id,))
    producto = cur.fetchone()
    cur.close()
    conn.close()
    return producto


def crear_producto(datos):
    """Crea un nuevo producto y su registro de inventario"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        # Insertar producto
        cur.execute("""
            INSERT INTO cat_productos
            (codigo, nombre, descripcion, unidad, precio_renta_dia,
             precio_venta, peso_kg, se_fabrica, sistema)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            datos['codigo'],
            datos['nombre'],
            datos['descripcion'],
            datos['unidad'],
            datos['precio_renta_dia'],
            datos['precio_venta'],
            datos['peso_kg'],
            datos['se_fabrica'],
            datos['sistema']
        ))
        nuevo_id = cur.fetchone()[0]

        # Crear registro en inventario automáticamente
        cur.execute("""
            INSERT INTO inv_master (producto_id, stock_minimo)
            VALUES (%s, %s)
        """, (nuevo_id, datos['stock_minimo']))

        conn.commit()
        return nuevo_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()


def actualizar_producto(producto_id, datos):
    """Actualiza un producto existente"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE cat_productos SET
                codigo          = %s,
                nombre          = %s,
                descripcion     = %s,
                unidad          = %s,
                precio_renta_dia = %s,
                precio_venta    = %s,
                peso_kg         = %s,
                se_fabrica      = %s,
                sistema         = %s,
                activo          = %s
            WHERE id = %s
        """, (
            datos['codigo'],
            datos['nombre'],
            datos['descripcion'],
            datos['unidad'],
            datos['precio_renta_dia'],
            datos['precio_venta'],
            datos['peso_kg'],
            datos['se_fabrica'],
            datos['sistema'],
            datos['activo'],
            producto_id
        ))

        # Actualizar stock mínimo en inventario
        cur.execute("""
            UPDATE inv_master SET stock_minimo = %s
            WHERE producto_id = %s
        """, (datos['stock_minimo'], producto_id))

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()
        
# ================================================
# COTIZACIONES
# ================================================

def generar_folio_cotizacion():
    """Genera el siguiente folio de cotización"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT generar_folio_cotizacion()")
    folio = cur.fetchone()[0]
    cur.close()
    conn.close()
    return folio


def crear_cotizacion(datos, items):
    """Crea una cotización con sus items"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO crm_cotizaciones
            (folio, cliente_id, obra_id, tipo_operacion, estatus,
             tipo_flete, distancia_km, tarifa_flete, monto_flete,
             subtotal, aplica_iva, iva, total, dias_renta, notas)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            datos['folio'],
            datos['cliente_id'],
            datos.get('obra_id'),
            datos['tipo_operacion'],
            datos['estatus'],
            datos['tipo_flete'],
            datos['distancia_km'],
            datos['tarifa_flete'],
            datos['monto_flete'],
            datos['subtotal'],
            datos['aplica_iva'],
            datos['iva'],
            datos['total'],
            datos['dias_renta'],
            datos['notas']
        ))
        cotizacion_id = cur.fetchone()[0]

        for item in items:
            cur.execute("""
                INSERT INTO crm_cotizacion_items
                (cotizacion_id, producto_id, cantidad, precio_unitario, subtotal)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                cotizacion_id,
                item['producto_id'],
                item['cantidad'],
                item['precio_unitario'],
                item['subtotal']
            ))

        conn.commit()
        return cotizacion_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()


def get_cotizaciones(estatus=None):
    """Retorna lista de cotizaciones"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    query = """
        SELECT c.*, cl.razon_social as cliente_nombre
        FROM crm_cotizaciones c
        JOIN crm_clientes cl ON c.cliente_id = cl.id
    """
    if estatus:
        query += " WHERE c.estatus = %s"
        cur.execute(query + " ORDER BY c.created_at DESC", (estatus,))
    else:
        cur.execute(query + " ORDER BY c.created_at DESC")
    cotizaciones = cur.fetchall()
    cur.close()
    conn.close()
    return cotizaciones


def get_cotizacion_detalle(cotizacion_id):
    """Retorna una cotización con sus items"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("""
        SELECT c.*, cl.razon_social as cliente_nombre, cl.rfc
        FROM crm_cotizaciones c
        JOIN crm_clientes cl ON c.cliente_id = cl.id
        WHERE c.id = %s
    """, (cotizacion_id,))
    cotizacion = cur.fetchone()

    cur.execute("""
        SELECT ci.*, p.nombre as producto_nombre, p.codigo, p.peso_kg
        FROM crm_cotizacion_items ci
        JOIN cat_productos p ON ci.producto_id = p.id
        WHERE ci.cotizacion_id = %s
    """, (cotizacion_id,))
    items = cur.fetchall()

    cur.close()
    conn.close()
    return cotizacion, items


def actualizar_estatus_cotizacion(cotizacion_id, estatus):
    """Actualiza el estatus de una cotización"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE crm_cotizaciones
        SET estatus = %s, updated_at = NOW()
        WHERE id = %s
    """, (estatus, cotizacion_id))
    conn.commit()
    cur.close()
    conn.close()
    
# ================================================
# OBRAS
# ================================================

def generar_folio_obra():
    """Genera el siguiente folio de obra"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT generar_folio_obra()")
    folio = cur.fetchone()[0]
    cur.close()
    conn.close()
    return folio


def crear_obra(datos):
    """Crea una nueva obra"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO crm_obras
            (folio_obra, cliente_id, nombre_proyecto, direccion_obra,
             fecha_inicio, fecha_fin_estimada, responsable, notas)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            datos['folio_obra'],
            datos['cliente_id'],
            datos['nombre_proyecto'],
            datos['direccion_obra'],
            datos['fecha_inicio'],
            datos['fecha_fin_estimada'],
            datos['responsable'],
            datos['notas']
        ))
        nuevo_id = cur.fetchone()[0]
        conn.commit()
        return nuevo_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()


def get_obras(estatus=None):
    """Retorna lista de obras"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    query = """
        SELECT o.*, c.razon_social as cliente_nombre
        FROM crm_obras o
        JOIN crm_clientes c ON o.cliente_id = c.id
    """
    if estatus:
        query += " WHERE o.estatus = %s"
        cur.execute(query + " ORDER BY o.created_at DESC", (estatus,))
    else:
        cur.execute(query + " ORDER BY o.created_at DESC")
    obras = cur.fetchall()
    cur.close()
    conn.close()
    return obras


def get_obra_by_id(obra_id):
    """Retorna una obra por su ID"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT o.*, c.razon_social as cliente_nombre
        FROM crm_obras o
        JOIN crm_clientes c ON o.cliente_id = c.id
        WHERE o.id = %s
    """, (obra_id,))
    obra = cur.fetchone()
    cur.close()
    conn.close()
    return obra


def actualizar_estatus_obra(obra_id, estatus):
    """Actualiza el estatus de una obra"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE crm_obras
        SET estatus = %s, updated_at = NOW()
        WHERE id = %s
    """, (estatus, obra_id))
    conn.commit()
    cur.close()
    conn.close()


def get_contratos_por_obra(obra_id):
    """Retorna contratos asociados a una obra"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT *
        FROM ops_contratos
        WHERE obra_id = %s
        ORDER BY created_at DESC
    """, (obra_id,))
    contratos = cur.fetchall()
    cur.close()
    conn.close()
    return contratos


def actualizar_total_facturado_obra(obra_id):
    """Recalcula el total facturado de una obra"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE crm_obras
        SET total_facturado = (
            SELECT COALESCE(SUM(monto_total), 0)
            FROM ops_contratos
            WHERE obra_id = %s
            AND estatus != 'cancelado'
        ),
        updated_at = NOW()
        WHERE id = %s
    """, (obra_id, obra_id))
    conn.commit()
    cur.close()
    conn.close()
    
def get_obras_por_cliente(cliente_id):
    """Retorna obras activas de un cliente específico"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT id, folio_obra, nombre_proyecto
        FROM crm_obras
        WHERE cliente_id = %s
        AND estatus = 'activa'
        ORDER BY created_at DESC
    """, (cliente_id,))
    obras = cur.fetchall()
    cur.close()
    conn.close()
    return obras

# ================================================
# CONTRATOS
# ================================================

def generar_folio_contrato():
    """Genera el siguiente folio de contrato"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT generar_folio_contrato()")
    folio = cur.fetchone()[0]
    cur.close()
    conn.close()
    return folio


def get_cotizaciones_aprobadas():
    """Retorna cotizaciones aprobadas sin contrato"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT c.*, cl.razon_social as cliente_nombre
        FROM crm_cotizaciones c
        JOIN crm_clientes cl ON c.cliente_id = cl.id
        WHERE c.estatus = 'aprobada'
        AND c.id NOT IN (
            SELECT cotizacion_id FROM ops_contratos
            WHERE cotizacion_id IS NOT NULL
        )
        ORDER BY c.created_at DESC
    """)
    cotizaciones = cur.fetchall()
    cur.close()
    conn.close()
    return cotizaciones


def crear_contrato(datos, items):
    """Crea un contrato con sus items"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO ops_contratos
            (folio, cotizacion_id, obra_id, cliente_id, tipo_contrato, estatus,
             fecha_contrato, fecha_inicio, fecha_fin, dias_renta,
             subtotal, monto_flete, iva, monto_total,
             anticipo_porcentaje, anticipo_requerido, anticipo_pagado,
             anticipo_referencia, anticipo_fecha_pago, anticipo_estatus,
             pagare_numero, pagare_monto, pagare_firmante,
             pagare_fecha_vencimiento, pagare_firmado,
             contrato_origen_id, notas)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
        """, (
            datos['folio'],
            datos.get('cotizacion_id'),
            datos.get('obra_id'),
            datos['cliente_id'],
            datos['tipo_contrato'],
            datos['estatus'],
            datos['fecha_contrato'],
            datos['fecha_inicio'],
            datos['fecha_fin'],
            datos['dias_renta'],
            datos['subtotal'],
            datos['monto_flete'],
            datos['iva'],
            datos['monto_total'],
            datos['anticipo_porcentaje'],
            datos['anticipo_requerido'],
            datos['anticipo_pagado'],
            datos.get('anticipo_referencia'),
            datos.get('anticipo_fecha_pago'),
            datos['anticipo_estatus'],
            datos.get('pagare_numero'),
            datos['pagare_monto'],
            datos.get('pagare_firmante'),
            datos.get('pagare_fecha_vencimiento'),
            datos['pagare_firmado'],
            datos.get('contrato_origen_id'),
            datos.get('notas')
        ))
        contrato_id = cur.fetchone()[0]

        for item in items:
            cur.execute("""
                INSERT INTO ops_contrato_items
                (contrato_id, producto_id, cantidad, precio_unitario, subtotal)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                contrato_id,
                item['producto_id'],
                item['cantidad'],
                item['precio_unitario'],
                item['subtotal']
            ))

        # Actualizar estatus cotización a 'en_revision'
        if datos.get('cotizacion_id'):
            cur.execute("""
                UPDATE crm_cotizaciones
                SET estatus = 'en_revision', updated_at = NOW()
                WHERE id = %s
            """, (datos['cotizacion_id'],))

        conn.commit()
        return contrato_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()


def get_contratos(estatus=None):
    """Retorna lista de contratos"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    query = """
        SELECT ct.*, cl.razon_social as cliente_nombre,
               o.nombre_proyecto as obra_nombre,
               o.folio_obra
        FROM ops_contratos ct
        JOIN crm_clientes cl ON ct.cliente_id = cl.id
        LEFT JOIN crm_obras o ON ct.obra_id = o.id
    """
    if estatus:
        query += " WHERE ct.estatus = %s"
        cur.execute(query + " ORDER BY ct.created_at DESC", (estatus,))
    else:
        cur.execute(query + " ORDER BY ct.created_at DESC")
    contratos = cur.fetchall()
    cur.close()
    conn.close()
    return contratos


def get_contrato_detalle(contrato_id):
    """Retorna contrato con sus items"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("""
        SELECT ct.*, cl.razon_social as cliente_nombre, cl.rfc,
               o.nombre_proyecto as obra_nombre, o.folio_obra,
               cot.folio as cotizacion_folio
        FROM ops_contratos ct
        JOIN crm_clientes cl ON ct.cliente_id = cl.id
        LEFT JOIN crm_obras o ON ct.obra_id = o.id
        LEFT JOIN crm_cotizaciones cot ON ct.cotizacion_id = cot.id
        WHERE ct.id = %s
    """, (contrato_id,))
    contrato = cur.fetchone()

    cur.execute("""
        SELECT ci.*, p.nombre as producto_nombre, p.codigo
        FROM ops_contrato_items ci
        JOIN cat_productos p ON ci.producto_id = p.id
        WHERE ci.contrato_id = %s
    """, (contrato_id,))
    items = cur.fetchall()

    cur.close()
    conn.close()
    return contrato, items


def actualizar_estatus_contrato(contrato_id, estatus):
    """Actualiza estatus de un contrato"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE ops_contratos
        SET estatus = %s, updated_at = NOW()
        WHERE id = %s
    """, (estatus, contrato_id))
    conn.commit()
    cur.close()
    conn.close()


def registrar_anticipo_pago(contrato_id, monto, referencia, fecha_pago):
    """Registra el pago del anticipo"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE ops_contratos SET
                anticipo_pagado     = %s,
                anticipo_referencia = %s,
                anticipo_fecha_pago = %s,
                anticipo_estatus    = CASE
                    WHEN %s >= anticipo_requerido THEN 'completo'
                    WHEN %s > 0 THEN 'parcial'
                    ELSE 'pendiente'
                END,
                updated_at = NOW()
            WHERE id = %s
        """, (monto, referencia, fecha_pago, monto, monto, contrato_id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()


def asignar_obra_contrato(contrato_id, obra_id):
    """Asigna una obra a un contrato existente"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE ops_contratos
        SET obra_id = %s, updated_at = NOW()
        WHERE id = %s
    """, (obra_id, contrato_id))
    conn.commit()
    cur.close()
    conn.close()
    
# ================================================
# HOJAS DE SALIDA
# ================================================

def generar_folio_salida():
    """Genera el siguiente folio de hoja de salida"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT generar_folio_salida()")
    folio = cur.fetchone()[0]
    cur.close()
    conn.close()
    return folio


def get_contratos_sin_hs_completa():
    """Retorna contratos activos con entregas pendientes"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT ct.*, cl.razon_social as cliente_nombre,
               cl.telefono as cliente_telefono,
               o.nombre_proyecto as obra_nombre,
               o.folio_obra, o.direccion_obra
        FROM ops_contratos ct
        JOIN crm_clientes cl ON ct.cliente_id = cl.id
        LEFT JOIN crm_obras o ON ct.obra_id = o.id
        WHERE ct.estatus = 'activo'
        ORDER BY ct.fecha_inicio ASC
    """)
    contratos = cur.fetchall()
    cur.close()
    conn.close()
    return contratos


def get_cantidad_enviada_por_contrato(contrato_id, producto_id):
    """Retorna cantidad ya enviada de un producto en un contrato"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT COALESCE(SUM(si.cantidad), 0)
        FROM inv_salida_items si
        JOIN inv_salidas s ON si.salida_id = s.id
        WHERE s.contrato_id = %s
        AND si.producto_id = %s
        AND s.estatus != 'cancelada'
    """, (contrato_id, producto_id))
    cantidad = cur.fetchone()[0]
    cur.close()
    conn.close()
    return int(cantidad)


def crear_hoja_salida(datos, items):
    """Crea una hoja de salida con sus items"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        peso_total = sum(i['peso_total'] for i in items)
        cur.execute("""
            INSERT INTO inv_salidas
            (folio, contrato_id, cliente_id, obra_id,
             chofer, observaciones, estatus, fecha_salida,
             peso_total, contacto_entrega, telefono_entrega)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            datos['folio'],
            datos['contrato_id'],
            datos['cliente_id'],
            datos.get('obra_id'),
            datos.get('chofer'),
            datos.get('observaciones'),
            datos['estatus'],
            datos['fecha_salida'],
            peso_total,
            datos.get('contacto_entrega'),
            datos.get('telefono_entrega')
        ))
        salida_id = cur.fetchone()[0]

        for item in items:
            cur.execute("""
                INSERT INTO inv_salida_items
                (salida_id, producto_id, cantidad, peso_unitario, peso_total)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                salida_id,
                item['producto_id'],
                item['cantidad'],
                item['peso_unitario'],
                item['peso_total']
            ))

        conn.commit()
        return salida_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()

def get_hojas_salida(contrato_id=None):
    """Retorna hojas de salida"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    query = """
        SELECT s.*, cl.razon_social as cliente_nombre,
               ct.folio as contrato_folio,
               o.nombre_proyecto as obra_nombre
        FROM inv_salidas s
        JOIN crm_clientes cl ON s.cliente_id = cl.id
        JOIN ops_contratos ct ON s.contrato_id = ct.id
        LEFT JOIN crm_obras o ON s.obra_id = o.id
    """
    if contrato_id:
        query += " WHERE s.contrato_id = %s"
        cur.execute(query + " ORDER BY s.created_at DESC", (contrato_id,))
    else:
        cur.execute(query + " ORDER BY s.created_at DESC")
    salidas = cur.fetchall()
    cur.close()
    conn.close()
    return salidas


def get_hoja_salida_detalle(salida_id):
    """Retorna hoja de salida con sus items"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("""
        SELECT s.*, cl.razon_social as cliente_nombre,
               cl.telefono as cliente_telefono,
               cl.contacto as cliente_contacto,
               ct.folio as contrato_folio,
               o.nombre_proyecto as obra_nombre,
               o.folio_obra, o.direccion_obra
        FROM inv_salidas s
        JOIN crm_clientes cl ON s.cliente_id = cl.id
        JOIN ops_contratos ct ON s.contrato_id = ct.id
        LEFT JOIN crm_obras o ON s.obra_id = o.id
        WHERE s.id = %s
    """, (salida_id,))
    salida = cur.fetchone()

    cur.execute("""
        SELECT si.*, p.nombre as producto_nombre,
               p.codigo, p.peso_kg,
               i.cantidad_disponible
        FROM inv_salida_items si
        JOIN cat_productos p ON si.producto_id = p.id
        LEFT JOIN inv_master i ON p.id = i.producto_id
        WHERE si.salida_id = %s
    """, (salida_id,))
    items = cur.fetchall()

    cur.close()
    conn.close()
    return salida, items


def actualizar_estatus_salida(salida_id, estatus, fecha_entrega=None):
    """Actualiza estatus de hoja de salida"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE inv_salidas SET
                estatus        = %s,
                fecha_entrega  = %s,
                updated_at     = NOW()
            WHERE id = %s
        """, (estatus, fecha_entrega, salida_id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()