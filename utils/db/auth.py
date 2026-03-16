from .connection import get_cursor
import hashlib

def create_auth_table_if_not_exists():
    """Crea la tabla de usuarios si no existe"""
    with get_cursor() as (cur, conn):
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sys_usuarios (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                nombre TEXT,
                rol TEXT NOT NULL DEFAULT 'operador',
                activo BOOLEAN DEFAULT True,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

def get_usuario_por_username(username):
    """Busca un usuario por su nombre de usuario"""
    with get_cursor() as (cur, conn):
        cur.execute("SELECT * FROM sys_usuarios WHERE username = %s AND activo = True", (username,))
        return cur.fetchone()

def crear_usuario_inicial(username, password, nombre, rol='admin'):
    """Crea un usuario inicial (usado para el primer admin)"""
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    with get_cursor() as (cur, conn):
        cur.execute("""
            INSERT INTO sys_usuarios (username, password_hash, nombre, rol)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (username) DO NOTHING
            RETURNING id
        """, (username, password_hash, nombre, rol))
        res = cur.fetchone()
        conn.commit()
        return res['id'] if res else None

def validar_credenciales(username, password):
    """Valida si las credenciales son correctas"""
    user = get_usuario_por_username(username)
    if not user:
        return None
    
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    if user['password_hash'] == password_hash:
        return user
    return None
