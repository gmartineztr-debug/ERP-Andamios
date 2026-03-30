# pages/10_anticipos.py
# Módulo de Anticipos y Pagos

import streamlit as st
import pandas as pd
from datetime import date
from utils.database import (
    get_contratos,
    get_contrato_detalle,
    get_clientes,
    generar_folio_anticipo,
    crear_anticipo,
    get_anticipos,
    get_pagos_por_contrato,
    get_contratos_con_saldo,
    actualizar_estatus_anticipo
)
from utils.logger import logger

# Validar permisos
roles_permitidos = ['admin', 'gerencia']
if st.session_state.get('rol', 'usuario').lower() not in roles_permitidos:
    st.error(f"🚫 **No tienes acceso a esta sección.**\nRoles requeridos: {', '.join(roles_permitidos)}")
    logger.warning(f"ACCESO_DENEGADO: {st.session_state.get('usuario')} intentó acceder a Anticipos")
    st.stop()

st.title(":material/payments: Anticipos y Pagos")
st.divider()

TIPO_PAGO_LABEL = {
    'anticipo'   : 'Anticipo inicial',
    'parcial'    : 'Pago parcial',
    'liquidacion': 'Liquidación'
}

ESTATUS_LABEL = {
    'registrado': 'Registrado',
    'verificado': 'Verificado',
    'cancelado' : 'Cancelado'
}

tab_nuevo, tab_saldos, tab_lista, tab_detalle = st.tabs([
    ":material/add_card: Registrar Pago",
    ":material/hourglass_empty: Saldos Pendientes",
    ":material/list_alt: Lista De Pagos",
    ":material/search: Detalle Por Contrato"
])

