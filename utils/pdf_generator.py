# utils/pdf_generator.py
# Generador de PDFs para cotizaciones

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from datetime import datetime
import io
from utils.config import EMPRESA

# ================================================
# COLORES
# ================================================
COLOR_PRIMARIO   = colors.HexColor('#1a3a5c')
COLOR_SECUNDARIO = colors.HexColor('#2e86c1')
COLOR_GRIS       = colors.HexColor('#f2f3f4')
COLOR_TEXTO      = colors.HexColor('#2c3e50')

# ================================================
# ESTILOS
# ================================================
styles = getSampleStyleSheet()

ESTILO_TITULO = ParagraphStyle(
    'Titulo',
    fontName='Helvetica-Bold',
    fontSize=20,
    textColor=COLOR_PRIMARIO,
    alignment=TA_LEFT,
    spaceAfter=2*mm
)
ESTILO_SUBTITULO = ParagraphStyle(
    'Subtitulo',
    fontName='Helvetica-Bold',
    fontSize=11,
    textColor=COLOR_SECUNDARIO,
    spaceAfter=2*mm
)
ESTILO_NORMAL = ParagraphStyle(
    'Normal2',
    fontName='Helvetica',
    fontSize=9,
    textColor=COLOR_TEXTO,
    spaceAfter=1*mm
)
ESTILO_SMALL = ParagraphStyle(
    'Small',
    fontName='Helvetica',
    fontSize=8,
    textColor=colors.gray,
    spaceAfter=1*mm
)
ESTILO_HEADER_TABLA = ParagraphStyle(
    'HeaderTabla',
    fontName='Helvetica-Bold',
    fontSize=9,
    textColor=colors.white,
    alignment=TA_CENTER
)
ESTILO_CELDA = ParagraphStyle(
    'Celda',
    fontName='Helvetica',
    fontSize=9,
    textColor=COLOR_TEXTO,
    alignment=TA_CENTER
)
ESTILO_DERECHA = ParagraphStyle(
    'Derecha',
    fontName='Helvetica',
    fontSize=9,
    textColor=COLOR_TEXTO,
    alignment=TA_RIGHT
)

# ================================================
# FUNCIÓN PRINCIPAL
# ================================================

