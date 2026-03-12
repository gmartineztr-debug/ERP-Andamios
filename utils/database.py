# utils/database.py
# Conexión centralizada a Supabase

from datetime import date

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
    try:
        query = "SELECT * FROM crm_clientes"
        if solo_activos:
            query += " WHERE activo = TRUE"
            query += " ORDER BY razon_social"
            cur.execute(query)
            return cur.fetchall()
    finally:
        cur.close()
        conn.close()


def get_cliente_by_id(cliente_id):
    """Retorna un cliente por su ID"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("SELECT * FROM crm_clientes WHERE id = %s", (cliente_id,))
        cliente = cur.fetchone()
        return cliente

    finally:
        cur.close()
        conn.close()


def crear_cliente(datos):
    """Crea un nuevo cliente"""
    conn = get_connection()
    cur = conn.cursor()
    try:
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
        return nuevo_id

    finally:
        cur.close()
        conn.close()


def actualizar_cliente(cliente_id, datos):
    """Actualiza un cliente existente"""
    conn = get_connection()
    cur = conn.cursor()
    try:
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
    finally:
        cur.close()
        conn.close()


# ================================================
# PRODUCTOS
# ================================================

def get_productos(solo_activos=True):
    """Retorna lista de productos"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
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
            return cur.fetchall()
    finally:
        cur.close()
        conn.close()

# ================================================
# PRODUCTOS - CRUD
# ================================================

def get_producto_by_id(producto_id):
    """Retorna un producto por su ID"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
        SELECT p.*, i.cantidad_disponible, i.cantidad_rentada,
        i.cantidad_mantenimiento, i.cantidad_chatarra, i.stock_minimo
        FROM cat_productos p
        LEFT JOIN inv_master i ON p.id = i.producto_id
        WHERE p.id = %s
        """, (producto_id,))
        producto = cur.fetchone()
        return producto

    finally:
        cur.close()
        conn.close()


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
    try:
        cur.execute("SELECT generar_folio_cotizacion()")
        folio = cur.fetchone()[0]
        return folio

    finally:
        cur.close()
        conn.close()


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
    try:
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
    finally:
        cur.close()
        conn.close()


def get_cotizacion_detalle(cotizacion_id):
    """Retorna una cotización con sus items"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:

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
    finally:
        cur.close()
        conn.close()

def actualizar_estatus_cotizacion(cotizacion_id, estatus):
    """Actualiza el estatus de una cotización"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
        UPDATE crm_cotizaciones
        SET estatus = %s, updated_at = NOW()
        WHERE id = %s
        """, (estatus, cotizacion_id))
        conn.commit()
    finally:
        cur.close()
        conn.close()
    
# ================================================
# OBRAS
# ================================================

def generar_folio_obra():
    """Genera el siguiente folio de obra"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT generar_folio_obra()")
        folio = cur.fetchone()[0]
        return folio

    finally:
        cur.close()
        conn.close()


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
    try:
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
    finally:
        cur.close()
        conn.close()


def get_obra_by_id(obra_id):
    """Retorna una obra por su ID"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
        SELECT o.*, c.razon_social as cliente_nombre
        FROM crm_obras o
        JOIN crm_clientes c ON o.cliente_id = c.id
        WHERE o.id = %s
        """, (obra_id,))
        obra = cur.fetchone()
        return obra

    finally:
        cur.close()
        conn.close()


def actualizar_estatus_obra(obra_id, estatus):
    """Actualiza el estatus de una obra"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
        UPDATE crm_obras
        SET estatus = %s, updated_at = NOW()
        WHERE id = %s
        """, (estatus, obra_id))
        conn.commit()
    finally:
        cur.close()
        conn.close()


def get_contratos_por_obra(obra_id):
    """Retorna contratos asociados a una obra"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
        SELECT *
        FROM ops_contratos
        WHERE obra_id = %s
        ORDER BY created_at DESC
        """, (obra_id,))
        contratos = cur.fetchall()
        return contratos

    finally:
        cur.close()
        conn.close()


def actualizar_total_facturado_obra(obra_id):
    """Recalcula el total facturado de una obra"""
    conn = get_connection()
    cur = conn.cursor()
    try:
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
    finally:
        cur.close()
        conn.close()
    
def get_obras_por_cliente(cliente_id):
    """Retorna obras activas de un cliente específico"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
        SELECT id, folio_obra, nombre_proyecto
        FROM crm_obras
        WHERE cliente_id = %s
        AND estatus = 'activa'
        ORDER BY created_at DESC
        """, (cliente_id,))
        obras = cur.fetchall()
        return obras

    finally:
        cur.close()
        conn.close()

# ================================================
# CONTRATOS
# ================================================

