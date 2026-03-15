from .connection import get_cursor

def generar_folio_anticipo():
    """Genera folio para pago/anticipo"""
    with get_cursor() as (cur, conn):
        cur.execute("SELECT generar_folio_anticipo()")
        return cur.fetchone()['generar_folio_anticipo']

def crear_anticipo(datos):
    """Registra un nuevo pago y actualiza el saldo del contrato"""
    with get_cursor() as (cur, conn):
        cur.execute("""
            INSERT INTO fin_anticipos (
                folio, contrato_id, cliente_id,
                tipo_pago, monto, fecha_pago,
                referencia_bancaria, concepto, estatus
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
        """, (
            datos['folio'], datos['contrato_id'], datos['cliente_id'],
            datos['tipo_pago'], datos['monto'], datos['fecha_pago'],
            datos.get('referencia_bancaria'), datos.get('concepto'),
            datos.get('estatus', 'registrado')
        ))
        anticipo_id = cur.fetchone()['id']

        cur.execute("""
            UPDATE ops_contratos SET
                anticipo_pagado = (SELECT COALESCE(SUM(monto), 0) FROM fin_anticipos WHERE contrato_id = %s AND estatus != 'cancelado'),
                anticipo_estatus = CASE
                    WHEN (SELECT COALESCE(SUM(monto), 0) FROM fin_anticipos WHERE contrato_id = %s AND estatus != 'cancelado') >= anticipo_requerido THEN 'completo'
                    WHEN (SELECT COALESCE(SUM(monto), 0) FROM fin_anticipos WHERE contrato_id = %s AND estatus != 'cancelado') > 0 THEN 'parcial'
                    ELSE 'pendiente'
                END,
                updated_at = NOW()
            WHERE id = %s
        """, (datos['contrato_id'], datos['contrato_id'], datos['contrato_id'], datos['contrato_id']))

        conn.commit()
        return anticipo_id

def get_anticipos(contrato_id=None, cliente_id=None, estatus=None):
    """Lista de pagos con filtros"""
    with get_cursor() as (cur, conn):
        filtros = []
        valores = []
        if contrato_id:
            filtros.append("contrato_id = %s"); valores.append(contrato_id)
        if cliente_id:
            filtros.append("cliente_id = %s"); valores.append(cliente_id)
        if estatus:
            filtros.append("estatus = %s"); valores.append(estatus)
        where = ("WHERE " + " AND ".join(filtros)) if filtros else ""
        cur.execute(f"SELECT * FROM v_anticipos {where}", valores)
        return cur.fetchall()

def get_pagos_por_contrato(contrato_id):
    """Resumen de pagos de un contrato específico"""
    with get_cursor() as (cur, conn):
        cur.execute("SELECT * FROM v_pagos_por_contrato WHERE contrato_id = %s", (contrato_id,))
        return cur.fetchone()

def get_contratos_con_saldo():
    """Contratos activos con saldo pendiente acumulado"""
    with get_cursor() as (cur, conn):
        cur.execute("SELECT * FROM v_pagos_por_contrato WHERE saldo_pendiente > 0 ORDER BY saldo_pendiente DESC")
        return cur.fetchall()

def actualizar_estatus_anticipo(anticipo_id, estatus):
    """Cambia estatus de pago y recalcula el contrato"""
    with get_cursor() as (cur, conn):
        cur.execute("UPDATE fin_anticipos SET estatus = %s, updated_at = NOW() WHERE id = %s RETURNING contrato_id", (estatus, anticipo_id))
        contrato_id = cur.fetchone()['contrato_id']

        cur.execute("""
            UPDATE ops_contratos SET
                anticipo_pagado = (SELECT COALESCE(SUM(monto), 0) FROM fin_anticipos WHERE contrato_id = %s AND estatus != 'cancelado'),
                anticipo_estatus = CASE
                    WHEN (SELECT COALESCE(SUM(monto), 0) FROM fin_anticipos WHERE contrato_id = %s AND estatus != 'cancelado') >= anticipo_requerido THEN 'completo'
                    WHEN (SELECT COALESCE(SUM(monto), 0) FROM fin_anticipos WHERE contrato_id = %s AND estatus != 'cancelado') > 0 THEN 'parcial'
                    ELSE 'pendiente'
                END,
                updated_at = NOW()
            WHERE id = %s
        """, (contrato_id, contrato_id, contrato_id, contrato_id))
        conn.commit()
