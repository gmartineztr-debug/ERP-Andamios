# pages/09_renovaciones.py
# Módulo de Renovaciones de Contratos

import streamlit as st
import pandas as pd
from datetime import date, timedelta
from utils.database import (
    get_contratos_por_vencer,
    get_contrato_detalle,
    get_cadena_renovaciones,
    generar_folio_contrato,
    renovar_contrato,
    get_contratos,
    get_todos_folios_raiz,           # ← agregar
    get_estado_cuenta_folio_raiz,    # ← agregar
    get_resumen_folio_raiz           # ← agregar
)



st.title("🔄 Renovaciones de Contratos")
st.divider()

tab_alertas, tab_renovar, tab_historial, tab_edocuenta = st.tabs([
    "🚨 Alertas de vencimiento",
    "🔄 Renovar contrato",
    "📋 Historial de renovaciones",
    "📊 Estado de cuenta"
])

# ================================================
# TAB 1 — ALERTAS
# ================================================
with tab_alertas:
    st.subheader("Contratos que vencen en los próximos 7 días")

    por_vencer = get_contratos_por_vencer()

    if not por_vencer:
        st.success("✅ No hay contratos por vencer en los próximos 7 días.")
    else:
        # Métricas rápidas
        vencen_hoy    = [c for c in por_vencer if c['dias_restantes'] == 0]
        vencen_3dias  = [c for c in por_vencer if 0 < c['dias_restantes'] <= 3]
        vencen_7dias  = [c for c in por_vencer if 3 < c['dias_restantes'] <= 7]

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                "🔴 Vencen hoy",
                len(vencen_hoy),
                delta=None
            )
        with col2:
            st.metric(
                "🟠 Vencen en 1-3 días",
                len(vencen_3dias)
            )
        with col3:
            st.metric(
                "🟡 Vencen en 4-7 días",
                len(vencen_7dias)
            )

        st.divider()

        # Tabla de alertas
        for ctr in por_vencer:
            dias = ctr['dias_restantes']
            if dias == 0:
                color = "🔴"
                msg   = "**VENCE HOY**"
            elif dias <= 3:
                color = "🟠"
                msg   = f"Vence en **{dias}** día(s)"
            else:
                color = "🟡"
                msg   = f"Vence en **{dias}** días"

            with st.container():
                col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
                with col1:
                    st.markdown(
                        f"{color} **{ctr['folio']}** — {ctr['cliente_nombre']}"
                    )
                    obra_txt = f"{ctr.get('folio_obra','—')} — {ctr.get('obra_nombre','')}" \
                               if ctr.get('obra_nombre') else "Sin obra"
                    st.caption(f"Obra: {obra_txt}")
                with col2:
                    ff = ctr['fecha_fin']
                    st.markdown(f"**Vence:** {ff.strftime('%d/%m/%Y') if ff else '—'}")
                    st.caption(msg)
                with col3:
                    st.markdown(f"**Total:** ${float(ctr['monto_total']):,.2f}")
                    st.caption(f"Tel: {ctr.get('cliente_telefono') or '—'}")
                with col4:
                    if st.button(
                        "🔄 Renovar",
                        key=f"btn_renovar_{ctr['id']}",
                        type="primary"
                    ):
                        st.session_state.contrato_a_renovar = ctr['id']
                        st.session_state.ir_a_renovar       = True
                        st.rerun()
                    if st.button(
                        "📦 Recolectar",
                        key=f"btn_recolectar_{ctr['id']}"
                    ):
                        st.info(
                            f"Ve al módulo **Hojas de Entrada** "
                            f"para registrar la devolución del contrato {ctr['folio']}."
                        )

            st.divider()

