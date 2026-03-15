import streamlit as st
from .connection import get_cursor

def get_productos(solo_activos=True):
    """Retorna lista de productos"""
    with get_cursor() as (cur, conn):
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
        res = cur.fetchall()
        return res if res is not None else []

def get_producto_by_id(producto_id):
    """Retorna un producto por su ID"""
    with get_cursor() as (cur, conn):
        cur.execute("""
            SELECT p.*, i.cantidad_disponible, i.cantidad_rentada,
            i.cantidad_mantenimiento, i.cantidad_chatarra, i.stock_minimo
            FROM cat_productos p
            LEFT JOIN inv_master i ON p.id = i.producto_id
            WHERE p.id = %s
        """, (producto_id,))
        res = cur.fetchone()
        return res if res is not None else {}

def crear_producto(datos):
    """Crea un nuevo producto y su registro de inventario"""
    with get_cursor() as (cur, conn):
        cur.execute("""
            INSERT INTO cat_productos
            (codigo, nombre, descripcion, unidad, precio_renta_dia,
             precio_venta, peso_kg, se_fabrica, sistema)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            datos['codigo'], datos['nombre'], datos['descripcion'],
            datos['unidad'], datos['precio_renta_dia'], datos['precio_venta'],
            datos['peso_kg'], datos['se_fabrica'], datos['sistema']
        ))
        nuevo_id = cur.fetchone()['id']

        cur.execute("""
            INSERT INTO inv_master (producto_id, stock_minimo)
            VALUES (%s, %s)
        """, (nuevo_id, datos['stock_minimo']))

        conn.commit()
        return nuevo_id

def actualizar_producto(producto_id, datos):
    """Actualiza un producto existente"""
    with get_cursor() as (cur, conn):
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
            datos['codigo'], datos['nombre'], datos['descripcion'],
            datos['unidad'], datos['precio_renta_dia'], datos['precio_venta'],
            datos['peso_kg'], datos['se_fabrica'], datos['sistema'],
            datos['activo'], producto_id
        ))

        cur.execute("""
            UPDATE inv_master SET stock_minimo = %s
            WHERE producto_id = %s
        """, (datos['stock_minimo'], producto_id))

        conn.commit()

def get_productos_por_codigo(codigo):
    """Busca producto por código exacto"""
    with get_cursor() as (cur, conn):
        cur.execute("""
            SELECT p.*, im.cantidad_disponible
            FROM cat_productos p
            LEFT JOIN inv_master im ON p.id = im.producto_id
            WHERE p.codigo = %s AND p.activo = TRUE
        """, (codigo,))
        res = cur.fetchone()
        return res if res is not None else {}
