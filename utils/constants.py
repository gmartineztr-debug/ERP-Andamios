"""
Centralized constants for the ERP system.
Includes status labels, color mappings, and common categories.
"""

# ================================================
# ESTATUS Y COLORES
# ================================================

# Cotizaciones
ESTATUS_COTIZACION = {
    'borrador': '📝 Borrador',
    'enviada': '📩 Enviada',
    'aprobada': '✅ Aprobada',
    'rechazada': '❌ Rechazada',
    'vencida': '⏰ Vencida',
    'en_revision': '🔍 En Revisión'
}

COLOR_COTIZACION = {
    'borrador': 'gray',
    'enviada': 'blue',
    'aprobada': 'green',
    'rechazada': 'red',
    'vencida': 'orange',
    'en_revision': 'violet'
}

# Obras
ESTATUS_OBRA = {
    'planeacion': '📋 Planeación',
    'activo': '🟢 Activo',
    'pausado': '🟡 Pausado',
    'terminado': '🏁 Terminado',
    'cancelado': '❌ Cancelado'
}

COLOR_OBRA = {
    'planeacion': 'gray',
    'activo': 'green',
    'pausado': 'orange',
    'terminado': 'blue',
    'cancelado': 'red'
}

# Contratos
ESTATUS_CONTRATO = {
    'activo': '🟢 Activo',
    'finalizado': '🏁 Finalizado',
    'cancelado': '🚫 Cancelado',
    'vencido': '⏰ Vencido',
    'renovado': '🔄 Renovado'
}

COLOR_CONTRATO = {
    'activo': 'green',
    'finalizado': 'blue',
    'cancelado': 'red',
    'vencido': 'orange',
    'renovado': 'violet'
}

# Órdenes de Fabricación
ESTATUS_OF = {
    'pendiente': '🟡 Pendiente',
    'en_proceso': '⚙️ En Proceso',
    'terminada': '✅ Terminada',
    'cancelada': '❌ Cancelada'
}

COLOR_OF = {
    'pendiente': 'orange',
    'en_proceso': 'blue',
    'terminada': 'green',
    'cancelada': 'red'
}

# Hojas de Salida / Entrada
ESTATUS_LOGISTICA = {
    'borrador': '📝 Borrador',
    'confirmado': '✅ Confirmado',
    'cancelado': '❌ Cancelado'
}

COLOR_LOGISTICA = {
    'borrador': 'gray',
    'confirmado': 'green',
    'cancelado': 'red'
}

# Anticipos / Pagos
ESTATUS_PAGO = {
    'pendiente': '🟡 Pendiente',
    'verificado': '✅ Verificado',
    'rechazado': '❌ Rechazada'
}

COLOR_PAGO = {
    'pendiente': 'orange',
    'verificado': 'green',
    'rechazado': 'red'
}

# ================================================
# CATEGORÍAS Y TIPOS
# ================================================

TIPOS_PAGO = {
    'anticipo': '💳 Anticipo inicial',
    'renta': '📦 Pago de renta',
    'venta': '💰 Pago de venta',
    'extra': '➕ Cargo extra'
}

TIPOS_ENTRADA = {
    'devolucion': '↩️ Devolución de renta',
    'compra': '📦 Compra de insumos',
    'ajuste': '⚙️ Ajuste de inventario'
}

UNIDADES_MEDIDA = ['PZA', 'ML', 'M2', 'JGO', 'KIT', 'KG', 'TON']

CATEGORIAS_PRODUCTO = [
    'Andamiaje',
    'Accesorios',
    'Maquinaria',
    'Consumibles',
    'Servicios',
    'Estructuras'
]
