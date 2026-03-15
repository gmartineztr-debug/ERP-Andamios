import streamlit as st
from .connection import get_cursor

def get_dashboard_metricas():
    """Métricas principales del dashboard"""
    with get_cursor() as (cur, conn):
        cur.execute("SELECT * FROM v_dashboard_metricas")
        return cur.fetchone()

def get_facturacion_mensual():
    """Facturación agregada de los últimos 6 meses"""
    with get_cursor() as (cur, conn):
        cur.execute("SELECT * FROM v_facturacion_mensual")
        return cur.fetchall()

def get_stock_critico():
    """Productos por debajo del stock mínimo configurado"""
    with get_cursor() as (cur, conn):
        cur.execute("SELECT * FROM v_stock_critico")
        return cur.fetchall()

def get_contratos_proximos(dias=30):
    """Listado de vencimientos cercanos"""
    with get_cursor() as (cur, conn):
        cur.execute("SELECT * FROM v_contratos_proximos_30 WHERE dias_restantes <= %s ORDER BY dias_restantes", (dias,))
        return cur.fetchall()

def get_facturacion_periodo(fecha_inicio, fecha_fin):
    """Métricas financieras en un rango de fechas específico"""
    with get_cursor() as (cur, conn):
        cur.execute("""
            SELECT
                COUNT(*) AS total_contratos,
                COALESCE(SUM(monto_total), 0) AS facturacion,
                COALESCE(SUM(COALESCE(anticipo_pagado, 0)), 0) AS cobrado,
                COALESCE(SUM(monto_total - COALESCE(anticipo_pagado, 0)), 0) AS por_cobrar
            FROM ops_contratos
            WHERE fecha_contrato BETWEEN %s AND %s AND estatus NOT IN ('cancelado')
        """, (fecha_inicio, fecha_fin))
        return cur.fetchone()
