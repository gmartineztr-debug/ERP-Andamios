# pages/04_obras.py
# Módulo de gestión de obras

import streamlit as st
import pandas as pd
from datetime import date
from utils.database import (
    get_clientes,
    get_obras,
    get_obra_by_id,
    crear_obra,
    generar_folio_obra,
    actualizar_estatus_obra,
    get_contratos_por_obra
)



st.title("🏗️ Obras")
st.divider()

ESTATUS_LABEL = {
    'activa'    : '🟢 Activa',
    'suspendida': '🟡 Suspendida',
    'terminada' : '✅ Terminada',
    'cancelada' : '❌ Cancelada'
}

tab_lista, tab_nueva, tab_detalle = st.tabs([
    "📋 Lista De Obras",
    "➕ Nueva Obra",
    "🔍 Ver Detalle"
])

# ================================================
# TAB 1 — LISTA
# ================================================
with tab_lista:
    st.subheader("Obras registradas")

    col1, col2 = st.columns([3, 1])
    with col1:
        filtro = st.selectbox(
            "Filtrar por estatus",
            ["Todos"] + list(ESTATUS_LABEL.values())
        )

    estatus_key = None
    if filtro != "Todos":
        estatus_key = [k for k, v in ESTATUS_LABEL.items() if v == filtro][0]

    obras = get_obras(estatus=estatus_key)

    if not obras:
        st.info("No hay obras registradas.")
    else:
        df = pd.DataFrame(obras)
        df['estatus'] = df['estatus'].map(ESTATUS_LABEL)
        df['total_facturado'] = df['total_facturado'].apply(lambda x: f"${x:,.2f}")

        # Fechas
        for col_fecha in ['fecha_inicio', 'fecha_fin_estimada']:
            if col_fecha in df.columns:
                df[col_fecha] = pd.to_datetime(df[col_fecha]).dt.strftime('%d/%m/%Y')

        df = df[[
            'folio_obra', 'cliente_nombre', 'nombre_proyecto',
            'fecha_inicio', 'fecha_fin_estimada',
            'total_facturado', 'estatus'
        ]]
        df.columns = [
            'Folio', 'Cliente', 'Proyecto',
            'Inicio', 'Fin Estimado',
            'Total Facturado', 'Estatus'
        ]
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.caption(f"Total: {len(obras)} obras")

        # Métricas rápidas
        st.divider()
        obras_df = pd.DataFrame(obras)
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("🟢 Activas", len(obras_df[obras_df['estatus'] == 'activa']))
        with col2:
            st.metric("🟡 Suspendidas", len(obras_df[obras_df['estatus'] == 'suspendida']))
        with col3:
            st.metric("✅ Terminadas", len(obras_df[obras_df['estatus'] == 'terminada']))
        with col4:
            total = obras_df['total_facturado'].sum()
            st.metric("💰 Total facturado", f"${total:,.2f}")

