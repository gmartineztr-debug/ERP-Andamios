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