import streamlit as st
from .connection import get_cursor

# ================================================
# INSUMOS
# ================================================

def get_insumos():
    """Retorna lista de insumos activos"""
    with get_cursor() as (cur, conn):
        cur.execute("SELECT * FROM fab_insumos WHERE activo = TRUE ORDER BY nombre")
        res = cur.fetchall()
        return res if res is not None else []

def crear_insumo(datos):
    """Crea un nuevo insumo"""
    with get_cursor() as (cur, conn):
        cur.execute("""
            INSERT INTO fab_insumos (codigo, nombre, unidad, descripcion)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (datos['codigo'], datos['nombre'], datos['unidad'], datos.get('descripcion')))
        nuevo_id = cur.fetchone()['id']
        conn.commit()
        return nuevo_id

# ================================================
# BOM (RECETAS)
# ================================================

def get_bom_producto(producto_id):
    """Retorna receta de un producto"""
    with get_cursor() as (cur, conn):
        cur.execute("""
            SELECT b.*, i.nombre AS insumo_nombre, i.codigo AS insumo_codigo, i.unidad
            FROM fab_bom b
            JOIN fab_insumos i ON b.insumo_id = i.id
            WHERE b.producto_id = %s
            ORDER BY i.nombre
        """, (producto_id,))
        res = cur.fetchall()
        return res if res is not None else []

def guardar_bom_producto(producto_id, items):
    """Reemplaza BOM completo de un producto"""
    with get_cursor() as (cur, conn):
        cur.execute("DELETE FROM fab_bom WHERE producto_id = %s", (producto_id,))
        for item in items:
            cur.execute("""
                INSERT INTO fab_bom (producto_id, insumo_id, cantidad_por_pieza, notas)
                VALUES (%s, %s, %s, %s)
            """, (producto_id, item['insumo_id'], item['cantidad_por_pieza'], item.get('notas')))
        conn.commit()

def calcular_materiales_of(items_of):
    """Calcula materiales necesarios para una OF e incluye costos estimados"""
    with get_cursor() as (cur, conn):
        materiales = {}
        for item in items_of:
            cur.execute("""
                SELECT b.insumo_id, i.codigo, i.nombre, i.unidad, b.cantidad_por_pieza,
                (SELECT costo_unitario FROM fab_oc_items WHERE insumo_id = b.insumo_id ORDER BY created_at DESC LIMIT 1) as last_cost
                FROM fab_bom b
                JOIN fab_insumos i ON b.insumo_id = i.id
                WHERE b.producto_id = %s
            """, (item['producto_id'],))
            bom = cur.fetchall()

            for linea in bom:
                ins_id = linea['insumo_id']
                cant = float(linea['cantidad_por_pieza']) * item['cantidad']
                costo = float(linea['last_cost'] or 0)
                
                if ins_id in materiales:
                    materiales[ins_id]['cantidad_necesaria'] += cant
                    materiales[ins_id]['subtotal'] = materiales[ins_id]['cantidad_necesaria'] * costo
                else:
                    materiales[ins_id] = {
                        'insumo_id': ins_id,
                        'codigo': linea['codigo'],
                        'nombre': linea['nombre'],
                        'unidad': linea['unidad'],
                        'cantidad_necesaria': cant,
                        'costo_unitario': costo,
                        'subtotal': cant * costo
                    }
        return list(materiales.values())

# ================================================
# ÓRDENES DE FABRICACIÓN (OF)
# ================================================

def generar_folio_of():
    """Genera folio para orden de fabricación"""
    with get_cursor() as (cur, conn):
        cur.execute("SELECT generar_folio_of()")
        return cur.fetchone()['generar_folio_of']

def crear_orden_fabricacion(datos, items):
    """Crea una OF con sus productos objetivo"""
    with get_cursor() as (cur, conn):
        cur.execute("""
            INSERT INTO fab_ordenes (folio, estatus, fecha_apertura, fecha_estimada, notas)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (datos['folio'], datos.get('estatus', 'abierta'), datos['fecha_apertura'], datos.get('fecha_estimada'), datos.get('notas')))
        orden_id = cur.fetchone()['id']

        for item in items:
            cur.execute("""
                INSERT INTO fab_orden_items (orden_id, producto_id, cantidad_solicitada)
                VALUES (%s, %s, %s)
            """, (orden_id, item['producto_id'], item['cantidad']))
        conn.commit()
        return orden_id

