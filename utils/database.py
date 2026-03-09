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