from .connection import get_cursor

def get_bitacora(producto_id=None, tipo=None, limite=100):
    """Lista de movimientos de inventario"""
    with get_cursor() as (cur, conn):
        filtros = []
        valores = []
        if producto_id:
            filtros.append("producto_id = %s")
            valores.append(producto_id)
        if tipo:
            filtros.append("tipo_movimiento = %s")
            valores.append(tipo)
        where = ("WHERE " + " AND ".join(filtros)) if filtros else ""
        cur.execute(f"""
            SELECT * FROM v_inv_bitacora
            {where}
            ORDER BY fecha DESC
            LIMIT %s
        """, valores + [limite])
        res = cur.fetchall()
        return res if res is not None else []

def get_bitacora_producto(producto_id):
    """Historial completo de un producto"""
    with get_cursor() as (cur, conn):
        cur.execute("""
            SELECT * FROM v_inv_bitacora
            WHERE producto_id = %s
            ORDER BY fecha DESC
        """, (producto_id,))
        return cur.fetchall()

def registrar_ajuste_manual(producto_id, notas, usuario="sistema"):
    """Registra un ajuste manual en la bitácora"""
    with get_cursor() as (cur, conn):
        cur.execute("""
            INSERT INTO inv_bitacora (
                producto_id, tipo_movimiento,
                referencia_tipo, notas
            ) VALUES (%s, 'ajuste_manual', 'MANUAL', %s)
        """, (producto_id, notas))
        conn.commit()

def generar_folio_conteo():
    """Genera folio para conteo físico"""
    with get_cursor() as (cur, conn):
        cur.execute("SELECT generar_folio_conteo()")
        return cur.fetchone()['generar_folio_conteo']

def crear_conteo(datos):
    """Crea un conteo físico y precarga con valores del sistema"""
    with get_cursor() as (cur, conn):
        cur.execute("""
            INSERT INTO inv_conteos (
                folio, fecha, periodo,
                estatus, responsable, notas
            ) VALUES (%s,%s,%s,%s,%s,%s)
            RETURNING id
        """, (
            datos['folio'], datos['fecha'], datos['periodo'],
            'en_proceso', datos.get('responsable'), datos.get('notas')
        ))
        conteo_id = cur.fetchone()['id']

        cur.execute("""
            INSERT INTO inv_conteo_items (
                conteo_id, producto_id,
                sistema_disponible, sistema_mantenimiento, sistema_chatarra,
                fisico_disponible, fisico_mantenimiento, fisico_chatarra
            )
            SELECT
                %s, im.producto_id,
                COALESCE(im.cantidad_disponible, 0),
                COALESCE(im.cantidad_mantenimiento, 0),
                COALESCE(im.cantidad_chatarra, 0),
                COALESCE(im.cantidad_disponible, 0),
                COALESCE(im.cantidad_mantenimiento, 0),
                COALESCE(im.cantidad_chatarra, 0)
            FROM inv_master im
            JOIN cat_productos p ON im.producto_id = p.id
            WHERE p.activo = TRUE
            ORDER BY p.codigo
        """, (conteo_id,))

        conn.commit()
        return conteo_id

def get_conteos():
    """Lista de conteos físicos"""
    with get_cursor() as (cur, conn):
        cur.execute("SELECT * FROM v_conteos ORDER BY fecha DESC")
        return cur.fetchall()

def get_conteo_items(conteo_id):
    """Items de un conteo físico"""
    with get_cursor() as (cur, conn):
        cur.execute("""
            SELECT ci.*, p.codigo, p.nombre AS producto_nombre
            FROM inv_conteo_items ci
            JOIN cat_productos p ON ci.producto_id = p.id
            WHERE ci.conteo_id = %s
            ORDER BY p.codigo
        """, (conteo_id,))
        return cur.fetchall()

def actualizar_conteo_item(item_id, fisico_disp, fisico_mant, fisico_chat, justificacion):
    """Actualiza un item de un conteo"""
    with get_cursor() as (cur, conn):
        cur.execute("""
            UPDATE inv_conteo_items SET
                fisico_disponible    = %s,
                fisico_mantenimiento = %s,
                fisico_chatarra      = %s,
                justificacion        = %s
            WHERE id = %s
        """, (fisico_disp, fisico_mant, fisico_chat, justificacion, item_id))
        conn.commit()

def aplicar_ajuste_conteo(conteo_id):
    """Aplica los ajustes de un conteo al inventario real"""
    with get_cursor() as (cur, conn):
        cur.execute("""
            SELECT * FROM inv_conteo_items
            WHERE conteo_id = %s
            AND ajuste_aplicado = FALSE
            AND (diff_disponible != 0 OR diff_mantenimiento != 0 OR diff_chatarra != 0)
        """, (conteo_id,))
        items = cur.fetchall()

        for item in items:
            cur.execute("""
                UPDATE inv_master SET
                    cantidad_disponible    = %s,
                    cantidad_mantenimiento = %s,
                    cantidad_chatarra      = %s,
                    updated_at             = NOW()
                WHERE producto_id = %s
            """, (
                item['fisico_disponible'],
                item['fisico_mantenimiento'],
                item['fisico_chatarra'],
                item['producto_id']
            ))
            cur.execute("UPDATE inv_conteo_items SET ajuste_aplicado = TRUE WHERE id = %s", (item['id'],))

        cur.execute("UPDATE inv_conteos SET estatus = 'cerrado', updated_at = NOW() WHERE id = %s", (conteo_id,))
        conn.commit()
