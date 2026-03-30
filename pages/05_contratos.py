# pages/05_contratos.py
# Módulo de gestión de contratos

import streamlit as st
import pandas as pd
from datetime import date, timedelta
from utils.logger import log_action, logger

# Validar permisos
roles_permitidos = ['admin', 'ventas']
if st.session_state.get('rol', 'usuario').lower() not in roles_permitidos:
    st.error(f"🚫 **No tienes acceso a esta sección.**\nRoles requeridos: {', '.join(roles_permitidos)}")
    logger.warning(f"ACCESO_DENEGADO: {st.session_state.get('usuario')} intentó acceder a Contratos")
    st.stop()

from utils.database import (
    get_clientes,
    get_productos,
    get_obras,
    get_obras_por_cliente,
    get_cotizaciones_aprobadas,
    get_cotizacion_detalle,
    generar_folio_contrato,
    crear_contrato,
    get_contratos,
    get_contrato_detalle,
    actualizar_estatus_contrato,
    registrar_anticipo_pago,
    asignar_obra_contrato,
    get_hojas_salida,
    get_hojas_entrada,
    get_pagos_por_contrato
)
from utils.reporting import export_to_csv, export_to_pdf
from utils.auth_manager import check_permission



st.title(":material/description: Contratos")
st.divider()

ESTATUS_LABEL = {
    'activo'    : 'Activo',
    'vencido'   : 'Vencido',
    'renovado'  : 'Renovado',
    'cancelado' : 'Cancelado',
    'finalizado': 'Finalizado',
    'venta'     : 'Venta'
}

TIPO_LABEL = {
    'renta' : 'Renta',
    'venta' : 'Venta',
    'armado': 'Armado'
}

tab_seguimiento, tab_cotizaciones, tab_lista, tab_nuevo, tab_detalle = st.tabs([
    ":material/insights: Seguimiento",
    ":material/assignment_turned_in: Cotizaciones Aprobadas",
    ":material/list_alt: Lista De Contratos",
    ":material/add_box: Nuevo Contrato",
    ":material/search: Ver Detalle"
])

# ================================================
# TAB 0 — SEGUIMIENTO DE CONTRATOS (DASHBOARD)
# ================================================
with tab_seguimiento:
    st.subheader("Tablero de Seguimiento de Contratos")
    
    contratos_todos = get_contratos(estatus='activo')
    hoy = date.today()
    
    if not contratos_todos:
        st.info("No hay contratos activos para monitorear.")
    else:
        df_base = pd.DataFrame(contratos_todos)
        df_base['fecha_fin'] = pd.to_datetime(df_base['fecha_fin']).dt.date
        df_base['atraso'] = df_base['fecha_fin'].apply(lambda x: max(0, (hoy - x).days))
        df_atraso = df_base[df_base['atraso'] > 0].sort_values('atraso', ascending=False)
        
        # 1. Contratos con ATRASO
        st.markdown(f"#### :material/error: Contratos con Atraso ({len(df_atraso)})")
        if not df_atraso.empty:
            df_atraso_display = df_atraso[['folio', 'cliente_nombre', 'atraso', 'fecha_fin', 'monto_total']]
            df_atraso_display.columns = ['Folio', 'Cliente', 'Días Atraso', 'Venció el', 'Monto Total']
            st.dataframe(df_atraso_display, use_container_width=True, hide_index=True)
        else:
            st.success(":material/check_circle: No hay contratos con atraso.")
            
        st.divider()
        
        # 2. Contratos PROXIMOS A VENCER (Próximos 7 días)
        df_vencer = df_base[(df_base['atraso'] == 0) & 
                            (df_base['fecha_fin'] <= hoy + timedelta(days=7))].sort_values('fecha_fin')
        st.markdown(f"#### :material/warning: Próximos a Vencer (7 días) ({len(df_vencer)})")
        if not df_vencer.empty:
            df_vencer_display = df_vencer[['folio', 'cliente_nombre', 'fecha_fin', 'monto_total']]
            df_vencer_display.columns = ['Folio', 'Cliente', 'Vence el', 'Monto Total']
            st.dataframe(df_vencer_display, use_container_width=True, hide_index=True)
        else:
            st.info("No hay contratos venciendo en los próximos 7 días.")

        st.divider()
        
        # 3. Acceso rápido a detalle
        st.markdown("#### 🔍 Consulta rápida")
        opciones_seg = {f"{c['folio']} — {c['cliente_nombre']}": c['id'] for c in contratos_todos}
        sel_seg = st.selectbox("Selecciona un contrato para inspeccionar logística y pagos", list(opciones_seg.keys()), key="seg_quick")
        if sel_seg:
            if st.button(":material/visibility: Ver detalle completo", key="btn_jump_detalle"):
                st.session_state.contrato_id_detalle = opciones_seg[sel_seg]
                st.info("Cargado. Cambia a la pestaña '🔍 Ver detalle' para inspeccionar.")

