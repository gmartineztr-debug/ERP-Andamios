#!/usr/bin/env python3
"""
Script para resetear contraseña de admin después de migración SHA256 → bcrypt
Ejecutar desde el directorio raíz del proyecto
"""

import bcrypt
import psycopg2
from dotenv import load_dotenv
import os

# Cargar variables de entorno
load_dotenv()

def reset_admin_password():
    """Resetea la contraseña de admin a contraseña temporal segura."""
    
    # Nueva contraseña temporal
    new_password = "Admin@2026Temporal"
    
    # Generar hash bcrypt
    salt = bcrypt.gensalt(rounds=12)
    password_hash = bcrypt.hashpw(new_password.encode('utf-8'), salt).decode('utf-8')
    
    print(f"🔄 Reseteando contraseña de admin...")
    print(f"   Hash generado: {password_hash[:30]}...")
    
    try:
        # Conectar a la base de datos (Supabase)
        conn = psycopg2.connect(
            host=os.getenv('SUPABASE_HOST'),
            database=os.getenv('SUPABASE_DB'),
            user=os.getenv('SUPABASE_USER'),
            password=os.getenv('SUPABASE_PASSWORD'),
            port=os.getenv('SUPABASE_PORT', 5432)
        )
        
        cursor = conn.cursor()
        
        # Actualizar contraseña de admin
        update_query = """
            UPDATE sys_usuarios 
            SET password_hash = %s 
            WHERE username = 'admin'
            RETURNING id, username
        """
        
        cursor.execute(update_query, (password_hash,))
        result = cursor.fetchone()
        
        conn.commit()
        
        if result:
            print(f"✅ Contraseña actualizada exitosamente")
            print(f"   Usuario: {result[1]}")
            print(f"\n📝 NUEVA CONTRASEÑA TEMPORAL:")
            print(f"   ➜ Usuario: admin")
            print(f"   ➜ Contraseña: {new_password}")
            print(f"\n⚠️  IMPORTANTE: Cambiar esta contraseña después de login")
        else:
            print("❌ Usuario 'admin' no encontrado en la base de datos")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print(f"\nVerifica que:")
        print(f"  1. El archivo .env existe y tiene SUPABASE_HOST, SUPABASE_DB, SUPABASE_USER, SUPABASE_PASSWORD")
        print(f"  2. La tabla sys_usuarios existe")
        print(f"  3. Tienes permisos para actualizar la tabla")

if __name__ == "__main__":
    reset_admin_password()
