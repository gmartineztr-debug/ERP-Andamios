# pages/06_hojas_salida.py
# Módulo de Hojas de Salida

import streamlit as st
import pandas as pd
from datetime import date
from utils.database import (
    get_contratos_sin_hs_completa,
    get_contrato_detalle,
    get_cantidad_enviada_por_contrato,
    generar_folio_salida,
    crear_hoja_salida,
    get_hojas_salida,
    get_hoja_salida_detalle,
    actualizar_estatus_salida
)



st.title("🚚 Hojas de Salida")
st.divider()

ESTATUS_LABEL = {
    'pendiente'   : '⏳ Pendiente',
    'en_transito' : '🚚 En tránsito',
    'entregada'   : '✅ Entregada',
    'cancelada'   : '❌ Cancelada'
}

tab_contratos, tab_nueva, tab_lista, tab_detalle = st.tabs([
    "📋 Contratos pendientes",
    "➕ Nueva hoja de salida",
    "📄 Lista de hojas",
    "🔍 Ver detalle"
])

# ================================================
# TAB 1 — CONTRATOS PENDIENTES
# ================================================
with tab_contratos:
    st.subheader("Contratos activos pendientes de entrega")

    contratos = get_contratos_sin_hs_completa()

    if not contratos:
        st.info("No hay contratos activos pendientes.")
    else:
        df = pd.DataFrame(contratos)
        df['monto_total'] = df['monto_total'].apply(lambda x: f"${x:,.2f}")
        for col_fecha in ['fecha_inicio', 'fecha_fin']:
            if col_fecha in df.columns:
                df[col_fecha] = pd.to_datetime(
                    df[col_fecha], errors='coerce'
                ).dt.strftime('%d/%m/%Y')

        df_show = df[[
            'folio', 'cliente_nombre', 'obra_nombre',
            'fecha_inicio', 'fecha_fin', 'monto_total'
        ]].fillna('—')
        df_show.columns = [
            'Contrato', 'Cliente', 'Obra',
            'Inicio', 'Fin', 'Total'
        ]
        st.dataframe(df_show, use_container_width=True, hide_index=True)
        st.caption(f"{len(contratos)} contratos activos")
        st.info("👆 Ve al tab **➕ Nueva hoja de salida** para crear una entrega.")

