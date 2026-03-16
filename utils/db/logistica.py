import streamlit as st
from .connection import get_cursor

# ================================================
# LOGÍSTICA - SALIDAS
# ================================================

def generar_folio_salida():
    """Genera el siguiente folio de hoja de salida"""
    with get_cursor() as (cur, conn):
        cur.execute("SELECT generar_folio_salida()")
        return cur.fetchone()['generar_folio_salida']

def get_contratos_sin_hs_completa():
    """Retorna contratos activos con entregas pendientes"""
    with get_cursor() as (cur, conn):
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
        return cur.fetchall()

def get_cantidad_enviada_por_contrato(contrato_id, producto_id):
    """Retorna cantidad ya enviada de un producto en un contrato"""
    with get_cursor(dict_cursor=False) as (cur, conn):
        cur.execute("""
            SELECT COALESCE(SUM(si.cantidad), 0)
            FROM inv_salida_items si
            JOIN inv_salidas s ON si.salida_id = s.id
            WHERE s.contrato_id = %s AND si.producto_id = %s AND s.estatus != 'cancelada'
        """, (contrato_id, producto_id))
        return int(cur.fetchone()[0])

def crear_hoja_salida(datos, items):
    """Crea una hoja de salida con sus items"""
    with get_cursor() as (cur, conn):
        peso_total = sum(i['peso_total'] for i in items)
        cur.execute("""
            INSERT INTO inv_salidas
            (folio, contrato_id, cliente_id, obra_id,
             chofer, observaciones, estatus, fecha_salida,
             peso_total, contacto_entrega, telefono_entrega)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            datos['folio'], datos['contrato_id'], datos['cliente_id'],
            datos.get('obra_id'), datos.get('chofer'), datos.get('observaciones'),
            datos['estatus'], datos['fecha_salida'], peso_total,
            datos.get('contacto_entrega'), datos.get('telefono_entrega')
        ))
        salida_id = cur.fetchone()['id']

        for item in items:
            cur.execute("""
                INSERT INTO inv_salida_items
                (salida_id, producto_id, cantidad, peso_unitario, peso_total)
                VALUES (%s, %s, %s, %s, %s)
            """, (salida_id, item['producto_id'], item['cantidad'], item['peso_unitario'], item['peso_total']))

        conn.commit()
        return salida_id

def get_hojas_salida(contrato_id=None):
    """Retorna hojas de salida"""
    with get_cursor() as (cur, conn):
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
        return cur.fetchall()

def get_hoja_salida_detalle(salida_id):
    """Retorna hoja de salida con sus items"""
    with get_cursor() as (cur, conn):
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

        return salida, items

def actualizar_estatus_salida(salida_id, estatus, fecha_entrega=None):
    """Actualiza estatus de hoja de salida"""
    with get_cursor() as (cur, conn):
        cur.execute("""
            UPDATE inv_salidas SET
                estatus        = %s,
                fecha_entrega  = %s,
                updated_at     = NOW()
            WHERE id = %s
        """, (estatus, fecha_entrega, salida_id))
        conn.commit()

# ================================================
# PROVEEDORES
# ================================================

def get_proveedores():
    """Retorna lista de proveedores activos"""
    with get_cursor() as (cur, conn):
        cur.execute("SELECT * FROM prov_proveedores WHERE activo = TRUE ORDER BY nombre")
        return cur.fetchall()

def crear_proveedor(datos):
    """Crea un nuevo proveedor"""
    with get_cursor() as (cur, conn):
        cur.execute("""
            INSERT INTO prov_proveedores
            (nombre, rfc, contacto, telefono, email, direccion)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            datos['nombre'], datos.get('rfc'), datos.get('contacto'),
            datos.get('telefono'), datos.get('email'), datos.get('direccion')
        ))
        nuevo_id = cur.fetchone()['id']
        conn.commit()
        return nuevo_id

# ================================================
# LOGÍSTICA - ENTRADAS
# ================================================

def generar_folio_entrada():
    """Genera folio para hoja de entrada"""
    with get_cursor() as (cur, conn):
        cur.execute("SELECT generar_folio_entrada()")
        return cur.fetchone()['generar_folio_entrada']

def get_saldo_en_campo(contrato_id):
    """Retorna saldo de equipo en campo para un contrato"""
    with get_cursor() as (cur, conn):
        cur.execute("""
            SELECT * FROM v_saldo_en_campo
            WHERE contrato_id = %s AND saldo_en_campo > 0
            ORDER BY codigo
        """, (contrato_id,))
        return cur.fetchall()

def get_contratos_con_equipo_en_campo():
    """Contratos activos que tienen equipo en campo"""
    with get_cursor() as (cur, conn):
        cur.execute("""
            SELECT DISTINCT
                ct.id, ct.folio, ct.cliente_id,
                cl.razon_social AS cliente_nombre,
                cl.telefono     AS cliente_telefono,
                ct.obra_id,
                o.folio_obra,
                o.nombre_proyecto AS obra_nombre,
                o.direccion_obra
            FROM v_saldo_en_campo v
            JOIN ops_contratos ct ON v.contrato_id = ct.id
            JOIN crm_clientes cl  ON ct.cliente_id = cl.id
            LEFT JOIN crm_obras o ON ct.obra_id    = o.id
            ORDER BY cl.razon_social
        """)
        return cur.fetchall()