def generar_folio_contrato():
    """Genera el siguiente folio de contrato"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT generar_folio_contrato()")
        folio = cur.fetchone()[0]
        return folio

    finally:
        cur.close()
        conn.close()


def get_cotizaciones_aprobadas():
    """Retorna cotizaciones aprobadas sin contrato"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
        SELECT c.*, cl.razon_social as cliente_nombre
        FROM crm_cotizaciones c
        JOIN crm_clientes cl ON c.cliente_id = cl.id
        WHERE c.estatus = 'aprobada'
        AND c.id NOT IN (
        SELECT cotizacion_id FROM ops_contratos
        WHERE cotizacion_id IS NOT NULL
        )
        ORDER BY c.created_at DESC
        """)
        cotizaciones = cur.fetchall()
        return cotizaciones

    finally:
        cur.close()
        conn.close()


def crear_contrato(datos, items):
    """Crea un contrato con sus items"""
    conn = get_connection()
    cur = conn.cursor()
    try:
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
            datos['folio'],
            datos['folio'],          # folio_raiz = su propio folio
            datos.get('cotizacion_id'),
            datos.get('obra_id'),
            datos['cliente_id'],
            datos['tipo_contrato'],
            datos['estatus'],
            datos['fecha_contrato'],
            datos['fecha_inicio'],
            datos['fecha_fin'],
            datos['dias_renta'],
            datos['subtotal'],
            datos['monto_flete'],
            datos['iva'],
            datos['monto_total'],
            datos['anticipo_porcentaje'],
            datos['anticipo_requerido'],
            datos['anticipo_pagado'],
            datos.get('anticipo_referencia'),
            datos.get('anticipo_fecha_pago'),
            datos['anticipo_estatus'],
            datos.get('pagare_numero'),
            datos['pagare_monto'],
            datos.get('pagare_firmante'),
            datos.get('pagare_fecha_vencimiento'),
            datos['pagare_firmado'],
            datos.get('contrato_origen_id'),
            datos.get('notas')
        ))
        contrato_id = cur.fetchone()[0]

        for item in items:
            cur.execute("""
                INSERT INTO ops_contrato_items
                (contrato_id, producto_id, cantidad, precio_unitario, subtotal)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                contrato_id,
                item['producto_id'],
                item['cantidad'],
                item['precio_unitario'],
                item['subtotal']
            ))

# Actualizar estatus cotización a 'en_revision'
        if datos.get('cotizacion_id'):
            cur.execute("""
                UPDATE crm_cotizaciones
                SET estatus = 'en_revision', updated_at = NOW()
                WHERE id = %s
            """, (datos['cotizacion_id'],))

            # Crear registro en fin_anticipos si hay pago inicial
            if datos.get('anticipo_pagado') and float(datos['anticipo_pagado']) > 0:
                cur.execute("SELECT generar_folio_anticipo()")
                folio_ant = cur.fetchone()[0]
                cur.execute("""
                    INSERT INTO fin_anticipos (
                        folio, contrato_id, cliente_id,
                        tipo_pago, monto, fecha_pago,
                        referencia_bancaria, concepto, estatus
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (
                    folio_ant,
                    contrato_id,
                    datos['cliente_id'],
                    'anticipo',
                    float(datos['anticipo_pagado']),
                    datos.get('anticipo_fecha_pago') or date.today(),
                    datos.get('anticipo_referencia'),
                    'Anticipo inicial al firmar contrato',
                    'verificado'
                ))

            conn.commit()
            return contrato_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()


def get_contratos(estatus=None):
    """Retorna lista de contratos"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
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
            return cur.fetchall()
    finally:
        cur.close()
        conn.close()


def get_contrato_detalle(contrato_id):
    """Retorna contrato con sus items"""
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

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
    finally:
        cur.close()
        conn.close()

def actualizar_estatus_contrato(contrato_id, estatus):
    """Actualiza estatus de un contrato"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
        UPDATE ops_contratos
        SET estatus = %s, updated_at = NOW()
        WHERE id = %s
        """, (estatus, contrato_id))
        conn.commit()
    finally:
        cur.close()
        conn.close()


def registrar_anticipo_pago(contrato_id, monto, referencia, fecha_pago):
    """Registra el pago del anticipo"""
    conn = get_connection()
    cur = conn.cursor()
    try:
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
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()


def asignar_obra_contrato(contrato_id, obra_id):
    """Asigna una obra a un contrato existente"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
        UPDATE ops_contratos
        SET obra_id = %s, updated_at = NOW()
        WHERE id = %s
        """, (obra_id, contrato_id))
        conn.commit()
    finally:
        cur.close()
        conn.close()
    
# ================================================
# HOJAS DE SALIDA
# ================================================

def generar_folio_salida():
    """Genera el siguiente folio de hoja de salida"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT generar_folio_salida()")
        folio = cur.fetchone()[0]
        return folio

    finally:
        cur.close()
        conn.close()


def get_contratos_sin_hs_completa():
    """Retorna contratos activos con entregas pendientes"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
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
        contratos = cur.fetchall()
        return contratos

    finally:
        cur.close()
        conn.close()


def get_cantidad_enviada_por_contrato(contrato_id, producto_id):
    """Retorna cantidad ya enviada de un producto en un contrato"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
        SELECT COALESCE(SUM(si.cantidad), 0)
        FROM inv_salida_items si
        JOIN inv_salidas s ON si.salida_id = s.id
        WHERE s.contrato_id = %s
        AND si.producto_id = %s
        AND s.estatus != 'cancelada'
        """, (contrato_id, producto_id))
        cantidad = cur.fetchone()[0]
        return int(cantidad)

    finally:
        cur.close()
        conn.close()


