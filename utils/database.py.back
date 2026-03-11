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
        SELECT p.*, i.cantidad_disponible, i.cantidad_rentada
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