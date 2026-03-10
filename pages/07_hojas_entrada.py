# pages/07_hojas_entrada.py
# Módulo de Hojas de Entrada

import streamlit as st
import pandas as pd
from datetime import date
from utils.database import (
    get_contratos_con_equipo_en_campo,
    get_contrato_detalle,
    get_saldo_en_campo,
    generar_folio_entrada,
    crear_hoja_entrada,
    get_hojas_entrada,
    get_hoja_entrada_detalle,
    actualizar_estatus_entrada,
    vincular_contrato_venta_entrada,
    get_proveedores,
    crear_proveedor,
    get_productos,
    generar_folio_contrato,
    crear_contrato,
    crear_contrato_item
)

st.set_page_config(page_title="Hojas de Entrada - ICAM ERP", layout="wide")

st.title("📦 Hojas de Entrada")
st.divider()

ESTATUS_LABEL = {
    'pendiente' : '⏳ Pendiente',
    'recibida'  : '📬 Recibida',
    'cerrada'   : '✅ Cerrada',
    'cancelada' : '❌ Cancelada'
}

TIPO_LABEL = {
    'devolucion'  : '🔄 Devolución',
    'compra'      : '🛒 Compra',
    'fabricacion' : '🔧 Fabricación'
}

tab_devolucion, tab_compra, tab_fabricacion, tab_lista, tab_detalle = st.tabs([
    "🔄 Devolución",
    "🛒 Compra",
    "🔧 Fabricación",
    "📄 Lista",
    "🔍 Detalle"
])

