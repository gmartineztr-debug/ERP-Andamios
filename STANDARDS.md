"""
============================================================
GUÍA DE ESTÁNDARES DE CÓDIGO PARA ERP-ANDAMIOS
============================================================

Documento de referencia para mantener consistencia en type hints,
docstrings y mejores prácticas a lo largo del proyecto.
"""

# ================================================================
# 1. TYPE HINTS — ESTÁNDARES OBLIGATORIOS
# ================================================================

"""
✅ OBLIGATORIO: Type hints en TODAS las funciones de utils/db/*.py

Tipos comunes:
  - int, str, bool, float
  - List[Dict], Optional[Dict], Tuple[int, str]
  - Dict[str, Any] para objetos flexibles
  - None explícito para funciones que no retornan

Ejemplos:

    def get_clientes(solo_activos: bool = True) -> List[Dict]:
        ...
    
    def crear_cliente(datos: Dict) -> int:
        ...
    
    def actualizar_cliente(cliente_id: int, datos: Dict) -> None:
        ...
    
    def get_cliente_by_id(cliente_id: int) -> Optional[Dict]:
        ...
    
    def get_cotizacion_detalle(cotizacion_id: int) -> Tuple[Dict, List[Dict]]:
        ...
"""

# ================================================================
# 2. DOCSTRINGS — FORMATO GOOGLE STYLE
# ================================================================

"""
✅ REQUERIDO: Docstring en formato Google para TODAS las funciones

Estructura obligatoria:
  1. Una línea de descripción concisa
  2. (Opcional) Párrafo más largo si es complejo
  3. Args: Parámetros y tipos
  4. Returns: Qué retorna la función
  5. Raises: Excepciones posibles

Ejemplo modelo:

    def crear_cotizacion(datos: Dict, items: List[Dict]) -> int:
        \"\"\"
        Crea una cotización con sus líneas de detalle.
        
        Realiza validación de montos y genera folio automático.
        
        Args:
            datos: Diccionario con claves:
                - cliente_id (int): ID del cliente
                - tipo_operacion (str): 'renta', 'venta' o 'armado'
                - subtotal (float): Monto sin IVA
                - total (float): Monto final con IVA
                - dias_renta (int): Plazo de renta
            items: Lista de diccionarios con:
                - producto_id (int)
                - cantidad (float)
                - precio_unitario (float)
                
        Returns:
            int: ID de la cotización creada
            
        Raises:
            ValueError: Si montos son inválidos
            DatabaseError: Si falla la inserción en BD
        \"\"\"
        ...
"""

# ================================================================
# 3. PATRONES COMUNES POR TIPO DE FUNCIÓN
# ================================================================

"""
Patrón: GET (Lectura)
  def get_xxx(filtro=None) -> List[Dict]:
      \"\"\"Obtiene registros...\"\"\"
      
Patrón: GET BY ID
  def get_xxx_by_id(id: int) -> Optional[Dict]:
      \"\"\"Obtiene un registro específico...\"\"\"
      
Patrón: CREATE (Creación)
  def crear_xxx(datos: Dict) -> int:
      \"\"\"Crea un nuevo registro...
      
      Returns:
          int: ID del registro creado
      \"\"\"
      
Patrón: UPDATE (Actualización)
  def actualizar_xxx(id: int, datos: Dict) -> None:
      \"\"\"Actualiza un registro...\"\"\"
      
Patrón: DELETE (Eliminación)
  def eliminar_xxx(id: int) -> bool:
      \"\"\"Elimina un registro...
      
      Returns:
          bool: True si la eliminación fue exitosa
      \"\"\"
      
Patrón: GENERAR FOLIO
  def generar_folio_xxx() -> str:
      \"\"\"Genera el siguiente folio...\"\"\"
"""

# ================================================================
# 4. VALIDACIONES Y MANEJO DE ERRORES
# ================================================================

"""
✅ SIEMPRE usar context manager get_cursor() con try-except:

    def crear_contrato(datos: Dict, items: List[Dict]) -> int:
        \"\"\"Crea un contrato...\"\"\"
        try:
            with get_cursor() as (cur, conn):
                cur.execute(...)
                nuevo_id = cur.fetchone()['id']
                conn.commit()
                return nuevo_id
        except psycopg2.IntegrityError as e:
            logger.error(f"RFC duplicado: {e}")
            raise ValueError(f"Datos duplicados: {e}")
        except psycopg2.DatabaseError as e:
            logger.error(f"Error BD: {e}")
            raise DatabaseError(f"Error de base de datos: {e}")
"""

# ================================================================
# 5. IMPORTS OBLIGATORIOS EN CADA MÓDULO DB
# ================================================================

"""
✅ Header de todo archivo utils/db/*.py:

    from datetime import date, datetime
    from typing import List, Dict, Optional, Tuple, Any
    from .connection import get_cursor
    import psycopg2
    from utils.logger import logger
    
    # Optional, solo si se necesita:
    # import streamlit as st
"""

# ================================================================
# 6. LOGGING — REQUERIDO PARA OPERACIONES CRÍTICAS
# ================================================================

