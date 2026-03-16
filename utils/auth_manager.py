import streamlit as st
from utils.database import validar_credenciales, create_auth_table_if_not_exists, crear_usuario_inicial

def init_auth():
    """Inicializa la sesión de autenticación"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user_info' not in st.session_state:
        st.session_state.user_info = None
        
    # Asegurar tabla de usuarios
    try:
        create_auth_table_if_not_exists()
        # Crear usuario admin por defecto si no hay ninguno (primera vez)
        crear_usuario_inicial('admin', 'admin123', 'Administrador Sistema', 'admin')
    except Exception as e:
        print(f"Error inicializando auth: {e}")

def login_screen():
    """Muestra la interfaz de login"""
    st.markdown("""
        <style>
        .login-container {
            max-width: 400px;
            margin: 100px auto;
            padding: 2rem;
            border-radius: 10px;
            background-color: #f8f9fa;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        </style>
    """, unsafe_allow_html=True)
    
    with st.container():
        st.title("🔐 Acceso al ERP")
        st.info("Ingresa tus credenciales para continuar.")
        
        with st.form("login_form"):
            username = st.text_input("Usuario")
            password = st.text_input("Contraseña", type="password")
            submitted = st.form_submit_button("Iniciar Sesión", use_container_width=True, type="primary")
            
            if submitted:
                if not username or not password:
                    st.error("Por favor completa todos los campos.")
                else:
                    user = validar_credenciales(username, password)
                    if user:
                        st.session_state.authenticated = True
                        st.session_state.user_info = user
                        st.success("¡Bienvenido!")
                        st.rerun()
                    else:
                        st.error("Usuario o contraseña incorrectos.")

def logout():
    """Cierra la sesión actual"""
    st.session_state.authenticated = False
    st.session_state.user_info = None
    st.rerun()

def check_permission(required_role='operador'):
    """Verifica si el usuario tiene permiso (True/False)"""
    if not st.session_state.authenticated:
        return False
    
    user_rol = st.session_state.user_info.get('rol', 'operador')
    if required_role == 'admin' and user_rol != 'admin':
        return False
    return True
