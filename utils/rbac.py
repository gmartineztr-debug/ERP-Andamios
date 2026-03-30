"""
Control de Acceso Basado en Roles (RBAC) - Role-Based Access Control
Proporciona decorators y funciones para validar permisos de usuario.
"""

from functools import wraps
from typing import Callable, Optional, List
import streamlit as st
from utils.logger import log_action, logger


def require_role(roles_requeridos: str | List[str]):
    """
    Decorator que valida que el usuario tenga uno de los roles requeridos.
    Si no tiene permiso, muestra error y detiene la ejecución.
    
    Uso:
        @require_role('admin')
        def admin_only_function():
            st.write("Solo admins ven esto")
        
        @require_role(['admin', 'gerencia'])
        def admin_or_manager():
            st.write("Admins o gerentes ven esto")
    
    Args:
        roles_requeridos: String o lista de strings con roles permitidos
    """
    # Normalizar a lista
    if isinstance(roles_requeridos, str):
        roles_requeridos = [roles_requeridos]
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Validar que usuario esté autenticado
            if 'usuario' not in st.session_state:
                st.error("❌ Debes estar autenticado. Inicia sesión primero.")
                st.stop()
            
            usuario = st.session_state.get('usuario')
            rol_usuario = st.session_state.get('rol', 'usuario')
            
            # Validar que tenga rol requerido
            if rol_usuario.lower() not in [r.lower() for r in roles_requeridos]:
                st.error(
                    f"🚫 **No tienes permisos para acceder a esta función.**\n\n"
                    f"Usuario: {usuario}\n"
                    f"Rol: {rol_usuario}\n"
                    f"Requerido: {', '.join(roles_requeridos)}"
                )
                logger.warning(
                    f"ACCESO_DENEGADO — {usuario} ({rol_usuario}) intentó acceder a {func.__name__}"
                )
                st.stop()
            
            # Log de acceso exitoso
            logger.info(f"ACCESO_PERMITIDO — {usuario} ejecutó {func.__name__}")
            
            # Ejecutar función
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def require_permission(permiso: str):
    """
    Decorator que valida un permiso específico.
    (Para futura expansión de granularidad.)
    
    Args:
        permiso: Nombre del permiso (ej: 'crear_contrato', 'editar_precio')
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            usuario = st.session_state.get('usuario', 'unknown')
            
            # Aquí se integraría con una tabla de permisos_por_rol
            # Por ahora, solo loguea
            logger.info(f"PERMISO_VERIFICADO — {usuario} en {func.__name__} requiere {permiso}")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def check_permission(rol_o_usuario: str) -> bool:
    """
    Versión no-decorator para validaciones inline.
    
    Uso:
        if check_permission('admin'):
            st.button("Eliminar usuario")
        else:
            st.warning("Solo admins pueden eliminar")
    
    Args:
        rol_o_usuario: Rol o username a validar
        
    Returns:
        True si usuario tiene el rol/permiso, False caso contrario
    """
    usuario = st.session_state.get('usuario')
    rol_usuario = st.session_state.get('rol', 'usuario')
    
    # Comparar por rol o por usuario
    return rol_usuario.lower() == rol_o_usuario.lower() or usuario == rol_o_usuario


def get_usuario_actual() -> Optional[dict]:
    """Retorna datos del usuario autenticado"""
    return {
        'usuario': st.session_state.get('usuario'),
        'rol': st.session_state.get('rol'),
        'id': st.session_state.get('usuario_id')
    }


def get_roles_permitidos(usuario_rol: str) -> List[str]:
    """
    Retorna permisos/funciones disponibles según el rol.
    Esto es una guía; la validación real ocurre en los decorators.
    """
    permisos_por_rol = {
        'admin': [
            'crear_cliente', 'editar_cliente', 'eliminar_cliente',
            'crear_producto', 'editar_producto',
            'aprobar_cotizacion', 'rechazar_cotizacion',
            'crear_contrato', 'editar_contrato', 'cancelar_contrato',
            'cambiar_estatus', 'ver_reportes', 'gestionar_usuarios',
            'editar_configuracion', 'ver_logs'
        ],
        'gerencia': [
            'crear_cliente', 'editar_cliente',
            'crear_cotizacion', 'editar_cotizacion', 'aprobar_cotizacion',
            'crear_contrato', 'ver_reportes',
            'ver_metricas', 'exportar_datos'
        ],
        'ventas': [
            'crear_cliente', 'editar_cliente',
            'crear_cotizacion', 'editar_cotizacion',
            'crear_contrato'
        ],
        'logistica': [
            'crear_hoja_salida', 'editar_hoja_salida',
            'crear_hoja_entrada', 'editar_hoja_entrada',
            'ver_inventario'
        ],
        'fabricacion': [
            'crear_orden_fabricacion', 'editar_orden_fabricacion',
            'crear_bom', 'editar_bom',
            'registrar_insumo'
        ],
        'usuario': [
            'ver_mis_datos'
        ]
    }
    
    return permisos_por_rol.get(usuario_rol.lower(), [])
