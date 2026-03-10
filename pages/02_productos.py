# pages/02_productos.py
# Módulo de gestión de productos e inventario

import streamlit as st
import pandas as pd
from utils.database import (
    get_productos,
    get_producto_by_id,
    crear_producto,
    actualizar_producto,
    get_insumos,
    crear_insumo,
    get_bom_producto,
    guardar_bom_producto
)

st.set_page_config(page_title="Productos - ICAM ERP", layout="wide")

st.title("📦 Productos")
st.divider()

SISTEMAS = ['torres_trabajo', 'multidireccional', 'hamacas', 'apuntalamientos']
SISTEMAS_LABEL = {
    'torres_trabajo'   : 'Torres de trabajo',
    'multidireccional' : 'Multidireccional',
    'hamacas'          : 'Hamacas',
    'apuntalamientos'  : 'Apuntalamientos'
}
UNIDADES = ['PZA', 'ML', 'M2', 'JGO', 'KIT']

tab_catalogo, tab_inventario, tab_nuevo, tab_editar, tab_bom = st.tabs([
    "📋 Catálogo",
    "📊 Inventario",
    "➕ Nuevo producto",
    "✏️ Editar producto",
    "🧪 BOM / Recetas"
])

# ================================================
# TAB 1 — CATÁLOGO
# ================================================
with tab_catalogo:
    st.subheader("Catálogo de productos")

    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        filtro_sistema = st.selectbox(
            "Filtrar por sistema",
            ["Todos"] + list(SISTEMAS_LABEL.values())
        )
    with col3:
        mostrar_inactivos = st.checkbox("Mostrar inactivos")

    productos = get_productos(solo_activos=not mostrar_inactivos)

    if filtro_sistema != "Todos":
        sistema_key = [k for k, v in SISTEMAS_LABEL.items() if v == filtro_sistema][0]
        productos = [p for p in productos if p['sistema'] == sistema_key]

    if not productos:
        st.info("No hay productos registrados.")
    else:
        df = pd.DataFrame(productos)
        df['sistema']    = df['sistema'].map(SISTEMAS_LABEL).fillna("—")
        df['se_fabrica'] = df['se_fabrica'].map({True: '✅ Sí', False: '🛒 Compra'})
        df = df[[
            'codigo', 'nombre', 'unidad', 'sistema',
            'precio_renta_dia', 'precio_venta',
            'peso_kg', 'se_fabrica', 'activo'
        ]]
        df.columns = [
            'Código', 'Nombre', 'Unidad', 'Sistema',
            'Renta/Día', 'Precio Venta',
            'Peso kg', 'Fabricación', 'Activo'
        ]
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.caption(f"Total: {len(productos)} productos")

# ================================================
# TAB 2 — INVENTARIO
# ================================================
with tab_inventario:
    st.subheader("Estado del inventario")

    productos = get_productos(solo_activos=True)

    if not productos:
        st.info("No hay productos registrados.")
    else:
        df = pd.DataFrame(productos)

        bajo_stock = df[df['cantidad_disponible'] < df['stock_minimo']]
        if not bajo_stock.empty:
            st.warning(f"⚠️ {len(bajo_stock)} producto(s) por debajo del stock mínimo")

        df['sistema'] = df['sistema'].map(SISTEMAS_LABEL).fillna("—")
        df = df[[
            'codigo', 'nombre', 'sistema',
            'cantidad_disponible', 'cantidad_rentada',
            'cantidad_mantenimiento', 'cantidad_chatarra',
            'stock_minimo'
        ]]
        df.columns = [
            'Código', 'Nombre', 'Sistema',
            'Disponible', 'Rentado',
            'Mantenimiento', 'Chatarra',
            'Stock Mínimo'
        ]

        st.dataframe(
            df.style.applymap(
                lambda v: 'background-color: #ffe0e0'
                if isinstance(v, (int, float)) and v < 0 else '',
                subset=['Disponible']
            ),
            use_container_width=True,
            hide_index=True
        )

        st.divider()
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("✅ Total disponible",   int(df['Disponible'].sum()))
        with col2:
            st.metric("🚧 Total rentado",      int(df['Rentado'].sum()))
        with col3:
            st.metric("🔧 En mantenimiento",   int(df['Mantenimiento'].sum()))
        with col4:
            st.metric("🗑️ Chatarra",           int(df['Chatarra'].sum()))