def crear_hoja_salida(datos, items):
    """Crea una hoja de salida con sus items"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        peso_total = sum(i['peso_total'] for i in items)
        cur.execute("""
            INSERT INTO inv_salidas
            (folio, contrato_id, cliente_id, obra_id,
             chofer, observaciones, estatus, fecha_salida,
             peso_total, contacto_entrega, telefono_entrega)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            datos['folio'],
            datos['contrato_id'],
            datos['cliente_id'],
            datos.get('obra_id'),
            datos.get('chofer'),
            datos.get('observaciones'),
            datos['estatus'],
            datos['fecha_salida'],
            peso_total,
            datos.get('contacto_entrega'),
            datos.get('telefono_entrega')
        ))
        salida_id = cur.fetchone()[0]

        for item in items:
            cur.execute("""
                INSERT INTO inv_salida_items
                (salida_id, producto_id, cantidad, peso_unitario, peso_total)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                salida_id,
                item['producto_id'],
                item['cantidad'],
                item['peso_unitario'],
                item['peso_total']
            ))

        conn.commit()
        return salida_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()

def get_hojas_salida(contrato_id=None):
    """Retorna hojas de salida"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
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
            salidas = cur.fetchall()
            return salidas

    finally:
        cur.close()
        conn.close()


def get_hoja_salida_detalle(salida_id):
    """Retorna hoja de salida con sus items"""
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

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
    finally:
        cur.close()
        conn.close()

def actualizar_estatus_salida(salida_id, estatus, fecha_entrega=None):
    """Actualiza estatus de hoja de salida"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE inv_salidas SET
                estatus        = %s,
                fecha_entrega  = %s,
                updated_at     = NOW()
            WHERE id = %s
        """, (estatus, fecha_entrega, salida_id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()

# ================================================
# PROVEEDORES
# ================================================

def get_proveedores():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
        SELECT * FROM prov_proveedores
        WHERE activo = TRUE
        ORDER BY nombre
        """)
        proveedores = cur.fetchall()
        return proveedores

    finally:
        cur.close()
        conn.close()


def crear_proveedor(datos):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO prov_proveedores
            (nombre, rfc, contacto, telefono, email, direccion)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            datos['nombre'],
            datos.get('rfc'),
            datos.get('contacto'),
            datos.get('telefono'),
            datos.get('email'),
            datos.get('direccion')
        ))
        id_ = cur.fetchone()[0]
        conn.commit()
        return id_
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()


# ================================================
# HOJAS DE ENTRADA
# ================================================

def generar_folio_entrada():
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT generar_folio_entrada()")
        folio = cur.fetchone()[0]
        return folio

    finally:
        cur.close()
        conn.close()


def get_saldo_en_campo(contrato_id):
    """Retorna saldo de equipo en campo para un contrato"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
        SELECT * FROM v_saldo_en_campo
        WHERE contrato_id = %s
        AND saldo_en_campo > 0
        ORDER BY codigo
        """, (contrato_id,))
        saldo = cur.fetchall()
        return saldo

    finally:
        cur.close()
        conn.close()


def get_contratos_con_equipo_en_campo():
    """Contratos activos que tienen equipo en campo"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
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
        contratos = cur.fetchall()
        return contratos

    finally:
        cur.close()
        conn.close()


def crear_hoja_entrada(datos, items):
    """Crea HE con sus items"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO inv_entradas
            (folio, tipo_entrada, estatus,
             contrato_id, cliente_id, obra_id,
             proveedor_id, num_factura, costo_total,
             lote_fabricacion, fecha_entrada, notas)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            datos['folio'],
            datos['tipo_entrada'],
            datos.get('estatus', 'pendiente'),
            datos.get('contrato_id'),
            datos.get('cliente_id'),
            datos.get('obra_id'),
            datos.get('proveedor_id'),
            datos.get('num_factura'),
            datos.get('costo_total', 0),
            datos.get('lote_fabricacion'),
            datos['fecha_entrada'],
            datos.get('notas')
        ))
        entrada_id = cur.fetchone()[0]

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
                entrada_id,
                item['producto_id'],
                item.get('cantidad_total', 0),
                item.get('costo_unitario', 0),
                item.get('cantidad_buena', 0),
                item.get('cantidad_danada', 0),
                item.get('cantidad_perdida', 0),
                item.get('cantidad_chatarra', 0),
                item.get('peso_unitario', 0),
                item.get('peso_total', 0)
            ))

        conn.commit()
        return entrada_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()


def get_hojas_entrada(tipo=None):
    """Retorna hojas de entrada"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
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
        if tipo:
            query += " WHERE e.tipo_entrada = %s"
            cur.execute(query + " ORDER BY e.created_at DESC", (tipo,))
        else:
            cur.execute(query + " ORDER BY e.created_at DESC")
            entradas = cur.fetchall()
            return entradas

    finally:
        cur.close()
        conn.close()


def get_hoja_entrada_detalle(entrada_id):
    """Retorna HE con sus items"""
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

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
    finally:
        cur.close()
        conn.close()

def actualizar_estatus_entrada(entrada_id, estatus, fecha_cierre=None):
    """Actualiza estatus — el trigger actualiza inventario al cerrar"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE inv_entradas SET
                estatus      = %s,
                fecha_cierre = %s,
                updated_at   = NOW()
            WHERE id = %s
        """, (estatus, fecha_cierre, entrada_id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()


def vincular_contrato_venta_entrada(entrada_id, contrato_venta_id):
    """Liga el contrato de venta generado a la HE"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE inv_entradas SET
                contrato_venta_id = %s,
                updated_at        = NOW()
            WHERE id = %s
        """, (contrato_venta_id, entrada_id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()


def get_productos_por_codigo(codigo):
    """Busca producto por código exacto"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
        SELECT p.*, im.cantidad_disponible
        FROM cat_productos p
        LEFT JOIN inv_master im ON p.id = im.producto_id
        WHERE p.codigo = %s AND p.activo = TRUE
        """, (codigo,))
        producto = cur.fetchone()
        return producto

    finally:
        cur.close()
        conn.close()

def crear_contrato_item(datos):
    """Crea un item de contrato"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO ops_contrato_items
            (contrato_id, producto_id, cantidad, precio_unitario, subtotal)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (
            datos['contrato_id'],
            datos['producto_id'],
            datos['cantidad'],
            datos['precio_unitario'],
            datos['subtotal']
        ))
        id_ = cur.fetchone()[0]
        conn.commit()
        return id_
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()
        
# ================================================
# FABRICACIÓN — INSUMOS
# ================================================

def get_insumos():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
        SELECT * FROM fab_insumos
        WHERE activo = TRUE
        ORDER BY nombre
        """)
        insumos = cur.fetchall()
        return insumos

    finally:
        cur.close()
        conn.close()


def crear_insumo(datos):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO fab_insumos (codigo, nombre, unidad, descripcion)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (
            datos['codigo'],
            datos['nombre'],
            datos['unidad'],
            datos.get('descripcion')
        ))
        id_ = cur.fetchone()[0]
        conn.commit()
        return id_
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()


# ================================================
# FABRICACIÓN — BOM
# ================================================

def get_bom_producto(producto_id):
    """Retorna receta de un producto"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
        SELECT b.*, i.nombre AS insumo_nombre,
        i.codigo AS insumo_codigo,
        i.unidad
        FROM fab_bom b
        JOIN fab_insumos i ON b.insumo_id = i.id
        WHERE b.producto_id = %s
        ORDER BY i.nombre
        """, (producto_id,))
        bom = cur.fetchall()
        return bom

    finally:
        cur.close()
        conn.close()