# ================================================
# TAB 1 — DEVOLUCIÓN
# ================================================
with tab_devolucion:
    st.subheader("Registrar devolución de equipo")

    contratos = get_contratos_con_equipo_en_campo()

    if not contratos:
        st.info("No hay contratos con equipo en campo.")
    else:
        opciones_ctr = {
            f"{c['folio']} — {c['cliente_nombre']}": c['id']
            for c in contratos
        }
        ctr_sel = st.selectbox(
            "Selecciona contrato *",
            list(opciones_ctr.keys()),
            key="dev_contrato"
        )
        ctr_id = opciones_ctr[ctr_sel]
        ctr    = next(c for c in contratos if c['id'] == ctr_id)

        # Info contrato
        with st.expander("📋 Datos del contrato", expanded=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"**Cliente:** {ctr['cliente_nombre']}")
                st.markdown(f"**Teléfono:** {ctr.get('cliente_telefono') or '—'}")
            with col2:
                obra_txt = f"{ctr.get('folio_obra','—')} — {ctr.get('obra_nombre','')}" \
                           if ctr.get('obra_nombre') else "Sin obra"
                st.markdown(f"**Obra:** {obra_txt}")
                st.markdown(f"**Dirección:** {ctr.get('direccion_obra') or '—'}")
            with col3:
                fecha_entrada = st.date_input(
                    "Fecha de entrada *",
                    value=date.today(),
                    key="dev_fecha"
                )
                notas = st.text_area(
                    "Observaciones",
                    placeholder="Notas de la devolución...",
                    key="dev_notas"
                )

        st.divider()

        # Saldo en campo
        saldo = get_saldo_en_campo(ctr_id)

        if not saldo:
            st.warning("Este contrato no tiene equipo en campo.")
        else:
            st.markdown("#### Inspección de equipo devuelto")
            st.caption("Registra las cantidades por estado para cada SKU.")

            # Encabezados
            cols = st.columns([3, 1, 1, 1, 1, 1])
            cols[0].markdown("**Producto**")
            cols[1].markdown("**En campo**")
            cols[2].markdown("**✅ Bueno**")
            cols[3].markdown("**🔧 Dañado**")
            cols[4].markdown("**❌ Pérdida**")
            cols[5].markdown("**💀 Chatarra**")

            items_devolucion = []
            hay_cobro = False

            for item in saldo:
                prod_id   = item['producto_id']
                en_campo  = item['saldo_en_campo']
                peso_kg   = float(item.get('peso_kg') or 0) if 'peso_kg' in item else 0

                cols = st.columns([3, 1, 1, 1, 1, 1])
                with cols[0]:
                    st.markdown(f"{item['codigo']} — {item['producto_nombre']}")
                with cols[1]:
                    st.markdown(f"**{en_campo}**")
                with cols[2]:
                    buena = st.number_input(
                        "b", min_value=0, max_value=en_campo,
                        value=en_campo, step=1,
                        label_visibility="collapsed",
                        key=f"dev_buena_{prod_id}"
                    )
                with cols[3]:
                    danada = st.number_input(
                        "d", min_value=0, max_value=en_campo,
                        value=0, step=1,
                        label_visibility="collapsed",
                        key=f"dev_danada_{prod_id}"
                    )
                with cols[4]:
                    perdida = st.number_input(
                        "p", min_value=0, max_value=en_campo,
                        value=0, step=1,
                        label_visibility="collapsed",
                        key=f"dev_perdida_{prod_id}"
                    )
                with cols[5]:
                    chatarra = st.number_input(
                        "c", min_value=0, max_value=en_campo,
                        value=0, step=1,
                        label_visibility="collapsed",
                        key=f"dev_chatarra_{prod_id}"
                    )

                total_capturado = buena + danada + perdida + chatarra
                if total_capturado > en_campo:
                    st.error(f"⚠️ {item['codigo']}: la suma ({total_capturado}) supera el saldo en campo ({en_campo})")

                if perdida + chatarra > 0:
                    hay_cobro = True

                items_devolucion.append({
                    'producto_id'      : prod_id,
                    'cantidad_total'   : total_capturado,
                    'cantidad_buena'   : buena,
                    'cantidad_danada'  : danada,
                    'cantidad_perdida' : perdida,
                    'cantidad_chatarra': chatarra,
                    'peso_unitario'    : peso_kg,
                    'peso_total'       : total_capturado * peso_kg,
                    'precio_venta'     : float(item.get('precio_venta') or 0)
                        if 'precio_venta' in item else 0
                })

            st.divider()

            # Alerta de cobro
            if hay_cobro:
                items_cobro = [
                    i for i in items_devolucion
                    if i['cantidad_perdida'] + i['cantidad_chatarra'] > 0
                ]
                total_cobro = sum(
                    (i['cantidad_perdida'] + i['cantidad_chatarra'])
                    * i['precio_venta'] * 0.90
                    for i in items_cobro
                )
                st.warning(
                    f"⚠️ Se detectaron piezas con cobro. "
                    f"Se generará un contrato de venta por **${total_cobro:,.2f}** (90% valor comercial)."
                )

            if st.button("💾 Crear hoja de entrada", type="primary",
                         use_container_width=True, key="btn_crear_dev"):
                errores = []
                for item in items_devolucion:
                    total = (item['cantidad_buena'] + item['cantidad_danada'] +
                             item['cantidad_perdida'] + item['cantidad_chatarra'])
                    if total > item['cantidad_total']:
                        errores.append(f"Suma incorrecta en producto {item['producto_id']}")

                if errores:
                    for e in errores:
                        st.error(e)
                else:
                    try:
                        folio = generar_folio_entrada()
                        entrada_id = crear_hoja_entrada({
                            'folio'       : folio,
                            'tipo_entrada': 'devolucion',
                            'estatus'     : 'pendiente',
                            'contrato_id' : ctr_id,
                            'cliente_id'  : ctr['cliente_id'],
                            'obra_id'     : ctr.get('obra_id'),
                            'fecha_entrada': fecha_entrada,
                            'notas'       : notas
                        }, items_devolucion)

                        # Generar contrato de venta si hay pérdida/chatarra
                        if hay_cobro:
                            items_venta = [
                                i for i in items_devolucion
                                if i['cantidad_perdida'] + i['cantidad_chatarra'] > 0
                            ]
                            folio_venta = generar_folio_contrato()
                            subtotal_venta = sum(
                                (i['cantidad_perdida'] + i['cantidad_chatarra'])
                                * i['precio_venta'] * 0.90
                                for i in items_venta
                            )
                            iva_venta    = subtotal_venta * 0.16
                            total_venta  = subtotal_venta + iva_venta

                            contrato_venta_id = crear_contrato({
                                'folio'              : folio_venta,
                                'cotizacion_id'      : None,
                                'obra_id'            : ctr.get('obra_id'),
                                'cliente_id'         : ctr['cliente_id'],
                                'tipo_contrato'      : 'venta',
                                'tipo_operacion'     : 'nuevo',
                                'estatus'            : 'activo',
                                'fecha_contrato'     : date.today(),
                                'fecha_inicio'       : date.today(),
                                'fecha_fin'          : date.today(),
                                'dias_renta'         : 0,
                                'subtotal'           : subtotal_venta,
                                'monto_flete'        : 0,
                                'aplica_iva'         : True,
                                'iva'                : iva_venta,
                                'monto_total'        : total_venta,
                                'anticipo_porcentaje': 100,
                                'anticipo_requerido' : total_venta,
                                'anticipo_pagado'    : 0,
                                'anticipo_estatus'   : 'pendiente',
                                'pagare_monto'       : 0,
                                'pagare_firmado'     : False,
                                'contrato_origen_id' : ctr_id,
                                'notas'              : f'Venta por pérdida/chatarra — origen {ctr["folio"]}'
                            })

                            for i in items_venta:
                                cant_cobro = i['cantidad_perdida'] + i['cantidad_chatarra']
                                precio_90  = i['precio_venta'] * 0.90
                                crear_contrato_item({
                                    'contrato_id'    : contrato_venta_id,
                                    'producto_id'    : i['producto_id'],
                                    'cantidad'       : cant_cobro,
                                    'precio_unitario': precio_90,
                                    'subtotal'       : cant_cobro * precio_90
                                })

                            vincular_contrato_venta_entrada(entrada_id, contrato_venta_id)

                            st.success(
                                f"✅ HE {folio} creada. "
                                f"Contrato de venta {folio_venta} generado automáticamente."
                            )
                        else:
                            st.success(f"✅ Hoja de entrada {folio} creada correctamente.")

                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error: {e}")