# ================================================
# TAB 1 — COTIZACIONES APROBADAS
# ================================================
with tab_cotizaciones:
    st.subheader("Cotizaciones listas para contrato")
    st.caption("Cotizaciones aprobadas que aún no tienen contrato generado.")

    cotizaciones = get_cotizaciones_aprobadas()

    if not cotizaciones:
        st.info("No hay cotizaciones aprobadas pendientes de contrato.")
    else:
        df = pd.DataFrame(cotizaciones)
        df['total'] = df['total'].apply(lambda x: f"${x:,.2f}")
        df['created_at'] = pd.to_datetime(df['created_at']).dt.strftime('%d/%m/%Y')
        df_show = df[[
            'folio', 'cliente_nombre', 'tipo_operacion',
            'dias_renta', 'total', 'created_at'
        ]]
        df_show.columns = ['Folio', 'Cliente', 'Tipo', 'Días', 'Total', 'Fecha']
        st.dataframe(df_show, use_container_width=True, hide_index=True)
        st.caption(f"{len(cotizaciones)} cotizaciones pendientes de contrato")

        st.divider()
        st.info("👆 Selecciona una cotización en el tab **➕ Nuevo contrato** para generar su contrato.")

# ================================================
# TAB 2 — LISTA DE CONTRATOS
# ================================================
with tab_lista:
    st.subheader("Contratos registrados")

    col1, col2 = st.columns([3, 1])
    with col1:
        filtro = st.selectbox(
            "Filtrar por estatus",
            ["Todos"] + list(ESTATUS_LABEL.values()),
            key="filtro_lista"
        )

    estatus_key = None
    if filtro != "Todos":
        estatus_key = [k for k, v in ESTATUS_LABEL.items() if v == filtro][0]

    contratos = get_contratos(estatus=estatus_key)

    if not contratos:
        st.info("No hay contratos registrados.")
    
    else:
        df = pd.DataFrame(contratos)
        df['estatus']      = df['estatus'].map(ESTATUS_LABEL)
        df['tipo_contrato'] = df['tipo_contrato'].map(TIPO_LABEL)
        df['monto_total']  = df['monto_total'].apply(lambda x: f"${x:,.2f}")
        df['anticipo_estatus'] = df['anticipo_estatus'].map({
            'pendiente': 'Pendiente',
            'parcial'  : 'Parcial',
            'completo' : 'Completo'
        })
        for col_fecha in ['fecha_inicio', 'fecha_fin']:
            if col_fecha in df.columns:
                df[col_fecha] = pd.to_datetime(df[col_fecha]).dt.strftime('%d/%m/%Y')

        df_show = df[[
            'folio', 'cliente_nombre', 'obra_nombre',
            'tipo_contrato', 'fecha_inicio', 'fecha_fin',
            'monto_total', 'anticipo_estatus', 'estatus'
        ]]
        df_show.columns = [
            'Folio', 'Cliente', 'Obra',
            'Tipo', 'Inicio', 'Fin',
            'Total', 'Anticipo', 'Estatus'
        ]
        st.dataframe(df_show, use_container_width=True, hide_index=True)

        # Métricas
        st.divider()
        contratos_df = pd.DataFrame(contratos)
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("🟢 Activos", len(contratos_df[contratos_df['estatus'] == 'activo']))
        with col2:
            st.metric("🔴 Vencidos", len(contratos_df[contratos_df['estatus'] == 'vencido']))
        with col3:
            pendientes = len(contratos_df[contratos_df['anticipo_estatus'] == 'pendiente'])
            st.metric("Anticipo pendiente", pendientes)
        with col4:
            total = contratos_df['monto_total'].sum()
            st.metric("💰 Total contratos", f"${total:,.2f}")