def guardar_bom_producto(producto_id, items):
    """Reemplaza BOM completo de un producto"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        # Eliminar BOM existente
        cur.execute(
            "DELETE FROM fab_bom WHERE producto_id = %s",
            (producto_id,)
        )
        # Insertar nuevo BOM
        for item in items:
            cur.execute("""
                INSERT INTO fab_bom
                (producto_id, insumo_id, cantidad_por_pieza, notas)
                VALUES (%s, %s, %s, %s)
            """, (
                producto_id,
                item['insumo_id'],
                item['cantidad_por_pieza'],
                item.get('notas')
            ))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()


def calcular_materiales_of(items_of):
    """
    Calcula materiales necesarios para una OF
    items_of: [{'producto_id': x, 'cantidad': y}, ...]
    Retorna: [{'insumo_id', 'nombre', 'unidad', 'cantidad_necesaria'}]
    """
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        materiales = {}
        for item in items_of:
            cur.execute("""
                SELECT b.insumo_id, i.codigo, i.nombre, i.unidad,
                       b.cantidad_por_pieza
                FROM fab_bom b
                JOIN fab_insumos i ON b.insumo_id = i.id
                WHERE b.producto_id = %s
            """, (item['producto_id'],))
            bom = cur.fetchall()

            for linea in bom:
                ins_id = linea['insumo_id']
                cant   = float(linea['cantidad_por_pieza']) * item['cantidad']
                if ins_id in materiales:
                    materiales[ins_id]['cantidad_necesaria'] += cant
                else:
                    materiales[ins_id] = {
                        'insumo_id'        : ins_id,
                        'codigo'           : linea['codigo'],
                        'nombre'           : linea['nombre'],
                        'unidad'           : linea['unidad'],
                        'cantidad_necesaria': cant,
                        'costo_unitario'   : 0,
                        'subtotal'         : 0
                    }

        return list(materiales.values())


# ================================================
# FABRICACIÓN — ÓRDENES DE FABRICACIÓN
# ================================================
    finally:
        cur.close()
        conn.close()

def generar_folio_of():
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT generar_folio_of()")
        folio = cur.fetchone()[0]
        return folio

    finally:
        cur.close()
        conn.close()


def crear_orden_fabricacion(datos, items):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO fab_ordenes
            (folio, estatus, fecha_apertura, fecha_estimada, notas)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (
            datos['folio'],
            datos.get('estatus', 'abierta'),
            datos['fecha_apertura'],
            datos.get('fecha_estimada'),
            datos.get('notas')
        ))
        orden_id = cur.fetchone()[0]

        for item in items:
            cur.execute("""
                INSERT INTO fab_orden_items
                (orden_id, producto_id, cantidad_solicitada)
                VALUES (%s, %s, %s)
            """, (
                orden_id,
                item['producto_id'],
                item['cantidad']
            ))

        conn.commit()
        return orden_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()


def get_ordenes_fabricacion():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
        SELECT f.*,
        COUNT(fi.id) AS total_productos
        FROM fab_ordenes f
        LEFT JOIN fab_orden_items fi ON fi.orden_id = f.id
        GROUP BY f.id
        ORDER BY f.created_at DESC
        """)
        ordenes = cur.fetchall()
        return ordenes

    finally:
        cur.close()
        conn.close()


def get_orden_fabricacion_detalle(orden_id):
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cur.execute("""
            SELECT * FROM fab_ordenes WHERE id = %s
        """, (orden_id,))
        orden = cur.fetchone()

        cur.execute("""
            SELECT fi.*, p.nombre AS producto_nombre,
                   p.codigo, p.peso_kg
            FROM fab_orden_items fi
            JOIN cat_productos p ON fi.producto_id = p.id
            WHERE fi.orden_id = %s
        """, (orden_id,))
        items = cur.fetchall()

        return orden, items
    finally:
        cur.close()
        conn.close()

