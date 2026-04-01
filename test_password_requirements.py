#!/usr/bin/env python3
"""
Demostración de requisitos de contraseña del sistema ERP
"""

from utils.validators import get_password_requirements

print("=" * 60)
print("REQUISITOS DE CONTRASEÑA — ERP ANDAMIOS")
print("=" * 60)

reqs = get_password_requirements()

print(f"\n⚙️ Mínimo: {reqs['minimo']} caracteres\n")

print("📋 Requisitos obligatorios:")
for req in reqs['requisitos']:
    print(f"   {req}")

print(f"\n🔤 Caracteres especiales permitidos:")
print(f"   {reqs['especiales_permitidos']}")

print("\n" + "=" * 60)
print("EJEMPLOS DE CONTRASEÑAS VÁLIDAS:")
print("=" * 60)

ejemplos_validas = [
    "Admin@2026",
    "Segura$123",
    "MiPassword#2026",
    "Temporal!2025"
]

for pwd in ejemplos_validas:
    print(f"✅ {pwd}")

print("\n" + "=" * 60)
print("EJEMPLOS DE CONTRASEÑAS INVÁLIDAS:")
print("=" * 60)

ejemplos_invalidas = [
    ("password123", "Sin mayúsculas ni caracteres especiales"),
    ("PASSWORD123", "Sin minúsculas ni caracteres especiales"),
    ("Contraseña", "Sin números ni caracteres especiales"),
    ("Pass@word", "8 caracteres exactos (válida), pero solo 8"),
    ("Pass123", "Solo 7 caracteres"),
]

for pwd, razon in ejemplos_invalidas:
    print(f"❌ {pwd:20} — {razon}")

print("\n" + "=" * 60)
