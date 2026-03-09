# pages/03_cotizaciones.py
# Módulo de cotizaciones

import streamlit as st
import pandas as pd
from utils.database import (
    get_clientes,
    get_productos,
    generar_folio_cotizacion,
    crear_cotizacion,
    get_cotizaciones,
    get_cotizacion_detalle,
    actualizar_estatus_cotizacion
)

st.set_page_config(page_title="Cotizaciones - ICAM ERP", layout="wide")

st.title("📋 Cotizaciones")
st.divider()

ESTATUS_LABEL = {
    'borrador'    : '📝 Borrador',
    'enviada'     : '📤 Enviada',
    'en_revision' : '🔍 En revisión',
    'aprobada'    : '✅ Aprobada',
    'cancelada'   : '❌ Cancelada'
}

ESTATUS_COLOR = {
    'borrador'    : 'gray',
    'enviada'     : 'blue',
    'en_revision' : 'orange',
    'aprobada'    : 'green',
    'cancelada'   : 'red'
}

tab_lista, tab_nueva, tab_detalle = st.tabs([
    "📋 Lista",
    "➕ Nueva cotización",
    "🔍 Ver detalle"
])

# ================================================
# TAB 1 — LISTA
# ================================================
with tab_lista:
    st.subheader("Cotizaciones registradas")

    col1, col2 = st.columns([3, 1])
    with col1:
        filtro = st.selectbox(
            "Filtrar por estatus",
            ["Todos"] + list(ESTATUS_LABEL.values())
        )

    estatus_key = None
    if filtro != "Todos":
        estatus_key = [k for k, v in ESTATUS_LABEL.items() if v == filtro][0]

    cotizaciones = get_cotizaciones(estatus=estatus_key)

    if not cotizaciones:
        st.info("No hay cotizaciones registradas.")
    else:
        df = pd.DataFrame(cotizaciones)
        df['estatus'] = df['estatus'].map(ESTATUS_LABEL)
        df['total'] = df['total'].apply(lambda x: f"${x:,.2f}")
        df = df[[
            'folio', 'cliente_nombre', 'tipo_operacion',
            'dias_renta', 'total', 'estatus', 'created_at'
        ]]
        df.columns = [
            'Folio', 'Cliente', 'Tipo',
            'Días', 'Total', 'Estatus', 'Fecha'
        ]
        df['Fecha'] = pd.to_datetime(df['Fecha']).dt.strftime('%d/%m/%Y')
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.caption(f"Total: {len(cotizaciones)} cotizaciones")

