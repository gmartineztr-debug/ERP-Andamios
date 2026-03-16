# pages/01_clientes.py
# Módulo de gestión de clientes

import streamlit as st
from utils.database import (
    get_clientes,
    crear_cliente,
    get_cliente_by_id,
    actualizar_cliente
)
from utils.reporting import export_to_csv, export_to_pdf
import datetime
from datetime import datetime, date



st.title("👥 Clientes")
st.divider()

# ================================================
# TABS PRINCIPALES
# ================================================
tab_lista, tab_nuevo, tab_editar = st.tabs([
    "📋 Lista De Clientes",
    "➕ Nuevo Cliente",
    "✏️ Editar Cliente"
])

# ================================================
# TAB 1 — LISTA
# ================================================
with tab_lista:
    st.subheader("Clientes registrados")

    col1, col2 = st.columns([3, 1])
    with col2:
        mostrar_inactivos = st.checkbox("Mostrar inactivos")

    clientes = get_clientes(solo_activos=not mostrar_inactivos)

    if not clientes:
        st.info("No hay clientes registrados.")
    else:
        import pandas as pd
        df = pd.DataFrame(clientes)
        df = df[[
            'id', 'razon_social', 'rfc', 'contacto',
            'telefono', 'email', 'tipo_cliente',
            'limite_credito', 'activo'
        ]]
        df.columns = [
            'ID', 'Razón Social', 'RFC', 'Contacto',
            'Teléfono', 'Email', 'Tipo',
            'Límite Crédito', 'Activo'
        ]
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.caption(f"Total: {len(clientes)} clientes")

        # Botones de exportación
        col_ex_a, col_ex_b, col_ex_empty = st.columns([1, 1, 3])
        with col_ex_a:
            csv_data = export_to_csv(df)
            st.download_button(
                label="📥 Descargar Excel",
                data=csv_data,
                file_name=f"clientes_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                key="btn_descarga_csv"
            )
        with col_ex_b:
            pdf_data = export_to_pdf(df, title="Listado de Clientes")
            st.download_button(
                label="📄 Descargar PDF",
                data=pdf_data,
                file_name=f"clientes_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                key="btn_descarga_pdf"
            )

# ================================================
# TAB 2 — NUEVO CLIENTE
# ================================================
with tab_nuevo:
    st.subheader("Registrar nuevo cliente")

    with st.form("form_nuevo_cliente", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            razon_social = st.text_input("Razón Social *", placeholder="Empresa SA de CV")
            rfc          = st.text_input("RFC *", placeholder="EMP900101AAA", max_chars=13)
            contacto     = st.text_input("Contacto", placeholder="Nombre del contacto")
            telefono     = st.text_input("Teléfono", placeholder="5551234567")

        with col2:
            email        = st.text_input("Email", placeholder="contacto@empresa.com")
            direccion    = st.text_area("Dirección", placeholder="Calle, Colonia, Ciudad")
            tipo_cliente = st.selectbox("Tipo de cliente", ["regular", "vip", "nuevo"])
            limite_credito = st.number_input(
                "Límite de crédito (MXN)",
                min_value=0.0,
                step=1000.0,
                format="%.2f"
            )

        st.divider()
        submitted = st.form_submit_button("💾 Guardar cliente", type="primary")

        if submitted:
            # Validaciones
            if not razon_social:
                st.error("La razón social es obligatoria.")
            elif not rfc:
                st.error("El RFC es obligatorio.")
            elif len(rfc) < 12:
                st.error("El RFC debe tener 12 o 13 caracteres.")
            else:
                try:
                    nuevo_id = crear_cliente({
                        'razon_social'  : razon_social,
                        'rfc'           : rfc.upper(),
                        'contacto'      : contacto,
                        'telefono'      : telefono,
                        'email'         : email,
                        'direccion'     : direccion,
                        'tipo_cliente'  : tipo_cliente,
                        'limite_credito': limite_credito
                    })
                    st.success(f"✅ Cliente registrado con ID: {nuevo_id}")
                except Exception as e:
                    if "unique" in str(e).lower():
                        st.error("❌ Ya existe un cliente con ese RFC.")
                    else:
                        st.error(f"❌ Error: {e}")

# ================================================
# TAB 3 — EDITAR CLIENTE
# ================================================
with tab_editar:
    st.subheader("Editar cliente existente")

    clientes = get_clientes(solo_activos=False)

    if not clientes:
        st.info("No hay clientes registrados.")
    else:
        opciones = {f"{c['id']} — {c['razon_social']}": c['id'] for c in clientes}
        seleccion = st.selectbox("Selecciona un cliente", list(opciones.keys()))
        cliente_id = opciones[seleccion]
        cliente = get_cliente_by_id(cliente_id)

        if cliente:
            with st.form("form_editar_cliente"):
                col1, col2 = st.columns(2)

                with col1:
                    razon_social = st.text_input("Razón Social *", value=cliente['razon_social'])
                    rfc          = st.text_input("RFC *", value=cliente['rfc'] or "")
                    contacto     = st.text_input("Contacto", value=cliente['contacto'] or "")
                    telefono     = st.text_input("Teléfono", value=cliente['telefono'] or "")

                with col2:
                    email        = st.text_input("Email", value=cliente['email'] or "")
                    direccion    = st.text_area("Dirección", value=cliente['direccion'] or "")
                    tipo_cliente = st.selectbox(
                        "Tipo de cliente",
                        ["regular", "vip", "nuevo"],
                        index=["regular", "vip", "nuevo"].index(cliente['tipo_cliente'])
                    )
                    limite_credito = st.number_input(
                        "Límite de crédito (MXN)",
                        min_value=0.0,
                        step=1000.0,
                        value=float(cliente['limite_credito'] or 0),
                        format="%.2f"
                    )

                st.divider()
                submitted = st.form_submit_button("💾 Actualizar cliente", type="primary")

                if submitted:
                    if not razon_social:
                        st.error("La razón social es obligatoria.")
                    else:
                        try:
                            actualizar_cliente(cliente_id, {
                                'razon_social'  : razon_social,
                                'rfc'           : rfc.upper(),
                                'contacto'      : contacto,
                                'telefono'      : telefono,
                                'email'         : email,
                                'direccion'     : direccion,
                                'tipo_cliente'  : tipo_cliente,
                                'limite_credito': limite_credito
                            })
                            st.success("✅ Cliente actualizado correctamente.")
                        except Exception as e:
                            st.error(f"❌ Error: {e}")