# ================================================
# TAB 3 — NUEVO CONTRATO
# ================================================
with tab_nuevo:
    st.subheader("Crear nuevo contrato")

    # Seleccionar cotización aprobada
    cotizaciones = get_cotizaciones_aprobadas()

    # Asegurar variables definidas en todos los caminos
    cot = None
    cot_items = []

    if not cotizaciones:
        st.warning("No hay cotizaciones aprobadas. Aprueba una cotización primero.")
    else:
        opciones_cot = {
            f"{c['folio']} — {c['cliente_nombre']} — ${float(c['total']):,.2f}": c['id']
            for c in cotizaciones
        }
        cot_sel = st.selectbox("Selecciona cotización aprobada *", list(opciones_cot.keys()))
        cot_id  = opciones_cot[cot_sel]
        # Inicializar por defecto para evitar referencias no definidas
        cot = None
        cot_items = []
        try:
            cot, cot_items = get_cotizacion_detalle(cot_id)
        except Exception:
            cot = None

    # Comprobar explícitamente None para evitar errores de ambigüedad
    if cot is not None:
        # Mostrar resumen cotización
        with st.expander(":material/list_alt: Ver resumen de cotización", expanded=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"**Cliente:** {cot['cliente_nombre']}")
                st.markdown(f"**Tipo:** {cot['tipo_operacion'].capitalize()}")
            with col2:
                st.markdown(f"**Días:** {cot['dias_renta']}")
                st.markdown(f"**Subtotal:** ${float(cot['subtotal']):,.2f}")
            with col3:
                st.markdown(f"**IVA:** ${float(cot['iva']):,.2f}")
                st.markdown(f"**Total:** ${float(cot['total']):,.2f}")

        st.divider()

        # Formulario contrato
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### Datos del contrato")
            tipo_contrato = st.selectbox(
                "Tipo de contrato",
                list(TIPO_LABEL.keys()),
                format_func=lambda x: TIPO_LABEL[x],
                index=0 if cot['tipo_operacion'] == 'renta' else 1
            )
            fecha_inicio = st.date_input("Fecha de inicio *", value=date.today())
            dias_renta   = st.number_input(
                "Días de renta",
                min_value=1,
                value=int(cot['dias_renta']),
                step=1
            )
            fecha_fin = fecha_inicio + timedelta(days=dias_renta)
            st.info(f"📅 Fecha de fin: {fecha_fin.strftime('%d/%m/%Y')}")

            # Obra
            obras_cliente = get_obras_por_cliente(cot['cliente_id'])
            obra_id = cot.get('obra_id')
            if obras_cliente:
                opciones_obras = {"Sin obra": None}
                opciones_obras.update({
                    f"{o['folio_obra']} — {o['nombre_proyecto']}": o['id']
                    for o in obras_cliente
                })
                idx_default = 0
                if obra_id:
                    keys = list(opciones_obras.keys())
                    vals = list(opciones_obras.values())
                    if obra_id in vals:
                        idx_default = vals.index(obra_id)
                obra_sel = st.selectbox(
                    "Obra (opcional)",
                    list(opciones_obras.keys()),
                    index=idx_default
                )
                obra_id = opciones_obras[obra_sel]
            else:
                st.caption("Cliente sin obras activas.")

            notas = st.text_area("Notas", placeholder="Condiciones especiales...")

        with col2:
            st.markdown("#### Anticipo")
            anticipo_pct = st.slider(
                "Porcentaje de anticipo requerido",
                min_value=10, max_value=100,
                value=50, step=5,
                format="%d%%"
            )
            anticipo_requerido = float(cot['total']) * anticipo_pct / 100
            st.metric("Monto anticipo requerido", f"${anticipo_requerido:,.2f}")

            st.divider()
            st.markdown("#### Registro de pago")
            anticipo_pagado = st.number_input(
                "Monto recibido",
                min_value=0.0,
                max_value=float(cot['total']),
                value=0.0,
                step=100.0,
                format="%.2f"
            )
            anticipo_ref  = st.text_input(
                "Referencia / folio de depósito",
                placeholder="REF-123456"
            )
            anticipo_fecha = st.date_input("Fecha de pago", value=date.today())

            if anticipo_pagado >= anticipo_requerido:
                st.success(":material/check_circle: Anticipo completo")
            elif anticipo_pagado > 0:
                st.warning(f":material/warning: Anticipo parcial — faltan ${anticipo_requerido - anticipo_pagado:,.2f}")
            else:
                st.error(":material/hourglass_empty: Anticipo pendiente")

            st.divider()
            st.markdown("#### Pagaré")
            pagare_numero   = st.text_input("Número de pagaré", placeholder="PAG-0001")
            pagare_monto    = st.number_input(
                "Monto del pagaré",
                min_value=0.0,
                value=float(cot['total']),
                step=100.0,
                format="%.2f"
            )
            pagare_firmante = st.text_input(
                "Firmante",
                placeholder="Nombre completo del firmante"
            )
            pagare_vencimiento = st.date_input(
                "Fecha de vencimiento del pagaré",
                value=fecha_inicio + timedelta(days=dias_renta + 30)
            )
            pagare_firmado = st.checkbox("¿Pagaré firmado?", value=False)

        st.divider()

        if st.button("💾 Generar contrato", type="primary", use_container_width=True):
            if anticipo_pagado == 0:
                st.error("❌ Debes registrar al menos el pago del anticipo.")
            elif not pagare_firmante:
                st.error("❌ El firmante del pagaré es obligatorio.")
            else:
                try:
                    # Determinar estatus anticipo
                    if anticipo_pagado >= anticipo_requerido:
                        ant_estatus = 'completo'
                    elif anticipo_pagado > 0:
                        ant_estatus = 'parcial'
                    else:
                        ant_estatus = 'pendiente'

                    folio = generar_folio_contrato()
                    nuevo_id = crear_contrato({
                        'folio'                   : folio,
                        'cotizacion_id'           : cot_id,
                        'obra_id'                 : obra_id,
                        'cliente_id'              : cot['cliente_id'],
                        'tipo_contrato'           : tipo_contrato,
                        'estatus'                 : 'activo',
                        'fecha_contrato'          : date.today(),
                        'fecha_inicio'            : fecha_inicio,
                        'fecha_fin'               : fecha_fin,
                        'dias_renta'              : dias_renta,
                        'subtotal'                : float(cot['subtotal']),
                        'monto_flete'             : float(cot['monto_flete']),
                        'iva'                     : float(cot['iva']),
                        'monto_total'             : float(cot['total']),
                        'anticipo_porcentaje'     : anticipo_pct,
                        'anticipo_requerido'      : anticipo_requerido,
                        'anticipo_pagado'         : anticipo_pagado,
                        'anticipo_referencia'     : anticipo_ref,
                        'anticipo_fecha_pago'     : anticipo_fecha,
                        'anticipo_estatus'        : ant_estatus,
                        'pagare_numero'           : pagare_numero,
                        'pagare_monto'            : pagare_monto,
                        'pagare_firmante'         : pagare_firmante,
                        'pagare_fecha_vencimiento': pagare_vencimiento,
                        'pagare_firmado'          : pagare_firmado,
                        'contrato_origen_id'      : None,
                        'notas'                   : notas
                    }, [dict(i) for i in cot_items])

                    # Actualizar total facturado en obra
                    if obra_id:
                        from utils.database import actualizar_total_facturado_obra
                        actualizar_total_facturado_obra(obra_id)

                    st.success(f":material/check_circle: Contrato {folio} generado correctamente.")
                    st.rerun()
                except Exception as e:
                    st.error(f":material/error: Error: {e}")

