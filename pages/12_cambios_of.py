# pages/12_cambios_of.py
# Módulo de Solicitudes de Cambio de Orden de Fabricación (SC)

import streamlit as st
import pandas as pd
from datetime import date
from utils.database import (
    get_ordenes_fabricacion,
    get_of_detalle,
    get_bom_producto,
    get_insumos,
    generar_folio_sc,
    crear_sc,
    get_solicitudes_cambio,
    get_sc_detalle,
    actualizar_estatus_sc,
    generar_folio_of,
    crear_orden_fabricacion
)



st.title(":material/history: Solicitudes de Cambio de OF")
st.caption("Registra interrupciones, cambios de plan o cierres parciales de Órdenes de Fabricación.")
st.divider()

tab_nueva, tab_lista, tab_detalle = st.tabs([
    ":material/add_box: Nueva Solicitud De Cambio",
    ":material/list_alt: Lista De Solicitudes De Cambio",
    ":material/search: Ver Detalle"
])

# ================================================
# TAB 1 — NUEVA SC
# ================================================
with tab_nueva:
    st.subheader("Nueva Solicitud de Cambio")

    # Seleccionar OF origen
    ofs = get_ordenes_fabricacion()
    ofs_activas = [
        o for o in ofs
        if o['estatus'] in ('abierta', 'espera_materiales', 'en_fabricacion')
    ]

    if not ofs_activas:
        st.info("No hay Órdenes de Fabricación activas (pendiente o en proceso).")
    else:
        opciones_of = {
            f"{o['folio']} — {o.get('fecha_apertura', '')}": o['id']
            for o in ofs_activas
    }

        col1, col2 = st.columns(2)
        with col1:
            of_sel = st.selectbox(
                "OF afectada *",
                list(opciones_of.keys()),
                key="sc_of_sel"
            )
            of_id = opciones_of[of_sel]
        with col2:
            fecha_sc = st.date_input(
                "Fecha *",
                value=date.today(),
                key="sc_fecha"
            )

        # Cargar detalle OF
        of_data, of_items = get_of_detalle(of_id)

        if of_data:
            col1, col2, col3 = st.columns(3)
            col1.metric("Folio OF", of_data.get('folio', '—'))
            col2.metric("Estatus",  of_data.get('estatus', '—'))
            col3.metric("Fecha apertura", str(of_data.get('fecha_apertura', '—')))

        st.divider()

        # Motivo y avance
        motivo = st.text_area(
            "Motivo del cambio *",
            placeholder="¿Por qué se interrumpe o modifica esta OF? "
                        "Ej: Material insuficiente, cambio de prioridad, "
                        "error en medidas...",
            key="sc_motivo"
        )

        avance_descr = st.text_area(
            "Descripción del avance actual",
            placeholder="¿Qué se alcanzó a fabricar antes del cambio? "
                        "Ej: Se terminaron 8 de 15 marcos, falta soldadura en 3...",
            key="sc_avance"
        )

        st.divider()

        # Avance por producto
        st.markdown("#### Avance por producto")
        st.caption("Captura cuánto se fabricó de lo planeado en esta OF.")

        sc_items = []
        if of_items:
            for item in of_items:
                col1, col2, col3 = st.columns([3, 2, 2])
                with col1:
                    st.markdown(
                        f"**{item.get('codigo','—')} — {item.get('nombre','—')}**"
                    )
                with col2:
                    st.caption(f"Planeado: {item.get('cantidad_solicitada', 0)}")
                with col3:
                    fab = st.number_input(
                        "Fabricado",
                        min_value=0,
                        max_value=int(item.get('cantidad_solicitada', 0)),
                        value=0,
                        step=1,
                        label_visibility="collapsed",
                        key=f"sc_fab_{item['id']}"
                    )
                sc_items.append({
                    'producto_id'       : item['producto_id'],
                    'cantidad_planeada' : item['cantidad_solicitada'],
                    'cantidad_fabricada': fab
                })

        st.divider()

        # Balance de materiales
        st.markdown("#### Balance de materiales (opcional)")
        st.caption(
            "Si hay insumos sobrantes, registra aquí su destino "
            "para mantener trazabilidad."
        )

        insumos = get_insumos()
        sc_materiales = []

        if insumos:
            with st.expander("Registrar sobrantes de material"):
                num_mat = st.number_input(
                    "¿Cuántos insumos sobraron?",
                    min_value=0, max_value=10,
                    value=0, step=1,
                    key="sc_num_mat"
                )
                for i in range(int(num_mat)):
                    st.markdown(f"**Insumo {i+1}**")
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        ins_opts = {
                            f"{ins['codigo']} — {ins['nombre']}": ins['id']
                            for ins in insumos
                        }
                        ins_sel = st.selectbox(
                            "Insumo",
                            list(ins_opts.keys()),
                            key=f"sc_ins_{i}"
                        )
                        ins_id = ins_opts[ins_sel]
                    with col2:
                        qty_est = st.number_input(
                            "Estimado usado",
                            min_value=0.0, value=0.0,
                            step=0.5, key=f"sc_est_{i}"
                        )
                    with col3:
                        qty_real = st.number_input(
                            "Real usado",
                            min_value=0.0, value=0.0,
                            step=0.5, key=f"sc_real_{i}"
                        )
                    with col4:
                        destino = st.selectbox(
                            "Destino sobrante",
                            ['desconocido', 'nueva_of', 'almacen'],
                            key=f"sc_dest_{i}"
                        )
                    notas_mat = st.text_input(
                        "Notas del material",
                        key=f"sc_notas_mat_{i}"
                    )
                    sc_materiales.append({
                        'insumo_id'            : ins_id,
                        'cantidad_estimada_uso': qty_est,
                        'cantidad_real_uso'    : qty_real,
                        'cantidad_sobrante'    : max(0, qty_est - qty_real),
                        'destino_sobrante'     : destino,
                        'notas'                : notas_mat
                    })

        st.divider()

        # ¿Genera nueva OF?
        st.markdown("#### ¿Se genera nueva OF para continuar?")
        genera_nueva_of = st.checkbox(
            "Sí, crear nueva OF para el pendiente",
            key="sc_genera_of"
        )

        notas_sc = st.text_area(
            "Notas adicionales",
            key="sc_notas"
        )

        # Botón crear SC
        if st.button(
            ":material/save: Registrar Solicitud de Cambio",
            type="primary",
            use_container_width=True,
            key="btn_crear_sc"
        ):
            if not motivo:
                st.error("❌ El motivo es obligatorio.")
            else:
                try:
                    folio_sc = generar_folio_sc()

                    # Si genera nueva OF, crearla primero
                    nueva_of_id = None
                    if genera_nueva_of:
                        pendientes = [
                            i for i in sc_items
                            if (i['cantidad_planeada'] - i['cantidad_fabricada']) > 0
                        ]
                        if pendientes:
                            folio_nueva = generar_folio_of()
                            items_nueva_of = [{
                                'producto_id': i['producto_id'],
                                'cantidad'   : i['cantidad_planeada'] - i['cantidad_fabricada']
                            } for i in pendientes]
                            nueva_of_id = crear_orden_fabricacion({
                                'folio'         : folio_nueva,
                                'fecha_apertura': date.today(),
                                'notas'         : f"Continuación de {of_data['folio']} — SC: {folio_sc}",
                                'estatus'       : 'abierta'
                            }, items_nueva_of)

                    sc_id = crear_sc(
                        datos={
                            'folio'       : folio_sc,
                            'of_origen_id': of_id,
                            'of_nueva_id' : nueva_of_id,
                            'motivo'      : motivo,
                            'avance_descr': avance_descr,
                            'estatus'     : 'aprobada',
                            'fecha'       : fecha_sc,
                            'notas'       : notas_sc
                        },
                        items=sc_items,
                        materiales=sc_materiales
                    )

                    msg = f":material/check_circle: SC {folio_sc} registrada."
                    if nueva_of_id:
                        msg += f" Nueva OF {folio_nueva} creada para los pendientes."
                    st.success(msg)
                    st.rerun()

                except Exception as e:
                    st.error(f"❌ Error: {e}")