def crear_hoja_entrada(datos, items):
    """Crea HE con sus items"""
    with get_cursor() as (cur, conn):
        cur.execute("""
            INSERT INTO inv_entradas
            (folio, tipo_entrada, estatus,
             contrato_id, cliente_id, obra_id,
             proveedor_id, num_factura, costo_total,
             lote_fabricacion, fecha_entrada, notas)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            datos['folio'], datos['tipo_entrada'], datos.get('estatus', 'pendiente'),
            datos.get('contrato_id'), datos.get('cliente_id'), datos.get('obra_id'),
            datos.get('proveedor_id'), datos.get('num_factura'),
            datos.get('costo_total', 0), datos.get('lote_fabricacion'),
            datos['fecha_entrada'], datos.get('notas')
        ))
        entrada_id = cur.fetchone()['id']

        for item in items:
            cur.execute("""
                INSERT INTO inv_entrada_items
                (entrada_id, producto_id,
                 cantidad_total, costo_unitario,
                 cantidad_buena, cantidad_danada,
                 cantidad_perdida, cantidad_chatarra,
                 peso_unitario, peso_total)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                entrada_id, item['producto_id'], item.get('cantidad_total', 0),
                item.get('costo_unitario', 0), item.get('cantidad_buena', 0),
                item.get('cantidad_danada', 0), item.get('cantidad_perdida', 0),
                item.get('cantidad_chatarra', 0), item.get('peso_unitario', 0),
                item.get('peso_total', 0)
            ))

        conn.commit()
        return entrada_id

def get_hojas_entrada(tipo=None, contrato_id=None):
    """Retorna hojas de entrada"""
    with get_cursor() as (cur, conn):
        query = """
            SELECT e.*,
            cl.razon_social  AS cliente_nombre,
            ct.folio         AS contrato_folio,
            o.nombre_proyecto AS obra_nombre,
            p.nombre         AS proveedor_nombre
            FROM inv_entradas e
            LEFT JOIN crm_clientes cl   ON e.cliente_id   = cl.id
            LEFT JOIN ops_contratos ct  ON e.contrato_id  = ct.id
            LEFT JOIN crm_obras o       ON e.obra_id      = o.id
            LEFT JOIN prov_proveedores p ON e.proveedor_id = p.id
        """
        filtros = []
        valores = []
        if tipo:
            filtros.append("e.tipo_entrada = %s")
            valores.append(tipo)
        if contrato_id:
            filtros.append("e.contrato_id = %s")
            valores.append(contrato_id)
            
        if filtros:
            query += " WHERE " + " AND ".join(filtros)
            
        cur.execute(query + " ORDER BY e.created_at DESC", valores)
        return cur.fetchall()

def get_hoja_entrada_detalle(entrada_id):
    """Retorna HE con sus items"""
    with get_cursor() as (cur, conn):
        cur.execute("""
            SELECT e.*,
                   cl.razon_social  AS cliente_nombre,
                   cl.telefono      AS cliente_telefono,
                   ct.folio         AS contrato_folio,
                   o.nombre_proyecto AS obra_nombre,
                   o.folio_obra,
                   o.direccion_obra,
                   p.nombre         AS proveedor_nombre
            FROM inv_entradas e
            LEFT JOIN crm_clientes cl    ON e.cliente_id   = cl.id
            LEFT JOIN ops_contratos ct   ON e.contrato_id  = ct.id
            LEFT JOIN crm_obras o        ON e.obra_id      = o.id
            LEFT JOIN prov_proveedores p ON e.proveedor_id = p.id
            WHERE e.id = %s
        """, (entrada_id,))
        entrada = cur.fetchone()

        cur.execute("""
            SELECT ei.*,
                   p.nombre  AS producto_nombre,
                   p.codigo,
                   p.peso_kg,
                   p.precio_venta
            FROM inv_entrada_items ei
            JOIN cat_productos p ON ei.producto_id = p.id
            WHERE ei.entrada_id = %s
        """, (entrada_id,))
        items = cur.fetchall()

        return entrada, items

def actualizar_estatus_entrada(entrada_id, estatus, fecha_cierre=None):
    """Actualiza estatus — el trigger actualiza inventario al cerrar"""
    with get_cursor() as (cur, conn):
        cur.execute("""
            UPDATE inv_entradas SET
                estatus      = %s,
                fecha_cierre = %s,
                updated_at   = NOW()
            WHERE id = %s
        """, (estatus, fecha_cierre, entrada_id))
        conn.commit()

def vincular_contrato_venta_entrada(entrada_id, contrato_venta_id):
    """Liga el contrato de venta generado a la HE"""
    with get_cursor() as (cur, conn):
        cur.execute("UPDATE inv_entradas SET contrato_venta_id = %s, updated_at = NOW() WHERE id = %s", (contrato_venta_id, entrada_id))
        conn.commit()