def get_ordenes_fabricacion():
    """Lista de todas las OFs"""
    with get_cursor() as (cur, conn):
        cur.execute("""
            SELECT f.*, COUNT(fi.id) AS total_productos
            FROM fab_ordenes f
            LEFT JOIN fab_orden_items fi ON fi.orden_id = f.id
            GROUP BY f.id ORDER BY f.created_at DESC
        """)
        return cur.fetchall()

def get_orden_fabricacion_detalle(orden_id):
    """Detalle de OF con items"""
    with get_cursor() as (cur, conn):
        cur.execute("SELECT * FROM fab_ordenes WHERE id = %s", (orden_id,))
        orden = cur.fetchone()
        cur.execute("""
            SELECT fi.*, p.nombre AS producto_nombre, p.codigo, p.peso_kg
            FROM fab_orden_items fi
            JOIN cat_productos p ON fi.producto_id = p.id
            WHERE fi.orden_id = %s
        """, (orden_id,))
        return orden, cur.fetchall()

def actualizar_estatus_of(orden_id, estatus, fecha_cierre=None, items_fabricados=None):
    """Actualiza estatus y registra producción final"""
    with get_cursor() as (cur, conn):
        cur.execute("""
            UPDATE fab_ordenes SET estatus = %s, fecha_cierre = %s, updated_at = NOW()
            WHERE id = %s
        """, (estatus, fecha_cierre, orden_id))

        if estatus == 'terminada' and items_fabricados:
            for item in items_fabricados:
                cur.execute("""
                    UPDATE fab_orden_items SET cantidad_fabricada = %s
                    WHERE orden_id = %s AND producto_id = %s
                """, (item['cantidad_fabricada'], orden_id, item['producto_id']))
        conn.commit()

def get_ordenes_terminadas_sin_he():
    """OFs que requieren entrada a almacén"""
    with get_cursor() as (cur, conn):
        cur.execute("""
            SELECT f.* FROM fab_ordenes f
            WHERE f.estatus = 'terminada'
            AND NOT EXISTS (SELECT 1 FROM inv_entradas e WHERE e.lote_fabricacion = f.folio)
            ORDER BY f.fecha_cierre DESC
        """)
        return cur.fetchall()

# ================================================
# ÓRDENES DE COMPRA (OC)
# ================================================

def generar_folio_oc():
    """Genera folio para orden de compra"""
    with get_cursor() as (cur, conn):
        cur.execute("SELECT generar_folio_oc()")
        return cur.fetchone()['generar_folio_oc']

