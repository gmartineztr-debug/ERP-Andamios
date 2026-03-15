from datetime import date
import streamlit as st
from .connection import get_cursor

# ================================================
# CLIENTES
# ================================================

def get_clientes(solo_activos=True):
    """Retorna lista de clientes"""
    with get_cursor() as (cur, conn):
        query = "SELECT * FROM crm_clientes"
        if solo_activos:
            query += " WHERE activo = TRUE"
        query += " ORDER BY razon_social"
        cur.execute(query)
        res = cur.fetchall()
        return res if res is not None else []

def get_cliente_by_id(cliente_id):
    """Retorna un cliente por su ID"""
    with get_cursor() as (cur, conn):
        cur.execute("SELECT * FROM crm_clientes WHERE id = %s", (cliente_id,))
        res = cur.fetchone()
        return res if res is not None else {}

def crear_cliente(datos):
    """Crea un nuevo cliente"""
    with get_cursor() as (cur, conn):
        cur.execute("""
            INSERT INTO crm_clientes
            (razon_social, rfc, contacto, telefono, email, direccion, tipo_cliente, limite_credito)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            datos['razon_social'], datos['rfc'], datos['contacto'],
            datos['telefono'], datos['email'], datos['direccion'],
            datos['tipo_cliente'], datos['limite_credito']
        ))
        nuevo_id = cur.fetchone()['id']
        conn.commit()
        return nuevo_id

def actualizar_cliente(cliente_id, datos):
    """Actualiza un cliente existente"""
    with get_cursor() as (cur, conn):
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
            datos['razon_social'], datos['rfc'], datos['contacto'],
            datos['telefono'], datos['email'], datos['direccion'],
            datos['tipo_cliente'], datos['limite_credito'],
            cliente_id
        ))
        conn.commit()

# ================================================
# OBRAS
# ================================================

def generar_folio_obra():
    """Genera el siguiente folio de obra"""
    with get_cursor() as (cur, conn):
        cur.execute("SELECT generar_folio_obra()")
        return cur.fetchone()['generar_folio_obra']

def crear_obra(datos):
    """Crea una nueva obra"""
    with get_cursor() as (cur, conn):
        cur.execute("""
            INSERT INTO crm_obras
            (folio_obra, cliente_id, nombre_proyecto, direccion_obra,
             fecha_inicio, fecha_fin_estimada, responsable, notas)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            datos['folio_obra'], datos['cliente_id'], datos['nombre_proyecto'],
            datos['direccion_obra'], datos['fecha_inicio'],
            datos['fecha_fin_estimada'], datos['responsable'], datos['notas']
        ))
        nuevo_id = cur.fetchone()['id']
        conn.commit()
        return nuevo_id

def get_obras(estatus=None):
    """Retorna lista de obras"""
    with get_cursor() as (cur, conn):
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
        return cur.fetchall()

def get_obra_by_id(obra_id):
    """Retorna una obra por su ID"""
    with get_cursor() as (cur, conn):
        cur.execute("""
            SELECT o.*, c.razon_social as cliente_nombre
            FROM crm_obras o
            JOIN crm_clientes c ON o.cliente_id = c.id
            WHERE o.id = %s
        """, (obra_id,))
        return cur.fetchone()

def actualizar_estatus_obra(obra_id, estatus):
    """Actualiza el estatus de una obra"""
    with get_cursor() as (cur, conn):
        cur.execute("UPDATE crm_obras SET estatus = %s, updated_at = NOW() WHERE id = %s", (estatus, obra_id))
        conn.commit()

def get_contratos_por_obra(obra_id):
    """Retorna contratos asociados a una obra"""
    with get_cursor() as (cur, conn):
        cur.execute("SELECT * FROM ops_contratos WHERE obra_id = %s ORDER BY created_at DESC", (obra_id,))
        return cur.fetchall()

def actualizar_total_facturado_obra(obra_id):
    """Recalcula el total facturado de una obra"""
    with get_cursor() as (cur, conn):
        cur.execute("""
            UPDATE crm_obras
            SET total_facturado = (
                SELECT COALESCE(SUM(monto_total), 0)
                FROM ops_contratos
                WHERE obra_id = %s AND estatus != 'cancelado'
            ),
            updated_at = NOW()
            WHERE id = %s
        """, (obra_id, obra_id))
        conn.commit()

def get_obras_por_cliente(cliente_id):
    """Retorna obras activas de un cliente específico"""
    with get_cursor() as (cur, conn):
        cur.execute("""
            SELECT id, folio_obra, nombre_proyecto
            FROM crm_obras
            WHERE cliente_id = %s AND estatus = 'activa'
            ORDER BY created_at DESC
        """, (cliente_id,))
        return cur.fetchall()

# ================================================
# COTIZACIONES
# ================================================

def generar_folio_cotizacion():
    """Genera el siguiente folio de cotización"""
    with get_cursor() as (cur, conn):
        cur.execute("SELECT generar_folio_cotizacion()")
        return cur.fetchone()['generar_folio_cotizacion']

def crear_cotizacion(datos, items):
    """Crea una cotización con sus items"""
    with get_cursor() as (cur, conn):
        cur.execute("""
            INSERT INTO crm_cotizaciones
            (folio, cliente_id, obra_id, tipo_operacion, estatus,
             tipo_flete, distancia_km, tarifa_flete, monto_flete,
             subtotal, aplica_iva, iva, total, dias_renta, notas)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            datos['folio'], datos['cliente_id'], datos.get('obra_id'),
            datos['tipo_operacion'], datos['estatus'], datos['tipo_flete'],
            datos['distancia_km'], datos['tarifa_flete'], datos['monto_flete'],
            datos['subtotal'], datos['aplica_iva'], datos['iva'],
            datos['total'], datos['dias_renta'], datos['notas']
        ))
        cotizacion_id = cur.fetchone()['id']

        for item in items:
            cur.execute("""
                INSERT INTO crm_cotizacion_items
                (cotizacion_id, producto_id, cantidad, precio_unitario, subtotal)
                VALUES (%s, %s, %s, %s, %s)
            """, (cotizacion_id, item['producto_id'], item['cantidad'], item['precio_unitario'], item['subtotal']))

        conn.commit()
        return cotizacion_id

def get_cotizaciones(estatus=None):
    """Retorna lista de cotizaciones"""
    with get_cursor() as (cur, conn):
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
        return cur.fetchall()

def get_cotizacion_detalle(cotizacion_id):
    """Retorna una cotización con sus items"""
    with get_cursor() as (cur, conn):
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

        return cotizacion, items

def actualizar_estatus_cotizacion(cotizacion_id, estatus):
    """Actualiza el estatus de una cotización"""
    with get_cursor() as (cur, conn):
        cur.execute("UPDATE crm_cotizaciones SET estatus = %s, updated_at = NOW() WHERE id = %s", (estatus, cotizacion_id))
        conn.commit()

def get_cotizaciones_aprobadas():
    """Retorna cotizaciones aprobadas sin contrato"""
    with get_cursor() as (cur, conn):
        cur.execute("""
            SELECT c.*, cl.razon_social as cliente_nombre
            FROM crm_cotizaciones c
            JOIN crm_clientes cl ON c.cliente_id = cl.id
            WHERE c.estatus = 'aprobada'
            AND c.id NOT IN (
                SELECT cotizacion_id FROM ops_contratos WHERE cotizacion_id IS NOT NULL
            )
            ORDER BY c.created_at DESC
        """)
        return cur.fetchall()