# ================================================
# TAB 2 — NUEVA OBRA
# ================================================
with tab_nueva:
    st.subheader("Registrar nueva obra")

    clientes = get_clientes()
    if not clientes:
        st.error("No hay clientes registrados. Crea un cliente primero.")
        st.stop()

    with st.form("form_nueva_obra", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            opciones_clientes = {c['razon_social']: c['id'] for c in clientes}
            cliente_sel    = st.selectbox("Cliente *", list(opciones_clientes.keys()))
            cliente_id     = opciones_clientes[cliente_sel]
            nombre_proyecto = st.text_input(
                "Nombre del proyecto *",
                placeholder="Edificio Torre Norte - Piso 5"
            )
            direccion_obra = st.text_area(
                "Dirección de la obra",
                placeholder="Calle, Colonia, Ciudad"
            )
            responsable = st.text_input(
                "Responsable de obra",
                placeholder="Nombre del ingeniero o supervisor"
            )

        with col2:
            fecha_inicio = st.date_input(
                "Fecha de inicio",
                value=date.today()
            )
            fecha_fin_estimada = st.date_input(
                "Fecha estimada de fin",
                value=date.today()
            )
            notas = st.text_area(
                "Notas",
                placeholder="Observaciones, condiciones especiales..."
            )

        st.divider()
        submitted = st.form_submit_button("💾 Guardar obra", type="primary")

        if submitted:
            if not nombre_proyecto:
                st.error("El nombre del proyecto es obligatorio.")
            elif fecha_fin_estimada < fecha_inicio:
                st.error("La fecha de fin no puede ser menor a la fecha de inicio.")
            else:
                try:
                    folio = generar_folio_obra()
                    nueva_id = crear_obra({
                        'folio_obra'        : folio,
                        'cliente_id'        : cliente_id,
                        'nombre_proyecto'   : nombre_proyecto,
                        'direccion_obra'    : direccion_obra,
                        'fecha_inicio'      : fecha_inicio,
                        'fecha_fin_estimada': fecha_fin_estimada,
                        'responsable'       : responsable,
                        'notas'             : notas
                    })
                    st.success(f"✅ Obra {folio} registrada correctamente.")
                except Exception as e:
                    st.error(f"❌ Error: {e}")

# ================================================
# TAB 3 — DETALLE
# ================================================
with tab_detalle:
    st.subheader("Detalle de obra")

    obras = get_obras()

    if not obras:
        st.info("No hay obras registradas.")
    else:
        opciones = {
            f"{o['folio_obra']} — {o['nombre_proyecto']}": o['id']
            for o in obras
        }
        seleccion = st.selectbox("Selecciona una obra", list(opciones.keys()))
        obra_id   = opciones[seleccion]
        obra      = get_obra_by_id(obra_id)

        if obra:
            # Datos generales
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"**Folio:** {obra['folio_obra']}")
                st.markdown(f"**Cliente:** {obra['cliente_nombre']}")
                st.markdown(f"**Proyecto:** {obra['nombre_proyecto']}")
            with col2:
                st.markdown(f"**Dirección:** {obra['direccion_obra'] or '—'}")
                st.markdown(f"**Responsable:** {obra['responsable'] or '—'}")
                fecha_i = obra['fecha_inicio']
                fecha_f = obra['fecha_fin_estimada']
                st.markdown(f"**Inicio:** {fecha_i.strftime('%d/%m/%Y') if fecha_i else '—'}")
                st.markdown(f"**Fin estimado:** {fecha_f.strftime('%d/%m/%Y') if fecha_f else '—'}")
            with col3:
                st.markdown(f"**Total facturado:** ${float(obra['total_facturado']):,.2f}")
                estatus_actual = obra['estatus']
                st.markdown(f"**Estatus:** {ESTATUS_LABEL[estatus_actual]}")

                # Cambiar estatus
                nuevo_estatus = st.selectbox(
                    "Cambiar estatus",
                    list(ESTATUS_LABEL.keys()),
                    index=list(ESTATUS_LABEL.keys()).index(estatus_actual),
                    format_func=lambda x: ESTATUS_LABEL[x]
                )
                if st.button("Actualizar estatus"):
                    actualizar_estatus_obra(obra_id, nuevo_estatus)
                    st.success("✅ Estatus actualizado.")
                    st.rerun()

            if obra['notas']:
                st.info(f"📝 {obra['notas']}")

            st.divider()

            # Contratos de la obra
            st.subheader("Contratos asociados")
            try:
                contratos = get_contratos_por_obra(obra_id)
                if not contratos:
                    st.info("Esta obra no tiene contratos aún.")
                else:
                    df_contratos = pd.DataFrame(contratos)
                    df_contratos = df_contratos[[
                        'folio', 'tipo_contrato', 'monto_total',
                        'estatus', 'created_at'
                    ]]
                    df_contratos.columns = [
                        'Folio', 'Tipo', 'Monto Total',
                        'Estatus', 'Fecha'
                    ]
                    df_contratos['Monto Total'] = df_contratos['Monto Total'].apply(
                        lambda x: f"${x:,.2f}"
                    )
                    df_contratos['Fecha'] = pd.to_datetime(
                        df_contratos['Fecha']
                    ).dt.strftime('%d/%m/%Y')
                    st.dataframe(df_contratos, use_container_width=True, hide_index=True)
            except Exception:
                st.info("Los contratos estarán disponibles cuando se implemente ese módulo.")