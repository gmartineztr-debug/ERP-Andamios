# pages/13_usuarios.py
# Módulo de Gestión de Usuarios y Roles

import streamlit as st
import pandas as pd
from utils.database import (
    get_usuarios,
    crear_usuario,
    actualizar_rol_usuario
)
from utils.auth_manager import check_permission
from utils.logger import logger
from datetime import datetime

# Verificar permisos (solo admin)
if not check_permission('admin'):
    st.error("🚫 No tienes permisos para acceder a esta sección.")
    logger.warning(f"ACCESO_DENEGADO: {st.session_state.get('usuario')} intentó acceder a Usuarios")
    st.stop()

st.title(":material/person_add: Gestión de Usuarios")
st.caption("Administra los accesos, roles y permisos de los usuarios del sistema.")
st.divider()

tab_lista, tab_nuevo = st.tabs([
    ":material/group: Lista de Usuarios",
    ":material/person_add: Registrar Nuevo Usuario"
])

# ================================================
# TAB 1 — LISTA DE USUARIOS
# ================================================
with tab_lista:
    st.subheader("Usuarios Registrados")
    
    usuarios = get_usuarios()
    
    if not usuarios:
        st.info("No hay usuarios registrados.")
    else:
        df = pd.DataFrame(usuarios)
        
        # Formatear fecha
        df['created_at'] = pd.to_datetime(df['created_at']).dt.strftime('%d/%m/%Y %H:%M')
        
        # Mostrar tabla
        df_show = df[['id', 'username', 'nombre', 'rol', 'activo', 'created_at']]
        df_show.columns = ['ID', 'Usuario', 'Nombre', 'Rol', 'Activo', 'Fecha Registro']
        
        st.dataframe(df_show, use_container_width=True, hide_index=True)
        
        st.divider()
        
        # Editar roles
        st.markdown("#### Actualizar Permisos / Estatus")
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            opciones_usr = {f"{u['nombre']} ({u['username']})": u for u in usuarios}
            sel_nombre = st.selectbox("Selecciona usuario para modificar", list(opciones_usr.keys()))
            u_sel = opciones_usr[sel_nombre]
            
        with col2:
            roles_disp = ['admin', 'ventas', 'finanzas', 'logistica', 'operador']
            nuevo_rol = st.selectbox(
                "Rol", 
                roles_disp, 
                index=roles_disp.index(u_sel['rol']) if u_sel['rol'] in roles_disp else 4,
                key=f"rol_{u_sel['id']}"
            )
            
        with col3:
            esta_activo = st.checkbox(
                "Activo", 
                value=bool(u_sel['activo']),
                key=f"act_{u_sel['id']}"
            )
            
        if st.button(":material/save: Guardar Cambios", type="primary", use_container_width=True):
            try:
                actualizar_rol_usuario(u_sel['id'], nuevo_rol, esta_activo)
                st.success(f":material/check_circle: Usuario {u_sel['username']} actualizado correctamente.")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error al actualizar: {e}")

# ================================================
# TAB 2 — REGISTRAR NUEVO USUARIO
# ================================================
with tab_nuevo:
    st.subheader("Crear Cuenta")
    
    with st.form("form_nuevo_usuario"):
        col1, col2 = st.columns(2)
        with col1:
            new_username = st.text_input("Nombre de usuario (Login) *")
            new_nombre = st.text_input("Nombre completo *")
        with col2:
            new_pass = st.text_input("Contraseña *", type="password")
            new_rol = st.selectbox("Rol inicial", ['operador', 'ventas', 'finanzas', 'logistica', 'admin'])
            
        submitted = st.form_submit_button(":material/person_add: Registrar Usuario", use_container_width=True)
        
        if submitted:
            if not new_username or not new_pass or not new_nombre:
                st.error("Todos los campos marcados con * son obligatorios.")
            else:
                try:
                    res = crear_usuario(new_username, new_pass, new_nombre, new_rol)
                    if res:
                        st.success(f":material/check_circle: Usuario {new_username} creado con éxito.")
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ Error al crear usuario: {e}")