# ================================================
# TAB 2 — NUEVA HOJA DE SALIDA
# ================================================
with tab_nueva:
    st.subheader("Crear nueva hoja de salida")

    contratos = get_contratos_sin_hs_completa()

    if not contratos:
        st.warning("No hay contratos activos.")
    else:
        # Seleccionar contrato
        opciones_ctr = {
            f"{c['folio']} — {c['cliente_nombre']}": c['id']
            for c in contratos
        }
        ctr_sel = st.selectbox("Selecciona contrato *", list(opciones_ctr.keys()))
        ctr_id  = opciones_ctr[ctr_sel]

        # Cargar detalle del contrato
        ctr, ctr_items = get_contrato_detalle(ctr_id)

        if ctr:
            # Info del contrato
            with st.expander("📋 Datos del contrato", expanded=True):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown(f"**Cliente:** {ctr['cliente_nombre']}")
                    st.markdown(f"**Teléfono:** {ctr.get('cliente_telefono') or '—'}")
                with col2:
                    obra_txt = f"{ctr.get('folio_obra', '')} — {ctr.get('obra_nombre', '')}" \
                               if ctr.get('obra_nombre') else "Sin obra"
                    st.markdown(f"**Obra:** {obra_txt}")
                    st.markdown(f"**Dirección:** {ctr.get('direccion_obra') or '—'}")
                with col3:
                    fi = ctr['fecha_inicio']
                    ff = ctr['fecha_fin']
                    st.markdown(f"**Inicio:** {fi.strftime('%d/%m/%Y') if fi else '—'}")
                    st.markdown(f"**Fin:** {ff.strftime('%d/%m/%Y') if ff else '—'}")

            st.divider()

            # Datos generales HS
            st.markdown("#### Datos de la salida")
            col1, col2 = st.columns(2)
            with col1:
                fecha_salida = st.date_input("Fecha de salida *", value=date.today())
                chofer       = st.text_input("Chofer / transportista", placeholder="Nombre del chofer")
                contacto_entrega = st.text_input(
                    "Contacto en obra",
                    value=ctr.get('cliente_contacto') or "",
                    placeholder="Nombre del responsable en obra"
                )
                telefono_entrega = st.text_input(
                    "Teléfono de contacto",
                    value=ctr.get('cliente_telefono') or "",
                    placeholder="Teléfono"
                )
            with col2:
                estatus_inicial = st.selectbox(
                    "Estatus inicial",
                    ['pendiente', 'en_transito'],
                    format_func=lambda x: ESTATUS_LABEL[x]
                )
                observaciones = st.text_area("Observaciones", placeholder="Notas de la entrega...")

            st.divider()

            # ----------------------------------------
            # TABLA DE PRODUCTOS — EDITABLE
            # ----------------------------------------
            st.markdown("#### Despiece de equipo")
            st.caption("Modifica las cantidades a enviar en esta salida.")

            if not ctr_items:
                st.warning("Este contrato no tiene productos.")
            else:
                # Construir tabla con inventario y enviado
                tabla_items = []
                for item in ctr_items:
                    prod_id        = item['producto_id']
                    cant_contrato  = item['cantidad']
                    cant_enviada   = get_cantidad_enviada_por_contrato(ctr_id, prod_id)
                    cant_pendiente = max(0, cant_contrato - cant_enviada)

                    from utils.database import get_productos
                    productos = get_productos()
                    prod_inv  = next((p for p in productos if p['id'] == prod_id), None)
                    cant_disponible = int(prod_inv['cantidad_disponible']) if prod_inv else 0

                    tabla_items.append({
                        'producto_id'    : prod_id,
                        'codigo'         : item['codigo'],
                        'nombre'         : item['producto_nombre'],
                        'peso_kg'        : float(item.get('peso_kg') or 0),
                        'en_contrato'    : cant_contrato,
                        'ya_enviado'     : cant_enviada,
                        'pendiente'      : cant_pendiente,
                        'disponible_inv' : cant_disponible,
                        'a_enviar'       : cant_pendiente
                    })

                # Tabla informativa
                df_info = pd.DataFrame(tabla_items)[[
                    'codigo', 'nombre', 'en_contrato',
                    'ya_enviado', 'pendiente', 'disponible_inv'
                ]]
                df_info.columns = [
                    'Código', 'Producto', 'En Contrato',
                    'Ya Enviado', 'Pendiente', 'Disponible Inv.'
                ]
                st.dataframe(df_info, use_container_width=True, hide_index=True)

                st.markdown("**Cantidades a enviar en esta salida:**")

                items_a_enviar = []
                cols = st.columns([3, 1, 1, 1])
                cols[0].markdown("**Producto**")
                cols[1].markdown("**Pendiente**")
                cols[2].markdown("**A enviar**")
                cols[3].markdown("**Peso total**")

                for i, item in enumerate(tabla_items):
                    if item['pendiente'] > 0:
                        cols = st.columns([3, 1, 1, 1])
                        with cols[0]:
                            st.markdown(f"{item['codigo']} — {item['nombre']}")
                        with cols[1]:
                            st.markdown(f"{item['pendiente']}")
                        with cols[2]:
                            cantidad = st.number_input(
                                f"cant_{i}",
                                min_value=0,
                                max_value=min(item['pendiente'], item['disponible_inv']),
                                value=item['pendiente'],
                                step=1,
                                label_visibility="collapsed",
                                key=f"hs_cant_{ctr_id}_{item['producto_id']}"
                            )
                        with cols[3]:
                            peso_total = cantidad * item['peso_kg']
                            st.markdown(f"{peso_total:.1f} kg")

                        if cantidad > 0:
                            items_a_enviar.append({
                                'producto_id'  : item['producto_id'],
                                'cantidad'     : cantidad,
                                'peso_unitario': item['peso_kg'],
                                'peso_total'   : peso_total
                            })

                peso_grand_total = sum(i['peso_total'] for i in items_a_enviar)
                st.divider()
                st.metric("⚖️ Peso total de la salida", f"{peso_grand_total:.1f} kg")

                st.divider()
                if st.button("💾 Crear hoja de salida", type="primary", use_container_width=True):
                    if not items_a_enviar:
                        st.error("❌ Debes incluir al menos un producto.")
                    else:
                        try:
                            folio = generar_folio_salida()
                            nueva_id = crear_hoja_salida({
                                'folio'           : folio,
                                'contrato_id'     : ctr_id,
                                'cliente_id'      : ctr['cliente_id'],
                                'obra_id'         : ctr.get('obra_id'),
                                'chofer'          : chofer,
                                'observaciones'   : observaciones,
                                'estatus'         : estatus_inicial,
                                'fecha_salida'    : fecha_salida,
                                'contacto_entrega': contacto_entrega,
                                'telefono_entrega': telefono_entrega
                            }, items_a_enviar)
                            st.success(f"✅ Hoja de salida {folio} creada correctamente.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error: {e}")

# ================================================
# TAB 3 — LISTA
# ================================================
with tab_lista:
    st.subheader("Hojas de salida registradas")

    col1, col2 = st.columns([3, 1])
    with col1:
        filtro = st.selectbox(
            "Filtrar por estatus",
            ["Todos"] + list(ESTATUS_LABEL.values()),
            key="filtro_hs"
        )

    salidas = get_hojas_salida()

    if filtro != "Todos":
        estatus_key = [k for k, v in ESTATUS_LABEL.items() if v == filtro][0]
        salidas = [s for s in salidas if s['estatus'] == estatus_key]

    if not salidas:
        st.info("No hay hojas de salida registradas.")
    else:
        df = pd.DataFrame(salidas)
        df['estatus']      = df['estatus'].map(ESTATUS_LABEL)
        df['fecha_salida'] = pd.to_datetime(df['fecha_salida']).dt.strftime('%d/%m/%Y')
        df['peso_total']   = df['peso_total'].apply(lambda x: f"{x:.1f} kg")
        df_show = df[[
            'folio', 'contrato_folio', 'cliente_nombre',
            'obra_nombre', 'fecha_salida', 'peso_total', 'estatus'
        ]].fillna('—')
        df_show.columns = [
            'Folio HS', 'Contrato', 'Cliente',
            'Obra', 'Fecha', 'Peso Total', 'Estatus'
        ]
        st.dataframe(df_show, use_container_width=True, hide_index=True)
        st.caption(f"Total: {len(salidas)} hojas de salida")