# ================================================
# TAB 2 — RENOVAR
# ================================================
with tab_renovar:
    st.subheader("Crear renovación de contrato")

    # Si viene de alertas
    if st.session_state.get('ir_a_renovar'):
        st.session_state.ir_a_renovar = False
        st.info("Contrato preseleccionado desde alertas.")

    # Selector de contrato
    contratos_activos = get_contratos(estatus='activo')
    contratos_renta   = [c for c in contratos_activos if c['tipo_contrato'] == 'renta']

    if not contratos_renta:
        st.warning("No hay contratos de renta activos.")
    else:
        opciones_ctr = {
            f"{c['folio']} — {c['cliente_nombre']}": c['id']
            for c in contratos_renta
        }

        # Preseleccionar si viene de alertas
        default_idx = 0
        if st.session_state.get('contrato_a_renovar'):
            ids_list = list(opciones_ctr.values())
            if st.session_state.contrato_a_renovar in ids_list:
                default_idx = ids_list.index(
                    st.session_state.contrato_a_renovar
                )

        ctr_sel = st.selectbox(
            "Selecciona contrato a renovar *",
            list(opciones_ctr.keys()),
            index=default_idx,
            key="ren_ctr_sel"
        )
        ctr_id = opciones_ctr[ctr_sel]
        st.session_state.contrato_a_renovar = None

        # Cargar detalle
        ctr, ctr_items = get_contrato_detalle(ctr_id)

        if ctr:
            # Info contrato origen
            with st.expander("📋 Contrato origen", expanded=True):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown(f"**Folio:** {ctr['folio']}")
                    st.markdown(f"**Cliente:** {ctr['cliente_nombre']}")
                    st.markdown(f"**Tel:** {ctr.get('cliente_telefono') or '—'}")
                with col2:
                    obra_txt = f"{ctr.get('folio_obra','—')} — {ctr.get('obra_nombre','')}" \
                               if ctr.get('obra_nombre') else "Sin obra"
                    st.markdown(f"**Obra:** {obra_txt}")
                    st.markdown(f"**Dirección:** {ctr.get('direccion_obra') or '—'}")
                with col3:
                    ff = ctr['fecha_fin']
                    st.markdown(
                        f"**Vence:** {ff.strftime('%d/%m/%Y') if ff else '—'}"
                    )
                    dias_rest = (ff - date.today()).days if ff else 0
                    if dias_rest <= 0:
                        st.error(f"⚠️ Vencido hace {abs(dias_rest)} días")
                    elif dias_rest <= 3:
                        st.warning(f"⚠️ Vence en {dias_rest} días")
                    else:
                        st.info(f"Vence en {dias_rest} días")

            st.divider()

            # Datos de la renovación
            st.markdown("#### Datos de la renovación")
            col1, col2 = st.columns(2)
            with col1:
                fecha_inicio_ren = st.date_input(
                    "Fecha inicio *",
                    value=ff if ff else date.today(),
                    key="ren_fecha_inicio"
                )
                dias_ren = st.number_input(
                    "Días de renta *",
                    min_value=1,
                    value=int(ctr['dias_renta']),
                    step=1,
                    key="ren_dias"
                )
                fecha_fin_ren = fecha_inicio_ren + timedelta(days=dias_ren)
                st.info(f"📅 Fecha fin: **{fecha_fin_ren.strftime('%d/%m/%Y')}**")
            with col2:
                aplica_iva_ren = st.checkbox(
                    "Aplica IVA",
                    value=True,
                    key="ren_iva"
                )
                notas_ren = st.text_area(
                    "Notas de la renovación",
                    placeholder="Condiciones especiales, ajustes...",
                    key="ren_notas"
                )

            st.divider()

            # Productos — ajuste de cantidades
            st.markdown("#### Equipo en la renovación")
            st.caption(
                "Mismo equipo del contrato origen. "
                "Puedes ajustar cantidades y precios."
            )

            if not ctr_items:
                st.warning("El contrato origen no tiene productos.")
            else:
                if 'ren_items' not in st.session_state:
                    st.session_state.ren_items = []

                # Inicializar con items del contrato origen
                if not st.session_state.ren_items:
                    st.session_state.ren_items = [
                        {
                            'producto_id'   : item['producto_id'],
                            'codigo'        : item['codigo'],
                            'nombre'        : item['producto_nombre'],
                            'cantidad'      : item['cantidad'],
                            'precio_unitario': float(item['precio_unitario']),
                            'subtotal'      : float(item['subtotal'])
                        }
                        for item in ctr_items
                    ]

                # Encabezados
                cols = st.columns([3, 1, 2, 2])
                cols[0].markdown("**Producto**")
                cols[1].markdown("**Cantidad**")
                cols[2].markdown("**Precio/día $**")
                cols[3].markdown("**Subtotal**")

                subtotal_ren = 0
                for idx, item in enumerate(st.session_state.ren_items):
                    cols = st.columns([3, 1, 2, 2])
                    with cols[0]:
                        st.markdown(f"{item['codigo']} — {item['nombre']}")
                    with cols[1]:
                        nueva_cant = st.number_input(
                            "cant",
                            min_value=0,
                            value=int(item['cantidad']),
                            step=1,
                            label_visibility="collapsed",
                            key=f"ren_cant_{ctr_id}_{idx}"
                        )
                        st.session_state.ren_items[idx]['cantidad'] = nueva_cant
                    with cols[2]:
                        nuevo_precio = st.number_input(
                            "precio",
                            min_value=0.0,
                            value=float(item['precio_unitario']),
                            format="%.2f",
                            label_visibility="collapsed",
                            key=f"ren_precio_{ctr_id}_{idx}"
                        )
                        st.session_state.ren_items[idx]['precio_unitario'] = nuevo_precio
                    with cols[3]:
                        sub = nueva_cant * nuevo_precio * dias_ren
                        st.session_state.ren_items[idx]['subtotal'] = sub
                        st.markdown(f"${sub:,.2f}")
                        subtotal_ren += sub

                st.divider()

                # Totales
                flete_ren = st.number_input(
                    "Flete $",
                    min_value=0.0,
                    value=float(ctr.get('monto_flete') or 0),
                    format="%.2f",
                    key="ren_flete"
                )
                iva_ren    = (subtotal_ren + flete_ren) * 0.16 if aplica_iva_ren else 0
                total_ren  = subtotal_ren + flete_ren + iva_ren

                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Subtotal equipo", f"${subtotal_ren:,.2f}")
                col2.metric("Flete",           f"${flete_ren:,.2f}")
                col3.metric("IVA 16%",         f"${iva_ren:,.2f}")
                col4.metric("**TOTAL**",        f"${total_ren:,.2f}")

                # Anticipo
                st.divider()
                st.markdown("#### Anticipo")
                col1, col2 = st.columns(2)
                with col1:
                    ant_pct = st.slider(
                        "Porcentaje de anticipo",
                        min_value=10, max_value=100,
                        value=50, step=5,
                        key="ren_ant_pct"
                    )
                with col2:
                    ant_req = total_ren * ant_pct / 100
                    st.metric(
                        f"Monto requerido ({ant_pct}%)",
                        f"${ant_req:,.2f}"
                    )

                st.divider()
                if st.button(
                    "💾 Crear renovación",
                    type="primary",
                    use_container_width=True,
                    key="btn_crear_ren"
                ):
                    items_validos = [
                        i for i in st.session_state.ren_items
                        if i['cantidad'] > 0
                    ]
                    if not items_validos:
                        st.error("❌ Debes incluir al menos un producto.")
                    else:
                        try:
                            folio_ren = generar_folio_contrato()
                            nuevo_id  = renovar_contrato(
                                ctr_id,
                                {
                                    'folio'              : folio_ren,
                                    'cliente_id'         : ctr['cliente_id'],
                                    'obra_id'            : ctr.get('obra_id'),
                                    'tipo_contrato'      : 'renta',
                                    'fecha_contrato'     : date.today(),
                                    'fecha_inicio'       : fecha_inicio_ren,
                                    'fecha_fin'          : fecha_fin_ren,
                                    'dias_renta'         : dias_ren,
                                    'subtotal'           : subtotal_ren,
                                    'monto_flete'        : flete_ren,
                                    'aplica_iva'         : aplica_iva_ren,
                                    'iva'                : iva_ren,
                                    'monto_total'        : total_ren,
                                    'anticipo_porcentaje': ant_pct,
                                    'anticipo_requerido' : ant_req,
                                    'pagare_monto'       : 0,
                                    'notas'              : notas_ren
                                },
                                items_validos
                            )
                            st.success(
                                f"✅ Renovación {folio_ren} creada. "
                                f"Contrato {ctr['folio']} marcado como renovado."
                            )
                            st.info(
                                "📌 El equipo sigue en obra — "
                                "no se generó Hoja de Entrada."
                            )
                            st.session_state.ren_items = []
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error: {e}")

