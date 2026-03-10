# main.py
# Dashboard principal ICAM ERP

import streamlit as st
from utils.database import get_clientes, get_productos

st.set_page_config(
    page_title="ANDAMIOS ERP",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .metric-card {
        background: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        text-align: center;
    }
    .metric-number {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
    }
    .metric-label {
        color: #666;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

st.title("🏗️ ICAM ERP")
st.caption("Sistema de gestión para renta y venta de andamios")
st.divider()

clientes = get_clientes()
productos = get_productos()

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("👥 Clientes activos", len(clientes))
with col2:
    st.metric("📦 Productos", len(productos))
with col3:
    st.metric("📋 Contratos activos", "—")
with col4:
    st.metric("💰 Facturación del mes", "—")

st.divider()
st.subheader("Módulos del sistema")

col1, col2, col3 = st.columns(3)

with col1:
    st.info("👥 **Clientes**\n\nGestión de clientes y contactos")
with col2:
    st.info("📦 **Productos**\n\nCatálogo e inventario")
with col3:
    st.warning("📋 **Cotizaciones**\n\nEn desarrollo...")