# ================================================
# TAB 2 — NUEVA COTIZACIÓN
# ================================================
with tab_nueva:
    st.subheader("Crear nueva cotización")

    # Inicializar items en session state
    if 'cot_items' not in st.session_state:
        st.session_state.cot_items = []

    clientes  = get_clientes()
    productos = get_productos()

    if not clientes:
        st.error("No hay clientes registrados. Crea un cliente primero.")
        st.stop()

    if not productos:
        st.error("No hay productos registrados. Crea productos primero.")
        st.stop()

    # — Datos generales —
    st.markdown("#### Datos generales")
    col1, col2, col3 = st.columns(3)

    with col1:
        opciones_clientes = {c['razon_social']: c['id'] for c in clientes}
        cliente_sel = st.selectbox("Cliente *", list(opciones_clientes.keys()))
        cliente_id  = opciones_clientes[cliente_sel]

    with col2:
        tipo_operacion = st.selectbox("Tipo de operación", ["renta", "venta"])

    with col3:
        dias_renta = st.number_input(
            "Días de renta",
            min_value=1, value=30, step=1,
            disabled=(tipo_operacion == "venta")
        )

    notas = st.text_area("Notas / condiciones", placeholder="Condiciones especiales, observaciones...")

    st.divider()

    # — Productos —
    st.markdown("#### Agregar productos")
    col1, col2, col3, col4 = st.columns([3, 1, 2, 1])

    opciones_productos = {f"{p['codigo']} — {p['nombre']}": p for p in productos}

    with col1:
        prod_sel = st.selectbox("Producto", list(opciones_productos.keys()))
    with col2:
        cantidad = st.number_input("Cantidad", min_value=1, value=1, step=1)
    with col3:
        producto_data = opciones_productos[prod_sel]
        precio_campo = 'precio_renta_dia' if tipo_operacion == 'renta' else 'precio_venta'
        precio_default = float(producto_data[precio_campo] or 0)
        precio = st.number_input("Precio unitario", min_value=0.0,
                                  value=precio_default, step=0.50, format="%.2f")
    with col4:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("➕ Agregar"):
            st.session_state.cot_items.append({
                'producto_id'   : producto_data['id'],
                'codigo'        : producto_data['codigo'],
                'nombre'        : producto_data['nombre'],
                'peso_kg'       : float(producto_data['peso_kg'] or 0),
                'cantidad'      : cantidad,
                'precio_unitario': precio,
                'subtotal'      : cantidad * precio
            })
            st.rerun()

    # Tabla de items agregados
    if st.session_state.cot_items:
        st.markdown("**Productos en cotización:**")
        df_items = pd.DataFrame(st.session_state.cot_items)

        col_tabla, col_eliminar = st.columns([5, 1])
        with col_tabla:
            st.dataframe(
                df_items[['codigo', 'nombre', 'cantidad', 'precio_unitario', 'subtotal']].rename(columns={
                    'codigo': 'Código', 'nombre': 'Nombre',
                    'cantidad': 'Cant.', 'precio_unitario': 'Precio', 'subtotal': 'Subtotal'
                }),
                use_container_width=True, hide_index=True
            )
        with col_eliminar:
            idx_eliminar = st.number_input("Eliminar fila #", min_value=1,
                                            max_value=len(st.session_state.cot_items), step=1)
            if st.button("🗑️ Eliminar"):
                st.session_state.cot_items.pop(idx_eliminar - 1)
                st.rerun()

    st.divider()

    # — Flete —
    st.markdown("#### Flete")
    col1, col2, col3 = st.columns(3)

    with col1:
        tipo_flete = st.selectbox(
            "Tipo de flete",
            ["cotizado", "sin_costo", "cliente"],
            format_func=lambda x: {
                'cotizado' : '💰 Se cotiza (cobrado)',
                'sin_costo': '🎁 Sin costo',
                'cliente'  : '🚛 Por cuenta del cliente'
            }[x]
        )

    peso_total = sum(i['peso_kg'] * i['cantidad'] for i in st.session_state.cot_items)
    monto_flete = 0.0

    if tipo_flete == 'cotizado':
        with col2:
            distancia_km = st.number_input("Distancia (km)", min_value=0.0, step=1.0)
        with col3:
            tarifa = st.number_input("Tarifa ($/kg/km)", min_value=0.0,
                                      value=0.025, step=0.001, format="%.3f")
        monto_flete = peso_total * distancia_km * tarifa
        st.info(f"Peso total: {peso_total:.1f} kg | Flete calculado: ${monto_flete:,.2f}")
    else:
        distancia_km = 0.0
        tarifa = 0.0

    st.divider()

    # — Totales —
    st.markdown("#### Totales")
    subtotal_equipo = sum(i['subtotal'] for i in st.session_state.cot_items)

    if tipo_operacion == 'renta':
        subtotal_equipo = subtotal_equipo * dias_renta

    subtotal = subtotal_equipo + monto_flete
    aplica_iva = st.checkbox("Aplicar IVA 16%", value=True)
    iva   = subtotal * 0.16 if aplica_iva else 0
    total = subtotal + iva

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Subtotal equipo", f"${subtotal_equipo:,.2f}")
    with col2:
        st.metric("Flete", f"${monto_flete:,.2f}")
    with col3:
        st.metric("IVA 16%", f"${iva:,.2f}")
    with col4:
        st.metric("**TOTAL**", f"${total:,.2f}")

    st.divider()

    # — Estatus y guardar —
    col1, col2 = st.columns([2, 1])
    with col1:
        estatus = st.selectbox(
            "Guardar como",
            list(ESTATUS_LABEL.keys()),
            format_func=lambda x: ESTATUS_LABEL[x]
        )
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("💾 Guardar cotización", type="primary", use_container_width=True):
            if not st.session_state.cot_items:
                st.error("Agrega al menos un producto.")
            else:
                try:
                    folio = generar_folio_cotizacion()
                    nueva_id = crear_cotizacion({
                        'folio'          : folio,
                        'cliente_id'     : cliente_id,
                        'tipo_operacion' : tipo_operacion,
                        'estatus'        : estatus,
                        'tipo_flete'     : tipo_flete,
                        'distancia_km'   : distancia_km,
                        'tarifa_flete'   : tarifa,
                        'monto_flete'    : monto_flete,
                        'subtotal'       : subtotal,
                        'aplica_iva'     : aplica_iva,
                        'iva'            : iva,
                        'total'          : total,
                        'dias_renta'     : dias_renta,
                        'notas'          : notas
                    }, st.session_state.cot_items)
                    st.success(f"✅ Cotización {folio} guardada correctamente.")
                    st.session_state.cot_items = []
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error: {e}")