# ================================================
# TAB 3 — HISTORIAL
# ================================================
with tab_historial:
    st.subheader("Historial de renovaciones")

    todos_contratos = get_contratos()
    if not todos_contratos:
        st.info("No hay contratos registrados.")
    else:
        opciones_hist = {
            f"{c['folio']} — {c['cliente_nombre']}": c['folio']
            for c in todos_contratos
        }
        hist_sel  = st.selectbox(
            "Selecciona contrato",
            list(opciones_hist.keys()),
            key="hist_ctr_sel"
        )
        hist_folio = opciones_hist[hist_sel]

        cadena = get_cadena_renovaciones(hist_folio)

        if not cadena:
            st.info("No se encontró historial para este contrato.")
        else:
            st.markdown(f"**Cadena de renovaciones — {len(cadena)} contrato(s)**")

            # Timeline visual
            for idx, c in enumerate(cadena):
                col1, col2, col3, col4, col5 = st.columns([1, 2, 2, 2, 2])
                with col1:
                    if idx == 0:
                        st.markdown("🏁 **Origen**")
                    else:
                        st.markdown(f"↳ **#{idx}**")
                with col2:
                    st.markdown(f"**{c['folio']}**")
                    tipo = "🔄 Renovación" if c['tipo_operacion'] == 'renovacion' \
                           else "📄 Original"
                    st.caption(tipo)
                with col3:
                    fi = c['fecha_inicio']
                    ff = c['fecha_fin']
                    st.markdown(
                        f"{fi.strftime('%d/%m/%Y') if fi else '—'} → "
                        f"{ff.strftime('%d/%m/%Y') if ff else '—'}"
                    )
                    st.caption(f"{c['dias_renta']} días")
                with col4:
                    st.markdown(f"${float(c['monto_total']):,.2f}")
                with col5:
                    ESTATUS_COLOR = {
                        'activo'  : '🟢',
                        'renovado': '🔵',
                        'vencido' : '🔴',
                        'cancelado': '⚫',
                        'finalizado': '✅'
                    }
                    color = ESTATUS_COLOR.get(c['estatus'], '⚪')
                    st.markdown(f"{color} {c['estatus'].capitalize()}")

                if idx < len(cadena) - 1:
                    st.markdown("---")

            # Resumen cadena
            st.divider()
            total_cadena = sum(float(c['monto_total']) for c in cadena)
            total_dias   = sum(int(c['dias_renta']) for c in cadena)

            col1, col2, col3 = st.columns(3)
            col1.metric("Contratos en cadena", len(cadena))
            col2.metric("Total días rentados",  total_dias)
            col3.metric("Facturación total",    f"${total_cadena:,.2f}")
            
