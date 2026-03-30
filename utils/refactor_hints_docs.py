"""
Script para agregar type hints y docstrings automáticamente a utils/db/*.py
Ejecutar: python -m utils.refactor_hints_docs
"""

import re
import os
from pathlib import Path
from typing import List, Tuple

# Template de docstring profesional
DOCSTRING_TEMPLATE = '''    """
    {description}
    
    Args:
{args}
        
    Returns:
        {return_type}: {return_desc}
        
    Raises:
        DatabaseError: Si hay error en la conexión o ejecución de query
    """'''

# Mapeos de tipos para funciones comunes
COMMON_PATTERNS = {
    'get_': ('dict | None | list[dict]', 'Datos obtenidos de la Base de Datos'),
    'crear_': ('int', 'ID del registro creado'),
    'actualizar_': ('bool', 'True si la actualización fue exitosa'),
    'eliminar_': ('bool', 'True si la eliminación fue exitosa'),
}

def add_type_hints_to_file(filepath: str) -> int:
    """
    Agrega type hints y docstrings mejorados a un archivo.
    
    Args:
        filepath: Ruta del archivo Python
        
    Returns:
        Número de funciones actualizadas
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Patrón para encontrar funciones
    func_pattern = r'def (\w+)\(([^)]*)\):'
    
    # No aplicar cambios aún - solo reportar lo que se haría
    matches = re.finditer(func_pattern, content)
    count = 0
    
    for match in matches:
        func_name = match.group(1)
        params = match.group(2)
        
        # Saltar si ya tiene tipos
        if '->' in params:
            continue
            
        count += 1
        print(f"  📝 {func_name}({params})")
    
    return count

def main():
    """Ejecuta refactorización en todos los módulos de utils/db/"""
    db_dir = Path('utils/db')
    
    if not db_dir.exists():
        print("❌ No se encontró directorio utils/db/")
        return
    
    print("\n🔍 Archivos que serían actualizados:\n")
    
    total = 0
    for py_file in sorted(db_dir.glob('*.py')):
        if py_file.name.startswith('__'):
            continue
            
        print(f"📄 {py_file.name}")
        count = add_type_hints_to_file(str(py_file))
        print(f"   → {count} funciones requerirían mejoras\n")
        total += count
    
    print(f"\n✅ Total de funciones que podrían mejorarse: {total}")
    print("\n💡 Recomendación: Ver los cambios propuestos manualmente")
    print("   y aplicar mediante find-replace en VS Code o editor.")
    print("\n📚 Ejemplo de mejora requerida:")
    print("""
    # ANTES:
    def get_clientes(solo_activos=True):
        \"\"\"Retorna lista de clientes\"\"\"
    
    # DESPUÉS:
    def get_clientes(solo_activos: bool = True) -> list[dict]:
        \"\"\"
        Obtiene todos los clientes del sistema.
        
        Args:
            solo_activos: Si True, retorna solo clientes con activo=True.
            
        Returns:
            list[dict]: Lista de diccionarios con datos de clientes.
            
        Raises:
            DatabaseError: Si falla la conexión a la base de datos.
        \"\"\"
    """)

if __name__ == '__main__':
    main()