# ================================================
# TAB 2 — COMPRA
# ================================================
with tab_compra:
    st.subheader("Registrar entrada por compra")

    proveedores = get_proveedores()

    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("➕ Nuevo proveedor", key="btn_nuevo_prov"):
            st.session_state.show_nuevo_prov = True

    # Formulario nuevo proveedor
    if st.session_state.get('show_nuevo_prov'):
        with st.expander("Nuevo proveedor", expanded=True):
            np_nombre = st.text_input("Nombre *", key="np_nombre")
            np_rfc    = st.text_input("RFC", key="np_rfc")
            col1, col2 = st.columns(2)
            with col1:
                np_contacto = st.text_input("Contacto", key="np_contacto")
                np_tel      = st.text_input("Teléfono", key="np_tel")
            with col2:
                np_email = st.text_input("Email", key="np_email")
                np_dir   = st.text_input("Dirección", key="np_dir")
            if st.button("💾 Guardar proveedor", key="btn_save_prov"):
                if not np_nombre:
                    st.error("El nombre es obligatorio.")
                else:
                    try:
                        crear_proveedor({
                            'nombre'  : np_nombre,
                            'rfc'     : np_rfc,
                            'contacto': np_contacto,
                            'telefono': np_tel,
                            'email'   : np_email,
                            'direccion': np_dir
                        })
                        st.success("✅ Proveedor guardado.")
                        st.session_state.show_nuevo_prov = False
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error: {e}")

    if not proveedores:
        st.warning("No hay proveedores registrados. Crea uno primero.")
    else:
        opciones_prov = {p['nombre']: p['id'] for p in proveedores}

        col1, col2 = st.columns(2)
        with col1:
            prov_sel    = st.selectbox("Proveedor *", list(opciones_prov.keys()), key="cmp_prov")
            prov_id     = opciones_prov[prov_sel]
            num_factura = st.text_input("Número de factura *", key="cmp_factura")
            fecha_cmp   = st.date_input("Fecha de entrada *", value=date.today(), key="cmp_fecha")
        with col2:
            notas_cmp = st.text_area("Observaciones", key="cmp_notas")

        st.divider()
        st.markdown("#### Productos comprados")

        productos = get_productos()
        opciones_prod = {
            f"{p['codigo']} — {p['nombre']}": p
            for p in productos if p['activo']
        }

        if 'cmp_items' not in st.session_state:
            st.session_state.cmp_items = []

        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
        with col1:
            prod_sel = st.selectbox("Producto", list(opciones_prod.keys()), key="cmp_prod_sel")
        with col2:
            cant_cmp = st.number_input("Cantidad", min_value=1, value=1, key="cmp_cant")
        with col3:
            costo_u = st.number_input("Costo unit. $", min_value=0.0, value=0.0,
                                       format="%.2f", key="cmp_costo")
        with col4:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("➕ Agregar", key="btn_add_cmp"):
                prod = opciones_prod[prod_sel]
                st.session_state.cmp_items.append({
                    'producto_id'  : prod['id'],
                    'codigo'       : prod['codigo'],
                    'nombre'       : prod['nombre'],
                    'cantidad_total': cant_cmp,
                    'costo_unitario': costo_u,
                    'peso_unitario' : float(prod.get('peso_kg') or 0),
                    'peso_total'    : cant_cmp * float(prod.get('peso_kg') or 0)
                })

        if st.session_state.cmp_items:
            df_cmp = pd.DataFrame(st.session_state.cmp_items)[[
                'codigo', 'nombre', 'cantidad_total', 'costo_unitario'
            ]]
            df_cmp.columns = ['Código', 'Producto', 'Cantidad', 'Costo Unit.']
            st.dataframe(df_cmp, use_container_width=True, hide_index=True)

            costo_total = sum(
                i['cantidad_total'] * i['costo_unitario']
                for i in st.session_state.cmp_items
            )
            st.metric("💰 Costo total", f"${costo_total:,.2f}")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("🗑️ Limpiar lista", key="btn_clear_cmp"):
                    st.session_state.cmp_items = []
                    st.rerun()
            with col2:
                if st.button("💾 Crear hoja de entrada", type="primary",
                             use_container_width=True, key="btn_crear_cmp"):
                    if not num_factura:
                        st.error("❌ El número de factura es obligatorio.")
                    else:
                        try:
                            folio = generar_folio_entrada()
                            crear_hoja_entrada({
                                'folio'        : folio,
                                'tipo_entrada' : 'compra',
                                'estatus'      : 'pendiente',
                                'proveedor_id' : prov_id,
                                'num_factura'  : num_factura,
                                'costo_total'  : costo_total,
                                'fecha_entrada': fecha_cmp,
                                'notas'        : notas_cmp
                            }, st.session_state.cmp_items)
                            st.success(f"✅ Hoja de entrada {folio} creada.")
                            st.session_state.cmp_items = []
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error: {e}")