# ================================================
# TAB 4 — ESTADO DE CUENTA
# ================================================
with tab_edocuenta:
    st.subheader("Estado de cuenta por folio raíz")

    folios = get_todos_folios_raiz()

    if not folios:
        st.info("No hay contratos registrados.")
    else:
        # Selector
        opciones_fr = {
            f"{f['folio_raiz']} — {f['cliente_nombre']} ({f.get('obra_nombre') or 'Sin obra'})": f['folio_raiz']
            for f in folios
        }
        fr_sel   = st.selectbox("Selecciona folio raíz", list(opciones_fr.keys()), key="fr_sel")
        fr_folio = opciones_fr[fr_sel]

        # Resumen
        resumen = get_resumen_folio_raiz(fr_folio)
        if resumen:
            st.divider()
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"**Cliente:** {resumen['cliente_nombre']}")
                st.markdown(f"**RFC:** {resumen['cliente_rfc']}")
            with col2:
                obra_txt = f"{resumen.get('folio_obra','—')} — {resumen.get('obra_nombre','')}" \
                           if resumen.get('obra_nombre') else "Sin obra"
                st.markdown(f"**Obra:** {obra_txt}")
                fi = resumen['fecha_inicio']
                ff = resumen['fecha_fin_estimada']
                st.markdown(
                    f"**Período:** "
                    f"{fi.strftime('%d/%m/%Y') if fi else '—'} → "
                    f"{ff.strftime('%d/%m/%Y') if ff else '—'}"
                )
            with col3:
                st.markdown(f"**Contratos:** {resumen['total_contratos']}")
                st.markdown(f"**Días totales:** {resumen['total_dias']}")

            st.divider()

            # Métricas financieras
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("💰 Facturación total",  f"${float(resumen['facturacion_total']):,.2f}")
            col2.metric("✅ Total cobrado",       f"${float(resumen['total_cobrado']):,.2f}")
            col3.metric("⏳ Saldo pendiente",     f"${float(resumen['saldo_total']):,.2f}")
            pct_cobrado = (
                float(resumen['total_cobrado']) / float(resumen['facturacion_total']) * 100
                if float(resumen['facturacion_total']) > 0 else 0
            )
            col4.metric("📊 % Cobrado", f"{pct_cobrado:.1f}%")

        st.divider()

        # Detalle por contrato
        st.markdown("#### Detalle por contrato")
        contratos_ec = get_estado_cuenta_folio_raiz(fr_folio)

        if contratos_ec:
            ESTATUS_COLOR = {
                'activo'    : '🟢',
                'renovado'  : '🔵',
                'vencido'   : '🔴',
                'cancelado' : '⚫',
                'finalizado': '✅'
            }
            TIPO_OP = {
                'nuevo'     : '📄 Original',
                'renovacion': '🔄 Renovación'
            }

            for ctr in contratos_ec:
                color = ESTATUS_COLOR.get(ctr['estatus'], '⚪')
                with st.expander(
                    f"{color} {ctr['folio']} — "
                    f"{TIPO_OP.get(ctr['tipo_operacion'],'—')} — "
                    f"${float(ctr['monto_total']):,.2f}",
                    expanded=False
                ):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        fi = ctr['fecha_inicio']
                        ff = ctr['fecha_fin']
                        st.markdown(
                            f"**Período:** "
                            f"{fi.strftime('%d/%m/%Y') if fi else '—'} → "
                            f"{ff.strftime('%d/%m/%Y') if ff else '—'}"
                        )
                        st.markdown(f"**Días:** {ctr['dias_renta']}")
                    with col2:
                        st.markdown(f"**Subtotal:** ${float(ctr['subtotal']):,.2f}")
                        st.markdown(f"**Flete:** ${float(ctr['monto_flete']):,.2f}")
                        st.markdown(f"**IVA:** ${float(ctr['iva']):,.2f}")
                        st.markdown(f"**Total:** ${float(ctr['monto_total']):,.2f}")
                    with col3:
                        st.markdown(f"**Anticipo requerido:** ${float(ctr['anticipo_requerido']):,.2f}")
                        st.markdown(f"**Anticipo pagado:** ${float(ctr['anticipo_pagado'] or 0):,.2f}")
                        saldo = float(ctr['saldo_pendiente'] or 0)
                        if saldo > 0:
                            st.error(f"**Saldo pendiente:** ${saldo:,.2f}")
                        else:
                            st.success("**Saldo:** $0.00 ✅")
                    if ctr.get('notas'):
                        st.caption(f"📝 {ctr['notas']}")

            # Tabla resumen exportable
            st.divider()
            st.markdown("#### Resumen exportable")
            df_ec = pd.DataFrame(contratos_ec)
            df_ec['tipo_operacion'] = df_ec['tipo_operacion'].map(TIPO_OP)
            df_ec['estatus']        = df_ec['estatus'].map(
                lambda x: ESTATUS_COLOR.get(x,'⚪') + ' ' + x.capitalize()
            )
            for col_fecha in ['fecha_inicio', 'fecha_fin', 'fecha_contrato']:
                if col_fecha in df_ec.columns:
                    df_ec[col_fecha] = pd.to_datetime(
                        df_ec[col_fecha], errors='coerce'
                    ).dt.strftime('%d/%m/%Y')
            for col_monto in ['subtotal','monto_flete','iva','monto_total',
                              'anticipo_requerido','anticipo_pagado','saldo_pendiente']:
                if col_monto in df_ec.columns:
                    df_ec[col_monto] = df_ec[col_monto].apply(
                        lambda x: f"${float(x):,.2f}" if x is not None else '$0.00'
                    )

            df_show = df_ec[[
                'folio','tipo_operacion','fecha_inicio','fecha_fin',
                'dias_renta','monto_total','anticipo_pagado',
                'saldo_pendiente','estatus'
            ]]
            df_show.columns = [
                'Folio','Tipo','Inicio','Fin',
                'Días','Total','Pagado',
                'Saldo','Estatus'
            ]
            st.dataframe(df_show, use_container_width=True, hide_index=True)