def actualizar_estatus_of(orden_id, estatus,
                           fecha_cierre=None, items_fabricados=None):
    """
    Actualiza estatus OF.
    Si estatus=terminada, actualiza cantidad_fabricada por item.
    """
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE fab_ordenes SET
                estatus      = %s,
                fecha_cierre = %s,
                updated_at   = NOW()
            WHERE id = %s
        """, (estatus, fecha_cierre, orden_id))

        if estatus == 'terminada' and items_fabricados:
            for item in items_fabricados:
                cur.execute("""
                    UPDATE fab_orden_items SET
                        cantidad_fabricada = %s
                    WHERE orden_id = %s AND producto_id = %s
                """, (
                    item['cantidad_fabricada'],
                    orden_id,
                    item['producto_id']
                ))

            conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()


def get_ordenes_terminadas_sin_he():
    """OF terminadas que aún no tienen HE generada"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
        SELECT f.*
        FROM fab_ordenes f
        WHERE f.estatus = 'terminada'
        AND NOT EXISTS (
        SELECT 1 FROM inv_entradas e
        WHERE e.orden_fabricacion_id = f.id
        )
        ORDER BY f.fecha_cierre DESC
        """)
        ordenes = cur.fetchall()
        return ordenes

    finally:
        cur.close()
        conn.close()


# ================================================
# FABRICACIÓN — ÓRDENES DE COMPRA
# ================================================

def generar_folio_oc():
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT generar_folio_oc()")
        folio = cur.fetchone()[0]
        return folio

    finally:
        cur.close()
        conn.close()


def crear_orden_compra(datos, items):
    conn = get_connection()
    cur = conn.cursor()
    try:
        total = sum(
            float(i['cantidad']) * float(i['costo_unitario'])
            for i in items
        )
        cur.execute("""
            INSERT INTO fab_ordenes_compra
            (folio, orden_id, proveedor_id, estatus,
             fecha_oc, fecha_estimada_entrega, total, notas)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            datos['folio'],
            datos.get('orden_id'),
            datos.get('proveedor_id'),
            datos.get('estatus', 'borrador'),
            datos['fecha_oc'],
            datos.get('fecha_estimada_entrega'),
            total,
            datos.get('notas')
        ))
        oc_id = cur.fetchone()[0]

        for item in items:
            subtotal = float(item['cantidad']) * float(item['costo_unitario'])
            cur.execute("""
                INSERT INTO fab_oc_items
                (oc_id, insumo_id, cantidad, costo_unitario, subtotal)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                oc_id,
                item['insumo_id'],
                item['cantidad'],
                item['costo_unitario'],
                subtotal
            ))

        conn.commit()
        return oc_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()


def get_ordenes_compra():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
        SELECT oc.*,
        f.folio  AS of_folio,
        p.nombre AS proveedor_nombre
        FROM fab_ordenes_compra oc
        LEFT JOIN fab_ordenes f        ON oc.orden_id    = f.id
        LEFT JOIN prov_proveedores p   ON oc.proveedor_id = p.id
        ORDER BY oc.created_at DESC
        """)
        ocs = cur.fetchall()
        return ocs

    finally:
        cur.close()
        conn.close()


def get_orden_compra_detalle(oc_id):
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cur.execute("""
            SELECT oc.*,
                   f.folio  AS of_folio,
                   p.nombre AS proveedor_nombre,
                   p.telefono AS proveedor_telefono
            FROM fab_ordenes_compra oc
            LEFT JOIN fab_ordenes f      ON oc.orden_id     = f.id
            LEFT JOIN prov_proveedores p ON oc.proveedor_id = p.id
            WHERE oc.id = %s
        """, (oc_id,))
        oc = cur.fetchone()

        cur.execute("""
            SELECT oi.*, i.nombre AS insumo_nombre,
                   i.codigo, i.unidad
            FROM fab_oc_items oi
            JOIN fab_insumos i ON oi.insumo_id = i.id
            WHERE oi.oc_id = %s
        """, (oc_id,))
        items = cur.fetchall()

        return oc, items
    finally:
        cur.close()
        conn.close()

def actualizar_estatus_oc(oc_id, estatus):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE fab_ordenes_compra SET
                estatus    = %s,
                updated_at = NOW()
            WHERE id = %s
        """, (estatus, oc_id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()
        
# ================================================
# RENOVACIONES
# ================================================

def get_contratos_por_vencer():
    """Contratos activos que vencen en los próximos 7 días"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("SELECT * FROM v_contratos_por_vencer")
        contratos = cur.fetchall()
        return contratos

    finally:
        cur.close()
        conn.close()


def get_cadena_renovaciones(folio):
    """Retorna cadena completa de renovaciones de un contrato"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("SELECT * FROM get_cadena_renovaciones(%s)", (folio,))
        cadena = cur.fetchall()
        return cadena

    finally:
        cur.close()
        conn.close()


def renovar_contrato(contrato_origen_id, datos, items):
    conn = get_connection()
    cur = conn.cursor()
    try:
        # Obtener folio_raiz del contrato origen
        cur.execute("""
            SELECT folio_raiz FROM ops_contratos WHERE id = %s
        """, (contrato_origen_id,))
        row = cur.fetchone()
        folio_raiz = row[0] if row else datos['folio']

        # Crear nuevo contrato heredando folio_raiz
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
            datos['folio'],
            folio_raiz,              # hereda del origen
            datos.get('cotizacion_id'),
            datos.get('obra_id'),
            datos['cliente_id'],
            datos['tipo_contrato'],
            'renovacion',
            'activo',
            datos['fecha_contrato'],
            datos['fecha_inicio'],
            datos['fecha_fin'],
            datos['dias_renta'],
            datos['subtotal'],
            datos.get('monto_flete', 0),
            datos.get('aplica_iva', True),
            datos['iva'],
            datos['monto_total'],
            datos.get('anticipo_porcentaje', 50),
            datos.get('anticipo_requerido', 0),
            0,
            'pendiente',
            datos.get('pagare_monto', 0),
            False,
            contrato_origen_id,
            datos.get('notas')
        ))
        nuevo_id = cur.fetchone()[0]

        # Insertar items
        for item in items:
            cur.execute("""
                INSERT INTO ops_contrato_items
                (contrato_id, producto_id, cantidad, precio_unitario, subtotal)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                nuevo_id,
                item['producto_id'],
                item['cantidad'],
                item['precio_unitario'],
                item['subtotal']
            ))

        # Marcar contrato origen como renovado
        cur.execute("""
            UPDATE ops_contratos SET
                estatus    = 'renovado',
                updated_at = NOW()
            WHERE id = %s
        """, (contrato_origen_id,))

        conn.commit()
        return nuevo_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()