# ================================================
# TAB 3 — FABRICACIÓN
# ================================================
with tab_fabricacion:
    st.subheader("Registrar alta de equipo fabricado")

    col1, col2 = st.columns(2)
    with col1:
        lote      = st.text_input("Lote de fabricación *",
                                   placeholder="Ej: LOTE-2026-001", key="fab_lote")
        fecha_fab = st.date_input("Fecha de entrada *",
                                   value=date.today(), key="fab_fecha")
    with col2:
        notas_fab = st.text_area("Observaciones", key="fab_notas")

    st.divider()
    st.markdown("#### Equipo fabricado")

    productos  = get_productos()
    fab_prods  = [p for p in productos if p.get('se_fabrica') and p['activo']]
    opciones_fab = {
        f"{p['codigo']} — {p['nombre']}": p
        for p in fab_prods
    }

    if not opciones_fab:
        st.warning("No hay productos marcados como fabricables en el catálogo.")
    else:
        if 'fab_items' not in st.session_state:
            st.session_state.fab_items = []

        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            fab_prod_sel = st.selectbox(
                "Producto fabricado",
                list(opciones_fab.keys()),
                key="fab_prod_sel"
            )
        with col2:
            cant_fab = st.number_input(
                "Cantidad", min_value=1, value=1, key="fab_cant"
            )
        with col3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("➕ Agregar", key="btn_add_fab"):
                prod = opciones_fab[fab_prod_sel]
                st.session_state.fab_items.append({
                    'producto_id'  : prod['id'],
                    'codigo'       : prod['codigo'],
                    'nombre'       : prod['nombre'],
                    'cantidad_total': cant_fab,
                    'peso_unitario' : float(prod.get('peso_kg') or 0),
                    'peso_total'    : cant_fab * float(prod.get('peso_kg') or 0)
                })

        if st.session_state.fab_items:
            df_fab = pd.DataFrame(st.session_state.fab_items)[[
                'codigo', 'nombre', 'cantidad_total'
            ]]
            df_fab.columns = ['Código', 'Producto', 'Cantidad']
            st.dataframe(df_fab, use_container_width=True, hide_index=True)

            col1, col2 = st.columns(2)
            with col1:
                if st.button("🗑️ Limpiar lista", key="btn_clear_fab"):
                    st.session_state.fab_items = []
                    st.rerun()
            with col2:
                if st.button("💾 Crear hoja de entrada", type="primary",
                             use_container_width=True, key="btn_crear_fab"):
                    if not lote:
                        st.error("❌ El lote de fabricación es obligatorio.")
                    else:
                        try:
                            folio = generar_folio_entrada()
                            crear_hoja_entrada({
                                'folio'            : folio,
                                'tipo_entrada'     : 'fabricacion',
                                'estatus'          : 'pendiente',
                                'lote_fabricacion' : lote,
                                'fecha_entrada'    : fecha_fab,
                                'notas'            : notas_fab
                            }, st.session_state.fab_items)
                            st.success(f"✅ Hoja de entrada {folio} creada.")
                            st.session_state.fab_items = []
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error: {e}")

