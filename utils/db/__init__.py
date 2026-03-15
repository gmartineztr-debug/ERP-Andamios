```python
"""
Database module re-exports.
This allows accessing all database functions from 'utils.db'.
"""

from .connection import get_connection, get_cursor
from .crm import *
from .productos import *
from .inventario import *
from .operaciones import *
from .logistica import *
from .fabricacion import *
from .finanzas import *
from .dashboard import *

def get_dashboard_metricas():
    """Métricas principales del dashboard"""
    with get_cursor() as (cur, conn):
        cur.execute("SELECT * FROM v_dashboard_metricas")
        res = cur.fetchone()
        return res if res is not None else {}

def get_contratos_activos():
    """Obtiene contratos activos"""
    with get_cursor() as (cur, conn):
        cur.execute("""
            SELECT
                ct.id,
                ct.cliente_id,
                cl.nombre AS cliente_nombre,
                ct.tipo_contrato,
                ct.fecha_inicio,
                ct.fecha_fin,
                ct.monto,
                ct.estatus
            FROM contratos ct
            JOIN clientes cl ON ct.cliente_id = cl.id
            WHERE ct.estatus = 'activo'
            ORDER BY ct.fecha_inicio ASC
        """)
        res = cur.fetchall()
        return res if res is not None else []
```