# ================================================
# TAB 4 — DETALLE
# ================================================
with tab_detalle:
    st.subheader("Detalle de contrato")

    contratos = get_contratos()

    if not contratos:
        st.info("No hay contratos registrados.")
    else:
        opciones = {
            f"{c['folio']} — {c['cliente_nombre']}": c['id']
            for c in contratos
        }
        if 'contrato_id_detalle' in st.session_state:
            default_ix = 0
            keys_list = list(opciones.keys())
            for i, k in enumerate(keys_list):
                if opciones[k] == st.session_state.contrato_id_detalle:
                    default_ix = i
                    break
            seleccion = st.selectbox("Selecciona contrato", keys_list, index=default_ix)
        else:
            seleccion = st.selectbox("Selecciona contrato", list(opciones.keys()))
        
        contrato_id = opciones[seleccion]
        try:
            ctr, items = get_contrato_detalle(contrato_id)
        except Exception as e:
            st.error(f"Error: {e}")
            st.stop()

        if ctr:
            # Datos generales
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"**Folio:** {ctr['folio']}")
                st.markdown(f"**Cliente:** {ctr['cliente_nombre']}")
                st.markdown(f"**RFC:** {ctr['rfc']}")
                st.markdown(f"**Cotización origen:** {ctr.get('cotizacion_folio') or '—'}")
            with col2:
                obra_txt = f"{ctr.get('folio_obra')} — {ctr.get('obra_nombre')}" if ctr.get('obra_nombre') else "Sin obra"
                st.markdown(f"**Obra:** {obra_txt}")
                st.markdown(f"**Tipo:** {TIPO_LABEL.get(ctr['tipo_contrato'], '—')}")
                fi = ctr['fecha_inicio']
                ff = ctr['fecha_fin']
                st.markdown(f"**Inicio:** {fi.strftime('%d/%m/%Y') if fi else '—'}")
                st.markdown(f"**Fin:** {ff.strftime('%d/%m/%Y') if ff else '—'}")
                st.markdown(f"**Días:** {ctr['dias_renta']}")
            with col3:
                st.markdown(f"**Total:** ${float(ctr['monto_total']):,.2f}")
                st.markdown(f"**Estatus:** {ESTATUS_LABEL.get(ctr['estatus'], '—')}")
                st.markdown(f"**Anticipo requerido:** ${float(ctr['anticipo_requerido']):,.2f}")
                st.markdown(f"**Anticipo pagado:** ${float(ctr['anticipo_pagado']):,.2f}")
                ant_est = {
                    'pendiente': 'Pendiente',
                    'parcial'  : 'Parcial',
                    'completo' : 'Completo'
                }.get(ctr['anticipo_estatus'], '—')
                st.markdown(f"**Estatus anticipo:** {ant_est}")

            # RECOMENDACIÓN: Saldo pendiente
            resumen_fin = get_pagos_por_contrato(contrato_id)
            if resumen_fin:
                saldo_p = float(resumen_fin.get('saldo_pendiente', 0))
                color_saldo = "red" if saldo_p > 0 else "green"
                st.markdown(f"**Saldo Pendiente:** <span style='color:{color_saldo};font-weight:bold'>${saldo_p:,.2f}</span>", unsafe_allow_html=True)
            
            st.divider()
            
            # SECCIÓN LOGÍSTICA
            st.subheader(":material/local_shipping: Flujo Logístico (Movimientos)")
            col_log1, col_log2 = st.columns(2)
            
            with col_log1:
                st.markdown("**Hojas de Salida (Entregas)**")
                hs_list = get_hojas_salida(contrato_id)
                if hs_list:
                    for hs in hs_list:
                        est = hs['estatus'].upper()
                        color = "orange" if est == "PENDIENTE" else "green"
                        st.markdown(f"- **{hs['folio']}** ({hs['fecha_salida'].strftime('%d/%m/%Y')}) — <span style='color:{color}'>{est}</span>", unsafe_allow_html=True)
                else:
                    st.caption("No hay salidas registradas.")
            
            with col_log2:
                st.markdown("**Hojas de Entrada (Devoluciones)**")
                he_list = get_hojas_entrada(contrato_id=contrato_id)
                if he_list:
                    for he in he_list:
                        est = he['estatus'].upper()
                        color = "orange" if est == "PENDIENTE" else "green"
                        st.markdown(f"- **{he['folio']}** ({he['fecha_entrada'].strftime('%d/%m/%Y')}) — <span style='color:{color}'>{est}</span>", unsafe_allow_html=True)
                else:
                    st.caption("No hay entradas registradas.")

            st.divider()

            # Pagaré
            with st.expander(":material/edit_note: Datos del Pagaré"):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Número:** {ctr.get('pagare_numero') or '—'}")
                    st.markdown(f"**Monto:** ${float(ctr['pagare_monto']):,.2f}")
                with col2:
                    st.markdown(f"**Firmante:** {ctr.get('pagare_firmante') or '—'}")
                    pv = ctr.get('pagare_fecha_vencimiento')
                    st.markdown(f"**Vencimiento:** {pv.strftime('%d/%m/%Y') if pv else '—'}")
                    st.markdown(f"**Firmado:** {'SI' if ctr['pagare_firmado'] else 'NO'}")

            # Productos
            st.divider()
            st.subheader("Productos del contrato")
            if items:
                df_items = pd.DataFrame(items)
                df_items = df_items[[
                    'codigo', 'producto_nombre', 'cantidad',
                    'precio_unitario', 'subtotal'
                ]]
                df_items.columns = ['Código', 'Producto', 'Cantidad', 'Precio Unit.', 'Subtotal']
                st.dataframe(df_items, use_container_width=True, hide_index=True)

            # Totales
            st.divider()
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Subtotal", f"${float(ctr['subtotal']):,.2f}")
            with col2:
                st.metric("Flete", f"${float(ctr['monto_flete']):,.2f}")
            with col3:
                st.metric("IVA", f"${float(ctr['iva']):,.2f}")
            with col4:
                st.metric("Total", f"${float(ctr['monto_total']):,.2f}")

            st.divider()

            # Acciones
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Cambiar estatus**")
                nuevo_estatus = st.selectbox(
                    "Estatus",
                    list(ESTATUS_LABEL.keys()),
                    index=list(ESTATUS_LABEL.keys()).index(ctr['estatus']),
                    format_func=lambda x: ESTATUS_LABEL[x],
                    key="sel_estatus"
                )
                if st.button("Actualizar estatus"):
                    if check_permission('admin'):
                        actualizar_estatus_contrato(contrato_id, nuevo_estatus)
                        st.success(":material/check_circle: Estatus actualizado.")
                        st.rerun()
                    else:
                        st.error("🚫 No tienes permisos de administrador para cambiar estatus.")

            with col2:
                st.markdown("**Asignar obra**")
                todas_obras = get_obras(estatus='activa')
                if todas_obras:
                    opciones_obras = {"Sin obra": None}
                    opciones_obras.update({
                        f"{o['folio_obra']} — {o['nombre_proyecto']}": o['id']
                        for o in todas_obras
                    })
                    obra_actual = ctr.get('obra_id')
                    idx_obra = 0
                    if obra_actual:
                        vals = list(opciones_obras.values())
                        if obra_actual in vals:
                            idx_obra = vals.index(obra_actual)
                    obra_nueva = st.selectbox(
                        "Obra",
                        list(opciones_obras.keys()),
                        index=idx_obra,
                        key="sel_obra"
                    )
                    if st.button("Asignar obra"):
                        if check_permission('admin'):
                            asignar_obra_contrato(contrato_id, opciones_obras[obra_nueva])
                            st.success(":material/check_circle: Obra asignada correctamente.")
                            st.rerun()
                        else:
                            st.error("🚫 No tienes permisos de administrador para asignar obras.")
                else:
                    st.caption("No hay obras activas.")

            # Botón PDF contrato
            st.divider()
            if st.button(":material/picture_as_pdf: Generar PDF contrato", type="primary"):
                try:
                    from utils.pdf_generator import generar_pdf_contrato
                    pdf_bytes = generar_pdf_contrato(dict(ctr), [dict(i) for i in items])
                    st.download_button(
                        label=":material/file_download: Descargar contrato PDF",
                        data=pdf_bytes,
                        file_name=f"Contrato_{ctr['folio']}.pdf",
                        mime="application/pdf"
                    )
                except Exception as e:
                    st.error(f":material/picture_as_pdf: Error generando PDF: {e}")

            if ctr.get('notas'):
                st.info(f"📝 {ctr['notas']}")