def crear_orden_compra(datos, items):
    """Crea una OC de insumos"""
    with get_cursor() as (cur, conn):
        total = sum(float(i['cantidad']) * float(i['costo_unitario']) for i in items)
        cur.execute("""
            INSERT INTO fab_ordenes_compra
            (folio, orden_id, proveedor_id, estatus, fecha_oc, fecha_estimada_entrega, total, notas)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (datos['folio'], datos.get('orden_id'), datos.get('proveedor_id'), datos.get('estatus', 'borrador'),
              datos['fecha_oc'], datos.get('fecha_estimada_entrega'), total, datos.get('notas')))
        oc_id = cur.fetchone()['id']

        for item in items:
            subtotal = float(item['cantidad']) * float(item['costo_unitario'])
            cur.execute("""
                INSERT INTO fab_oc_items (oc_id, insumo_id, cantidad, costo_unitario, subtotal)
                VALUES (%s, %s, %s, %s, %s)
            """, (oc_id, item['insumo_id'], item['cantidad'], item['costo_unitario'], subtotal))
        conn.commit()
        return oc_id

def get_ordenes_compra():
    """Lista de OCs con info de proveedor y OF"""
    with get_cursor() as (cur, conn):
        cur.execute("""
            SELECT oc.*, f.folio AS of_folio, p.nombre AS proveedor_nombre
            FROM fab_ordenes_compra oc
            LEFT JOIN fab_ordenes f ON oc.orden_id = f.id
            LEFT JOIN prov_proveedores p ON oc.proveedor_id = p.id
            ORDER BY oc.created_at DESC
        """)
        return cur.fetchall()

def get_orden_compra_detalle(oc_id):
    """Detalle de OC con items"""
    with get_cursor() as (cur, conn):
        cur.execute("""
            SELECT oc.*, f.folio AS of_folio, p.nombre AS proveedor_nombre, p.telefono AS proveedor_telefono
            FROM fab_ordenes_compra oc
            LEFT JOIN fab_ordenes f ON oc.orden_id = f.id
            LEFT JOIN prov_proveedores p ON oc.proveedor_id = p.id
            WHERE oc.id = %s
        """, (oc_id,))
        oc = cur.fetchone()
        cur.execute("""
            SELECT oi.*, i.nombre AS insumo_nombre, i.codigo, i.unidad
            FROM fab_oc_items oi
            JOIN fab_insumos i ON oi.insumo_id = i.id
            WHERE oi.oc_id = %s
        """, (oc_id,))
        return oc, cur.fetchall()

def actualizar_estatus_oc(oc_id, estatus):
    """Actualiza estatus de una OC"""
    with get_cursor() as (cur, conn):
        cur.execute("UPDATE fab_ordenes_compra SET estatus = %s, updated_at = NOW() WHERE id = %s", (estatus, oc_id))
        conn.commit()

# ================================================
# SOLICITUDES DE CAMBIO (SC)
# ================================================

def generar_folio_sc():
    """Genera folio para solicitud de cambio"""
    with get_cursor() as (cur, conn):
        cur.execute("SELECT generar_folio_sc()")
        return cur.fetchone()['generar_folio_sc']

def crear_sc(datos, items, materiales):
    """Crea una SC vinculada a una OF"""
    with get_cursor() as (cur, conn):
        cur.execute("""
            INSERT INTO fab_solicitudes_cambio (
                folio, of_origen_id, of_nueva_id, motivo, avance_descr, estatus, fecha, notas
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
        """, (datos['folio'], datos['of_origen_id'], datos.get('of_nueva_id'), datos['motivo'],
              datos.get('avance_descr'), datos.get('estatus', 'borrador'), datos['fecha'], datos.get('notas')))
        sc_id = cur.fetchone()['id']

        for item in items:
            cur.execute("""
                INSERT INTO fab_sc_items (sc_id, producto_id, cantidad_planeada, cantidad_fabricada)
                VALUES (%s,%s,%s,%s)
            """, (sc_id, item['producto_id'], item['cantidad_planeada'], item['cantidad_fabricada']))

        for mat in materiales:
            cur.execute("""
                INSERT INTO fab_sc_materiales (
                    sc_id, insumo_id, cantidad_estimada_uso, cantidad_real_uso,
                    cantidad_sobrante, destino_sobrante, notas
                ) VALUES (%s,%s,%s,%s,%s,%s,%s)
            """, (sc_id, mat['insumo_id'], mat.get('cantidad_estimada_uso', 0), mat.get('cantidad_real_uso'),
                  mat.get('cantidad_sobrante'), mat.get('destino_sobrante', 'desconocido'), mat.get('notas')))

        cur.execute("UPDATE fab_ordenes SET estatus = 'modificada', updated_at = NOW() WHERE id = %s", (datos['of_origen_id'],))
        conn.commit()
        return sc_id

def get_solicitudes_cambio():
    """Lista de todas las SCs"""
    with get_cursor() as (cur, conn):
        cur.execute("SELECT * FROM v_solicitudes_cambio")
        return cur.fetchall()

def get_sc_detalle(sc_id):
    """Detalle de SC con productos y balance de materiales"""
    with get_cursor() as (cur, conn):
        cur.execute("SELECT * FROM v_solicitudes_cambio WHERE id = %s", (sc_id,))
        sc = cur.fetchone()
        cur.execute("""
            SELECT si.*, p.codigo, p.nombre AS producto_nombre
            FROM fab_sc_items si JOIN cat_productos p ON si.producto_id = p.id WHERE si.sc_id = %s
        """, (sc_id,))
        items = cur.fetchall()
        cur.execute("""
            SELECT sm.*, i.codigo, i.nombre AS insumo_nombre, i.unidad
            FROM fab_sc_materiales sm JOIN fab_insumos i ON sm.insumo_id = i.id WHERE sm.sc_id = %s
        """, (sc_id,))
        return sc, items, cur.fetchall()

def actualizar_estatus_sc(sc_id, estatus, of_nueva_id=None):
    """Actualiza estatus de SC"""
    with get_cursor() as (cur, conn):
        cur.execute("""
            UPDATE fab_solicitudes_cambio SET estatus = %s, of_nueva_id = COALESCE(%s, of_nueva_id), updated_at = NOW()
            WHERE id = %s
        """, (estatus, of_nueva_id, sc_id))
        conn.commit()

def get_of_detalle(of_id):
    """Alias para get_orden_fabricacion_detalle (compatibilidad)"""
    return get_orden_fabricacion_detalle(of_id)