# ================================================
# TAB 3 — DETALLE
# ================================================
with tab_detalle:
    st.subheader("Detalle de cotización")

    cotizaciones = get_cotizaciones()

    if not cotizaciones:
        st.info("No hay cotizaciones registradas.")
    else:
        opciones = {
            f"{c['folio']} — {c['cliente_nombre']}": c['id']
            for c in cotizaciones
        }
        seleccion  = st.selectbox("Selecciona cotización", list(opciones.keys()))
        cot_id     = opciones[seleccion]
        cot, items = get_cotizacion_detalle(cot_id)

        if cot:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"**Folio:** {cot['folio']}")
                st.markdown(f"**Cliente:** {cot['cliente_nombre']}")
                st.markdown(f"**RFC:** {cot['rfc']}")
            with col2:
                st.markdown(f"**Tipo:** {cot['tipo_operacion'].capitalize()}")
                st.markdown(f"**Días:** {cot['dias_renta']}")
                st.markdown(f"**Fecha:** {cot['created_at'].strftime('%d/%m/%Y')}")
            with col3:
                estatus_actual = cot['estatus']
                st.markdown(f"**Estatus:** {ESTATUS_LABEL[estatus_actual]}")

                # Cambiar estatus
                nuevo_estatus = st.selectbox(
                    "Cambiar estatus",
                    list(ESTATUS_LABEL.keys()),
                    index=list(ESTATUS_LABEL.keys()).index(estatus_actual),
                    format_func=lambda x: ESTATUS_LABEL[x]
                )
                if st.button("Actualizar estatus"):
                    actualizar_estatus_cotizacion(cot_id, nuevo_estatus)
                    st.success("✅ Estatus actualizado.")
                    st.rerun()

            st.divider()

            # Items
            if items:
                df_items = pd.DataFrame(items)
                df_items = df_items[[
                    'codigo', 'producto_nombre', 'cantidad',
                    'precio_unitario', 'subtotal'
                ]]
                df_items.columns = ['Código', 'Producto', 'Cantidad', 'Precio Unit.', 'Subtotal']
                st.dataframe(df_items, use_container_width=True, hide_index=True)

            st.divider()
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Subtotal", f"${cot['subtotal']:,.2f}")
            with col2:
                st.metric("IVA", f"${cot['iva']:,.2f}")
            with col3:
                st.metric("Total", f"${cot['total']:,.2f}")

            if cot['notas']:
                st.markdown(f"**Notas:** {cot['notas']}")