# ================================================
# TAB 1 — REGISTRAR PAGO
# ================================================
with tab_nuevo:
    st.subheader("Registrar nuevo pago")

    contratos = get_contratos()
    contratos_validos = [
        c for c in contratos
        if c['estatus'] not in ('cancelado',)
    ]

    if not contratos_validos:
        st.warning("No hay contratos disponibles.")
    else:
        opciones_ctr = {
            f"{c['folio']} — {c['cliente_nombre']}": c['id']
            for c in contratos_validos
        }
        ctr_sel = st.selectbox(
            "Selecciona contrato *",
            list(opciones_ctr.keys()),
            key="ant_ctr_sel"
        )
        ctr_id = opciones_ctr[ctr_sel]

        # Cargar detalle contrato y resumen pagos
        ctr, _ = get_contrato_detalle(ctr_id)
        resumen = get_pagos_por_contrato(ctr_id)

        if ctr and resumen:
            # Resumen financiero del contrato
            with st.expander(":material/query_stats: Estado de pagos del contrato", expanded=True):
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total contrato",    f"${float(ctr['monto_total']):,.2f}")
                with col2:
                    st.metric("Anticipo requerido", f"${float(ctr['anticipo_requerido']):,.2f}")
                with col3:
                    total_pag = float(resumen['total_pagado'] or 0)
                    st.metric("Total pagado",       f"${total_pag:,.2f}")
                with col4:
                    saldo = float(resumen['saldo_pendiente'] or 0)
                    if saldo <= 0:
                        st.metric("Saldo pendiente", "$0.00")
                    else:
                        st.metric("Saldo pendiente", f"${saldo:,.2f}")

            st.divider()

            # Formulario pago
            col1, col2 = st.columns(2)
            with col1:
                tipo_pago = st.selectbox(
                    "Tipo de pago *",
                    list(TIPO_PAGO_LABEL.keys()),
                    format_func=lambda x: TIPO_PAGO_LABEL[x],
                    key="ant_tipo"
                )
                fecha_pago = st.date_input(
                    "Fecha de pago *",
                    value=date.today(),
                    key="ant_fecha"
                )
                saldo_actual = float(resumen['saldo_pendiente'] or 0)
                monto = st.number_input(
                    "Monto *",
                    min_value=0.01,
                    max_value=float(ctr['monto_total']),
                    value=min(float(ctr['anticipo_requerido']), saldo_actual)
                          if saldo_actual > 0 else float(ctr['anticipo_requerido']),
                    step=100.0,
                    format="%.2f",
                    key="ant_monto"
                )

            with col2:
                referencia = st.text_input(
                    "Referencia bancaria",
                    placeholder="REF-123456 / No. transferencia",
                    key="ant_ref"
                )
                concepto = st.text_area(
                    "Concepto / notas",
                    placeholder="Anticipo inicial, pago mensualidad...",
                    key="ant_concepto"
                )
                estatus_pago = st.selectbox(
                    "Estatus del pago",
                    ['registrado', 'verificado'],
                    format_func=lambda x: ESTATUS_LABEL[x],
                    key="ant_estatus"
                )

            # Preview saldo después del pago
            nuevo_pagado = total_pag + monto
            nuevo_saldo  = float(ctr['monto_total']) - nuevo_pagado
            col1, col2 = st.columns(2)
            with col1:
                st.info(f"📊 Total pagado después de este pago: **${nuevo_pagado:,.2f}**")
            with col2:
                if nuevo_saldo <= 0:
                    st.success(":material/check_circle: Contrato quedaría **liquidado**")
                else:
                    st.warning(f":material/warning: Saldo restante: **${nuevo_saldo:,.2f}**")

            st.divider()

            if st.button(
                ":material/save: Registrar pago",
                type="primary",
                use_container_width=True,
                key="btn_crear_ant"
            ):
                try:
                    folio_ant = generar_folio_anticipo()
                    crear_anticipo({
                        'folio'              : folio_ant,
                        'contrato_id'        : ctr_id,
                        'cliente_id'         : ctr['cliente_id'],
                        'tipo_pago'          : tipo_pago,
                        'monto'              : monto,
                        'fecha_pago'         : fecha_pago,
                        'referencia_bancaria': referencia,
                        'concepto'           : concepto,
                        'estatus'            : estatus_pago
                    })
                    st.success(f":material/check_circle: Pago {folio_ant} registrado correctamente.")

                    # Generar recibo PDF
                    try:
                        from utils.pdf_generator import generar_pdf_recibo
                        pdf_bytes = generar_pdf_recibo({
                            'folio'              : folio_ant,
                            'contrato_folio'     : ctr['folio'],
                            'cliente_nombre'     : ctr['cliente_nombre'],
                            'cliente_rfc'        : ctr['rfc'],
                            'tipo_pago'          : TIPO_PAGO_LABEL[tipo_pago],
                            'monto'              : monto,
                            'fecha_pago'         : fecha_pago,
                            'referencia_bancaria': referencia,
                            'concepto'           : concepto,
                            'total_contrato'     : float(ctr['monto_total']),
                            'total_pagado'       : nuevo_pagado,
                            'saldo_pendiente'    : max(nuevo_saldo, 0)
                        })
                        st.download_button(
                            label=":material/file_download: Descargar recibo PDF",
                            data=pdf_bytes,
                            file_name=f"Recibo_{folio_ant}.pdf",
                            mime="application/pdf"
                        )
                    except Exception as e:
                        st.warning(f"Pago registrado. Error generando PDF: {e}")

                    st.rerun()
                except Exception as e:
                    st.error(f":material/error: Error: {e}")

# ================================================
# TAB 2 — SALDOS PENDIENTES
# ================================================
with tab_saldos:
    st.subheader("Contratos con saldo pendiente")

    saldos = get_contratos_con_saldo()

    if not saldos:
        st.success(":material/check_circle: No hay contratos con saldo pendiente.")
    else:
        # Métricas
        total_saldo = sum(float(s['saldo_pendiente'] or 0) for s in saldos)
        col1, col2 = st.columns(2)
        col1.metric("Contratos con saldo", len(saldos))
        col2.metric("Total por cobrar",    f"${total_saldo:,.2f}")

        st.divider()

        df = pd.DataFrame(saldos)
        df['monto_total']      = df['monto_total'].apply(lambda x: f"${float(x):,.2f}")
        df['anticipo_requerido'] = df['anticipo_requerido'].apply(lambda x: f"${float(x):,.2f}")
        df['total_pagado']     = df['total_pagado'].apply(lambda x: f"${float(x):,.2f}")
        df['saldo_pendiente']  = df['saldo_pendiente'].apply(lambda x: f"${float(x):,.2f}")

        df_show = df[[
            'contrato_folio', 'cliente_nombre',
            'monto_total', 'total_pagado',
            'saldo_pendiente', 'num_pagos'
        ]]
        df_show.columns = [
            'Contrato', 'Cliente',
            'Total', 'Pagado',
            'Saldo', 'Pagos'
        ]
        st.dataframe(df_show, use_container_width=True, hide_index=True)

