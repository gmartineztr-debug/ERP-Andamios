# pages/08_fabricacion.py
# Módulo de Fabricación — OF y OC de materiales

import streamlit as st
import pandas as pd
from datetime import date
from utils.database import (
    get_productos,
    get_proveedores,
    get_insumos,
    generar_folio_of,
    crear_orden_fabricacion,
    get_ordenes_fabricacion,
    get_orden_fabricacion_detalle,
    actualizar_estatus_of,
    get_ordenes_terminadas_sin_he,
    generar_folio_oc,
    crear_orden_compra,
    get_ordenes_compra,
    get_orden_compra_detalle,
    actualizar_estatus_oc,
    calcular_materiales_of,
    generar_folio_entrada,
    crear_hoja_entrada
)
from utils.logger import logger

# Validar permisos
roles_permitidos = ['admin', 'fabricacion']
if st.session_state.get('rol', 'usuario').lower() not in roles_permitidos:
    st.error(f"🚫 **No tienes acceso a esta sección.**\nRoles requeridos: {', '.join(roles_permitidos)}")
    logger.warning(f"ACCESO_DENEGADO: {st.session_state.get('usuario')} intentó acceder a Fabricación")
    st.stop()

st.title(":material/construction: Fabricación")
st.divider()

ESTATUS_OF_LABEL = {
    'abierta'            : 'Abierta',
    'espera_materiales'  : 'En espera de materiales',
    'en_fabricacion'     : 'En fabricación',
    'terminada'          : 'Terminada',
    'cancelada'          : 'Cancelada',
    'modificada'         : 'Modificada'
}

ESTATUS_OC_LABEL = {
    'borrador' : 'Borrador',
    'enviada'  : 'Enviada',
    'recibida' : 'Recibida',
    'cancelada': 'Cancelada'
}

tab_nueva_of, tab_nueva_oc, tab_lista_of, tab_lista_oc, tab_detalle_of = st.tabs([
    ":material/add_box: Nueva OF",
    ":material/shopping_cart: Nueva OC",
    ":material/list_alt: Órdenes De Fabricación",
    ":material/list_alt: Órdenes De Compra",
    ":material/search: Ver Detalle OF"
])

# ================================================
# TAB 1 — NUEVA OF
# ================================================
with tab_nueva_of:
    st.subheader("Nueva Orden de Fabricación")

    col1, col2 = st.columns(2)
    with col1:
        fecha_apertura  = st.date_input("Fecha apertura *", value=date.today(), key="of_fecha")
        fecha_estimada  = st.date_input("Fecha estimada entrega", value=None, key="of_fecha_est")
    with col2:
        notas_of = st.text_area("Notas / justificación", key="of_notas",
                                 placeholder="Ej: Reposición por ventas de marco 1.90...")

    st.divider()
    st.markdown("#### Productos a fabricar")

    productos    = get_productos(solo_activos=True)
    fab_productos = [p for p in productos if p.get('se_fabrica')]

    if not fab_productos:
        st.warning("No hay productos marcados como fabricables en el catálogo.")
    else:
        opciones_fab = {
            f"{p['codigo']} — {p['nombre']}": p
            for p in fab_productos
        }

        if 'of_items' not in st.session_state:
            st.session_state.of_items = []

        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            of_prod_sel = st.selectbox(
                "Producto", list(opciones_fab.keys()), key="of_prod_sel"
            )
        with col2:
            of_cant = st.number_input(
                "Cantidad", min_value=1, value=1, step=1, key="of_cant"
            )
        with col3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button(":material/add: Agregar", key="btn_add_of"):
                prod = opciones_fab[of_prod_sel]
                existe = any(
                    i['producto_id'] == prod['id']
                    for i in st.session_state.of_items
                )
                if existe:
                    st.warning("Este producto ya está en la OF.")
                else:
                    st.session_state.of_items.append({
                        'producto_id': prod['id'],
                        'codigo'     : prod['codigo'],
                        'nombre'     : prod['nombre'],
                        'cantidad'   : of_cant
                    })

        if st.session_state.of_items:
            st.markdown("**Productos en esta OF:**")
            df_of = pd.DataFrame(st.session_state.of_items)[
                ['codigo', 'nombre', 'cantidad']
            ]
            df_of.columns = ['Código', 'Producto', 'Cantidad']
            st.dataframe(df_of, use_container_width=True, hide_index=True)

            # Preview materiales necesarios
            with st.expander(":material/inventory_2: Vista previa de materiales necesarios (BOM)"):
                materiales = calcular_materiales_of(st.session_state.of_items)
                if materiales:
                    df_mat = pd.DataFrame(materiales)[[
                        'codigo', 'nombre', 'cantidad_necesaria', 'unidad', 'costo_unitario', 'subtotal'
                    ]]
                    df_mat.columns = ['Código', 'Material', 'Cantidad necesaria', 'Unidad', 'Costo Unit.', 'Subtotal']
                    df_mat['Cantidad necesaria'] = df_mat['Cantidad necesaria'].apply(
                        lambda x: f"{x:.4f}"
                    )
                    df_mat['Costo Unit.'] = df_mat['Costo Unit.'].apply(lambda x: f"${x:,.2f}")
                    df_mat['Subtotal'] = df_mat['Subtotal'].apply(lambda x: f"${x:,.2f}")
                    st.dataframe(df_mat, use_container_width=True, hide_index=True)
                    
                    total_est = sum(m['subtotal'] for m in materiales)
                    st.metric("Costo Total Estimado Insumos", f"${total_est:,.2f}")
                else:
                    st.info(":material/info: Algunos productos no tienen BOM definido.")

            st.divider()
            col1, col2 = st.columns(2)
            with col1:
                if st.button(":material/delete_sweep: Limpiar lista", key="btn_clear_of"):
                    st.session_state.of_items = []
                    st.rerun()
            with col2:
                if st.button(":material/save: Crear Orden de Fabricación",
                             type="primary", use_container_width=True,
                             key="btn_crear_of"):
                    try:
                        folio = generar_folio_of()
                        crear_orden_fabricacion({
                            'folio'          : folio,
                            'estatus'        : 'abierta',
                            'fecha_apertura' : fecha_apertura,
                            'fecha_estimada' : fecha_estimada,
                            'notas'          : notas_of
                        }, st.session_state.of_items)
                        st.success(f":material/check_circle: Orden de Fabricación {folio} creada.")
                        st.session_state.of_items = []
                        st.rerun()
                    except Exception as e:
                        st.error(f":material/error: Error: {e}")

