import sys
import os
from datetime import datetime

# Añadir el directorio raíz al path para poder importar utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from utils.db.connection import get_cursor
    import streamlit as st
except ImportError:
    print("Error: No se pudo importar la conexión a la base de datos.")
    print("Asegúrate de ejecutar este script desde la raíz del proyecto o con el entorno virtual activo.")
    sys.exit(1)

# Estructura esperada simplificada (Tablas y Columnas Clave)
SCHEMA_REQUERIDO = {
    "crm_clientes": ["id", "razon_social", "rfc", "activo"],
    "crm_obras": ["id", "folio_obra", "cliente_id", "estatus"],
    "crm_cotizaciones": ["id", "folio", "cliente_id", "estatus"],
    "cat_productos": ["id", "codigo", "nombre", "activo"],
    "inv_master": ["producto_id", "cantidad_disponible", "cantidad_rentada"],
    "ops_contratos": ["id", "folio", "cliente_id", "estatus"],
    "ops_contrato_items": ["id", "contrato_id", "producto_id"],
    "inv_salidas": ["id", "folio", "contrato_id", "estatus"],
    "inv_entradas": ["id", "folio", "tipo_entrada", "estatus"],
    "fab_insumos": ["id", "codigo", "nombre"],
    "fab_ordenes": ["id", "folio", "estatus"],
    "fin_anticipos": ["id", "folio", "contrato_id", "monto"]
}

VISTAS_REQUERIDAS = [
    "v_contratos_por_vencer",
    "v_inv_bitacora",
    "v_estado_cuenta",
    "v_resumen_folio_raiz",
    "v_saldo_en_campo",
    "v_anticipos",
    "v_pagos_por_contrato"
]

FUNCIONES_REQUERIDAS = [
    "generar_folio_obra",
    "generar_folio_cotizacion",
    "generar_folio_contrato",
    "generar_folio_salida",
    "generar_folio_entrada",
    "generar_folio_of",
    "generar_folio_oc",
    "generar_folio_sc",
    "generar_folio_anticipo",
    "get_cadena_renovaciones"
]

def check_alignment():
    print(f"--- DIAGNÓSTICO DE BASE DE DATOS ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ---")
    
    with get_cursor() as (cur, conn):
        errors = 0
        warnings = 0
        
        # 1. Verificar Tablas y Columnas
        print("\n[1] Verificando Tablas y Columnas...")
        for tabla, columnas in SCHEMA_REQUERIDO.items():
            cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = %s)", (tabla,))
            exists = cur.fetchone()['exists']
            
            if not exists:
                print(f"❌ ERROR: Tabla '{tabla}' no existe.")
                errors += 1
                continue
            
            # Verificar columnas
            for col in columnas:
                cur.execute("SELECT EXISTS (SELECT FROM information_schema.columns WHERE table_name = %s AND column_name = %s)", (tabla, col))
                col_exists = cur.fetchone()['exists']
                if not col_exists:
                    print(f"❌ ERROR: Columna '{col}' no existe en tabla '{tabla}'.")
                    errors += 1
            
            if exists:
                print(f"✅ Tabla '{tabla}' OK.")

        # 2. Verificar Vistas
        print("\n[2] Verificando Vistas...")
        for vista in VISTAS_REQUERIDAS:
            cur.execute("SELECT EXISTS (SELECT FROM information_schema.views WHERE table_name = %s)", (vista,))
            exists = cur.fetchone()['exists']
            if exists:
                print(f"✅ Vista '{vista}' OK.")
            else:
                print(f"⚠️ WARNING: Vista '{vista}' no encontrada (podría ser crítica para reportes).")
                warnings += 1

        # 3. Verificar Funciones
        print("\n[3] Verificando Funciones/Procedimientos...")
        for func in FUNCIONES_REQUERIDAS:
            cur.execute("SELECT EXISTS (SELECT FROM information_schema.routines WHERE routine_name = %s)", (func,))
            exists = cur.fetchone()['exists']
            if exists:
                print(f"✅ Función '{func}' OK.")
            else:
                print(f"❌ ERROR: Función '{func}' no encontrada (vital para folios).")
                errors += 1

        print("\n--- RESUMEN ---")
        if errors == 0 and warnings == 0:
            print("🚀 Alineación Perfecta. La base de datos está lista.")
        elif errors == 0:
            print(f"👌 Alineación Funcional con {warnings} advertencias (vistas faltantes).")
        else:
            print(f"⚡ ALERTA: Se encontraron {errors} errores críticos y {warnings} advertencias.")
            print("Se recomienda revisar los esquemas de Supabase.")

if __name__ == "__main__":
    try:
        check_alignment()
    except Exception as e:
        print(f"Error fatal durante el diagnóstico: {e}")
