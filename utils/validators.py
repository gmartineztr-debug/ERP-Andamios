"""
Esquemas de validación centralizados con Pydantic.
Define la estructura y validación de datos para todas las entidades del ERP.
"""

from pydantic import BaseModel, EmailStr, field_validator, Field
from typing import Optional
from datetime import date, datetime


# ================================================
# CLIENTES
# ================================================

class ClienteBase(BaseModel):
    """Datos comunes de cliente"""
    razon_social: str = Field(..., min_length=3, max_length=255)
    rfc: str = Field(..., min_length=12, max_length=13)
    contacto: Optional[str] = Field(None, max_length=100)
    telefono: Optional[str] = Field(None, max_length=20)
    email: Optional[EmailStr] = None
    direccion: Optional[str] = Field(None, max_length=500)
    tipo_cliente: str = Field(default="general")
    limite_credito: float = Field(default=0.0, ge=0)
    
    @field_validator('rfc')
    @classmethod
    def validar_rfc(cls, v: str) -> str:
        """Valida que RFC tenga largo correcto"""
        if len(v) not in [12, 13]:
            raise ValueError('RFC debe tener 12 o 13 caracteres')
        return v.upper()
    
    @field_validator('telefono')
    @classmethod
    def validar_telefono(cls, v: Optional[str]) -> Optional[str]:
        """Valida formato de teléfono"""
        if v and not v.replace('-', '').replace(' ', '').isdigit():
            raise ValueError('Teléfono debe contener solo dígitos, espacios y guiones')
        return v
    
    model_config = {"str_strip_whitespace": True}


class ClienteCreate(ClienteBase):
    """Para crear cliente"""
    pass


class ClienteUpdate(ClienteBase):
    """Para actualizar cliente (todos opcionales excepto RFC)"""
    rfc: str = Field(min_length=12, max_length=13)


# ================================================
# PRODUCTOS
# ================================================

class ProductoBase(BaseModel):
    """Datos comunes de producto"""
    codigo: str = Field(..., min_length=1, max_length=50)
    nombre: str = Field(..., min_length=3, max_length=255)
    descripcion: Optional[str] = Field(None, max_length=1000)
    categoria: str = Field(default="general")
    precio_unitario: float = Field(ge=0)
    peso_kg: Optional[float] = Field(None, ge=0)
    activo: bool = Field(default=True)
    
    @field_validator('codigo')
    @classmethod
    def validar_codigo(cls, v: str) -> str:
        """Valida que código no tenga caracteres especiales"""
        if not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError('Código solo puede contener letras, números, guiones y guiones bajos')
        return v.upper()


class ProductoCreate(ProductoBase):
    pass


class ProductoUpdate(ProductoBase):
    codigo: str = Field(min_length=1, max_length=50)


# ================================================
# COTIZACIONES
# ================================================

class CotizacionItemBase(BaseModel):
    """Item de cotización"""
    producto_id: int = Field(gt=0)
    cantidad: float = Field(gt=0)
    precio_unitario: float = Field(ge=0)
    subtotal: float = Field(ge=0)


class CotizacionBase(BaseModel):
    """Datos comunes de cotización"""
    cliente_id: int = Field(gt=0)
    obra_id: Optional[int] = Field(None, gt=0)
    tipo_operacion: str = Field(default="renta")  # renta, venta, armado
    tipo_flete: str = Field(default="sin_flete")
    distancia_km: float = Field(default=0, ge=0)
    tarifa_flete: float = Field(default=0, ge=0)
    monto_flete: float = Field(default=0, ge=0)
    subtotal: float = Field(ge=0)
    aplica_iva: bool = Field(default=True)
    iva: float = Field(default=0, ge=0)
    total: float = Field(gt=0)
    dias_renta: int = Field(default=1, gt=0)
    notas: Optional[str] = Field(None, max_length=2000)
    estatus: str = Field(default="borrador")  # borrador, aprobada, rechazada
    
    @field_validator('tipo_operacion')
    @classmethod
    def validar_tipo(cls, v: str) -> str:
        if v not in ['renta', 'venta', 'armado']:
            raise ValueError('Tipo debe ser renta, venta o armado')
        return v


class CotizacionCreate(CotizacionBase):
    items: list[CotizacionItemBase] = Field(min_items=1)


# ================================================
# CONTRATOS
# ================================================

class ContratoBase(BaseModel):
    """Datos comunes de contrato"""
    cotizacion_id: int = Field(gt=0)
    obra_id: Optional[int] = Field(None, gt=0)
    cliente_id: int = Field(gt=0)
    tipo_contrato: str = Field(default="renta")  # renta, venta, armado
    fecha_inicio: date
    fecha_fin: date
    dias_renta: int = Field(gt=0)
    monto_total: float = Field(gt=0)
    anticipo_porcentaje: int = Field(default=50, ge=10, le=100)
    anticipo_requerido: float = Field(ge=0)
    anticipo_pagado: float = Field(default=0, ge=0)
    anticipo_referencia: Optional[str] = Field(None, max_length=100)
    anticipo_estatus: str = Field(default="pendiente")  # pendiente, parcial, completo
    pagare_numero: Optional[str] = Field(None, max_length=50)
    pagare_monto: float = Field(ge=0)
    pagare_firmante: Optional[str] = Field(None, max_length=100)
    pagare_fecha_vencimiento: Optional[date] = None
    pagare_firmado: bool = Field(default=False)
    notas: Optional[str] = Field(None, max_length=2000)
    
    @field_validator('fecha_fin')
    @classmethod
    def validar_fechas(cls, v: date, info):
        """Valida que fecha_fin sea posterior a fecha_inicio"""
        if 'fecha_inicio' in info.data and v <= info.data['fecha_inicio']:
            raise ValueError('Fecha fin debe ser posterior a fecha inicio')
        return v
    
    @field_validator('anticipo_pagado')
    @classmethod
    def validar_anticipo(cls, v: float, info):
        """Valida que anticipo no exceda total"""
        if 'monto_total' in info.data and v > info.data['monto_total']:
            raise ValueError('Anticipo no puede ser mayor que el total')
        return v


