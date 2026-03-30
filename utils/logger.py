"""
Logging centralizado para auditoría y debugging.
Registra todas las operaciones críticas del sistema.
"""

import logging
import logging.handlers
from pathlib import Path
from datetime import datetime
import streamlit as st

# Crear directorio de logs si no existe
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# Configurar logger
logger = logging.getLogger("erp_andamios")
logger.setLevel(logging.DEBUG)

# Handler: Archivo rotativo (máx 5MB, 10 archivos)
file_handler = logging.handlers.RotatingFileHandler(
    filename=LOG_DIR / "erp.log",
    maxBytes=5_000_000,  # 5MB
    backupCount=10
)
file_handler.setLevel(logging.DEBUG)

# Handler: Errores en archivo separado
error_handler = logging.handlers.RotatingFileHandler(
    filename=LOG_DIR / "erp_errors.log",
    maxBytes=5_000_000,
    backupCount=5
)
error_handler.setLevel(logging.ERROR)

# Formato
formatter = logging.Formatter(
    '%(asctime)s — [%(levelname)s] — %(name)s — %(funcName)s:%(lineno)d — %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler.setFormatter(formatter)
error_handler.setFormatter(formatter)

# Agregar handlers
logger.addHandler(file_handler)
logger.addHandler(error_handler)


def log_action(usuario: str, accion: str, entidad: str, entidad_id: int, detalles: str = ""):
    """
    Registra una acción en el sistema (CREATE, UPDATE, DELETE).
    
    Args:
        usuario: Username del usuario que realiza la acción
        accion: CREATE, UPDATE, DELETE, CANCEL, APPROVE
        entidad: Tipo de entidad (Cliente, Contrato, Cotización, etc.)
        entidad_id: ID de la entidad
        detalles: Info adicional (campos cambiados, motivos, etc.)
    """
    mensaje = f"[{accion}] {usuario} → {entidad}#{entidad_id}"
    if detalles:
        mensaje += f" | {detalles}"
    logger.info(mensaje)


def log_error(error: Exception, contexto: str = ""):
    """
    Registra un error en el sistema.
    
    Args:
        error: Exception capturada
        contexto: Información adicional del contexto donde ocurrió
    """
    if contexto:
        logger.error(f"[{contexto}] {type(error).__name__}: {str(error)}", exc_info=True)
    else:
        logger.error(f"{type(error).__name__}: {str(error)}", exc_info=True)


def log_login(usuario: str, exitoso: bool, ip: str = "unknown"):
    """Registra intentos de login"""
    estado = "LOGIN_EXITOSO" if exitoso else "LOGIN_FALLIDO"
    logger.info(f"{estado} — {usuario} desde {ip}")


def log_database_error(query: str, error: Exception):
    """Registra errores de base de datos"""
    logger.error(f"Database Error en query: {query[:100]}... — {str(error)}")


def get_logger():
    """Retorna el logger configurado"""
    return logger