# ================================================
# TAB 2 — NUEVA OC
# ================================================
with tab_nueva_oc:
    st.subheader("Nueva Orden de Compra de materiales")

    ordenes = get_ordenes_fabricacion()
    of_activas = [
        o for o in ordenes
        if o['estatus'] in ('abierta', 'espera_materiales', 'en_fabricacion')
    ]

    proveedores = get_proveedores()

    if not proveedores:
        st.warning("No hay proveedores registrados. Ve a Hojas de Entrada → Compra para agregar uno.")
    elif not of_activas:
        st.warning("No hay Órdenes de Fabricación activas.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            opciones_of = {
                f"{o['folio']} — {ESTATUS_OF_LABEL.get(o['estatus'],'—')}": o['id']
                for o in of_activas
            }
            of_sel  = st.selectbox("OF relacionada *", list(opciones_of.keys()), key="oc_of")
            of_id   = opciones_of[of_sel]

            opciones_prov = {p['nombre']: p['id'] for p in proveedores}
            prov_sel = st.selectbox("Proveedor *", list(opciones_prov.keys()), key="oc_prov")
            prov_id  = opciones_prov[prov_sel]

        with col2:
            fecha_oc   = st.date_input("Fecha OC *", value=date.today(), key="oc_fecha")
            fecha_est  = st.date_input("Fecha estimada entrega", value=None, key="oc_fecha_est")
            notas_oc   = st.text_area("Notas", key="oc_notas")

        st.divider()
        st.markdown("#### Materiales a comprar")

        # Sugerir materiales desde BOM de la OF seleccionada
        of_detalle, of_items = get_orden_fabricacion_detalle(of_id)
        if of_items:
            materiales_sugeridos = calcular_materiales_of([
                {'producto_id': i['producto_id'], 'cantidad': i['cantidad_solicitada']}
                for i in of_items
            ])
            if materiales_sugeridos:
                with st.expander(":material/lightbulb: Materiales sugeridos por BOM", expanded=True):
                    st.caption("Basado en la receta de los productos de la OF seleccionada.")
                    df_sug = pd.DataFrame(materiales_sugeridos)[[
                        'codigo', 'nombre', 'cantidad_necesaria', 'unidad'
                    ]]
                    df_sug.columns = ['Código', 'Material', 'Cantidad necesaria', 'Unidad']
                    df_sug['Cantidad necesaria'] = df_sug['Cantidad necesaria'].apply(
                        lambda x: f"{x:.4f}"
                    )
                    st.dataframe(df_sug, use_container_width=True, hide_index=True)

        insumos = get_insumos()
        if not insumos:
            st.warning("No hay insumos registrados en el catálogo.")
        else:
            opciones_ins = {
                f"{i['codigo']} — {i['nombre']} ({i['unidad']})": i
                for i in insumos
            }

            if 'oc_items' not in st.session_state:
                st.session_state.oc_items = []

            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            with col1:
                ins_sel = st.selectbox(
                    "Material", list(opciones_ins.keys()), key="oc_ins_sel"
                )
            with col2:
                cant_oc = st.number_input(
                    "Cantidad", min_value=0.0001, value=1.0,
                    format="%.4f", key="oc_cant"
                )
            with col3:
                costo_oc = st.number_input(
                    "Costo unit. $", min_value=0.0, value=0.0,
                    format="%.2f", key="oc_costo"
                )
            with col4:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button(":material/add: Agregar", key="btn_add_oc"):
                    ins = opciones_ins[ins_sel]
                    existe = any(
                        i['insumo_id'] == ins['id']
                        for i in st.session_state.oc_items
                    )
                    if existe:
                        st.warning("Este material ya está en la OC.")
                    else:
                        st.session_state.oc_items.append({
                            'insumo_id'    : ins['id'],
                            'codigo'       : ins['codigo'],
                            'nombre'       : ins['nombre'],
                            'unidad'       : ins['unidad'],
                            'cantidad'     : cant_oc,
                            'costo_unitario': costo_oc,
                            'subtotal'     : cant_oc * costo_oc
                        })

            if st.session_state.oc_items:
                df_oc = pd.DataFrame(st.session_state.oc_items)[[
                    'codigo', 'nombre', 'cantidad', 'unidad', 'costo_unitario', 'subtotal'
                ]]
                df_oc.columns = [
                    'Código', 'Material', 'Cantidad', 'Unidad',
                    'Costo Unit.', 'Subtotal'
                ]
                st.dataframe(df_oc, use_container_width=True, hide_index=True)

                total_oc = sum(i['subtotal'] for i in st.session_state.oc_items)
                st.metric("💰 Total OC", f"${total_oc:,.2f}")

                col1, col2 = st.columns(2)
                with col1:
                    if st.button(":material/delete_sweep: Limpiar lista", key="btn_clear_oc"):
                        st.session_state.oc_items = []
                        st.rerun()
                with col2:
                    if st.button(":material/save: Crear Orden de Compra",
                                 type="primary", use_container_width=True,
                                 key="btn_crear_oc"):
                        try:
                            folio_oc = generar_folio_oc()
                            crear_orden_compra({
                                'folio'                  : folio_oc,
                                'orden_id'               : of_id,
                                'proveedor_id'           : prov_id,
                                'estatus'                : 'borrador',
                                'fecha_oc'               : fecha_oc,
                                'fecha_estimada_entrega' : fecha_est,
                                'notas'                  : notas_oc
                            }, st.session_state.oc_items)
                            st.success(f":material/check_circle: Orden de Compra {folio_oc} creada.")
                            st.session_state.oc_items = []
                            st.rerun()
                        except Exception as e:
                            st.error(f":material/error: Error: {e}")

# ================================================
# TAB 3 — LISTA OF
# ================================================
with tab_lista_of:
    st.subheader("Órdenes de Fabricación")

    filtro_of = st.selectbox(
        "Filtrar por estatus",
        ["Todos"] + list(ESTATUS_OF_LABEL.values()),
        key="filtro_of"
    )

    ordenes = get_ordenes_fabricacion()

    if filtro_of != "Todos":
        est_key = [k for k, v in ESTATUS_OF_LABEL.items() if v == filtro_of][0]
        ordenes = [o for o in ordenes if o['estatus'] == est_key]

    if not ordenes:
        st.info("No hay Órdenes de Fabricación registradas.")
    else:
        df = pd.DataFrame(ordenes)
        df['estatus'] = df['estatus'].map(ESTATUS_OF_LABEL)
        df['fecha_apertura'] = pd.to_datetime(
            df['fecha_apertura'], errors='coerce'
        ).dt.strftime('%d/%m/%Y')
        df['fecha_estimada'] = pd.to_datetime(
            df['fecha_estimada'], errors='coerce'
        ).dt.strftime('%d/%m/%Y')

        df_show = df[[
            'folio', 'estatus', 'total_productos',
            'fecha_apertura', 'fecha_estimada'
        ]].fillna('—')
        df_show.columns = [
            'Folio OF', 'Estatus', 'Productos',
            'Apertura', 'Est. Entrega'
        ]
        st.dataframe(df_show, use_container_width=True, hide_index=True)
        st.caption(f"Total: {len(ordenes)} órdenes")

# ================================================
# TAB 4 — LISTA OC
# ================================================
with tab_lista_oc:
    st.subheader("Órdenes de Compra de materiales")

    filtro_oc = st.selectbox(
        "Filtrar por estatus",
        ["Todos"] + list(ESTATUS_OC_LABEL.values()),
        key="filtro_oc"
    )

    ocs = get_ordenes_compra()

    if filtro_oc != "Todos":
        est_key = [k for k, v in ESTATUS_OC_LABEL.items() if v == filtro_oc][0]
        ocs = [o for o in ocs if o['estatus'] == est_key]

    if not ocs:
        st.info("No hay Órdenes de Compra registradas.")
    else:
        df = pd.DataFrame(ocs)
        df['estatus']  = df['estatus'].map(ESTATUS_OC_LABEL)
        df['fecha_oc'] = pd.to_datetime(
            df['fecha_oc'], errors='coerce'
        ).dt.strftime('%d/%m/%Y')
        df['total']    = df['total'].apply(lambda x: f"${float(x):,.2f}")

        df_show = df[[
            'folio', 'of_folio', 'proveedor_nombre',
            'fecha_oc', 'total', 'estatus'
        ]].fillna('—')
        df_show.columns = [
            'Folio OC', 'OF', 'Proveedor',
            'Fecha', 'Total', 'Estatus'
        ]
        st.dataframe(df_show, use_container_width=True, hide_index=True)
        st.caption(f"Total: {len(ocs)} órdenes de compra")