# ================================================
# TAB 4 — DETALLE
# ================================================
with tab_detalle:
    st.subheader("Detalle de hoja de salida")

    salidas = get_hojas_salida()

    if not salidas:
        st.info("No hay hojas de salida registradas.")
    else:
        opciones = {
            f"{s['folio']} — {s['cliente_nombre']} — {s['contrato_folio']}": s['id']
            for s in salidas
        }
        seleccion = st.selectbox("Selecciona hoja de salida", list(opciones.keys()))
        salida_id = opciones[seleccion]

        try:
            hs, items = get_hoja_salida_detalle(salida_id)
        except Exception as e:
            st.error(f"Error: {e}")
            st.stop()

        if hs:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"**Folio HS:** {hs['folio']}")
                st.markdown(f"**Contrato:** {hs['contrato_folio']}")
                st.markdown(f"**Cliente:** {hs['cliente_nombre']}")
                st.markdown(f"**Contacto:** {hs.get('contacto_entrega') or '—'}")
                st.markdown(f"**Teléfono:** {hs.get('telefono_entrega') or '—'}")
            with col2:
                obra_txt = f"{hs.get('folio_obra', '')} — {hs.get('obra_nombre', '')}" \
                           if hs.get('obra_nombre') else "Sin obra"
                st.markdown(f"**Obra:** {obra_txt}")
                st.markdown(f"**Dirección:** {hs.get('direccion_obra') or '—'}")
                fs = hs['fecha_salida']
                st.markdown(f"**Fecha salida:** {fs.strftime('%d/%m/%Y') if fs else '—'}")
                st.markdown(f"**Chofer:** {hs.get('chofer') or '—'}")
            with col3:
                st.markdown(f"**Estatus:** {ESTATUS_LABEL.get(hs['estatus'], '—')}")
                st.markdown(f"**Peso total:** {float(hs['peso_total']):.1f} kg")
                if hs.get('observaciones'):
                    st.markdown(f"**Observaciones:** {hs['observaciones']}")

            st.divider()

            # Items
            if items:
                st.subheader("Despiece de equipo")
                df_items = pd.DataFrame(items)

                # Total de piezas
                total_piezas = df_items['cantidad'].sum()
                total_peso   = df_items['peso_total'].sum()

                df_items['peso_total'] = df_items['peso_total'].apply(lambda x: f"{x:.1f} kg")
                df_items = df_items[[
                    'codigo', 'producto_nombre', 'cantidad',
                    'peso_unitario', 'peso_total'
                ]]
                df_items.columns = ['Código', 'Producto', 'Cantidad', 'Peso Unit. kg', 'Peso Total']
                st.dataframe(df_items, use_container_width=True, hide_index=True)

                col1, col2 = st.columns(2)
                with col1:
                    st.metric("📦 Total piezas", int(total_piezas))
                with col2:
                    st.metric("⚖️ Peso total", f"{float(total_peso):.1f} kg")

            st.divider()

            # Cambiar estatus
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Actualizar estatus**")
                nuevo_estatus = st.selectbox(
                    "Estatus",
                    list(ESTATUS_LABEL.keys()),
                    index=list(ESTATUS_LABEL.keys()).index(hs['estatus']),
                    format_func=lambda x: ESTATUS_LABEL[x],
                    key="sel_estatus_hs"
                )
                fecha_entrega = None
                if nuevo_estatus == 'entregada':
                    fecha_entrega = st.date_input(
                        "Fecha de entrega confirmada",
                        value=date.today()
                    )
                    st.warning("⚠️ Al confirmar entrega se actualizará el inventario automáticamente.")

                if st.button("Actualizar estatus", type="primary"):
                    actualizar_estatus_salida(salida_id, nuevo_estatus, fecha_entrega)
                    st.success("✅ Estatus actualizado.")
                    if nuevo_estatus == 'entregada':
                        st.info("📦 Inventario actualizado: disponible ↓ | rentado ↑")
                    st.rerun()

            # PDF
            st.divider()
            if st.button("📄 Generar PDF Hoja de Salida", type="primary"):
                try:
                    from utils.pdf_generator import generar_pdf_hoja_salida
                    pdf_bytes = generar_pdf_hoja_salida(dict(hs), [dict(i) for i in items])
                    st.download_button(
                        label="⬇️ Descargar Hoja de Salida PDF",
                        data=pdf_bytes,
                        file_name=f"HojaSalida_{hs['folio']}.pdf",
                        mime="application/pdf"
                    )
                except Exception as e:
                    st.error(f"❌ Error generando PDF: {e}")