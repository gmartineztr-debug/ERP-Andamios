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

def generate_monthly_report(metrics, top_products, stock_critico):
    """Genera un PDF consolidado de Corte Mensual"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    
    # Header
    elements.append(Paragraph("📊 Reporte de Corte Mensual - ERP", styles['Title']))
    elements.append(Paragraph(f"Generado el: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
    elements.append(Spacer(1, 20))
    
    # Financial Summary
    elements.append(Paragraph("💰 Resumen Financiero", styles['Heading2']))
    fin_data = [
        ["Concepto", "Valor"],
        ["Facturación Mensual", f"${float(metrics['facturacion_mes'] or 0):,.2f}"],
        ["Anticipos Pendientes", f"${float(metrics['anticipos_pendientes'] or 0):,.2f}"],
        ["Contratos Activos", str(metrics['contratos_activos'])]
    ]
    t_fin = Table(fin_data, colWidths=[200, 200])
    t_fin.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.darkblue),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('PADDING', (0,0), (-1,-1), 6)
    ]))
    elements.append(t_fin)
    elements.append(Spacer(1, 20))
    
    # Inventory Summary
    elements.append(Paragraph("📦 Estado de Inventario", styles['Heading2']))
    inv_data = [
        ["Estatus", "Piezas"],
        ["Disponible", str(int(metrics['total_disponible'] or 0))],
        ["En Renta", str(int(metrics['total_rentado'] or 0))],
        ["Mantenimiento", str(int(metrics['total_mantenimiento'] or 0))],
        ["Chatarra", str(int(metrics['total_chatarra'] or 0))]
    ]
    t_inv = Table(inv_data, colWidths=[200, 200])
    t_inv.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.darkgreen),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('PADDING', (0,0), (-1,-1), 6)
    ]))
    elements.append(t_inv)
    elements.append(Spacer(1, 20))
    
    # Top Products
    if top_products:
        elements.append(Paragraph("🔝 Top 5 Productos en Campo", styles['Heading2']))
        top_data = [["Código", "Nombre", "Cantidad en Renta"]]
        for p in top_products:
            top_data.append([p['codigo'], p['nombre'], str(int(p['cantidad_rentada']))])
        t_top = Table(top_data, colWidths=[100, 200, 100])
        t_top.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.orange),
            ('GRID', (0,0), (-1,-1), 1, colors.black),
            ('FONTSIZE', (0,1), (-1,-1), 9)
        ]))
        elements.append(t_top)
    
    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf
