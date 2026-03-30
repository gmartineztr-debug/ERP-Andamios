# pages/11_inventario.py
# Módulo de Inventario — Bitácora de movimientos y Conteo Físico

import streamlit as st
import pandas as pd
from datetime import date
from utils.database import (
    get_productos,
    get_bitacora,
    get_bitacora_producto,
    generar_folio_conteo,
    crear_conteo,
    get_conteos,
    get_conteo_items,
    actualizar_conteo_item,
    aplicar_ajuste_conteo,
    get_contratos_con_equipo_en_campo,
    get_saldo_en_campo
)
from utils.reporting import export_to_csv, export_to_pdf
from datetime import datetime
from utils.auth_manager import check_permission
from utils.logger import logger

# Validar permisos
roles_permitidos = ['admin', 'logistica']
if st.session_state.get('rol', 'usuario').lower() not in roles_permitidos:
    st.error(f"🚫 **No tienes acceso a esta sección.**\nRoles requeridos: {', '.join(roles_permitidos)}")
    logger.warning(f"ACCESO_DENEGADO: {st.session_state.get('usuario')} intentó acceder a Inventario")
    st.stop()

st.title(":material/inventory: Control de Inventario")
st.divider()

tab_bitacora, tab_saldo_obra, tab_nuevo_conteo, tab_conteos = st.tabs([
    ":material/list_alt: Bitácora De Movimientos",
    ":material/foundation: Saldo En Obra",
    ":material/add_box: Nuevo Conteo Físico",
    ":material/inventory_2: Conteos Realizados"
])

# ================================================
# TAB 1 — BITÁCORA
# ================================================
with tab_bitacora:
    st.subheader("Bitácora de movimientos de inventario")
    st.caption("Registro automático de todos los movimientos generados por el sistema.")

    col1, col2, col3 = st.columns(3)
    with col1:
        productos = get_productos(solo_activos=True)
        opciones_prod = {"Todos los productos": None}
        opciones_prod.update({
            f"{p['codigo']} — {p['nombre']}": p['id']
            for p in productos
        })
        prod_sel = st.selectbox(
            "Filtrar por producto",
            list(opciones_prod.keys()),
            key="bit_prod"
        )
        prod_id = opciones_prod[prod_sel]

    with col2:
        TIPOS_MOV = {
            "Todos"               : None,
            "Salida entrega"   : "salida_entrega",
            "Entrada devolución": "entrada_devolucion",
            "Entrada compra"   : "entrada_compra",
            "Entrada fabricación": "entrada_fabricacion",
            "Ajuste manual"    : "ajuste_manual",
            "Ajuste conteo"    : "ajuste_conteo"
        }
        tipo_sel = st.selectbox(
            "Filtrar por tipo",
            list(TIPOS_MOV.keys()),
            key="bit_tipo"
        )
        tipo_val = TIPOS_MOV[tipo_sel]

    with col3:
        limite = st.number_input(
            "Últimos N movimientos",
            min_value=10, max_value=500,
            value=100, step=10,
            key="bit_limite"
        )

    movimientos = get_bitacora(
        producto_id=prod_id,
        tipo=tipo_val,
        limite=limite
    )

    if not movimientos:
        st.info("No hay movimientos registrados aún. Los movimientos se generan automáticamente cuando se confirman Hojas de Salida y Entrada.")
    else:
        df = pd.DataFrame(movimientos)

        # Formatear
        df['fecha'] = pd.to_datetime(df['fecha']).dt.strftime('%d/%m/%Y %H:%M')
        df['tipo_movimiento'] = df['tipo_movimiento'].map({
            'salida_entrega'     : 'Salida entrega',
            'entrada_devolucion' : 'Devolución',
            'entrada_compra'     : 'Compra',
            'entrada_fabricacion': 'Fabricación',
            'ajuste_manual'      : 'Ajuste manual',
            'ajuste_conteo'      : 'Ajuste conteo'
        })

        # Métricas rápidas
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total movimientos", len(df))
        col2.metric("Salidas",  len(df[df['tipo_movimiento'].str.contains('Salida', na=False)]))
        col3.metric("Entradas", len(df[df['tipo_movimiento'].str.contains('Devolución|Compra|Fabricación', na=False)]))
        col4.metric("Ajustes",  len(df[df['tipo_movimiento'].str.contains('Ajuste', na=False)]))

        st.divider()

        # Estilos para deltas
        def style_delta(v):
            if not isinstance(v, (int, float)): return ''
            if v > 0: return 'color: #10B981; font-weight: 500;'
            if v < 0: return 'color: #EF4444; font-weight: 500;'
            return 'color: #94A3B8;'

        # Preparar DataFrame para mostrar/exportar: construir `df_show` de forma segura
        df_show = pd.DataFrame()

        # Columnas candidatas (nombre en datos -> título de columna)
        cols_map = [
            ('fecha', 'Fecha'),
            ('codigo', 'Código'),
            ('producto_nombre', 'Producto'),
            ('nombre', 'Producto'),
            ('tipo_movimiento', 'Tipo'),
            ('referencia_folio', 'Referencia'),
            ('usuario', 'Usuario')
        ]

        for src, title in cols_map:
            if src in df.columns and title not in df_show.columns:
                df_show[title] = df[src]

        # Calcular deltas (si existen campos antes/despues)
        if 'disponible_despues' in df.columns and 'disponible_antes' in df.columns:
            df_show['Δ Disponible'] = df['disponible_despues'] - df['disponible_antes']
        else:
            df_show['Δ Disponible'] = 0

        if 'rentado_despues' in df.columns and 'rentado_antes' in df.columns:
            df_show['Δ Rentado'] = df['rentado_despues'] - df['rentado_antes']
        else:
            df_show['Δ Rentado'] = 0

        if 'mantenimiento_despues' in df.columns and 'mantenimiento_antes' in df.columns:
            df_show['Δ Mantenimiento'] = df['mantenimiento_despues'] - df['mantenimiento_antes']
        else:
            df_show['Δ Mantenimiento'] = 0

        if 'chatarra_despues' in df.columns and 'chatarra_antes' in df.columns:
            df_show['Δ Chatarra'] = df['chatarra_despues'] - df['chatarra_antes']
        else:
            df_show['Δ Chatarra'] = 0

        # Si no hay columnas de producto, intentar usar 'producto_id'
        if 'Producto' not in df_show.columns and 'producto_id' in df.columns:
            df_show['Producto'] = df['producto_id']

        # Rellenar campos vacíos con guión para presentación
        df_show = df_show.fillna('—')

        st.dataframe(
            df_show.style.applymap(style_delta, subset=['Δ Disponible', 'Δ Rentado', 'Δ Mantenimiento', 'Δ Chatarra']),
            use_container_width=True, 
            hide_index=True
        )

        # Botones de exportación
        col_ex_a, col_ex_b, col_ex_empty = st.columns([1, 1, 3])
        with col_ex_a:
            csv_data = export_to_csv(df_show)
            st.download_button(
                label=":material/file_download: Exportar Bitácora",
                data=csv_data,
                file_name=f"bitacora_inv_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
                key="btn_inv_csv"
            )
        with col_ex_b:
            pdf_data = export_to_pdf(df_show, title="Bitácora de Movimientos de Inventario")
            st.download_button(
                label=":material/picture_as_pdf: PDF Bitácora",
                data=pdf_data,
                file_name=f"bitacora_inv_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                mime="application/pdf",
                key="btn_inv_pdf"
            )

        # Detalle de un movimiento
        if prod_id:
            st.divider()
            st.markdown("#### Historial completo del producto")
            historial = get_bitacora_producto(prod_id)
            if historial:
                with st.expander("Ver estado antes/después de cada movimiento"):
                    for mov in historial[:20]:
                        col1, col2, col3 = st.columns([2, 3, 3])
                        with col1:
                            fecha = mov['fecha']
                            st.markdown(
                                f"**{fecha.strftime('%d/%m/%Y %H:%M') if hasattr(fecha,'strftime') else fecha}**"
                            )
                            st.caption(mov['tipo_movimiento'])
                            st.caption(mov.get('referencia_folio') or '—')
                        with col2:
                            st.markdown("**Antes:**")
                            st.caption(f"Disponible: {mov['disponible_antes']}")
                            st.caption(f"Rentado: {mov['rentado_antes']}")
                            st.caption(f"Mantenimiento: {mov['mantenimiento_antes']}")
                        with col3:
                            st.markdown("**Después:**")
                            st.caption(f"Disponible: {mov['disponible_despues']}")
                            st.caption(f"Rentado: {mov['rentado_despues']}")
                            st.caption(f"Mantenimiento: {mov['mantenimiento_despues']}")
                        st.divider()

# ================================================
# TAB 2 — SALDO EN OBRA
# ================================================
with tab_saldo_obra:
    st.subheader("Inventario actualmente en obra")
    st.caption("Resumen detallado de las piezas que se encuentran en posesión de los clientes.")

    contratos_campo = get_contratos_con_equipo_en_campo()

    if not contratos_campo:
        st.info("No hay equipo en campo actualmente. Todas las piezas están en almacén.")
    else:
        opciones_c = {
            f"{c['folio']} — {c['cliente_nombre']} ({c['obra_nombre'] or 'Sin Obra'})": c
            for c in contratos_campo
        }
        c_sel = st.selectbox(
            "Selecciona un contrato/obra para ver el detalle",
            list(opciones_c.keys()),
            key="so_contrato_sel"
        )
        data_c = opciones_c[c_sel]

        # Obtener saldo detallado
        saldo = get_saldo_en_campo(data_c['id'])

        if not saldo:
            st.warning("No se encontró saldo detallado para este contrato.")
        else:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Cliente:** {data_c['cliente_nombre']}")
                st.markdown(f"**Obra:** {data_c['obra_nombre'] or '—'}")
            with col2:
                st.markdown(f"**Folio Contrato:** {data_c['folio']}")
                st.markdown(f"**Dirección:** {data_c['direccion_obra'] or '—'}")

            st.divider()

            df_so = pd.DataFrame(saldo)
            df_so_show = df_so[[
                'codigo', 'nombre', 'total_enviado',
                'total_devuelto', 'saldo_en_campo'
            ]]
            df_so_show.columns = [
                'Código', 'Producto', 'Enviado',
                'Devuelto', 'En Campo'
            ]
            
            # Estilo para destacar el saldo
            st.dataframe(
                df_so_show.style.applymap(
                    lambda x: 'background-color: #f8fafc; font-weight: bold;' if isinstance(x, (int, float)) and x > 0 else '',
                    subset=['En Campo']
                ),
                use_container_width=True,
                hide_index=True
            )

            # Exportar saldo
            csv_so = export_to_csv(df_so_show)
            st.download_button(
                label=f":material/file_download: Exportar Saldo {data_c['folio']}",
                data=csv_so,
                file_name=f"saldo_campo_{data_c['folio']}_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )

# ================================================
# TAB 2 — NUEVO CONTEO FÍSICO
# ================================================
with tab_nuevo_conteo:
    st.subheader("Iniciar nuevo conteo físico")

    col1, col2 = st.columns(2)
    with col1:
        fecha_conteo = st.date_input(
            "Fecha del conteo *",
            value=date.today(),
            key="cnt_fecha"
        )
        periodo = st.text_input(
            "Período *",
            value=date.today().strftime('%Y-%m'),
            placeholder="2026-03",
            key="cnt_periodo"
        )
    with col2:
        responsable = st.text_input(
            "Responsable *",
            placeholder="Nombre del encargado de almacén",
            key="cnt_resp"
        )
        notas_cnt = st.text_area(
            "Notas",
            placeholder="Observaciones generales del conteo...",
            key="cnt_notas"
        )

    st.info(
        "📌 Al crear el conteo, el sistema precarga automáticamente "
        "todos los productos con sus valores actuales. "
        "El encargado corrige los que difieran de la realidad física."
    )

    if st.button(
        ":material/add_box: Iniciar conteo físico",
        type="primary",
        use_container_width=True,
        key="btn_crear_conteo"
    ):
        if not responsable:
            st.error("❌ El responsable es obligatorio.")
        elif not periodo:
            st.error("❌ El período es obligatorio.")
        else:
            try:
                folio = generar_folio_conteo()
                conteo_id = crear_conteo({
                    'folio'      : folio,
                    'fecha'      : fecha_conteo,
                    'periodo'    : periodo,
                    'responsable': responsable,
                    'notas'      : notas_cnt
                })
                st.success(f":material/check_circle: Conteo {folio} iniciado. Ve al tab 'Conteos realizados' para capturar los valores físicos.")
                st.session_state.conteo_activo = conteo_id
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error: {e}")

# ================================================
# TAB 3 — CONTEOS REALIZADOS
# ================================================
with tab_conteos:
    st.subheader("Conteos físicos")

    conteos = get_conteos()

    if not conteos:
        st.info("No hay conteos registrados. Inicia uno en el tab anterior.")
    else:
        ESTATUS_CNT = {
            'en_proceso': 'En proceso',
            'cerrado'   : 'Cerrado',
            'cancelado' : 'Cancelado'
        }

        # Lista de conteos
        df_cnt = pd.DataFrame(conteos)
        df_cnt['estatus'] = df_cnt['estatus'].map(ESTATUS_CNT)
        df_cnt['fecha']   = pd.to_datetime(df_cnt['fecha'], errors='coerce').dt.strftime('%d/%m/%Y')
        df_show = df_cnt[[
            'folio', 'periodo', 'fecha', 'responsable',
            'total_productos', 'productos_con_diferencia',
            'ajustes_aplicados', 'estatus'
        ]].fillna('—')
        df_show.columns = [
            'Folio', 'Período', 'Fecha', 'Responsable',
            'Productos', 'Con diferencia',
            'Ajustes aplicados', 'Estatus'
        ]
        st.dataframe(df_show, use_container_width=True, hide_index=True)

        st.divider()

        # Seleccionar conteo para capturar / revisar
        opciones_cnt = {
            f"{c['folio']} — {c['periodo']} — {ESTATUS_CNT.get(c['estatus'], c['estatus'])}": c['id']
            for c in conteos
        }
        cnt_sel = st.selectbox(
            "Selecciona conteo",
            list(opciones_cnt.keys()),
            key="cnt_sel"
        )
        cnt_id = opciones_cnt[cnt_sel]

        # Conteo seleccionado
        conteo_actual = next((c for c in conteos if c['id'] == cnt_id), None)
        items = get_conteo_items(cnt_id)

        if items:
            est_actual = conteo_actual['estatus'] if conteo_actual else 'cerrado'
            es_editable = est_actual == 'en_proceso'

            # Métricas
            df_items = pd.DataFrame(items)
            con_diff = len(df_items[
                (df_items['diff_disponible'] != 0) |
                (df_items['diff_mantenimiento'] != 0) |
                (df_items['diff_chatarra'] != 0)
            ])
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total productos",    len(items))
            col2.metric("Con diferencia",     con_diff)
            col3.metric("Sin diferencia",     len(items) - con_diff)
            col4.metric("Ajustes aplicados",  int(df_items['ajuste_aplicado'].sum()))

            if con_diff > 0:
                st.warning(f":material/warning: {con_diff} producto(s) tienen diferencia entre el sistema y el conteo físico.")
            else:
                st.success(":material/check_circle: Todos los productos coinciden con el sistema.")

            st.divider()

            # Tabla de captura
            st.markdown("#### Captura de conteo físico")

            if es_editable:
                st.caption("Modifica solo los productos donde el conteo físico difiera del sistema.")

            # Mostrar por grupos: con diferencia primero
            items_diff    = [i for i in items if i['diff_disponible'] != 0 or i['diff_mantenimiento'] != 0 or i['diff_chatarra'] != 0]
            items_sin_diff = [i for i in items if i['diff_disponible'] == 0 and i['diff_mantenimiento'] == 0 and i['diff_chatarra'] == 0]

            def render_items(lista, titulo, expandido):
                if not lista:
                    return
                with st.expander(titulo, expanded=expandido):
                    # Encabezados
                    cols = st.columns([2, 1, 1, 1, 1, 1, 1, 2])
                    cols[0].markdown("**Producto**")
                    cols[1].markdown("**Sys Disp**")
                    cols[2].markdown("**Sys Mant**")
                    cols[3].markdown("**Sys Chat**")
                    cols[4].markdown("**Fís Disp**")
                    cols[5].markdown("**Fís Mant**")
                    cols[6].markdown("**Fís Chat**")
                    cols[7].markdown("**Justificación**")

                    for item in lista:
                        cols = st.columns([2, 1, 1, 1, 1, 1, 1, 2])
                        with cols[0]:
                            st.markdown(f"**{item['codigo']}**")
                            st.caption(item['producto_nombre'])
                        cols[1].markdown(str(item['sistema_disponible']))
                        cols[2].markdown(str(item['sistema_mantenimiento']))
                        cols[3].markdown(str(item['sistema_chatarra']))

                        if es_editable:
                            with cols[4]:
                                fd = st.number_input(
                                    "fd", min_value=0,
                                    value=int(item['fisico_disponible']),
                                    step=1, label_visibility="collapsed",
                                    key=f"fd_{item['id']}"
                                )
                            with cols[5]:
                                fm = st.number_input(
                                    "fm", min_value=0,
                                    value=int(item['fisico_mantenimiento']),
                                    step=1, label_visibility="collapsed",
                                    key=f"fm_{item['id']}"
                                )
                            with cols[6]:
                                fc = st.number_input(
                                    "fc", min_value=0,
                                    value=int(item['fisico_chatarra']),
                                    step=1, label_visibility="collapsed",
                                    key=f"fc_{item['id']}"
                                )
                            with cols[7]:
                                just = st.text_input(
                                    "just",
                                    value=item.get('justificacion') or '',
                                    label_visibility="collapsed",
                                    placeholder="Motivo...",
                                    key=f"just_{item['id']}"
                                )
                            # Guardar cambios por item
                            if (fd != item['fisico_disponible'] or
                                fm != item['fisico_mantenimiento'] or
                                fc != item['fisico_chatarra']):
                                actualizar_conteo_item(
                                    item['id'], fd, fm, fc, just
                                )
                        else:
                            cols[4].markdown(str(item['fisico_disponible']))
                            cols[5].markdown(str(item['fisico_mantenimiento']))
                            cols[6].markdown(str(item['fisico_chatarra']))
                            with cols[7]:
                                diff_d = item['diff_disponible']
                                diff_m = item['diff_mantenimiento']
                                diff_c = item['diff_chatarra']
                                if diff_d != 0 or diff_m != 0 or diff_c != 0:
                                    st.caption(
                                        f"Δ: {diff_d:+d} / {diff_m:+d} / {diff_c:+d}"
                                    )
                                    if item.get('justificacion'):
                                        st.caption(item['justificacion'])

            if items_diff:
                render_items(
                    items_diff,
                    f"⚠️ Productos con diferencia ({len(items_diff)})",
                    True
                )
            render_items(
                items_sin_diff,
                f"✅ Productos sin diferencia ({len(items_sin_diff)})",
                False
            )

            # Acciones
            if es_editable:
                st.divider()
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(
                        ":material/refresh: Actualizar vista",
                        key="btn_refresh_cnt"
                    ):
                        st.rerun()
                with col2:
                    if con_diff > 0:
                        st.warning(
                            f"Al aplicar ajuste se actualizará el inventario "
                            f"en {con_diff} producto(s)."
                        )
                        if st.button(
                            ":material/bolt: Aplicar ajustes al inventario",
                            type="primary",
                            use_container_width=True,
                            key="btn_aplicar_cnt"
                        ):
                            items_sin_just = [
                                i for i in items_diff
                                if not i.get('justificacion')
                            ]
                            if items_sin_just:
                                st.error(
                                    f"❌ {len(items_sin_just)} producto(s) con "
                                    f"diferencia no tienen justificación. "
                                    f"Completa el campo antes de aplicar."
                                )
                            else:
                                try:
                                    if check_permission('admin'):
                                        aplicar_ajuste_conteo(cnt_id)
                                        st.success(
                                            ":material/check_circle: Ajustes aplicados. Inventario actualizado. "
                                            "Conteo cerrado."
                                        )
                                        st.rerun()
                                    else:
                                        st.error("🚫 No tienes permisos de administrador para aplicar ajustes.")
                                except Exception as e:
                                    st.error(f"❌ Error: {e}")
                    else:
                        if st.button(
                            ":material/check_circle: Cerrar conteo sin ajustes",
                            type="primary",
                            use_container_width=True,
                            key="btn_cerrar_cnt"
                        ):
                            try:
                                aplicar_ajuste_conteo(cnt_id)
                                st.success(":material/check_circle: Conteo cerrado. Todo cuadró.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Error: {e}")