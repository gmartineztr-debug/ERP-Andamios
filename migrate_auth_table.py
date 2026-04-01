#!/usr/bin/env python3
"""
Script de migración para agregar columnas faltantes a sys_usuarios
"""

import psycopg2
from dotenv import load_dotenv
import os

# Cargar variables de entorno
load_dotenv()

def migrate_add_email_column():
    """Agrega la columna email si no existe"""
    
    try:
        conn = psycopg2.connect(
            host=os.getenv('SUPABASE_HOST'),
            database=os.getenv('SUPABASE_DB'),
            user=os.getenv('SUPABASE_USER'),
            password=os.getenv('SUPABASE_PASSWORD'),
            port=os.getenv('SUPABASE_PORT', 5432)
        )
        
        cursor = conn.cursor()
        
        print("🔄 Verificando estructura de tabla sys_usuarios...")
        
        # Agregar email si no existe
        try:
            cursor.execute("""
                ALTER TABLE sys_usuarios 
                ADD COLUMN IF NOT EXISTS email TEXT UNIQUE
            """)
            print("✅ Columna 'email' agregada (o ya existe)")
        except Exception as e:
            print(f"⚠️  Columna 'email': {e}")
        
        # Agregar nombre si no existe
        try:
            cursor.execute("""
                ALTER TABLE sys_usuarios 
                ADD COLUMN IF NOT EXISTS nombre TEXT
            """)
            print("✅ Columna 'nombre' agregada (o ya existe)")
        except Exception as e:
            print(f"⚠️  Columna 'nombre': {e}")
        
        # Agregar created_at si no existe
        try:
            cursor.execute("""
                ALTER TABLE sys_usuarios 
                ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            """)
            print("✅ Columna 'created_at' agregada (o ya existe)")
        except Exception as e:
            print(f"⚠️  Columna 'created_at': {e}")
        
        # Agregar updated_at si no existe
        try:
            cursor.execute("""
                ALTER TABLE sys_usuarios 
                ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            """)
            print("✅ Columna 'updated_at' agregada (o ya existe)")
        except Exception as e:
            print(f"⚠️  Columna 'updated_at': {e}")
        
        conn.commit()
        
        # Mostrar tabla actual
        print("\n📋 Estructura actual de sys_usuarios:")
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'sys_usuarios'
            ORDER BY ordinal_position
        """)
        
        cols = cursor.fetchall()
        for col in cols:
            nullable = "NULL" if col[2] == "YES" else "NOT NULL"
            print(f"   {col[0]:20} {col[1]:20} {nullable}")
        
        print("\n✅ Migración completada exitosamente")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    migrate_add_email_column()
