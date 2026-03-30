from .connection import get_cursor
import bcrypt
from typing import Optional, List, Dict

# ================================================
# HASHING DE CONTRASEÑAS CON BCRYPT
# ================================================

def hash_password(password: str) -> str:
    """
    Genera un hash seguro de contraseña usando bcrypt.
    
    Args:
        password: Contraseña en texto plano
        
    Returns:
        Hash bcrypt (incluye salt internamente)
    """
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verifica si una contraseña coincide con su hash bcrypt.
    
    Args:
        password: Contraseña en texto plano
        password_hash: Hash bcrypt almacenado en BD
        
    Returns:
        True si la contraseña es válida
    """
    try:
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    except Exception:
        return False


# ================================================
# GESTIÓN DE USUARIOS
# ================================================

def create_auth_table_if_not_exists() -> None:
    """Crea la tabla de usuarios si no existe"""
    with get_cursor() as (cur, conn):
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sys_usuarios (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                nombre TEXT,
                email TEXT UNIQUE,
                rol TEXT NOT NULL DEFAULT 'usuario',
                activo BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


def get_usuario_por_username(username: str) -> Optional[Dict]:
    """
    Busca un usuario por su nombre de usuario.
    
    Args:
        username: Nombre de usuario
        
    Returns:
        Diccionario con datos del usuario o None
    """
    with get_cursor() as (cur, conn):
        cur.execute(
            "SELECT * FROM sys_usuarios WHERE username = %s AND activo = TRUE",
            (username,)
        )
        return cur.fetchone()


def crear_usuario_inicial(username: str, password: str, nombre: str, rol: str = 'admin') -> Optional[int]:
    """
    Crea un usuario inicial (usado para el primer admin).
    
    Args:
        username: Nombre de usuario
        password: Contraseña en texto plano
        nombre: Nombre completo
        rol: Rol del usuario (admin, gerencia, ventas, etc.)
        
    Returns:
        ID del usuario creado o None
    """
    password_hash = hash_password(password)
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


def validar_credenciales(username: str, password: str) -> Optional[Dict]:
    """
    Valida si las credenciales son correctas.
    
    Args:
        username: Nombre de usuario
        password: Contraseña en texto plano
        
    Returns:
        Diccionario con datos del usuario si son válidas, None caso contrario
    """
    user = get_usuario_por_username(username)
    if not user:
        return None
    
    if verify_password(password, user['password_hash']):
        return user
    return None


def get_usuarios() -> List[Dict]:
    """
    Obtiene la lista de todos los usuarios registrados.
    
    Returns:
        Lista de diccionarios con datos de usuarios
    """
    with get_cursor() as (cur, conn):
        cur.execute("""
            SELECT id, username, nombre, email, rol, activo, created_at 
            FROM sys_usuarios 
            ORDER BY created_at DESC
        """)
        return cur.fetchall() or []


def crear_usuario(username: str, password: str, nombre: str, rol: str = 'usuario', email: str = None) -> Optional[int]:
    """
    Crea un nuevo usuario en el sistema.
    
    Args:
        username: Nombre de usuario único
        password: Contraseña en texto plano
        nombre: Nombre completo
        rol: Rol del usuario
        email: Email del usuario (opcional)
        
    Returns:
        ID del usuario creado o None si falla
    """
    password_hash = hash_password(password)
    with get_cursor() as (cur, conn):
        cur.execute("""
            INSERT INTO sys_usuarios (username, password_hash, nombre, rol, email)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (username, password_hash, nombre, rol, email))
        res = cur.fetchone()
        conn.commit()
        return res['id'] if res else None


def actualizar_rol_usuario(usuario_id: int, nuevo_rol: str, activo: bool = True) -> bool:
    """
    Actualiza el rol y estatus de un usuario.
    
    Args:
        usuario_id: ID del usuario
        nuevo_rol: Nuevo rol
        activo: Si el usuario debe estar activo
        
    Returns:
        True si la actualización fue exitosa
    """
    with get_cursor() as (cur, conn):
        cur.execute("""
            UPDATE sys_usuarios 
            SET rol = %s, activo = %s, updated_at = NOW()
            WHERE id = %s
        """, (nuevo_rol, activo, usuario_id))
        conn.commit()
        return True


def cambiar_password(usuario_id: int, password_actual: str, password_nueva: str) -> bool:
    """
    Cambia la contraseña de un usuario tras validar la actual.
    
    Args:
        usuario_id: ID del usuario
        password_actual: Contraseña actual en texto plano
        password_nueva: Nueva contraseña en texto plano
        
    Returns:
        True si el cambio fue exitoso
    """
    with get_cursor() as (cur, conn):
        # Obtener hash actual
        cur.execute("SELECT password_hash FROM sys_usuarios WHERE id = %s", (usuario_id,))
        user = cur.fetchone()
        
        if not user or not verify_password(password_actual, user['password_hash']):
            return False
        
        # Generar nuevo hash y actualizar
        nuevo_hash = hash_password(password_nueva)
        cur.execute("""
            UPDATE sys_usuarios 
            SET password_hash = %s, updated_at = NOW()
            WHERE id = %s
        """, (nuevo_hash, usuario_id))
        conn.commit()
        return True
