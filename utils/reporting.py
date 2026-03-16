import pandas as pd
import io
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from datetime import datetime

def export_to_csv(df):
    """Convierte un DataFrame a CSV para descarga (Excel compatible)"""
    if df.empty:
        return None
    
    # Usar separador punto y coma para mejor compatibilidad con Excel en español
    output = io.StringIO()
    df.to_csv(output, index=False, sep=';', encoding='utf-8-sig')
    return output.getvalue().encode('utf-8-sig')

def export_to_pdf(df, title="Reporte ERP"):
    """Genera un archivo PDF a partir de un DataFrame usando ReportLab"""
    if df.empty:
        return None

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    
    styles = getSampleStyleSheet()
    
    # Título
    elements.append(Paragraph(title, styles['Title']))
    elements.append(Paragraph(f"Fecha de generación: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
    elements.append(Spacer(1, 12))
    
    # Preparar datos para la tabla
    # Limitar columnas si son demasiadas para que quepan en una página
    max_cols = 8
    df_plot = df.iloc[:, :max_cols] if len(df.columns) > max_cols else df
    
    data = [df_plot.columns.tolist()] + df_plot.values.tolist()
    
    # Crear Tabla
    # Calcular anchos de columna relativos (simplificado)
    t = Table(data)
    
    # Estilos de la Tabla
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
    ])
    t.setStyle(style)
    
    elements.append(t)
    doc.build(elements)
    
    pdf = buffer.getvalue()
    buffer.close()
    return pdf
