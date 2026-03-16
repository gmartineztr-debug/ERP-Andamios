"""
Facade for the database layer.
Directs all calls to the modularized 'utils.db' implementation.
Maintains backward compatibility for existing imports in 'pages/*.py'.
"""

from .db.connection import get_connection, get_cursor
from .db.crm import (
    get_clientes, get_cliente_by_id, crear_cliente, actualizar_cliente,
    generar_folio_obra, crear_obra, get_obras, get_obra_by_id,
    actualizar_estatus_obra, get_contratos_por_obra, actualizar_total_facturado_obra,
    get_obras_por_cliente, generar_folio_cotizacion, crear_cotizacion,
    get_cotizaciones, get_cotizacion_detalle, actualizar_estatus_cotizacion,
    get_cotizaciones_aprobadas
)
from .db.productos import (
    get_productos, get_producto_by_id, crear_producto, actualizar_producto,
    get_productos_por_codigo
)
from .db.inventario import (
    get_bitacora, get_bitacora_producto, registrar_ajuste_manual,
    generar_folio_conteo, crear_conteo, get_conteos, get_conteo_items,
    actualizar_conteo_item, aplicar_ajuste_conteo
)
from .db.operaciones import (
    generar_folio_contrato, crear_contrato, get_contratos, get_contrato_detalle,
    actualizar_estatus_contrato, registrar_anticipo_pago, asignar_obra_contrato,
    crear_contrato_item, get_contratos_por_vencer, get_cadena_renovaciones,
    renovar_contrato, get_estado_cuenta_folio_raiz, get_resumen_folio_raiz,
    get_folios_raiz_cliente, get_todos_folios_raiz
)
from .db.logistica import (
    generar_folio_salida, get_contratos_sin_hs_completa, get_cantidad_enviada_por_contrato,
    crear_hoja_salida, get_hojas_salida, get_hoja_salida_detalle,
    actualizar_estatus_salida, get_proveedores, crear_proveedor,
    generar_folio_entrada, get_saldo_en_campo, get_contratos_con_equipo_en_campo,
    crear_hoja_entrada, get_hojas_entrada, get_hoja_entrada_detalle,
    actualizar_estatus_entrada, vincular_contrato_venta_entrada
)
from .db.fabricacion import (
    get_insumos, crear_insumo, get_bom_producto, guardar_bom_producto,
    calcular_materiales_of, generar_folio_of, crear_orden_fabricacion,
    get_ordenes_fabricacion, get_orden_fabricacion_detalle, actualizar_estatus_of,
    get_ordenes_terminadas_sin_he, generar_folio_oc, crear_orden_compra,
    get_ordenes_compra, get_orden_compra_detalle, actualizar_estatus_oc,
    generar_folio_sc, crear_sc, get_solicitudes_cambio, get_sc_detalle,
    actualizar_estatus_sc, get_of_detalle
)
from .db.finanzas import (
    generar_folio_anticipo, crear_anticipo, get_anticipos, get_pagos_por_contrato,
    get_contratos_con_saldo, actualizar_estatus_anticipo
)
from .db.dashboard import (
    get_dashboard_metricas, get_facturacion_mensual, get_stock_critico,
    get_contratos_proximos, get_facturacion_periodo, get_top_productos
)
from .db.auth import (
    create_auth_table_if_not_exists, get_usuario_por_username,
    crear_usuario_inicial, validar_credenciales,
    get_usuarios, crear_usuario, actualizar_rol_usuario
)