# ================================================
# TAB 5 — DETALLE OF
# ================================================
with tab_detalle_of:
    st.subheader("Detalle de Orden de Fabricación")

    ordenes = get_ordenes_fabricacion()

    if not ordenes:
        st.info("No hay Órdenes de Fabricación registradas.")
    else:
        opciones_of = {
            f"{o['folio']} — {ESTATUS_OF_LABEL.get(o['estatus'],'—')}": o['id']
            for o in ordenes
        }
        of_sel_det = st.selectbox(
            "Selecciona OF", list(opciones_of.keys()), key="det_of_sel"
        )
        of_id_det = opciones_of[of_sel_det]

        try:
            orden, items = get_orden_fabricacion_detalle(of_id_det)
        except Exception as e:
            st.error(f"Error: {e}")
            st.stop()

        if orden:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"**Folio:** {orden['folio']}")
                st.markdown(f"**Estatus:** {ESTATUS_OF_LABEL.get(orden['estatus'],'—')}")
            with col2:
                fa = orden['fecha_apertura']
                fe = orden['fecha_estimada']
                fc = orden['fecha_cierre']
                st.markdown(f"**Apertura:** {fa.strftime('%d/%m/%Y') if fa else '—'}")
                st.markdown(f"**Est. entrega:** {fe.strftime('%d/%m/%Y') if fe else '—'}")
                st.markdown(f"**Cierre:** {fc.strftime('%d/%m/%Y') if fc else '—'}")
            with col3:
                if orden.get('notas'):
                    st.markdown(f"**Notas:** {orden['notas']}")

            st.divider()

            # Productos de la OF
            if items:
                st.markdown("#### Productos")
                df_items = pd.DataFrame(items)[[
                    'codigo', 'producto_nombre',
                    'cantidad_solicitada', 'cantidad_fabricada'
                ]]
                df_items.columns = [
                    'Código', 'Producto',
                    'Solicitado', 'Fabricado'
                ]
                st.dataframe(df_items, use_container_width=True, hide_index=True)

            # OCs ligadas a esta OF
            ocs_of = [
                o for o in get_ordenes_compra()
                if o.get('of_folio') == orden['folio']
            ]
            if ocs_of:
                st.divider()
                st.markdown("#### Órdenes de Compra ligadas")
                df_ocs = pd.DataFrame(ocs_of)[[
                    'folio', 'proveedor_nombre', 'total', 'estatus'
                ]].fillna('—')
                df_ocs['estatus'] = df_ocs['estatus'].map(ESTATUS_OC_LABEL)
                df_ocs['total']   = df_ocs['total'].apply(lambda x: f"${float(x):,.2f}")
                df_ocs.columns    = ['Folio OC', 'Proveedor', 'Total', 'Estatus']
                st.dataframe(df_ocs, use_container_width=True, hide_index=True)

                # Actualizar estatus OC
                st.markdown("**Actualizar estatus de OC:**")
                oc_opciones = {o['folio']: o['id'] for o in ocs_of}
                col1, col2, col3 = st.columns(3)
                with col1:
                    oc_sel = st.selectbox(
                        "OC", list(oc_opciones.keys()), key="oc_upd_sel"
                    )
                with col2:
                    nuevo_est_oc = st.selectbox(
                        "Nuevo estatus",
                        list(ESTATUS_OC_LABEL.keys()),
                        format_func=lambda x: ESTATUS_OC_LABEL[x],
                        key="oc_upd_est"
                    )
                with col3:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("Actualizar OC", key="btn_upd_oc"):
                        actualizar_estatus_oc(oc_opciones[oc_sel], nuevo_est_oc)
                        st.success(":material/check_circle: Estatus OC actualizado.")
                        st.rerun()

            st.divider()

            # Actualizar estatus OF
            if orden['estatus'] not in ('terminada', 'cancelada'):
                st.markdown("#### Actualizar estatus OF")
                col1, col2 = st.columns(2)
                with col1:
                    nuevo_est_of = st.selectbox(
                        "Nuevo estatus",
                        list(ESTATUS_OF_LABEL.keys()),
                        format_func=lambda x: ESTATUS_OF_LABEL[x],
                        key="of_upd_est"
                    )
                    fecha_cierre_of = None
                    items_fabricados = []

                    if nuevo_est_of in ('terminada', 'modificada'):
                        fecha_cierre_of = st.date_input(
                            "Fecha de cierre", value=date.today(),
                            key="of_fecha_cierre"
                        )
                        st.markdown("**Cantidad real fabricada por producto:**")
                        for item in items:
                            cant_fab = st.number_input(
                                f"{item['codigo']} — {item['producto_nombre']}",
                                min_value=0,
                                value=int(item['cantidad_solicitada']),
                                step=1,
                                key=f"fab_real_{item['producto_id']}"
                            )
                            items_fabricados.append({
                                'producto_id'      : item['producto_id'],
                                'cantidad_fabricada': cant_fab
                            })

                    if st.button("Actualizar OF", type="primary", key="btn_upd_of"):
                        actualizar_estatus_of(
                            of_id_det, nuevo_est_of,
                            fecha_cierre_of,
                            items_fabricados if items_fabricados else None
                        )
                        st.success(":material/check_circle: Estatus OF actualizado.")
                        st.rerun()

            # Generar HE desde OF terminada
            if orden['estatus'] in ('terminada', 'modificada'):
                st.divider()
                ofs_sin_he = [o['folio'] for o in get_ordenes_terminadas_sin_he()]
                if orden['folio'] in ofs_sin_he:
                    st.info(":material/move_to_inbox: Esta OF está terminada y no tiene Hoja de Entrada generada.")
                    if st.button(
                        ":material/move_to_inbox: Generar Hoja de Entrada automáticamente",
                        type="primary", key="btn_gen_he"
                    ):
                        try:
                            folio_he = generar_folio_entrada()
                            items_he = [
                                {
                                    'producto_id'  : i['producto_id'],
                                    'cantidad_total': i['cantidad_fabricada'] or
                                                      i['cantidad_solicitada'],
                                    'peso_unitario' : float(i.get('peso_kg') or 0),
                                    'peso_total'    : (
                                        i['cantidad_fabricada'] or
                                        i['cantidad_solicitada']
                                    ) * float(i.get('peso_kg') or 0)
                                }
                                for i in items
                            ]
                            crear_hoja_entrada({
                                'folio'               : folio_he,
                                'tipo_entrada'        : 'fabricacion',
                                'estatus'             : 'pendiente',
                                'lote_fabricacion'    : orden['folio'],
                                'fecha_entrada'       : date.today(),
                                'orden_fabricacion_id': of_id_det,
                                'notas'               : f'Generada desde {orden["folio"]}'
                            }, items_he)
                            st.success(
                                f"✅ Hoja de Entrada {folio_he} creada. "
                                f"Ve al módulo HE para cerrarla y actualizar inventario."
                            )
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error: {e}")
                else:
                    st.success("✅ Esta OF ya tiene Hoja de Entrada generada.")