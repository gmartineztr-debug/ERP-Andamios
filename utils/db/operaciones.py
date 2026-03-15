from datetime import date
from .connection import get_cursor

# ================================================
# CONTRATOS
# ================================================

def generar_folio_contrato():
    """Genera el siguiente folio de contrato"""
    with get_cursor() as (cur, conn):
        cur.execute("SELECT generar_folio_contrato()")
        return cur.fetchone()['generar_folio_contrato']

def crear_contrato(datos, items):
    """Crea un contrato con sus items"""
    with get_cursor() as (cur, conn):
        cur.execute("""
            INSERT INTO ops_contratos
            (folio, folio_raiz, cotizacion_id, obra_id, cliente_id, tipo_contrato, estatus,
             fecha_contrato, fecha_inicio, fecha_fin, dias_renta,
             subtotal, monto_flete, iva, monto_total,
             anticipo_porcentaje, anticipo_requerido, anticipo_pagado,
             anticipo_referencia, anticipo_fecha_pago, anticipo_estatus,
             pagare_numero, pagare_monto, pagare_firmante,
             pagare_fecha_vencimiento, pagare_firmado,
             contrato_origen_id, notas)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
        """, (
            datos['folio'], datos['folio'], datos.get('cotizacion_id'),
            datos.get('obra_id'), datos['cliente_id'], datos['tipo_contrato'],
            datos['estatus'], datos['fecha_contrato'], datos['fecha_inicio'],
            datos['fecha_fin'], datos['dias_renta'], datos['subtotal'],
            datos['monto_flete'], datos['iva'], datos['monto_total'],
            datos['anticipo_porcentaje'], datos['anticipo_requerido'],
            datos['anticipo_pagado'], datos.get('anticipo_referencia'),
            datos.get('anticipo_fecha_pago'), datos['anticipo_estatus'],
            datos.get('pagare_numero'), datos['pagare_monto'],
            datos.get('pagare_firmante'), datos.get('pagare_fecha_vencimiento'),
            datos['pagare_firmado'], datos.get('contrato_origen_id'), datos.get('notas')
        ))
        contrato_id = cur.fetchone()['id']

        for item in items:
            cur.execute("""
                INSERT INTO ops_contrato_items
                (contrato_id, producto_id, cantidad, precio_unitario, subtotal)
                VALUES (%s, %s, %s, %s, %s)
            """, (contrato_id, item['producto_id'], item['cantidad'], item['precio_unitario'], item['subtotal']))

        if datos.get('cotizacion_id'):
            cur.execute("UPDATE crm_cotizaciones SET estatus = 'en_revision', updated_at = NOW() WHERE id = %s", (datos['cotizacion_id'],))
            
            if datos.get('anticipo_pagado') and float(datos['anticipo_pagado']) > 0:
                cur.execute("SELECT generar_folio_anticipo()")
                folio_ant = cur.fetchone()['generar_folio_anticipo']
                cur.execute("""
                    INSERT INTO fin_anticipos (
                        folio, contrato_id, cliente_id,
                        tipo_pago, monto, fecha_pago,
                        referencia_bancaria, concepto, estatus
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (
                    folio_ant, contrato_id, datos['cliente_id'], 'anticipo',
                    float(datos['anticipo_pagado']),
                    datos.get('anticipo_fecha_pago') or date.today(),
                    datos.get('anticipo_referencia'),
                    'Anticipo inicial al firmar contrato', 'verificado'
                ))

        conn.commit()
        return contrato_id

def get_contratos(estatus=None):
    """Retorna lista de contratos"""
    with get_cursor() as (cur, conn):
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
        res = cur.fetchall()
        return res if res is not None else []

def get_contrato_detalle(contrato_id):
    """Retorna contrato con sus items"""
    with get_cursor() as (cur, conn):
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

        return contrato, items

def actualizar_estatus_contrato(contrato_id, estatus):
    """Actualiza estatus de un contrato"""
    with get_cursor() as (cur, conn):
        cur.execute("UPDATE ops_contratos SET estatus = %s, updated_at = NOW() WHERE id = %s", (estatus, contrato_id))
        conn.commit()

def registrar_anticipo_pago(contrato_id, monto, referencia, fecha_pago):
    """Registra el pago del anticipo"""
    with get_cursor() as (cur, conn):
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

def asignar_obra_contrato(contrato_id, obra_id):
    """Asigna una obra a un contrato existente"""
    with get_cursor() as (cur, conn):
        cur.execute("UPDATE ops_contratos SET obra_id = %s, updated_at = NOW() WHERE id = %s", (obra_id, contrato_id))
        conn.commit()

def crear_contrato_item(datos):
    """Crea un item de contrato"""
    with get_cursor() as (cur, conn):
        cur.execute("""
            INSERT INTO ops_contrato_items
            (contrato_id, producto_id, cantidad, precio_unitario, subtotal)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (datos['contrato_id'], datos['producto_id'], datos['cantidad'], datos['precio_unitario'], datos['subtotal']))
        nuevo_id = cur.fetchone()['id']
        conn.commit()
        return nuevo_id