# ================================================
# TAB 4 — LISTA
# ================================================
with tab_lista:
    st.subheader("Hojas de entrada registradas")

    col1, col2 = st.columns(2)
    with col1:
        filtro_tipo = st.selectbox(
            "Tipo",
            ["Todos"] + list(TIPO_LABEL.values()),
            key="filtro_he_tipo"
        )
    with col2:
        filtro_est = st.selectbox(
            "Estatus",
            ["Todos"] + list(ESTATUS_LABEL.values()),
            key="filtro_he_est"
        )

    entradas = get_hojas_entrada()

    if filtro_tipo != "Todos":
        tipo_key = [k for k, v in TIPO_LABEL.items() if v == filtro_tipo][0]
        entradas = [e for e in entradas if e['tipo_entrada'] == tipo_key]

    if filtro_est != "Todos":
        est_key = [k for k, v in ESTATUS_LABEL.items() if v == filtro_est][0]
        entradas = [e for e in entradas if e['estatus'] == est_key]

    if not entradas:
        st.info("No hay hojas de entrada registradas.")
    else:
        df = pd.DataFrame(entradas)
        df['tipo_entrada'] = df['tipo_entrada'].map(TIPO_LABEL)
        df['estatus']      = df['estatus'].map(ESTATUS_LABEL)
        df['fecha_entrada'] = pd.to_datetime(
            df['fecha_entrada'], errors='coerce'
        ).dt.strftime('%d/%m/%Y')

        df_show = df[[
            'folio', 'tipo_entrada', 'cliente_nombre',
            'obra_nombre', 'proveedor_nombre',
            'fecha_entrada', 'estatus'
        ]].fillna('—')
        df_show.columns = [
            'Folio HE', 'Tipo', 'Cliente',
            'Obra', 'Proveedor', 'Fecha', 'Estatus'
        ]
        st.dataframe(df_show, use_container_width=True, hide_index=True)
        st.caption(f"Total: {len(entradas)} hojas de entrada")

