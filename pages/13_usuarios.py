# pages/13_usuarios.py
# Módulo de Gestión de Usuarios y Roles

import streamlit as st
import pandas as pd
from utils.database import (
    get_usuarios,
    crear_usuario,
    actualizar_rol_usuario,
    cambiar_password,
    cambiar_password_admin,
    eliminar_usuario
)
from utils.auth_manager import check_permission
from utils.logger import logger
from datetime import datetime
from utils.validators import PasswordChange, PasswordReset, UsuarioCreate, get_password_requirements
from pydantic import ValidationError

# Verificar permisos (solo admin)
if not check_permission('admin'):
    st.error("🚫 No tienes permisos para acceder a esta sección.")
    logger.warning(f"ACCESO_DENEGADO: {st.session_state.get('usuario')} intentó acceder a Usuarios")
    st.stop()

st.title(":material/person_add: Gestión de Usuarios")
st.caption("Administra los accesos, roles y permisos de los usuarios del sistema.")
st.divider()

tab_lista, tab_nuevo, tab_mi_password, tab_password, tab_eliminar = st.tabs([
    ":material/group: Lista de Usuarios",
    ":material/person_add: Registrar Nuevo Usuario",
    ":material/lock: Mi Contraseña",
    ":material/lock_reset: Resetear Contraseña de Otros",
    ":material/delete: Eliminar Usuario"
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
    
    # Mostrar requisitos
    with st.expander("📋 Requisitos de Contraseña"):
        reqs = get_password_requirements()
        for req in reqs['requisitos']:
            st.write(req)
        st.caption(f"Caracteres especiales permitidos: {reqs['especiales_permitidos']}")
    
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
                st.error("⚠️ Todos los campos marcados con * son obligatorios.")
            else:
                # Validar contraseña con Pydantic
                try:
                    UsuarioCreate(username=new_username, email="temp@example.com", password=new_pass)
                    # Si pasa validación, crear usuario
                    res = crear_usuario(new_username, new_pass, new_nombre, new_rol)
                    if res:
                        st.success(f":material/check_circle: Usuario {new_username} creado con éxito.")
                        st.rerun()
                except ValidationError as e:
                    for error in e.errors():
                        st.error(f"❌ {error['msg']}")

# ================================================
# TAB 3 — MI CONTRASEÑA (usuario actual)
# ================================================
with tab_mi_password:
    st.subheader("Cambiar Mi Contraseña")
    st.info("Cambia la contraseña de tu cuenta.")
    
    # Mostrar requisitos
    with st.expander("📋 Requisitos de Contraseña"):
        reqs = get_password_requirements()
        for req in reqs['requisitos']:
            st.write(req)
        st.caption(f"Caracteres especiales permitidos: {reqs['especiales_permitidos']}")
    
    with st.form("form_mi_password"):
        current_pass = st.text_input("Contraseña Actual *", type="password")
        new_password = st.text_input("Nueva Contraseña *", type="password")
        confirm_pass = st.text_input("Confirmar Nueva Contraseña *", type="password")
        submitted = st.form_submit_button(":material/lock: Cambiar Contraseña", type="primary", use_container_width=True)
        
        if submitted:
            if not current_pass or not new_password or not confirm_pass:
                st.error("⚠️ Completa todos los campos.")
            elif new_password != confirm_pass:
                st.error("⚠️ Las contraseñas no coinciden.")
            else:
                # Validar con Pydantic
                try:
                    PasswordChange(password_actual=current_pass, password_nueva=new_password)
                    # Pasar validación, intentar cambiar
                    success = cambiar_password(
                        st.session_state.get('usuario_id'),
                        current_pass,
                        new_password
                    )
                    if success:
                        logger.info(f"PASSWORD_CHANGED — {st.session_state.get('usuario')} cambió su contraseña")
                        st.success(":material/check_circle: Contraseña actualizada correctamente.")
                    else:
                        st.error("❌ La contraseña actual es incorrecta.")
                except ValidationError as e:
                    for error in e.errors():
                        st.error(f"❌ {error['msg']}")

# ================================================
# TAB 4 — RESETEAR CONTRASEÑA DE OTROS USUARIOS
# ================================================
with tab_password:
    st.subheader("Resetear Contraseña de Usuario")
    st.info("Como administrador, puedes resetear la contraseña de cualquier usuario sin necesidad de validar la contraseña anterior.")
    
    # Mostrar requisitos
    with st.expander("📋 Requisitos de Contraseña"):
        reqs = get_password_requirements()
        for req in reqs['requisitos']:
            st.write(req)
        st.caption(f"Caracteres especiales permitidos: {reqs['especiales_permitidos']}")
    
    usuarios = get_usuarios()
    
    if not usuarios:
        st.error("No hay usuarios registrados.")
    else:
        # Excluir al usuario actual
        usuarios_otros = [u for u in usuarios if u['username'] != st.session_state.get('usuario')]
        
        if not usuarios_otros:
            st.info("No hay otros usuarios para modificar.")
        else:
            opciones_usr = {f"{u['nombre']} ({u['username']})": u for u in usuarios_otros}
            sel_nombre = st.selectbox("Selecciona usuario", list(opciones_usr.keys()), key="sel_pwd")
            u_sel = opciones_usr[sel_nombre]
            
            st.warning(f"⚠️ Vas a cambiar la contraseña de **{u_sel['username']}**")
            
            with st.form("form_cambiar_password"):
                new_password = st.text_input("Nueva contraseña *", type="password")
                confirm_pass = st.text_input("Confirmar contraseña *", type="password")
                submitted = st.form_submit_button(":material/lock: Resetear Contraseña", type="primary", use_container_width=True)
                
                if submitted:
                    if not new_password or not confirm_pass:
                        st.error("⚠️ Completa todos los campos.")
                    elif new_password != confirm_pass:
                        st.error("⚠️ Las contraseñas no coinciden.")
                    else:
                        # Validar con Pydantic
                        try:
                            PasswordReset(password_nueva=new_password)
                            cambiar_password_admin(u_sel['id'], new_password)
                            logger.info(f"PASSWORD_RESET — admin cambió contraseña de {u_sel['username']}")
                            st.success(f":material/check_circle: Contraseña de {u_sel['username']} actualizada correctamente.")
                            st.rerun()
                        except ValidationError as e:
                            for error in e.errors():
                                st.error(f"❌ {error['msg']}")

# ================================================
# TAB 5 — ELIMINAR USUARIO
# ================================================
with tab_eliminar:
    st.subheader("Eliminar Usuario del Sistema")
    st.error("⚠️ Esta acción es **irreversible**. El usuario será eliminado completamente del sistema.")
    
    usuarios = get_usuarios()
    
    if not usuarios:
        st.error("No hay usuarios registrados.")
    else:
        # Excluir al usuario actual
        usuarios_otros = [u for u in usuarios if u['username'] != st.session_state.get('usuario')]
        
        if not usuarios_otros:
            st.info("No hay otros usuarios para eliminar.")
        else:
            opciones_usr = {f"{u['nombre']} ({u['username']})": u for u in usuarios_otros}
            sel_nombre = st.selectbox("Selecciona usuario a eliminar", list(opciones_usr.keys()), key="sel_delete")
            u_sel = opciones_usr[sel_nombre]
            
            st.error(f"⚠️ **Vas a eliminar a {u_sel['username']}** — Esta acción no se puede deshacer")
            
            # Confirmación adicional
            col1, col2 = st.columns(2)
            
            with col1:
                confirm_text = st.text_input(
                    f"Escribe '{u_sel['username']}' para confirmar la eliminación",
                    key="confirm_user_delete"
                )
            
            with col2:
                st.write("")
                st.write("")
                delete_btn = st.button(
                    ":material/delete: Eliminar Usuario Permanentemente",
                    type="secondary",
                    use_container_width=True,
                    disabled=(confirm_text != u_sel['username'])
                )
            
            if delete_btn and confirm_text == u_sel['username']:
                try:
                    eliminar_usuario(u_sel['id'])
                    logger.info(f"USER_DELETED — admin eliminó usuario {u_sel['username']}")
                    st.success(f":material/check_circle: Usuario {u_sel['username']} eliminado correctamente.")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error al eliminar: {e}")