# ================================================
# TAB 2 — LISTA DE SC
# ================================================
with tab_lista:
    st.subheader("Solicitudes de Cambio registradas")

    scs = get_solicitudes_cambio()

    if not scs:
        st.info("No hay solicitudes de cambio registradas.")
    else:
        ESTATUS_SC = {
            'borrador' : '📝 Borrador',
            'aprobada' : '✅ Aprobada',
            'aplicada' : '⚡ Aplicada',
            'cancelada': '❌ Cancelada'
        }

        df = pd.DataFrame(scs)
        df['estatus'] = df['estatus'].map(ESTATUS_SC)
        df['fecha']   = pd.to_datetime(df['fecha'], errors='coerce').dt.strftime('%d/%m/%Y')

        col1, col2, col3 = st.columns(3)
        col1.metric("Total SC", len(df))
        col2.metric("Aprobadas",
            len(df[df['estatus'] == 'Aprobada']))
        col3.metric("Canceladas",
            len(df[df['estatus'] == 'Cancelada']))

        st.divider()

        df_show = df[[
            'folio', 'fecha', 'of_origen_folio',
            'of_nueva_folio', 'estatus', 'motivo'
        ]].fillna('—')
        df_show.columns = [
            'Folio SC', 'Fecha', 'OF Origen',
            'OF Nueva', 'Estatus', 'Motivo'
        ]
        st.dataframe(df_show, use_container_width=True, hide_index=True)

