"""
Módulo de autenticación y autorización del ERP.
Maneja login, sessionstate y validación de permisos.
"""

import streamlit as st
from utils.database import (
    validar_credenciales, 
    create_auth_table_if_not_exists, 
    crear_usuario_inicial
)
from utils.logger import log_login, log_error, logger


def init_auth() -> None:
    """
    Inicializa la sesión de autenticación.
    Se ejecuta una sola vez al cargar la app.
    """
    # Inicializar variables de sesión
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'usuario' not in st.session_state:
        st.session_state.usuario = None
    if 'usuario_id' not in st.session_state:
        st.session_state.usuario_id = None
    if 'rol' not in st.session_state:
        st.session_state.rol = 'usuario'
    
    # Asegurar tabla de usuarios existe
    try:
        create_auth_table_if_not_exists()
        # Crear usuario admin por defecto si es la primera vez
        crear_usuario_inicial('admin', 'admin123', 'Administrador del Sistema', 'admin')
        logger.info("Sistema de autenticación inicializado correctamente")
    except Exception as e:
        log_error(e, "init_auth - Error inicializando autenticación")
        st.error("Error al inicializar autenticación. Contacta al administrador.")


def login_screen() -> None:
    """
    Renderiza la pantalla de login.
    """
    st.markdown("""
        <style>
        [data-testid="stAppViewContainer"] {
            background-color: #0F172A !important;
        }
        [data-testid="stAppViewContainer"] .stText, 
        [data-testid="stAppViewContainer"] h1, 
        [data-testid="stAppViewContainer"] h2,
        [data-testid="stAppViewContainer"] h3,
        [data-testid="stAppViewContainer"] p {
            color: #FFFFFF !important;
        }
        div[data-testid="stTextInput"] input,
        div[data-testid="stPasswordInput"] input {
            background-color: #F1F5F9 !important;
            color: #0F172A !important;
            border: 1px solid #E2E8F0 !important;
            border-radius: 6px !important;
            padding: 6px 8px !important;
        }
        button[data-testid="stButton"] {
            background-color: #1F6FEB !important;
            color: #FFFFFF !important;
            border-radius: 8px !important;
            border: none !important;
            padding: 8px 12px !important;
        }
        button[data-testid="stButton"]:hover {
            filter: brightness(0.95) !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    with st.container():
        st.title("🔐 Acceso al ERP")
        st.info("Ingresa tus credenciales para continuar.")
        
        with st.form("login_form"):
            username = st.text_input("Usuario")
            password = st.text_input("Contraseña", type="password")
            submitted = st.form_submit_button(
                "Iniciar Sesión", 
                use_container_width=True, 
                type="primary"
            )
        
        if submitted:
            if not username or not password:
                st.error("❌ Por favor completa todos los campos.")
            else:
                user = validar_credenciales(username, password)
                
                if user:
                    # Login exitoso
                    st.session_state.authenticated = True
                    st.session_state.usuario = user['username']
                    st.session_state.usuario_id = user['id']
                    st.session_state.rol = user['rol']
                    
                    log_login(username, True)
                    
                    st.success("✅ ¡Bienvenido!")
                    st.rerun()
                else:
                    # Login fallido
                    log_login(username, False)
                    st.error("❌ Usuario o contraseña incorrectos.")


def logout() -> None:
    """
    Cierra la sesión actual del usuario.
    """
    usuario = st.session_state.get('usuario', 'unknown')
    logger.info(f"LOGOUT — {usuario}")
    
    st.session_state.authenticated = False
    st.session_state.usuario = None
    st.session_state.usuario_id = None
    st.session_state.rol = 'usuario'
    st.rerun()


def check_permission(required_role: str = 'usuario') -> bool:
    """
    Verifica si el usuario actual tiene un rol específico.
    
    Args:
        required_role: Rol requerido (ej: 'admin', 'ventas')
        
    Returns:
        True si el usuario tiene el rol, False caso contrario
    """
    if not st.session_state.authenticated:
        return False
    
    user_rol = st.session_state.get('rol', 'usuario')
    return user_rol.lower() == required_role.lower()


def get_usuario_actual() -> dict:
    """
    Retorna información del usuario autenticado.
    
    Returns:
        Diccionario con usuario, rol e id
    """
    return {
        'usuario': st.session_state.get('usuario'),
        'rol': st.session_state.get('rol'),
        'id': st.session_state.get('usuario_id')
    }