# ================================================
# TAB 3 — LISTA DE PAGOS
# ================================================
with tab_lista:
    st.subheader("Lista de pagos registrados")

    col1, col2 = st.columns(2)
    with col1:
        filtro_est = st.selectbox(
            "Filtrar por estatus",
            ["Todos"] + list(ESTATUS_LABEL.values()),
            key="ant_filtro_est"
        )
    with col2:
        filtro_tipo = st.selectbox(
            "Filtrar por tipo",
            ["Todos"] + list(TIPO_PAGO_LABEL.values()),
            key="ant_filtro_tipo"
        )

    estatus_key = None
    if filtro_est != "Todos":
        estatus_key = [k for k, v in ESTATUS_LABEL.items() if v == filtro_est][0]

    pagos = get_anticipos(estatus=estatus_key)

    if filtro_tipo != "Todos":
        tipo_key = [k for k, v in TIPO_PAGO_LABEL.items() if v == filtro_tipo][0]
        pagos = [p for p in pagos if p['tipo_pago'] == tipo_key]

    if not pagos:
        st.info("No hay pagos registrados.")
    else:
        df = pd.DataFrame(pagos)
        df['tipo_pago'] = df['tipo_pago'].map(TIPO_PAGO_LABEL)
        df['estatus']   = df['estatus'].map(ESTATUS_LABEL)
        df['monto']     = df['monto'].apply(lambda x: f"${float(x):,.2f}")
        df['fecha_pago'] = pd.to_datetime(
            df['fecha_pago'], errors='coerce'
        ).dt.strftime('%d/%m/%Y')

        df_show = df[[
            'folio', 'contrato_folio', 'cliente_nombre',
            'tipo_pago', 'monto', 'fecha_pago',
            'referencia_bancaria', 'estatus'
        ]].fillna('—')
        df_show.columns = [
            'Folio', 'Contrato', 'Cliente',
            'Tipo', 'Monto', 'Fecha',
            'Referencia', 'Estatus'
        ]
        st.dataframe(df_show, use_container_width=True, hide_index=True)

        total_pagos = sum(
            float(p['monto'].replace('$','').replace(',',''))
            if isinstance(p['monto'], str)
            else float(p['monto'])
            for p in pagos
        )
        st.caption(f"{len(pagos)} pagos — Total: ${sum(float(p['monto']) for p in get_anticipos(estatus=estatus_key) if filtro_tipo == 'Todos' or [k for k,v in TIPO_PAGO_LABEL.items() if v == filtro_tipo][0] == p['tipo_pago']):,.2f}")