# ================================================
# FOLIO RAÍZ Y ESTADO DE CUENTA
# ================================================

def get_estado_cuenta_folio_raiz(folio_raiz):
    """Todos los contratos de una cadena por folio raíz"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
        SELECT * FROM v_estado_cuenta
        WHERE folio_raiz = %s
        ORDER BY fecha_contrato
        """, (folio_raiz,))
        contratos = cur.fetchall()
        return contratos

    finally:
        cur.close()
        conn.close()


def get_resumen_folio_raiz(folio_raiz):
    """Resumen financiero de una cadena por folio raíz"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
        SELECT * FROM v_resumen_folio_raiz
        WHERE folio_raiz = %s
        """, (folio_raiz,))
        resumen = cur.fetchone()
        return resumen

    finally:
        cur.close()
        conn.close()


def get_folios_raiz_cliente(cliente_id):
    """Todos los folios raíz de un cliente"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
        SELECT * FROM v_resumen_folio_raiz
        WHERE cliente_nombre IN (
        SELECT razon_social FROM crm_clientes WHERE id = %s
        )
        ORDER BY fecha_inicio DESC
        """, (cliente_id,))
        folios = cur.fetchall()
        return folios

    finally:
        cur.close()
        conn.close()


def get_todos_folios_raiz():
    """Todos los folios raíz existentes"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
        SELECT * FROM v_resumen_folio_raiz
        ORDER BY fecha_inicio DESC
        """)
        folios = cur.fetchall()
        return folios

    finally:
        cur.close()
        conn.close()

# ================================================
# DASHBOARD
# ================================================

def get_dashboard_metricas():
    """Métricas principales del dashboard"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("SELECT * FROM v_dashboard_metricas")
        row = cur.fetchone()
        return row

    finally:
        cur.close()
        conn.close()


def get_facturacion_mensual():
    """Facturación de los últimos 6 meses"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("SELECT * FROM v_facturacion_mensual")
        rows = cur.fetchall()
        return rows

    finally:
        cur.close()
        conn.close()


def get_stock_critico():
    """Productos por debajo del stock mínimo"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("SELECT * FROM v_stock_critico")
        rows = cur.fetchall()
        return rows

    finally:
        cur.close()
        conn.close()


def get_contratos_proximos(dias=30):
    """Contratos que vencen en los próximos N días"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
        SELECT * FROM v_contratos_proximos_30
        WHERE dias_restantes <= %s
        ORDER BY dias_restantes
        """, (dias,))
        rows = cur.fetchall()
        return rows

    finally:
        cur.close()
        conn.close()


def get_facturacion_periodo(fecha_inicio, fecha_fin):
    """Facturación entre dos fechas"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
        SELECT
        COUNT(*)                          AS total_contratos,
        COALESCE(SUM(monto_total), 0)     AS facturacion,
        COALESCE(SUM(COALESCE(anticipo_pagado, 0)), 0) AS cobrado,
        COALESCE(SUM(monto_total - COALESCE(anticipo_pagado, 0)), 0) AS por_cobrar
        FROM ops_contratos
        WHERE fecha_contrato BETWEEN %s AND %s
        AND estatus NOT IN ('cancelado')
        """, (fecha_inicio, fecha_fin))
        row = cur.fetchone()
        return row

    finally:
        cur.close()
        conn.close()

# ================================================
# ANTICIPOS / PAGOS
# ================================================

def generar_folio_anticipo():
    """Genera folio PAG-0001"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT generar_folio_anticipo()")
        folio = cur.fetchone()[0]
        return folio

    finally:
        cur.close()
        conn.close()


def crear_anticipo(datos):
    """Registra un pago"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO fin_anticipos (
                folio, contrato_id, cliente_id,
                tipo_pago, monto, fecha_pago,
                referencia_bancaria, concepto, estatus
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
        """, (
            datos['folio'],
            datos['contrato_id'],
            datos['cliente_id'],
            datos['tipo_pago'],
            datos['monto'],
            datos['fecha_pago'],
            datos.get('referencia_bancaria'),
            datos.get('concepto'),
            datos.get('estatus', 'registrado')
        ))
        anticipo_id = cur.fetchone()[0]

        # Actualizar anticipo_pagado y estatus en el contrato
        cur.execute("""
            UPDATE ops_contratos SET
                anticipo_pagado = (
                    SELECT COALESCE(SUM(monto), 0)
                    FROM fin_anticipos
                    WHERE contrato_id = %s
                    AND estatus != 'cancelado'
                ),
                anticipo_estatus = CASE
                    WHEN (
                        SELECT COALESCE(SUM(monto), 0)
                        FROM fin_anticipos
                        WHERE contrato_id = %s
                        AND estatus != 'cancelado'
                    ) >= anticipo_requerido THEN 'completo'
                    WHEN (
                        SELECT COALESCE(SUM(monto), 0)
                        FROM fin_anticipos
                        WHERE contrato_id = %s
                        AND estatus != 'cancelado'
                    ) > 0 THEN 'parcial'
                    ELSE 'pendiente'
                END,
                updated_at = NOW()
            WHERE id = %s
        """, (
            datos['contrato_id'],
            datos['contrato_id'],
            datos['contrato_id'],
            datos['contrato_id']
        ))

        conn.commit()
        return anticipo_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()