"""
✅ Log estas operaciones:

    # Al crear
    logger.info(f"CREAR: {tabla} | usuario_id={usuario_id}")
    
    # Al actualizar
    logger.info(f"ACTUALIZAR: {tabla}#{id} | campos={list(datos.keys())}")
    
    # Al eliminar
    logger.warning(f"ELIMINAR: {tabla}#{id} | usuario_id={usuario_id}")
    
    # Errores
    logger.error(f"Error en {func_name}: {exception}", exc_info=True)
"""

# ================================================================
# 7. CHECKLIST DE REVISIÓN
# ================================================================

"""
Para cada función, verificar:

  ☐ Type hints en parámetros
  ☐ Return type explícito
  ☐ Docstring en formato Google
  ☐ Descripción clara en una línea
  ☐ Args documenta tipos y propósito
  ☐ Returns documenta el tipo y qué representa
  ☐ Raises lista excepciones posibles
  ☐ Usa context manager get_cursor()
  ☐ Logging para errores y operaciones críticas
  ☐ SQL usa parámetros bindrados (%s, not f-strings)
  ☐ Manejo explícito de None vs empty list
  ☐ Retorna valores consistentes
"""

# ================================================================
# 8. EJEMPLOS REALES COMPLETOS
# ================================================================

"""
EJEMPLO 1: Función simple de lectura

    def get_contratos_por_vencer(dias: int = 30) -> List[Dict]:
        \"\"\"
        Obtiene contratos que vencen en los próximos N días.
        
        Args:
            dias: Número de días para búsqueda (default 30)
            
        Returns:
            list[dict]: Contratos por vencer con campos:
               - id, folio, cliente_nombre, fecha_fin, monto_total
               
        Raises:
            DatabaseError: Si falla la conexión
        \"\"\"
        try:
            with get_cursor() as (cur, conn):
                cur.execute('''
                    SELECT * FROM ops_contratos
                    WHERE estatus = 'activo'
                    AND fecha_fin <= NOW() + INTERVAL '%s days'
                    AND fecha_fin > NOW()
                    ORDER BY fecha_fin ASC
                ''', (dias,))
                return cur.fetchall() or []
        except psycopg2.DatabaseError as e:
            logger.error(f"Error obteniendo contratos: {e}")
            raise

---

EJEMPLO 2: Función con creación y logging

    def crear_contrato(datos: Dict, items: List[Dict]) -> int:
        \"\"\"
        Crea un nuevo contrato con sus líneas.
        
        Args:
            datos: Diccionario con:
                - cotizacion_id, cliente_id, monto_total,
                - fecha_inicio, fecha_fin, tipo_contrato
            items: Lista de productos con cantidad y precio
            
        Returns:
            int: ID del contrato creado
            
        Raises:
            ValueError: Si datos requeridos faltan
            DatabaseError: Si falla la inserción
        \"\"\"
        if not datos.get('cliente_id') or not datos.get('monto_total'):
            raise ValueError("cliente_id y monto_total son requeridos")
            
        try:
            with get_cursor() as (cur, conn):
                # Insertar contrato principal
                cur.execute('''
                    INSERT INTO ops_contratos
                    (folio, cliente_id, monto_total, fecha_inicio, 
                     fecha_fin, tipo_contrato, estatus)
                    VALUES (%s, %s, %s, %s, %s, %s, 'activo')
                    RETURNING id
                ''', (
                    datos['folio'], datos['cliente_id'],
                    datos['monto_total'], datos['fecha_inicio'],
                    datos['fecha_fin'], datos['tipo_contrato']
                ))
                contrato_id = cur.fetchone()['id']
                
                # Insertar líneas
                for item in items:
                    cur.execute('''
                        INSERT INTO ops_contrato_items
                        (contrato_id, producto_id, cantidad, precio)
                        VALUES (%s, %s, %s, %s)
                    ''', (contrato_id, item['producto_id'],
                          item['cantidad'], item['precio']))
                
                conn.commit()
                logger.info(f"CREAR_CONTRATO: {datos['folio']} | cliente_id={datos['cliente_id']}")
                return contrato_id
                
        except psycopg2.IntegrityError as e:
            logger.warning(f"Violación de constraint: {e}")
            raise ValueError(f"Datos duplicados o inválidos: {e}")
        except psycopg2.DatabaseError as e:
            logger.error(f"Error creando contrato: {e}", exc_info=True)
            raise
"""

# ================================================================
# 9. PLAN DE IMPLEMENTACIÓN INCREMENTAL
# ================================================================

"""
Aplicar mejoras en orden de criticidad:

FASE 1 (INMEDIATA):
  ✅ auth.py (ya completado)
  ○ crm.py — funciones principales (get, crear, actualizar)
  ○ operaciones.py — contratos (crear, actualizar, renovar)
  ○ finanzas.py — anticipos

FASE 2 (ESTA SEMANA):
  ○ logistica.py (hojas entrada/salida)
  ○ fabricacion.py (órdenes)
  ○ inventario.py (control stock)

FASE 3 (LA PRÓXIMA SEMANA):
  ○ productos.py
  ○ dashboard.py
  ○ connection.py

Tiempo estimado: 4-6 horas de refactorización manual
Alternativa: Usar Pylance o similar para auto-generation parcial
"""