# ================================================
# TAB 4 — DETALLE POR CONTRATO
# ================================================
with tab_detalle:
    st.subheader("Detalle de pagos por contrato")

    contratos_det = get_contratos()
    if not contratos_det:
        st.info("No hay contratos registrados.")
    else:
        opciones_det = {
            f"{c['folio']} — {c['cliente_nombre']}": c['id']
            for c in contratos_det
        }
        det_sel = st.selectbox(
            "Selecciona contrato",
            list(opciones_det.keys()),
            key="det_ant_sel"
        )
        det_id = opciones_det[det_sel]

        ctr_det, _ = get_contrato_detalle(det_id)
        resumen_det = get_pagos_por_contrato(det_id)
        pagos_det   = get_anticipos(contrato_id=det_id)

        if ctr_det and resumen_det:
            # Resumen
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total contrato",     f"${float(ctr_det['monto_total']):,.2f}")
            col2.metric("Anticipo requerido", f"${float(ctr_det['anticipo_requerido']):,.2f}")
            col3.metric("Total pagado",       f"${float(resumen_det['total_pagado'] or 0):,.2f}")
            saldo_det = float(resumen_det['saldo_pendiente'] or 0)
            if saldo_det <= 0:
                col4.metric("Saldo", "$0.00 ✅")
            else:
                col4.metric("Saldo pendiente", f"${saldo_det:,.2f}")

            # Barra de progreso
            pct = min(
                float(resumen_det['total_pagado'] or 0) /
                float(ctr_det['monto_total']) * 100
                if float(ctr_det['monto_total']) > 0 else 0,
                100
            )
            st.progress(pct / 100, text=f"Cobrado: {pct:.1f}%")

            st.divider()

            # Lista de pagos del contrato
            if not pagos_det:
                st.info("Este contrato no tiene pagos registrados.")
            else:
                st.markdown("#### Pagos registrados")
                for pago in pagos_det:
                    col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 2])
                    with col1:
                        st.markdown(f"**{pago['folio']}**")
                        st.caption(TIPO_PAGO_LABEL.get(pago['tipo_pago'], '—'))
                    with col2:
                        fp = pago['fecha_pago']
                        st.markdown(
                            f"{fp.strftime('%d/%m/%Y') if fp else '—'}"
                        )
                        st.caption(pago.get('referencia_bancaria') or 'Sin referencia')
                    with col3:
                        st.markdown(f"**${float(pago['monto']):,.2f}**")
                    with col4:
                        st.caption(pago.get('concepto') or '—')
                    with col5:
                        est = pago['estatus']
                        st.markdown(ESTATUS_LABEL.get(est, '—'))

                        # Acciones
                        if est == 'registrado':
                            if st.button(
                                "✅ Verificar",
                                key=f"ver_{pago['id']}"
                            ):
                                actualizar_estatus_anticipo(pago['id'], 'verificado')
                                st.success("✅ Pago verificado.")
                                st.rerun()
                        if est != 'cancelado':
                            if st.button(
                                "❌ Cancelar",
                                key=f"can_{pago['id']}"
                            ):
                                actualizar_estatus_anticipo(pago['id'], 'cancelado')
                                st.warning("Pago cancelado.")
                                st.rerun()

                    st.divider()

                # Botón recibo del último pago verificado
                pagos_verificados = [
                    p for p in pagos_det if p['estatus'] == 'verificado'
                ]
                if pagos_verificados:
                    st.markdown("#### Generar recibo")
                    opciones_recibo = {
                        f"{p['folio']} — ${float(p['monto']):,.2f} — "
                        f"{p['fecha_pago'].strftime('%d/%m/%Y') if p['fecha_pago'] else '—'}": p
                        for p in pagos_verificados
                    }
                    rec_sel = st.selectbox(
                        "Selecciona pago",
                        list(opciones_recibo.keys()),
                        key="rec_sel"
                    )
                    pago_rec = opciones_recibo[rec_sel]

                    if st.button(":material/picture_as_pdf: Generar recibo PDF", key="btn_rec_pdf"):
                        try:
                            from utils.pdf_generator import generar_pdf_recibo
                            resumen_rec = get_pagos_por_contrato(det_id)
                            pdf_bytes = generar_pdf_recibo({
                                'folio'              : pago_rec['folio'],
                                'contrato_folio'     : ctr_det['folio'],
                                'cliente_nombre'     : ctr_det['cliente_nombre'],
                                'cliente_rfc'        : ctr_det['rfc'],
                                'tipo_pago'          : TIPO_PAGO_LABEL[pago_rec['tipo_pago']],
                                'monto'              : float(pago_rec['monto']),
                                'fecha_pago'         : pago_rec['fecha_pago'],
                                'referencia_bancaria': pago_rec.get('referencia_bancaria'),
                                'concepto'           : pago_rec.get('concepto'),
                                'total_contrato'     : float(ctr_det['monto_total']),
                                'total_pagado'       : float(resumen_rec['total_pagado'] or 0),
                                'saldo_pendiente'    : float(resumen_rec['saldo_pendiente'] or 0)
                            })
                            st.download_button(
                                label=":material/file_download: Descargar recibo",
                                data=pdf_bytes,
                                file_name=f"Recibo_{pago_rec['folio']}.pdf",
                                mime="application/pdf"
                            )
                        except Exception as e:
                            st.error(f"❌ Error generando PDF: {e}")