# ================================================
# TAB 3 — DETALLE SC
# ================================================
with tab_detalle:
    st.subheader("Detalle de Solicitud de Cambio")

    scs = get_solicitudes_cambio()

    if not scs:
        st.info("No hay solicitudes de cambio registradas.")
    else:
        ESTATUS_SC = {
            'borrador' : '📝 Borrador',
            'aprobada' : '✅ Aprobada',
            'aplicada' : '⚡ Aplicada',
            'cancelada': '❌ Cancelada'
        }

        opciones_sc = {
            f"{s['folio']} — OF: {s['of_origen_folio']} — {ESTATUS_SC.get(s['estatus'], s['estatus'])}": s['id']
            for s in scs
        }
        sc_sel = st.selectbox(
            "Selecciona SC",
            list(opciones_sc.keys()),
            key="det_sc_sel"
        )
        sc_id = opciones_sc[sc_sel]

        sc, items, materiales = get_sc_detalle(sc_id)

        if sc:
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Folio",      sc['folio'])
            col2.metric("OF Origen",  sc['of_origen_folio'])
            col3.metric("OF Nueva",   sc.get('of_nueva_folio') or '—')
            col4.metric("Estatus",    ESTATUS_SC.get(sc['estatus'], sc['estatus']))

            st.divider()

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Motivo del cambio:**")
                st.info(sc['motivo'])
            with col2:
                st.markdown("**Avance al momento del cambio:**")
                st.info(sc.get('avance_descr') or 'No especificado')

            # Items
            if items:
                st.divider()
                st.markdown("#### Avance por producto")
                df_items = pd.DataFrame(items)
                df_items['pct'] = (
                    df_items['cantidad_fabricada'] /
                    df_items['cantidad_planeada'].replace(0, 1) * 100
                ).round(1)
                df_show = df_items[[
                    'codigo', 'producto_nombre',
                    'cantidad_planeada', 'cantidad_fabricada',
                    'cantidad_pendiente', 'pct'
                ]].fillna(0)
                df_show.columns = [
                    'Código', 'Producto',
                    'Planeado', 'Fabricado',
                    'Pendiente', '% Avance'
                ]
                st.dataframe(df_show, use_container_width=True, hide_index=True)

            # Materiales
            if materiales:
                st.divider()
                st.markdown("#### Balance de materiales")
                df_mat = pd.DataFrame(materiales)
                df_show = df_mat[[
                    'codigo', 'insumo_nombre', 'unidad',
                    'cantidad_estimada_uso', 'cantidad_real_uso',
                    'cantidad_sobrante', 'destino_sobrante', 'notas'
                ]].fillna('—')
                df_show.columns = [
                    'Código', 'Insumo', 'Unidad',
                    'Est. Usado', 'Real Usado',
                    'Sobrante', 'Destino', 'Notas'
                ]
                st.dataframe(df_show, use_container_width=True, hide_index=True)

            # Notas
            if sc.get('notas'):
                st.divider()
                st.markdown("**Notas:**")
                st.caption(sc['notas'])

            # Cambiar estatus
            st.divider()
            est_actual = sc['estatus']
            if est_actual not in ('aplicada', 'cancelada'):
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(
                        ":material/bolt: Marcar como Aplicada",
                        type="primary",
                        use_container_width=True,
                        key="btn_sc_aplicada"
                    ):
                        actualizar_estatus_sc(sc_id, 'aplicada')
                        st.success(":material/check_circle: SC marcada como aplicada.")
                        st.rerun()
                with col2:
                    if st.button(
                        "❌ Cancelar SC",
                        use_container_width=True,
                        key="btn_sc_cancelar"
                    ):
                        actualizar_estatus_sc(sc_id, 'cancelada')
                        st.warning("SC cancelada.")
                        st.rerun()