# ================================================
# TAB 3 — NUEVO PRODUCTO
# ================================================
with tab_nuevo:
    st.subheader("Registrar nuevo producto")

    with st.form("form_nuevo_producto", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            codigo       = st.text_input("Código *", placeholder="AND-001")
            nombre       = st.text_input("Nombre *", placeholder="Marco 1.0m x 1.70m")
            descripcion  = st.text_area("Descripción", placeholder="Descripción del producto")
            unidad       = st.selectbox("Unidad de medida", UNIDADES)
            stock_minimo = st.number_input("Stock mínimo", min_value=0, step=1)

        with col2:
            sistema = st.selectbox("Sistema", list(SISTEMAS_LABEL.values()))
            precio_renta_dia = st.number_input(
                "Precio renta por día (MXN)",
                min_value=0.0, step=0.50, format="%.2f"
            )
            precio_venta = st.number_input(
                "Precio venta (MXN)",
                min_value=0.0, step=100.0, format="%.2f"
            )
            peso_kg = st.number_input(
                "Peso (kg)",
                min_value=0.0, step=0.1, format="%.2f"
            )
            se_fabrica = st.radio(
                "¿Se fabrica?",
                ["Sí, se fabrica", "No, se compra"],
                horizontal=True
            )

        st.divider()
        submitted = st.form_submit_button("💾 Guardar producto", type="primary")

        if submitted:
            if not codigo:
                st.error("El código es obligatorio.")
            elif not nombre:
                st.error("El nombre es obligatorio.")
            else:
                try:
                    sistema_key = [k for k, v in SISTEMAS_LABEL.items() if v == sistema][0]
                    nuevo_id = crear_producto({
                        'codigo'          : codigo.upper(),
                        'nombre'          : nombre,
                        'descripcion'     : descripcion,
                        'unidad'          : unidad,
                        'precio_renta_dia': precio_renta_dia,
                        'precio_venta'    : precio_venta,
                        'peso_kg'         : peso_kg,
                        'se_fabrica'      : se_fabrica == "Sí, se fabrica",
                        'sistema'         : sistema_key,
                        'stock_minimo'    : stock_minimo
                    })
                    st.success(f"✅ Producto registrado con ID: {nuevo_id}")
                except Exception as e:
                    if "unique" in str(e).lower():
                        st.error("❌ Ya existe un producto con ese código.")
                    else:
                        st.error(f"❌ Error: {e}")

# ================================================
# TAB 4 — EDITAR PRODUCTO
# ================================================
with tab_editar:
    st.subheader("Editar producto existente")

    productos = get_productos(solo_activos=False)

    if not productos:
        st.info("No hay productos registrados.")
    else:
        opciones    = {f"{p['codigo']} — {p['nombre']}": p['id'] for p in productos}
        seleccion   = st.selectbox("Selecciona un producto", list(opciones.keys()))
        producto_id = opciones[seleccion]
        p           = get_producto_by_id(producto_id)

        if p:
            with st.form("form_editar_producto"):
                col1, col2 = st.columns(2)

                with col1:
                    codigo      = st.text_input("Código *", value=p['codigo'])
                    nombre      = st.text_input("Nombre *", value=p['nombre'])
                    descripcion = st.text_area("Descripción", value=p['descripcion'] or "")
                    unidad      = st.selectbox(
                        "Unidad",
                        UNIDADES,
                        index=UNIDADES.index(p['unidad']) if p['unidad'] in UNIDADES else 0
                    )
                    stock_minimo = st.number_input(
                        "Stock mínimo",
                        min_value=0, step=1,
                        value=int(p['stock_minimo'] or 0)
                    )
                    activo = st.checkbox("Producto activo", value=p['activo'])

                with col2:
                    sistema_actual = p['sistema'] or SISTEMAS[0]
                    sistema = st.selectbox(
                        "Sistema",
                        list(SISTEMAS_LABEL.values()),
                        index=SISTEMAS.index(sistema_actual)
                    )
                    precio_renta_dia = st.number_input(
                        "Precio renta por día (MXN)",
                        min_value=0.0, step=0.50, format="%.2f",
                        value=float(p['precio_renta_dia'] or 0)
                    )
                    precio_venta = st.number_input(
                        "Precio venta (MXN)",
                        min_value=0.0, step=100.0, format="%.2f",
                        value=float(p['precio_venta'] or 0)
                    )
                    peso_kg = st.number_input(
                        "Peso (kg)",
                        min_value=0.0, step=0.1, format="%.2f",
                        value=float(p['peso_kg'] or 0)
                    )
                    se_fabrica = st.radio(
                        "¿Se fabrica?",
                        ["Sí, se fabrica", "No, se compra"],
                        index=0 if p['se_fabrica'] else 1,
                        horizontal=True
                    )

                st.divider()
                submitted = st.form_submit_button("💾 Actualizar producto", type="primary")

                if submitted:
                    if not codigo or not nombre:
                        st.error("Código y nombre son obligatorios.")
                    else:
                        try:
                            sistema_key = [
                                k for k, v in SISTEMAS_LABEL.items() if v == sistema
                            ][0]
                            actualizar_producto(producto_id, {
                                'codigo'          : codigo.upper(),
                                'nombre'          : nombre,
                                'descripcion'     : descripcion,
                                'unidad'          : unidad,
                                'precio_renta_dia': precio_renta_dia,
                                'precio_venta'    : precio_venta,
                                'peso_kg'         : peso_kg,
                                'se_fabrica'      : se_fabrica == "Sí, se fabrica",
                                'sistema'         : sistema_key,
                                'stock_minimo'    : stock_minimo,
                                'activo'          : activo
                            })
                            st.success("✅ Producto actualizado correctamente.")
                        except Exception as e:
                            st.error(f"❌ Error: {e}")

# ================================================
# TAB 5 — BOM / RECETAS
# ================================================
with tab_bom:
    st.subheader("Lista de materiales (BOM)")
    st.caption("Define la receta de materiales para cada producto fabricable.")

    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("➕ Nuevo insumo", key="btn_nuevo_insumo"):
            st.session_state.show_nuevo_insumo = True

    # Formulario nuevo insumo
    if st.session_state.get('show_nuevo_insumo'):
        with st.expander("➕ Registrar nuevo insumo", expanded=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                ni_codigo = st.text_input("Código *", key="ni_codigo",
                                          placeholder="TUB-002")
            with col2:
                ni_nombre = st.text_input("Nombre *", key="ni_nombre",
                                          placeholder="Tubo 2 pulgadas")
            with col3:
                ni_unidad = st.selectbox(
                    "Unidad *", key="ni_unidad",
                    options=['metro', 'kg', 'litro', 'pieza', 'rollo', 'lata']
                )
            ni_desc = st.text_input("Descripción", key="ni_desc")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 Guardar insumo", key="btn_save_insumo"):
                    if not ni_codigo or not ni_nombre:
                        st.error("Código y nombre son obligatorios.")
                    else:
                        try:
                            crear_insumo({
                                'codigo'     : ni_codigo.upper(),
                                'nombre'     : ni_nombre,
                                'unidad'     : ni_unidad,
                                'descripcion': ni_desc
                            })
                            st.success("✅ Insumo registrado.")
                            st.session_state.show_nuevo_insumo = False
                            st.rerun()
                        except Exception as e:
                            if 'unique' in str(e).lower():
                                st.error("❌ Ya existe un insumo con ese código.")
                            else:
                                st.error(f"❌ Error: {e}")
            with col2:
                if st.button("Cancelar", key="btn_cancel_insumo"):
                    st.session_state.show_nuevo_insumo = False
                    st.rerun()

    st.divider()

    # Catálogo de insumos
    with st.expander("📋 Catálogo de insumos registrados"):
        insumos = get_insumos()
        if insumos:
            df_ins = pd.DataFrame(insumos)[['codigo', 'nombre', 'unidad']]
            df_ins.columns = ['Código', 'Nombre', 'Unidad']
            st.dataframe(df_ins, use_container_width=True, hide_index=True)
        else:
            st.info("No hay insumos registrados.")

    st.divider()

    # Seleccionar producto fabricable
    productos    = get_productos(solo_activos=True)
    fab_productos = [p for p in productos if p.get('se_fabrica')]

    if not fab_productos:
        st.warning("No hay productos marcados como fabricables.")
    else:
        opciones_fab = {
            f"{p['codigo']} — {p['nombre']}": p['id']
            for p in fab_productos
        }
        prod_sel    = st.selectbox(
            "Selecciona producto fabricable",
            list(opciones_fab.keys()),
            key="bom_prod_sel"
        )
        producto_id = opciones_fab[prod_sel]

        # BOM actual
        bom_actual = get_bom_producto(producto_id)

        st.markdown("#### Receta actual")
        if bom_actual:
            df_bom = pd.DataFrame(bom_actual)[[
                'insumo_codigo', 'insumo_nombre',
                'cantidad_por_pieza', 'unidad'
            ]]
            df_bom.columns = ['Código', 'Insumo', 'Cantidad x pieza', 'Unidad']
            st.dataframe(df_bom, use_container_width=True, hide_index=True)
        else:
            st.info("Este producto no tiene receta definida aún.")

        st.divider()
        st.markdown("#### Editar receta")
        st.caption("Define todos los materiales necesarios para fabricar UNA pieza.")

        insumos = get_insumos()
        if not insumos:
            st.warning("Primero registra insumos en el catálogo.")
        else:
            opciones_ins = {
                f"{i['codigo']} — {i['nombre']} ({i['unidad']})": i
                for i in insumos
            }

            # Inicializar BOM en session state
            if f'bom_items_{producto_id}' not in st.session_state:
                st.session_state[f'bom_items_{producto_id}'] = [
                    {
                        'insumo_id'        : b['insumo_id'],
                        'codigo'           : b['insumo_codigo'],
                        'nombre'           : b['insumo_nombre'],
                        'unidad'           : b['unidad'],
                        'cantidad_por_pieza': float(b['cantidad_por_pieza'])
                    }
                    for b in bom_actual
                ]

            bom_items = st.session_state[f'bom_items_{producto_id}']

            # Agregar insumo
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                ins_sel = st.selectbox(
                    "Insumo",
                    list(opciones_ins.keys()),
                    key=f"bom_ins_sel_{producto_id}"
                )
            with col2:
                cant_ins = st.number_input(
                    "Cantidad x pieza",
                    min_value=0.0001,
                    value=1.0,
                    format="%.4f",
                    key=f"bom_cant_{producto_id}"
                )
            with col3:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("➕ Agregar", key=f"btn_add_bom_{producto_id}"):
                    ins = opciones_ins[ins_sel]
                    # Verificar si ya existe
                    existe = any(
                        b['insumo_id'] == ins['id'] for b in bom_items
                    )
                    if existe:
                        st.warning("Este insumo ya está en la receta.")
                    else:
                        bom_items.append({
                            'insumo_id'        : ins['id'],
                            'codigo'           : ins['codigo'],
                            'nombre'           : ins['nombre'],
                            'unidad'           : ins['unidad'],
                            'cantidad_por_pieza': cant_ins
                        })
                        st.rerun()

            # Mostrar BOM editable
            if bom_items:
                st.markdown("**Receta en edición:**")

                for idx, item in enumerate(bom_items):
                    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                    with col1:
                        st.markdown(
                            f"{item['codigo']} — {item['nombre']} ({item['unidad']})"
                        )
                    with col2:
                        nueva_cant = st.number_input(
                            "cant",
                            min_value=0.0001,
                            value=float(item['cantidad_por_pieza']),
                            format="%.4f",
                            label_visibility="collapsed",
                            key=f"bom_edit_{producto_id}_{idx}"
                        )
                        bom_items[idx]['cantidad_por_pieza'] = nueva_cant
                    with col3:
                        st.markdown(item['unidad'])
                    with col4:
                        if st.button("🗑️", key=f"bom_del_{producto_id}_{idx}"):
                            bom_items.pop(idx)
                            st.rerun()

                st.divider()
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(
                        "🗑️ Limpiar receta",
                        key=f"btn_clear_bom_{producto_id}"
                    ):
                        st.session_state[f'bom_items_{producto_id}'] = []
                        st.rerun()
                with col2:
                    if st.button(
                        "💾 Guardar receta",
                        type="primary",
                        use_container_width=True,
                        key=f"btn_save_bom_{producto_id}"
                    ):
                        try:
                            guardar_bom_producto(producto_id, bom_items)
                            st.success("✅ Receta guardada correctamente.")
                            # Limpiar cache
                            del st.session_state[f'bom_items_{producto_id}']
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error: {e}")