# ================================================
# TAB 5 — DETALLE
# ================================================
with tab_detalle:
    st.subheader("Detalle de hoja de entrada")

    entradas = get_hojas_entrada()

    if not entradas:
        st.info("No hay hojas de entrada registradas.")
    else:
        opciones = {
            f"{e['folio']} — {TIPO_LABEL.get(e['tipo_entrada'],'—')} — {e.get('cliente_nombre') or e.get('proveedor_nombre') or '—'}": e['id']
            for e in entradas
        }
        seleccion  = st.selectbox("Selecciona hoja de entrada", list(opciones.keys()))
        entrada_id = opciones[seleccion]

        try:
            he, items = get_hoja_entrada_detalle(entrada_id)
        except Exception as e:
            st.error(f"Error: {e}")
            st.stop()

        if he:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"**Folio HE:** {he['folio']}")
                st.markdown(f"**Tipo:** {TIPO_LABEL.get(he['tipo_entrada'],'—')}")
                st.markdown(f"**Estatus:** {ESTATUS_LABEL.get(he['estatus'],'—')}")
            with col2:
                if he['tipo_entrada'] == 'devolucion':
                    st.markdown(f"**Cliente:** {he.get('cliente_nombre') or '—'}")
                    obra_txt = f"{he.get('folio_obra','—')} — {he.get('obra_nombre','')}" \
                               if he.get('obra_nombre') else "Sin obra"
                    st.markdown(f"**Obra:** {obra_txt}")
                    st.markdown(f"**Contrato:** {he.get('contrato_folio') or '—'}")
                elif he['tipo_entrada'] == 'compra':
                    st.markdown(f"**Proveedor:** {he.get('proveedor_nombre') or '—'}")
                    st.markdown(f"**Factura:** {he.get('num_factura') or '—'}")
                    st.markdown(f"**Costo total:** ${float(he.get('costo_total') or 0):,.2f}")
                elif he['tipo_entrada'] == 'fabricacion':
                    st.markdown(f"**Lote:** {he.get('lote_fabricacion') or '—'}")
            with col3:
                fi = he['fecha_entrada']
                st.markdown(f"**Fecha entrada:** {fi.strftime('%d/%m/%Y') if fi else '—'}")
                fc = he.get('fecha_cierre')
                st.markdown(f"**Fecha cierre:** {fc.strftime('%d/%m/%Y') if fc else '—'}")
                if he.get('contrato_venta_id'):
                    st.markdown(f"**Contrato venta:** generado ✅")
                if he.get('notas'):
                    st.markdown(f"**Notas:** {he['notas']}")

            st.divider()

            # Items
            if items:
                st.subheader("Detalle de equipo")
                df_items = pd.DataFrame(items)

                if he['tipo_entrada'] == 'devolucion':
                    total_piezas = df_items['cantidad_total'].sum()
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("✅ Buenas", int(df_items['cantidad_buena'].sum()))
                    col2.metric("🔧 Dañadas", int(df_items['cantidad_danada'].sum()))
                    col3.metric("❌ Pérdidas", int(df_items['cantidad_perdida'].sum()))
                    col4.metric("💀 Chatarra", int(df_items['cantidad_chatarra'].sum()))

                    df_show = df_items[[
                        'codigo', 'producto_nombre',
                        'cantidad_buena', 'cantidad_danada',
                        'cantidad_perdida', 'cantidad_chatarra'
                    ]]
                    df_show.columns = [
                        'Código', 'Producto',
                        '✅ Bueno', '🔧 Dañado',
                        '❌ Pérdida', '💀 Chatarra'
                    ]
                else:
                    total_piezas = df_items['cantidad_total'].sum()
                    st.metric("📦 Total piezas", int(total_piezas))
                    df_show = df_items[['codigo', 'producto_nombre', 'cantidad_total']]
                    df_show.columns = ['Código', 'Producto', 'Cantidad']

                st.dataframe(df_show, use_container_width=True, hide_index=True)

            st.divider()

            # Actualizar estatus
            if he['estatus'] not in ['cerrada', 'cancelada']:
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Actualizar estatus**")
                    opciones_est = {
                        k: v for k, v in ESTATUS_LABEL.items()
                        if k != he['estatus']
                    }
                    nuevo_est = st.selectbox(
                        "Nuevo estatus",
                        list(opciones_est.keys()),
                        format_func=lambda x: ESTATUS_LABEL[x],
                        key="sel_est_he"
                    )
                    fecha_cierre = None
                    if nuevo_est == 'cerrada':
                        fecha_cierre = st.date_input(
                            "Fecha de cierre",
                            value=date.today(),
                            key="he_fecha_cierre"
                        )
                        st.warning(
                            "⚠️ Al cerrar se actualizará el inventario automáticamente."
                        )

                    if st.button("Actualizar estatus", type="primary", key="btn_upd_he"):
                        actualizar_estatus_entrada(entrada_id, nuevo_est, fecha_cierre)
                        st.success("✅ Estatus actualizado.")
                        if nuevo_est == 'cerrada':
                            st.info("📦 Inventario actualizado correctamente.")
                        st.rerun()
            else:
                st.info(f"Esta HE está **{ESTATUS_LABEL[he['estatus']]}** — no se puede modificar.")