def generar_pdf_cotizacion(cotizacion, items):
    """
    Genera PDF de cotización y retorna bytes
    cotizacion: dict con datos de la cotización
    items: list de dicts con productos
    """
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=15*mm,
        leftMargin=15*mm,
        topMargin=15*mm,
        bottomMargin=15*mm
    )

    contenido = []

    # ============================================
    # ENCABEZADO
    # ============================================
    datos_encabezado = [
        [
            Paragraph(EMPRESA['nombre'], ESTILO_TITULO),
            Paragraph(
                f"<b>COTIZACIÓN</b><br/>"
                f"<font size=14 color='#2e86c1'>{cotizacion['folio']}</font>",
                ParagraphStyle('Folio', fontName='Helvetica-Bold',
                               fontSize=11, alignment=TA_RIGHT,
                               textColor=COLOR_PRIMARIO)
            )
        ]
    ]

    tabla_encabezado = Table(datos_encabezado, colWidths=[100*mm, 75*mm])
    tabla_encabezado.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2*mm),
    ]))
    contenido.append(tabla_encabezado)

    # Datos empresa
    contenido.append(Paragraph(
        f"RFC: {EMPRESA['rfc']} | {EMPRESA['direccion']}",
        ESTILO_SMALL
    ))
    contenido.append(Paragraph(
        f"Tel: {EMPRESA['telefono']} | {EMPRESA['email']} | {EMPRESA['web']}",
        ESTILO_SMALL
    ))
    contenido.append(HRFlowable(width="100%", thickness=2,
                                 color=COLOR_PRIMARIO, spaceAfter=4*mm))

    # ============================================
    # DATOS COTIZACIÓN + CLIENTE
    # ============================================
    fecha = cotizacion['created_at']
    if hasattr(fecha, 'strftime'):
        fecha_str = fecha.strftime('%d/%m/%Y')
    else:
        fecha_str = str(fecha)[:10]

    tipo_flete_label = {
        'cotizado' : 'Incluido',
        'sin_costo': 'Sin costo',
        'cliente'  : 'Por cuenta del cliente'
    }.get(cotizacion['tipo_flete'], '—')

    datos_info = [
        [
            Paragraph("<b>DATOS DEL CLIENTE</b>", ESTILO_SUBTITULO),
            Paragraph("<b>DATOS DE LA COTIZACIÓN</b>", ESTILO_SUBTITULO)
        ],
        [
            Paragraph(f"<b>Razón Social:</b> {cotizacion['cliente_nombre']}", ESTILO_NORMAL),
            Paragraph(f"<b>Fecha:</b> {fecha_str}", ESTILO_NORMAL)
        ],
        [
            Paragraph(f"<b>RFC:</b> {cotizacion.get('rfc', '—')}", ESTILO_NORMAL),
            Paragraph(f"<b>Tipo:</b> {cotizacion['tipo_operacion'].capitalize()}", ESTILO_NORMAL)
        ],
        [
            Paragraph("", ESTILO_NORMAL),
            Paragraph(f"<b>Días de renta:</b> {cotizacion['dias_renta']}", ESTILO_NORMAL)
        ],
        [
            Paragraph("", ESTILO_NORMAL),
            Paragraph(f"<b>Flete:</b> {tipo_flete_label}", ESTILO_NORMAL)
        ],
    ]

    tabla_info = Table(datos_info, colWidths=[90*mm, 85*mm])
    tabla_info.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_GRIS),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1.5*mm),
        ('TOPPADDING', (0, 0), (-1, -1), 1.5*mm),
        ('LINEBELOW', (0, 0), (-1, 0), 0.5, COLOR_SECUNDARIO),
        ('BOX', (0, 0), (0, -1), 0.5, colors.lightgrey),
        ('BOX', (1, 0), (1, -1), 0.5, colors.lightgrey),
    ]))
    contenido.append(tabla_info)
    contenido.append(Spacer(1, 4*mm))

    # ============================================
    # TABLA DE PRODUCTOS
    # ============================================
    contenido.append(Paragraph("PRODUCTOS", ESTILO_SUBTITULO))

    encabezados = [
        Paragraph("Código", ESTILO_HEADER_TABLA),
        Paragraph("Descripción", ESTILO_HEADER_TABLA),
        Paragraph("Cantidad", ESTILO_HEADER_TABLA),
        Paragraph("Precio Unit.", ESTILO_HEADER_TABLA),
        Paragraph("Subtotal", ESTILO_HEADER_TABLA),
    ]

    filas = [encabezados]
    for item in items:
        filas.append([
            Paragraph(item['codigo'], ESTILO_CELDA),
            Paragraph(item['producto_nombre'], ESTILO_NORMAL),
            Paragraph(str(item['cantidad']), ESTILO_CELDA),
            Paragraph(f"${float(item['precio_unitario']):,.2f}", ESTILO_CELDA),
            Paragraph(f"${float(item['subtotal']):,.2f}", ESTILO_CELDA),
        ])

    tabla_productos = Table(
        filas,
        colWidths=[25*mm, 75*mm, 20*mm, 25*mm, 25*mm]
    )
    tabla_productos.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_PRIMARIO),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COLOR_GRIS]),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.lightgrey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 2*mm),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2*mm),
    ]))
    contenido.append(tabla_productos)
    contenido.append(Spacer(1, 4*mm))

    # ============================================
    # DESGLOSE DE FLETE Y TOTALES
    # ============================================
    flete_label = {
        'cotizado' : f"Flete (incluido): ${float(cotizacion['monto_flete']):,.2f}",
        'sin_costo': "Flete: Sin costo",
        'cliente'  : "Flete: Por cuenta del cliente"
    }.get(cotizacion['tipo_flete'], '—')

    iva_label = "IVA 16%:" if cotizacion['aplica_iva'] else "IVA: No aplica"

    datos_totales = [
        ["", flete_label],
        ["", f"Subtotal: ${float(cotizacion['subtotal']):,.2f}"],
        ["", f"{iva_label} ${float(cotizacion['iva']):,.2f}"],
        ["", f"TOTAL: ${float(cotizacion['total']):,.2f}"],
    ]

    tabla_totales = Table(datos_totales, colWidths=[120*mm, 55*mm])
    tabla_totales.setStyle(TableStyle([
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (1, -1), (1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (1, -1), (1, -1), 11),
        ('TEXTCOLOR', (1, -1), (1, -1), COLOR_PRIMARIO),
        ('LINEABOVE', (1, -1), (1, -1), 1, COLOR_PRIMARIO),
        ('TOPPADDING', (0, 0), (-1, -1), 1.5*mm),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1.5*mm),
    ]))
    contenido.append(tabla_totales)
    contenido.append(HRFlowable(width="100%", thickness=0.5,
                                 color=colors.lightgrey, spaceAfter=4*mm))

    # ============================================
    # NOTAS Y CONDICIONES
    # ============================================
    if cotizacion.get('notas'):
        contenido.append(Paragraph("NOTAS Y CONDICIONES", ESTILO_SUBTITULO))
        contenido.append(Paragraph(cotizacion['notas'], ESTILO_NORMAL))
        contenido.append(Spacer(1, 4*mm))

    # ============================================
    # FIRMA Y SELLO
    # ============================================
    contenido.append(Spacer(1, 10*mm))
    datos_firma = [
        [
            Paragraph("_______________________________", ESTILO_NORMAL),
            Paragraph("_______________________________", ESTILO_NORMAL),
        ],
        [
            Paragraph(f"<b>{EMPRESA['nombre']}</b>", ESTILO_NORMAL),
            Paragraph("<b>Cliente</b>", ESTILO_NORMAL),
        ],
        [
            Paragraph("Autorizado por", ESTILO_SMALL),
            Paragraph("Firma de aceptación", ESTILO_SMALL),
        ],
    ]
    tabla_firma = Table(datos_firma, colWidths=[87*mm, 87*mm])
    tabla_firma.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 2*mm),
    ]))
    contenido.append(tabla_firma)

    # ============================================
    # PIE DE PÁGINA
    # ============================================
    contenido.append(Spacer(1, 6*mm))
    contenido.append(HRFlowable(width="100%", thickness=0.5,
                                 color=colors.lightgrey, spaceAfter=2*mm))
    contenido.append(Paragraph(
        f"Cotización válida por 30 días a partir de la fecha de emisión. "
        f"{EMPRESA['nombre']} | {EMPRESA['telefono']} | {EMPRESA['email']}",
        ESTILO_SMALL
    ))

    doc.build(contenido)
    buffer.seek(0)
    return buffer.getvalue()