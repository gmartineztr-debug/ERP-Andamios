# main.py
# Dashboard principal — ICAM ERP

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import date, timedelta
from utils.database import (
    get_dashboard_metricas,
    get_facturacion_mensual,
    get_stock_critico,
    get_contratos_proximos,
    get_facturacion_periodo,
    get_top_productos
)
from utils.reporting import export_to_csv, export_to_pdf, generate_monthly_report
from datetime import datetime
from utils.auth_manager import init_auth, login_screen, logout

# 1. Configuración de página (DEBE ser lo primero)
st.set_page_config(
    page_title="Andamios ERP",
    page_icon=":material/foundation:",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Definición de páginas (definirlas aquí para que estén disponibles en el dashboard)
pg_clientes = st.Page("pages/01_clientes.py", title="Clientes", icon=":material/groups:")
pg_productos = st.Page("pages/02_productos.py", title="Productos", icon=":material/inventory_2:")
pg_cotizaciones = st.Page("pages/03_cotizaciones.py", title="Cotizaciones", icon=":material/assignment:")
pg_obras = st.Page("pages/04_obras.py", title="Obras", icon=":material/foundation:")
pg_contratos = st.Page("pages/05_contratos.py", title="Contratos", icon=":material/description:")
pg_hojas_salida = st.Page("pages/06_hojas_salida.py", title="Hojas De Salida", icon=":material/local_shipping:")
pg_hojas_entrada = st.Page("pages/07_hojas_entrada.py", title="Hojas De Entrada", icon=":material/move_to_inbox:")
pg_fabricacion = st.Page("pages/08_fabricacion.py", title="Fabricación", icon=":material/build:")
pg_renovaciones = st.Page("pages/09_renovaciones.py", title="Renovaciones", icon=":material/refresh:")
pg_anticipos = st.Page("pages/10_anticipos.py", title="Anticipos", icon=":material/payments:")
pg_inventario = st.Page("pages/11_inventario.py", title="Inventario", icon=":material/bar_chart:")
pg_cambios_of = st.Page("pages/12_cambios_of.py", title="Cambios OF", icon=":material/sync_alt:")
pg_usuarios = st.Page("pages/13_usuarios.py", title="Gestión de Usuarios", icon=":material/person_add:")

def show_dashboard():
    # ─── Estilos ────────────────────────────────────────────────────────────────
    st.markdown("""
    <style>
    /* Tarjetas métricas */
    div[data-testid="metric-container"] {
        background: white;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    }
    div[data-testid="metric-container"] label {
        font-size: 0.78rem !important;
        color: #64748B !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
        font-size: 1.6rem !important;
        font-weight: 700 !important;
        color: #0F172A !important;
    }
    /* Alerta urgente */
    .alerta-roja {
        background: #FEF2F2;
        border-left: 4px solid #64748B;
        border-radius: 8px;
        padding: 10px 16px;
        margin-bottom: 8px;
    }
    .alerta-naranja {
        background: #F1F5F9;
        border-left: 4px solid #94A3B8;
        border-radius: 8px;
        padding: 10px 16px;
        margin-bottom: 8px;
    }
    .alerta-amarilla {
        background: #F8FAFC;
        border-left: 4px solid #CBD5E1;
        border-radius: 8px;
        padding: 10px 16px;
        margin-bottom: 8px;
    }
    /* Encabezado sección */
    .seccion-titulo {
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #94A3B8;
        margin-bottom: 12px;
        margin-top: 4px;
    }
    </style>
    """, unsafe_allow_html=True)

    # ─── Encabezado ─────────────────────────────────────────────────────────────
    col_titulo, col_periodo = st.columns([3, 2])
    with col_titulo:
        st.markdown("## :material/foundation: Andamios ERP — Dashboard")
        st.caption(f"Actualizado: {date.today().strftime('%d de %B de %Y')}")

    with col_periodo:
        col_a, col_b = st.columns(2)
        with col_a:
            fecha_inicio_filtro = st.date_input(
                "Desde",
                value=date.today().replace(day=1),
                key="dash_fi"
            )
        with col_b:
            fecha_fin_filtro = st.date_input(
                "Hasta",
                value=date.today(),
                key="dash_ff"
            )
        
        # Botón de Corte Mensual
        report_data = generate_monthly_report(metricas if 'metricas' in locals() else get_dashboard_metricas(), top_prod if 'top_prod' in locals() else [], stock_crit if 'stock_crit' in locals() else [])
        st.download_button(
            label=":material/description: Descargar Corte Mensual (PDF)",
            data=report_data,
            file_name=f"corte_mensual_{datetime.now().strftime('%Y%m')}.pdf",
            mime="application/pdf",
            use_container_width=True,
            type="primary"
        )

    st.divider()

    # ─── Cargar datos ────────────────────────────────────────────────────────────
    try:
        metricas   = get_dashboard_metricas()
        fac_meses  = get_facturacion_mensual()
        stock_crit = get_stock_critico()
        proximos   = get_contratos_proximos(30)
        fac_periodo = get_facturacion_periodo(fecha_inicio_filtro, fecha_fin_filtro)
        top_prod    = get_top_productos(5)
    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        st.stop()

    # ─── FILA 1: Métricas principales ───────────────────────────────────────────
    st.markdown('<p class="seccion-titulo">Resumen general</p>', unsafe_allow_html=True)

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            "Contratos activos",
            int(metricas['contratos_activos'] or 0)
        )
    with col2:
        vencen = int(metricas['contratos_por_vencer'] or 0)
        st.metric(
            "Vencen en 7 días",
            vencen,
            delta=f"-{vencen} urgentes" if vencen > 0 else None,
            delta_color="inverse"
        )
    with col3:
        fac_mes = float(metricas['facturacion_mes'] or 0)
        fac_ant = float(metricas['facturacion_mes_anterior'] or 0)
        delta_fac = fac_mes - fac_ant
        st.metric(
            "Facturación mes",
            f"${fac_mes:,.0f}",
            delta=f"${delta_fac:+,.0f} vs mes ant." if fac_ant > 0 else None
        )
    with col4:
        ant_pend = float(metricas['anticipos_pendientes'] or 0)
        st.metric(
            "Anticipos por cobrar",
            f"${ant_pend:,.0f}",
            delta=f"{int(metricas['contratos_anticipo_pendiente'] or 0)} contratos",
            delta_color="off"
        )
    with col5:
        total_inv = float((metricas['total_disponible'] or 0) + (metricas['total_rentado'] or 0))
        utilizacion = (
            float(metricas['total_rentado'] or 0) / total_inv * 100
            if total_inv > 0 else 0
        )
        st.metric(
            "Utilización inventario",
            f"{utilizacion:.1f}%",
            delta=f"{int(metricas['total_rentado'] or 0)} pzas rentadas",
            delta_color="off"
        )

    st.divider()

    # ─── FILA 2: Gráfica facturación + Contratos próximos ───────────────────────
    col_graf, col_proximos = st.columns([3, 2])

    with col_graf:
        st.markdown('<p class="seccion-titulo">Facturación mensual</p>', unsafe_allow_html=True)

        if fac_meses:
            df_fac = pd.DataFrame(fac_meses)
            df_fac['facturacion'] = df_fac['facturacion'].astype(float)
            df_fac['cobrado']     = df_fac['cobrado'].astype(float)

            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=df_fac['mes_label'],
                y=df_fac['facturacion'],
                name='Facturado',
                marker_color='#64748B',
                opacity=0.85
            ))
            fig.add_trace(go.Bar(
                x=df_fac['mes_label'],
                y=df_fac['cobrado'],
                name='Cobrado',
                marker_color='#94A3B8',
                opacity=0.85
            ))
            fig.update_layout(
                barmode='group',
                height=280,
                margin=dict(l=0, r=0, t=10, b=0),
                legend=dict(orientation='h', yanchor='bottom', y=1.02),
                plot_bgcolor='white',
                paper_bgcolor='white',
                yaxis=dict(tickprefix='$', gridcolor='#F1F5F9'),
                xaxis=dict(gridcolor='#F1F5F9')
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Exportar datos de facturación
            csv_fac = export_to_csv(df_fac)
            st.download_button(
                label=":material/bar_chart: Descargar Datos de Facturación",
                data=csv_fac,
                file_name=f"facturacion_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                key="btn_fac_csv",
                use_container_width=True
            )
        else:
            st.info("Sin datos de facturación aún.")

        # Métricas del período seleccionado
        if fac_periodo:
            st.markdown(
                f'<p class="seccion-titulo">Período: '
                f'{fecha_inicio_filtro.strftime("%d/%m/%Y")} — '
                f'{fecha_fin_filtro.strftime("%d/%m/%Y")}</p>',
                unsafe_allow_html=True
            )
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Contratos", int(fac_periodo['total_contratos'] or 0))
            c2.metric("Facturado",  f"${float(fac_periodo['facturacion'] or 0):,.0f}")
            c3.metric("Cobrado",    f"${float(fac_periodo['cobrado'] or 0):,.0f}")
            c4.metric("Por cobrar", f"${float(fac_periodo['por_cobrar'] or 0):,.0f}")

    with col_proximos:
        st.markdown('<p class="seccion-titulo">Contratos próximos a vencer (30 días)</p>', unsafe_allow_html=True)

        if not proximos:
            st.success(":material/check_circle: Sin contratos por vencer en 30 días.")
        else:
            for ctr in proximos[:8]:
                dias = int(ctr['dias_restantes'])
                if dias <= 0:
                    css = "alerta-roja"
                    icono = ":material/error:"
                    txt_dias = "VENCE HOY"
                elif dias <= 3:
                    css = "alerta-roja"
                    icono = ":material/error:"
                    txt_dias = f"{dias}d"
                elif dias <= 7:
                    css = "alerta-naranja"
                    icono = ":material/warning:"
                    txt_dias = f"{dias}d"
                else:
                    css = "alerta-amarilla"
                    icono = ":material/info:"
                    txt_dias = f"{dias}d"

                ff = ctr['fecha_fin']
                st.markdown(f"""
                <div class="{css}">
                    <div style="display:flex;justify-content:space-between;align-items:center">
                        <div>
                            <strong>{icono} {ctr['folio']}</strong>
                            <span style="color:#64748B;font-size:0.85rem">
                                — {ctr['cliente_nombre']}
                            </span><br>
                            <span style="font-size:0.8rem;color:#475569">
                                {ctr.get('obra_nombre') or 'Sin obra'} •
                                ${float(ctr['monto_total']):,.0f}
                            </span>
                        </div>
                        <div style="text-align:right">
                            <strong style="font-size:1.1rem">{txt_dias}</strong><br>
                            <span style="font-size:0.75rem;color:#64748B">
                                {ff.strftime('%d/%m/%Y') if ff else '—'}
                            </span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            if len(proximos) > 8:
                st.caption(f"+ {len(proximos) - 8} contratos más → ve a Renovaciones")

    st.divider()

    # ─── FILA 3: Inventario + Stock crítico + Accesos rápidos ───────────────────
    col_inv, col_stock, col_accesos = st.columns([2, 2, 1])

    with col_inv:
        st.markdown('<p class="seccion-titulo">Estado del inventario</p>', unsafe_allow_html=True)

        disponible    = float(metricas['total_disponible']    or 0)
        rentado       = float(metricas['total_rentado']       or 0)
        mantenimiento = float(metricas['total_mantenimiento'] or 0)
        chatarra      = float(metricas['total_chatarra']      or 0)
        total_general = disponible + rentado + mantenimiento + chatarra

        if total_general > 0:
            fig_pie = go.Figure(go.Pie(
                labels=['Disponible', 'Rentado', 'Mantenimiento', 'Chatarra'],
                values=[disponible, rentado, mantenimiento, chatarra],
                hole=0.55,
                marker_colors=['#64748B', '#94A3B8', '#CBD5E1', '#E2E8F0'],
                textinfo='label+percent',
                textfont_size=11
            ))
            fig_pie.update_layout(
                height=220,
                margin=dict(l=0, r=0, t=10, b=0),
                showlegend=False,
                paper_bgcolor='white'
            )
            st.plotly_chart(fig_pie, use_container_width=True)
            
            # Eficiencia de Cobro
            if float(metricas['facturacion_mes'] or 0) > 0:
                eficiencia = (float(metricas['facturacion_mes'] or 0) - float(metricas['anticipos_pendientes'] or 0)) / float(metricas['facturacion_mes'] or 0) * 100
                st.markdown(f"**:material/target: Eficiencia de Cobro (Mes): {eficiencia:.1f}%**")
                st.progress(eficiencia / 100)

    with col_stock:
        st.markdown('<p class="seccion-titulo">Top 5 Productos Rentados</p>', unsafe_allow_html=True)
        if top_prod:
            df_top = pd.DataFrame(top_prod)
            fig_top = go.Figure(go.Bar(
                x=df_top['cantidad_rentada'],
                y=df_top['codigo'],
                orientation='h',
                marker_color='#64748B'
            ))
            fig_top.update_layout(
                height=220,
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis=dict(title="Unidades en campo"),
                yaxis=dict(autorange="reversed")
            )
            st.plotly_chart(fig_top, use_container_width=True)
        else:
            st.info("No hay productos rentados.")

    with col_accesos:
        st.markdown('<p class="seccion-titulo">Stock Crítico</p>', unsafe_allow_html=True)
        criticos = int(metricas['productos_stock_critico'] or 0)
        if criticos == 0:
            st.success(":material/check_circle: Todo OK")
        else:
            st.warning(f":material/warning: {criticos} bajo mínimo")
            if stock_crit:
                for s in stock_crit[:3]:
                    st.caption(f"**{s['codigo']}**: {int(s['cantidad_disponible'])}/{int(s['stock_minimo'])}")
        st.markdown('<p class="seccion-titulo">Accesos rápidos</p>', unsafe_allow_html=True)
        
        # Obtener rol para filtrar accesos rápidos
        rol = st.session_state.user_info.get('rol', 'operador')
        
        if rol in ['admin', 'ventas', 'operador']:
            st.page_link(pg_cotizaciones, label=":material/add_circle: Nueva cotización")
        
        if rol in ['admin', 'finanzas']:
            st.page_link(pg_contratos, label=":material/description: Nuevo contrato")
        
        if rol in ['admin', 'finanzas', 'logistica', 'operador']:
            st.page_link(pg_hojas_salida, label=":material/local_shipping: Hoja de salida")
            st.page_link(pg_hojas_entrada, label=":material/move_to_inbox: Hoja de entrada")
        
        if rol in ['admin', 'finanzas']:
            st.page_link(pg_renovaciones, label=":material/refresh: Renovaciones")
        
        if rol in ['admin', 'logistica', 'operador']:
            st.page_link(pg_fabricacion, label=":material/build: Fabricación")

# Inicializar Auth
init_auth()

# 3. Preparar páginas
pg_dashboard = st.Page(show_dashboard, title="Dashboard", icon=":material/dashboard:", default=True)

if not st.session_state.authenticated:
    pg = st.navigation([st.Page(login_screen, title="Iniciar Sesión", icon=":material/lock:")])
else:
    with st.sidebar:
        st.markdown(f"### :material/foundation: ERP ICAM")
        st.markdown(f":material/person: **{st.session_state.user_info['nombre']}**")
        st.caption(f"Rol: {st.session_state.user_info['rol'].capitalize()}")
        if st.button(":material/logout: Cerrar Sesión", type="secondary", use_container_width=True):
            logout()
        st.divider()

    # Definir todas las páginas posibles
    # Principal
    sec_principal = [pg_dashboard]
    
    # Ventas y Clientes
    sec_ventas = [pg_clientes, pg_cotizaciones, pg_obras]
    
    # Logística e Inventario
    sec_logistica = [pg_productos, pg_inventario, pg_hojas_salida, pg_hojas_entrada]
    
    # Finanzas
    sec_finanzas = [pg_contratos, pg_renovaciones, pg_anticipos]
    
    # Operaciones
    sec_operaciones = [pg_fabricacion, pg_cambios_of]
    
    # Configuración
    sec_config = [pg_usuarios]

    # Construir mapa de navegación según rol
    rol = st.session_state.user_info.get('rol', 'operador')
    menu = {"Principal": sec_principal}

    if rol == 'admin':
        menu["Ventas y Clientes"] = sec_ventas
        menu["Logística e Inventario"] = sec_logistica
        menu["Finanzas"] = sec_finanzas
        menu["Operaciones"] = sec_operaciones
        menu["Configuración"] = sec_config
        
    elif rol == 'ventas':
        menu["Ventas y Clientes"] = sec_ventas
        
    elif rol == 'finanzas':
        menu["Finanzas"] = sec_finanzas
        menu["Logística e Inventario"] = sec_logistica
        
    elif rol == 'logistica':
        menu["Logística e Inventario"] = sec_logistica
        menu["Operaciones"] = sec_operaciones
        
    elif rol == 'operador':
        # Conservar el comportamiento anterior para 'operador' si existe
        menu["Ventas y Clientes"] = sec_ventas
        menu["Logística e Inventario"] = sec_logistica
        menu["Operaciones"] = sec_operaciones

    pg = st.navigation(menu)

pg.run()