class ContratoCreate(ContratoBase):
    pass


# ================================================
# USUARIOS
# ================================================

class UsuarioBase(BaseModel):
    """Datos comunes de usuario"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    rol: str = Field(default="usuario")  # admin, ventas, logistica, usuario
    activo: bool = Field(default=True)
    
    @field_validator('username')
    @classmethod
    def validar_username(cls, v: str) -> str:
        """Valida que username sea alfanumérico"""
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Username solo puede contener letras, números, guiones y guiones bajos')
        return v.lower()
    
    @field_validator('rol')
    @classmethod
    def validar_rol(cls, v: str) -> str:
        roles_validos = ['admin', 'ventas', 'logistica', 'usuario', 'gerencia', 'fabricacion']
        if v.lower() not in roles_validos:
            raise ValueError(f'Rol debe ser uno de: {", ".join(roles_validos)}')
        return v.lower()


class UsuarioCreate(UsuarioBase):
    password: str = Field(..., min_length=8)
    
    @field_validator('password')
    @classmethod
    def validar_password(cls, v: str) -> str:
        """Valida que la contraseña cumpla requisitos de seguridad"""
        errores = []
        
        if len(v) < 8:
            errores.append("mínimo 8 caracteres")
        if not any(c.isupper() for c in v):
            errores.append("al menos 1 mayúscula")
        if not any(c.islower() for c in v):
            errores.append("al menos 1 minúscula")
        if not any(c.isdigit() for c in v):
            errores.append("al menos 1 número")
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v):
            errores.append("al menos 1 carácter especial: !@#$%^&*()_+-=[]{}|;:,.<>?")
        
        if errores:
            raise ValueError(f"Contraseña debe tener: {', '.join(errores)}")
        return v


class UsuarioUpdate(BaseModel):
    """Para actualizar usuario (sin password)"""
    email: Optional[EmailStr] = None
    rol: Optional[str] = None
    activo: Optional[bool] = None


# ================================================
# CONTRASEÑA
# ================================================

class PasswordChange(BaseModel):
    """Esquema para cambiar contraseña"""
    password_actual: str = Field(..., min_length=1)
    password_nueva: str = Field(..., min_length=8)
    
    @field_validator('password_nueva')
    @classmethod
    def validar_password_nueva(cls, v: str) -> str:
        """Valida que la nueva contraseña cumpla requisitos de seguridad"""
        errores = []
        
        if len(v) < 8:
            errores.append("mínimo 8 caracteres")
        if not any(c.isupper() for c in v):
            errores.append("al menos 1 mayúscula")
        if not any(c.islower() for c in v):
            errores.append("al menos 1 minúscula")
        if not any(c.isdigit() for c in v):
            errores.append("al menos 1 número")
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v):
            errores.append("al menos 1 carácter especial: !@#$%^&*()_+-=[]{}|;:,.<>?")
        
        if errores:
            raise ValueError(f"Contraseña debe tener: {', '.join(errores)}")
        return v


class PasswordReset(BaseModel):
    """Esquema para resetear contraseña (admin only)"""
    password_nueva: str = Field(..., min_length=8)
    
    @field_validator('password_nueva')
    @classmethod
    def validar_password(cls, v: str) -> str:
        """Valida que la contraseña cumpla requisitos de seguridad"""
        errores = []
        
        if len(v) < 8:
            errores.append("mínimo 8 caracteres")
        if not any(c.isupper() for c in v):
            errores.append("al menos 1 mayúscula")
        if not any(c.islower() for c in v):
            errores.append("al menos 1 minúscula")
        if not any(c.isdigit() for c in v):
            errores.append("al menos 1 número")
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v):
            errores.append("al menos 1 carácter especial: !@#$%^&*()_+-=[]{}|;:,.<>?")
        
        if errores:
            raise ValueError(f"Contraseña debe tener: {', '.join(errores)}")
        return v


def get_password_requirements() -> dict:
    """
    Retorna los requisitos de contraseña en formato amigable.
    Útil para mostrar en UI.
    """
    return {
        "minimo": 8,
        "requisitos": [
            "✓ Mínimo 8 caracteres",
            "✓ Al menos 1 mayúscula (A-Z)",
            "✓ Al menos 1 minúscula (a-z)",
            "✓ Al menos 1 número (0-9)",
            "✓ Al menos 1 carácter especial: !@#$%^&*()"
        ],
        "especiales_permitidos": "!@#$%^&*()_+-=[]{}|;:,.<>?"
    }