# ================================================
# RENOVACIONES
# ================================================

def get_contratos_por_vencer():
    """Contratos activos que vencen en los próximos 7 días"""
    with get_cursor() as (cur, conn):
        cur.execute("SELECT * FROM v_contratos_por_vencer")
        return cur.fetchall()

def get_cadena_renovaciones(folio):
    """Retorna cadena completa de renovaciones de un contrato"""
    with get_cursor() as (cur, conn):
        cur.execute("SELECT * FROM get_cadena_renovaciones(%s)", (folio,))
        return cur.fetchall()

def renovar_contrato(contrato_origen_id, datos, items):
    with get_cursor() as (cur, conn):
        cur.execute("SELECT folio_raiz FROM ops_contratos WHERE id = %s", (contrato_origen_id,))
        row = cur.fetchone()
        folio_raiz = row['folio_raiz'] if row else datos['folio']

        cur.execute("""
            INSERT INTO ops_contratos (
                folio, folio_raiz, cotizacion_id, obra_id, cliente_id,
                tipo_contrato, tipo_operacion, estatus,
                fecha_contrato, fecha_inicio, fecha_fin, dias_renta,
                subtotal, monto_flete, aplica_iva, iva, monto_total,
                anticipo_porcentaje, anticipo_requerido, anticipo_pagado,
                anticipo_estatus, pagare_monto, pagare_firmado,
                contrato_origen_id, notas
            ) VALUES (
                %s,%s,%s,%s,%s,
                %s,%s,%s,
                %s,%s,%s,%s,
                %s,%s,%s,%s,%s,
                %s,%s,%s,
                %s,%s,%s,
                %s,%s
            ) RETURNING id
        """, (
            datos['folio'], folio_raiz, datos.get('cotizacion_id'),
            datos.get('obra_id'), datos['cliente_id'], datos['tipo_contrato'],
            'renovacion', 'activo', datos['fecha_contrato'],
            datos['fecha_inicio'], datos['fecha_fin'], datos['dias_renta'],
            datos['subtotal'], datos.get('monto_flete', 0),
            datos.get('aplica_iva', True), datos['iva'], datos['monto_total'],
            datos.get('anticipo_porcentaje', 50), datos.get('anticipo_requerido', 0),
            0, 'pendiente', datos.get('pagare_monto', 0),
            False, contrato_origen_id, datos.get('notas')
        ))
        nuevo_id = cur.fetchone()['id']

        for item in items:
            cur.execute("""
                INSERT INTO ops_contrato_items
                (contrato_id, producto_id, cantidad, precio_unitario, subtotal)
                VALUES (%s, %s, %s, %s, %s)
            """, (nuevo_id, item['producto_id'], item['cantidad'], item['precio_unitario'], item['subtotal']))

        cur.execute("UPDATE ops_contratos SET estatus = 'renovado', updated_at = NOW() WHERE id = %s", (contrato_origen_id,))
        conn.commit()
        return nuevo_id

# ================================================
# ESTADO DE CUENTA
# ================================================

def get_estado_cuenta_folio_raiz(folio_raiz):
    """Todos los contratos de una cadena por folio raíz"""
    with get_cursor() as (cur, conn):
        cur.execute("SELECT * FROM v_estado_cuenta WHERE folio_raiz = %s ORDER BY fecha_contrato", (folio_raiz,))
        return cur.fetchall()

def get_resumen_folio_raiz(folio_raiz):
    """Resumen financiero de una cadena por folio raíz"""
    with get_cursor() as (cur, conn):
        cur.execute("SELECT * FROM v_resumen_folio_raiz WHERE folio_raiz = %s", (folio_raiz,))
        return cur.fetchone()

def get_folios_raiz_cliente(cliente_id):
    """Todos los folios raíz de un cliente"""
    with get_cursor() as (cur, conn):
        cur.execute("""
            SELECT * FROM v_resumen_folio_raiz
            WHERE cliente_nombre IN (SELECT razon_social FROM crm_clientes WHERE id = %s)
            ORDER BY fecha_inicio DESC
        """, (cliente_id,))
        return cur.fetchall()

def get_todos_folios_raiz():
    """Todos los folios raíz existentes"""
    with get_cursor() as (cur, conn):
        cur.execute("SELECT * FROM v_resumen_folio_raiz ORDER BY fecha_inicio DESC")
        return cur.fetchall()