def get_anticipos(contrato_id=None, cliente_id=None, estatus=None):
    """Lista de pagos con filtros opcionales"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        filtros = []
        valores = []
        if contrato_id:
            filtros.append("contrato_id = %s")
            valores.append(contrato_id)
        if cliente_id:
            filtros.append("cliente_id = %s")
            valores.append(cliente_id)
        if estatus:
            filtros.append("estatus = %s")
            valores.append(estatus)
        where = ("WHERE " + " AND ".join(filtros)) if filtros else ""
        cur.execute(f"SELECT * FROM v_anticipos {where}", valores)
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


def get_pagos_por_contrato(contrato_id):
    """Resumen de pagos de un contrato"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
        SELECT * FROM v_pagos_por_contrato
        WHERE contrato_id = %s
        """, (contrato_id,))
        row = cur.fetchone()
        return row

    finally:
        cur.close()
        conn.close()


def get_contratos_con_saldo():
    """Contratos activos con saldo pendiente"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
        SELECT * FROM v_pagos_por_contrato
        WHERE saldo_pendiente > 0
        ORDER BY saldo_pendiente DESC
        """)
        rows = cur.fetchall()
        return rows

    finally:
        cur.close()
        conn.close()


def actualizar_estatus_anticipo(anticipo_id, estatus):
    """Cambia estatus de un pago (verificado/cancelado)"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE fin_anticipos SET
                estatus    = %s,
                updated_at = NOW()
            WHERE id = %s
            RETURNING contrato_id
        """, (estatus, anticipo_id))
        contrato_id = cur.fetchone()[0]

        # Recalcular anticipo_pagado en el contrato
        cur.execute("""
            UPDATE ops_contratos SET
                anticipo_pagado = (
                    SELECT COALESCE(SUM(monto), 0)
                    FROM fin_anticipos
                    WHERE contrato_id = %s
                    AND estatus != 'cancelado'
                ),
                anticipo_estatus = CASE
                    WHEN (
                        SELECT COALESCE(SUM(monto), 0)
                        FROM fin_anticipos
                        WHERE contrato_id = %s
                        AND estatus != 'cancelado'
                    ) >= anticipo_requerido THEN 'completo'
                    WHEN (
                        SELECT COALESCE(SUM(monto), 0)
                        FROM fin_anticipos
                        WHERE contrato_id = %s
                        AND estatus != 'cancelado'
                    ) > 0 THEN 'parcial'
                    ELSE 'pendiente'
                END,
                updated_at = NOW()
            WHERE id = %s
        """, (contrato_id, contrato_id, contrato_id, contrato_id))

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()
    
# ================================================
# BITÁCORA DE INVENTARIO
# ================================================

def get_bitacora(producto_id=None, tipo=None, limite=100):
    """Lista de movimientos de inventario"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
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
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


def get_bitacora_producto(producto_id):
    """Historial completo de un producto"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
        SELECT * FROM v_inv_bitacora
        WHERE producto_id = %s
        ORDER BY fecha DESC
        """, (producto_id,))
        rows = cur.fetchall()
        return rows

    finally:
        cur.close()
        conn.close()


def registrar_ajuste_manual(producto_id, notas, usuario="sistema"):
    """Registra un ajuste manual en la bitácora"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO inv_bitacora (
                producto_id, tipo_movimiento,
                referencia_tipo, notas
            ) VALUES (%s, 'ajuste_manual', 'MANUAL', %s)
        """, (producto_id, notas))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()
        
# ================================================
# SOLICITUDES DE CAMBIO DE OF
# ================================================

def generar_folio_sc():
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT generar_folio_sc()")
        folio = cur.fetchone()[0]
        return folio

    finally:
        cur.close()
        conn.close()


def crear_sc(datos, items, materiales):
    """Crea una Solicitud de Cambio de OF"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO fab_solicitudes_cambio (
                folio, of_origen_id, of_nueva_id,
                motivo, avance_descr, estatus, fecha, notas
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
        """, (
            datos['folio'],
            datos['of_origen_id'],
            datos.get('of_nueva_id'),
            datos['motivo'],
            datos.get('avance_descr'),
            datos.get('estatus', 'borrador'),
            datos['fecha'],
            datos.get('notas')
        ))
        sc_id = cur.fetchone()[0]

        # Items — avance por producto
        for item in items:
            cur.execute("""
                INSERT INTO fab_sc_items (
                    sc_id, producto_id,
                    cantidad_planeada, cantidad_fabricada
                ) VALUES (%s,%s,%s,%s)
            """, (
                sc_id,
                item['producto_id'],
                item['cantidad_planeada'],
                item['cantidad_fabricada']
            ))

        # Materiales — balance
        for mat in materiales:
            cur.execute("""
                INSERT INTO fab_sc_materiales (
                    sc_id, insumo_id,
                    cantidad_estimada_uso, cantidad_real_uso,
                    cantidad_sobrante, destino_sobrante, notas
                ) VALUES (%s,%s,%s,%s,%s,%s,%s)
            """, (
                sc_id,
                mat['insumo_id'],
                mat.get('cantidad_estimada_uso', 0),
                mat.get('cantidad_real_uso'),
                mat.get('cantidad_sobrante'),
                mat.get('destino_sobrante', 'desconocido'),
                mat.get('notas')
            ))

        # Marcar OF origen como modificada
        cur.execute("""
            UPDATE fab_ordenes SET
                estatus    = 'modificada',
                updated_at = NOW()
            WHERE id = %s
        """, (datos['of_origen_id'],))

        conn.commit()
        return sc_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()


def get_solicitudes_cambio():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("SELECT * FROM v_solicitudes_cambio")
        rows = cur.fetchall()
        return rows

    finally:
        cur.close()
        conn.close()


def get_sc_detalle(sc_id):
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT * FROM v_solicitudes_cambio WHERE id = %s
        """, (sc_id,))
        sc = cur.fetchone()

        cur.execute("""
            SELECT
                si.*, p.codigo, p.nombre AS producto_nombre
            FROM fab_sc_items si
            JOIN cat_productos p ON si.producto_id = p.id
            WHERE si.sc_id = %s
        """, (sc_id,))
        items = cur.fetchall()

        cur.execute("""
            SELECT
                sm.*, i.codigo, i.nombre AS insumo_nombre, i.unidad
            FROM fab_sc_materiales sm
            JOIN fab_insumos i ON sm.insumo_id = i.id
            WHERE sm.sc_id = %s
        """, (sc_id,))
        materiales = cur.fetchall()

        return sc, items, materiales
    finally:
        cur.close()
        conn.close()

def actualizar_estatus_sc(sc_id, estatus, of_nueva_id=None):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE fab_solicitudes_cambio SET
                estatus    = %s,
                of_nueva_id = COALESCE(%s, of_nueva_id),
                updated_at = NOW()
            WHERE id = %s
        """, (estatus, of_nueva_id, sc_id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()


# ================================================
# CONTEO FÍSICO
# ================================================

def generar_folio_conteo():
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT generar_folio_conteo()")
        folio = cur.fetchone()[0]
        return folio

    finally:
        cur.close()
        conn.close()


def crear_conteo(datos):
    """Crea un conteo físico y precarga con valores del sistema"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO inv_conteos (
                folio, fecha, periodo,
                estatus, responsable, notas
            ) VALUES (%s,%s,%s,%s,%s,%s)
            RETURNING id
        """, (
            datos['folio'],
            datos['fecha'],
            datos['periodo'],
            'en_proceso',
            datos.get('responsable'),
            datos.get('notas')
        ))
        conteo_id = cur.fetchone()[0]

        # Precargar todos los productos con valores actuales del sistema
        cur.execute("""
            INSERT INTO inv_conteo_items (
                conteo_id, producto_id,
                sistema_disponible, sistema_mantenimiento, sistema_chatarra,
                fisico_disponible, fisico_mantenimiento, fisico_chatarra
            )
            SELECT
                %s,
                im.producto_id,
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
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()


def get_conteos():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("SELECT * FROM v_conteos ORDER BY fecha DESC")
        rows = cur.fetchall()
        return rows

    finally:
        cur.close()
        conn.close()


def get_conteo_items(conteo_id):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
        SELECT
        ci.*,
        p.codigo,
        p.nombre AS producto_nombre
        FROM inv_conteo_items ci
        JOIN cat_productos p ON ci.producto_id = p.id
        WHERE ci.conteo_id = %s
        ORDER BY p.codigo
        """, (conteo_id,))
        rows = cur.fetchall()
        return rows

    finally:
        cur.close()
        conn.close()


def actualizar_conteo_item(item_id, fisico_disp, fisico_mant,
                            fisico_chat, justificacion):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE inv_conteo_items SET
                fisico_disponible    = %s,
                fisico_mantenimiento = %s,
                fisico_chatarra      = %s,
                justificacion        = %s
            WHERE id = %s
        """, (fisico_disp, fisico_mant, fisico_chat, justificacion, item_id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()


def aplicar_ajuste_conteo(conteo_id):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
            SELECT * FROM inv_conteo_items
            WHERE conteo_id = %s
            AND ajuste_aplicado = FALSE
            AND (diff_disponible != 0
                OR diff_mantenimiento != 0
                OR diff_chatarra != 0)
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
            cur.execute("""
                UPDATE inv_conteo_items SET
                    ajuste_aplicado = TRUE
                WHERE id = %s
            """, (item['id'],))

        cur.execute("""
            UPDATE inv_conteos SET
                estatus    = 'cerrado',
                updated_at = NOW()
            WHERE id = %s
        """, (conteo_id,))

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()
        
def get_of_detalle(of_id):
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT *
            FROM fab_ordenes
            WHERE id = %s
        """, (of_id,))
        of_data = cur.fetchone()

        cur.execute("""
            SELECT
                oi.*,
                p.codigo,
                p.nombre,
                p.id AS producto_id
            FROM fab_orden_items oi
            JOIN cat_productos p ON oi.producto_id = p.id
            WHERE oi.orden_id = %s
        """, (of_id,))
        items = cur.fetchall()

        return of_data, items
    finally:
        cur.close()
        conn.close()