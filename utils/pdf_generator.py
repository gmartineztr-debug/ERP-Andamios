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

# ================================================
# PDF CONTRATO
# ================================================

CLAUSULAS_CONTRATO = [
    ("PRIMERA - OBJETO DEL CONTRATO",
     "El arrendador se obliga a entregar al arrendatario el equipo de andamiaje descrito en el presente contrato, "
     "en condiciones óptimas de uso, para ser utilizado exclusivamente en la obra señalada. "
     "El arrendatario se obliga a usar el equipo de manera adecuada y conforme a las normas de seguridad vigentes."),

    ("SEGUNDA - VIGENCIA",
     "El presente contrato tendrá vigencia por el número de días pactados a partir de la fecha de inicio. "
     "En caso de requerir una extensión, el arrendatario deberá notificar con al menos 5 días hábiles de anticipación "
     "al vencimiento del contrato, sujeto a disponibilidad de equipo."),

    ("TERCERA - PRECIO Y FORMA DE PAGO",
     "El arrendatario se obliga a pagar el monto total establecido en el presente contrato. "
     "El anticipo pactado deberá ser cubierto previo a la entrega del equipo. "
     "El saldo restante deberá liquidarse a más tardar en la fecha de devolución del equipo. "
     "Los pagos deberán realizarse mediante transferencia bancaria o depósito a la cuenta del arrendador."),

    ("CUARTA - ENTREGA Y DEVOLUCIÓN",
     "La entrega del equipo se realizará en la dirección de la obra indicada, previa confirmación del pago del anticipo. "
     "La devolución del equipo deberá efectuarse en las instalaciones del arrendador o en el lugar acordado, "
     "en las mismas condiciones en que fue entregado, libre de suciedad, cemento, pintura u otros materiales. "
     "El equipo que se devuelva en malas condiciones generará un cargo adicional por limpieza y/o reparación."),

    ("QUINTA - RESPONSABILIDAD POR DAÑOS Y PÉRDIDAS",
     "El arrendatario será responsable de cualquier daño, pérdida, robo o destrucción del equipo durante el periodo "
     "de arrendamiento. En caso de pérdida o daño irreparable, el arrendatario deberá cubrir el valor comercial "
     "del equipo dañado o perdido, independientemente del monto del contrato. "
     "El arrendador no se hace responsable por accidentes derivados del mal uso del equipo."),

    ("SEXTA - PENALIZACIONES POR RETRASO",
     "En caso de no devolver el equipo en la fecha pactada sin previo aviso, se generará un cargo adicional "
     "equivalente al precio de renta diaria por cada día de retraso, más un cargo administrativo del 10%. "
     "Dicho monto deberá ser cubierto dentro de los 5 días hábiles siguientes al vencimiento."),

    ("SÉPTIMA - PROHIBICIONES",
     "Queda estrictamente prohibido al arrendatario: subarrendar o ceder el equipo a terceros sin autorización escrita "
     "del arrendador; modificar, reparar o alterar el equipo sin previa autorización; trasladar el equipo a una "
     "ubicación distinta a la indicada en el contrato sin notificación previa."),

    ("OCTAVA - SEGURIDAD",
     "El arrendatario se obliga a cumplir con todas las normas de seguridad aplicables al uso de andamios, "
     "conforme a la NOM-009-STPS-2011 y demás disposiciones vigentes en materia de seguridad e higiene en el trabajo. "
     "El arrendatario asume total responsabilidad por el armado, uso y desarmado del equipo."),

    ("NOVENA - RESCISIÓN",
     "El arrendador podrá rescindir el presente contrato de manera inmediata en caso de incumplimiento de pago, "
     "mal uso del equipo, o cualquier violación a las cláusulas establecidas, procediendo a la recuperación "
     "inmediata del equipo sin responsabilidad alguna para el arrendador."),

    ("DÉCIMA - JURISDICCIÓN",
     "Para todo lo relacionado con la interpretación y cumplimiento del presente contrato, las partes se someten "
     "expresamente a la jurisdicción de los Tribunales competentes de la Ciudad de México, renunciando a cualquier "
     "otro fuero que pudiera corresponderles por razón de su domicilio presente o futuro.")
]


def generar_pdf_contrato(contrato, items):
    """
    Genera PDF de contrato y retorna bytes
    contrato: dict con datos del contrato
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
                f"<b>CONTRATO DE ARRENDAMIENTO</b><br/>"
                f"<font size=14 color='#2e86c1'>{contrato['folio']}</font>",
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
    # DATOS CONTRATO + CLIENTE
    # ============================================
    fecha_c = contrato['fecha_contrato']
    fecha_i = contrato['fecha_inicio']
    fecha_f = contrato['fecha_fin']

    def fmt_fecha(f):
        if f and hasattr(f, 'strftime'):
            return f.strftime('%d/%m/%Y')
        return str(f)[:10] if f else '—'

    obra_txt = f"{contrato.get('folio_obra', '')} — {contrato.get('obra_nombre', '')}" \
               if contrato.get('obra_nombre') else "Sin obra asignada"

    datos_info = [
        [
            Paragraph("<b>DATOS DEL ARRENDATARIO</b>", ESTILO_SUBTITULO),
            Paragraph("<b>DATOS DEL CONTRATO</b>", ESTILO_SUBTITULO)
        ],
        [
            Paragraph(f"<b>Razón Social:</b> {contrato['cliente_nombre']}", ESTILO_NORMAL),
            Paragraph(f"<b>Folio:</b> {contrato['folio']}", ESTILO_NORMAL)
        ],
        [
            Paragraph(f"<b>RFC:</b> {contrato.get('rfc', '—')}", ESTILO_NORMAL),
            Paragraph(f"<b>Fecha contrato:</b> {fmt_fecha(fecha_c)}", ESTILO_NORMAL)
        ],
        [
            Paragraph(f"<b>Obra:</b> {obra_txt}", ESTILO_NORMAL),
            Paragraph(f"<b>Fecha inicio:</b> {fmt_fecha(fecha_i)}", ESTILO_NORMAL)
        ],
        [
            Paragraph("", ESTILO_NORMAL),
            Paragraph(f"<b>Fecha fin:</b> {fmt_fecha(fecha_f)}", ESTILO_NORMAL)
        ],
        [
            Paragraph("", ESTILO_NORMAL),
            Paragraph(f"<b>Días de renta:</b> {contrato['dias_renta']}", ESTILO_NORMAL)
        ],
        [
            Paragraph("", ESTILO_NORMAL),
            Paragraph(f"<b>Tipo:</b> {contrato['tipo_contrato'].capitalize()}", ESTILO_NORMAL)
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
    contenido.append(Paragraph("EQUIPO ARRENDADO", ESTILO_SUBTITULO))

    encabezados = [
        Paragraph("Código", ESTILO_HEADER_TABLA),
        Paragraph("Descripción", ESTILO_HEADER_TABLA),
        Paragraph("Cantidad", ESTILO_HEADER_TABLA),
        Paragraph("Precio/Día", ESTILO_HEADER_TABLA),
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

    tabla_productos = Table(filas, colWidths=[25*mm, 75*mm, 20*mm, 25*mm, 25*mm])
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
    # TOTALES
    # ============================================
    datos_totales = [
        ["", f"Subtotal equipo: ${float(contrato['subtotal']):,.2f}"],
        ["", f"Flete: ${float(contrato['monto_flete']):,.2f}"],
        ["", f"IVA 16%: ${float(contrato['iva']):,.2f}"],
        ["", f"TOTAL: ${float(contrato['monto_total']):,.2f}"],
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
    contenido.append(Spacer(1, 4*mm))

    # ============================================
    # ANTICIPO
    # ============================================
    contenido.append(HRFlowable(width="100%", thickness=0.5,
                                 color=colors.lightgrey, spaceAfter=3*mm))
    contenido.append(Paragraph("ANTICIPO", ESTILO_SUBTITULO))

    ant_est = {
        'pendiente': 'Pendiente',
        'parcial'  : 'Parcial',
        'completo' : 'Completo'
    }.get(contrato['anticipo_estatus'], '—')

    fecha_ap = contrato.get('anticipo_fecha_pago')

    datos_anticipo = [
        [
            Paragraph(f"<b>Porcentaje pactado:</b> {contrato['anticipo_porcentaje']}%", ESTILO_NORMAL),
            Paragraph(f"<b>Monto requerido:</b> ${float(contrato['anticipo_requerido']):,.2f}", ESTILO_NORMAL),
        ],
        [
            Paragraph(f"<b>Monto pagado:</b> ${float(contrato['anticipo_pagado']):,.2f}", ESTILO_NORMAL),
            Paragraph(f"<b>Referencia:</b> {contrato.get('anticipo_referencia') or '—'}", ESTILO_NORMAL),
        ],
        [
            Paragraph(f"<b>Fecha de pago:</b> {fmt_fecha(fecha_ap)}", ESTILO_NORMAL),
            Paragraph(f"<b>Estatus:</b> {ant_est}", ESTILO_NORMAL),
        ],
    ]
    tabla_anticipo = Table(datos_anticipo, colWidths=[87*mm, 87*mm])
    tabla_anticipo.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 1.5*mm),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1.5*mm),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_GRIS),
    ]))
    contenido.append(tabla_anticipo)
    contenido.append(Spacer(1, 4*mm))

    # ============================================
    # PAGARÉ
    # ============================================
    contenido.append(Paragraph("PAGARÉ", ESTILO_SUBTITULO))
    fecha_pv = contrato.get('pagare_fecha_vencimiento')
    datos_pagare = [
        [
            Paragraph(f"<b>Número:</b> {contrato.get('pagare_numero') or '—'}", ESTILO_NORMAL),
            Paragraph(f"<b>Monto:</b> ${float(contrato['pagare_monto']):,.2f}", ESTILO_NORMAL),
        ],
        [
            Paragraph(f"<b>Firmante:</b> {contrato.get('pagare_firmante') or '—'}", ESTILO_NORMAL),
            Paragraph(f"<b>Vencimiento:</b> {fmt_fecha(fecha_pv)}", ESTILO_NORMAL),
        ],
        [
            Paragraph(f"<b>Firmado:</b> {'✅ Sí' if contrato['pagare_firmado'] else '❌ No'}", ESTILO_NORMAL),
            Paragraph("", ESTILO_NORMAL),
        ],
    ]
    tabla_pagare = Table(datos_pagare, colWidths=[87*mm, 87*mm])
    tabla_pagare.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 1.5*mm),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1.5*mm),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_GRIS),
    ]))
    contenido.append(tabla_pagare)
    contenido.append(Spacer(1, 6*mm))

    # ============================================
    # CLÁUSULAS
    # ============================================
    contenido.append(HRFlowable(width="100%", thickness=1,
                                 color=COLOR_PRIMARIO, spaceAfter=4*mm))
    contenido.append(Paragraph("TÉRMINOS Y CONDICIONES", ESTILO_SUBTITULO))

    for titulo, texto in CLAUSULAS_CONTRATO:
        contenido.append(Paragraph(titulo, ParagraphStyle(
            'ClausulaTitle',
            fontName='Helvetica-Bold',
            fontSize=8,
            textColor=COLOR_PRIMARIO,
            spaceBefore=3*mm,
            spaceAfter=1*mm
        )))
        contenido.append(Paragraph(texto, ParagraphStyle(
            'ClausulaText',
            fontName='Helvetica',
            fontSize=7.5,
            textColor=COLOR_TEXTO,
            spaceAfter=1*mm,
            leading=10
        )))

    # ============================================
    # FIRMA Y SELLO
    # ============================================
    contenido.append(Spacer(1, 8*mm))
    contenido.append(HRFlowable(width="100%", thickness=0.5,
                                 color=colors.lightgrey, spaceAfter=6*mm))
    datos_firma = [
        [
            Paragraph("_______________________________", ESTILO_NORMAL),
            Paragraph("_______________________________", ESTILO_NORMAL),
        ],
        [
            Paragraph(f"<b>{EMPRESA['nombre']}</b>", ESTILO_NORMAL),
            Paragraph(f"<b>{contrato['cliente_nombre']}</b>", ESTILO_NORMAL),
        ],
        [
            Paragraph("Arrendador", ESTILO_SMALL),
            Paragraph("Arrendatario", ESTILO_SMALL),
        ],
    ]
    tabla_firma = Table(datos_firma, colWidths=[87*mm, 87*mm])
    tabla_firma.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 2*mm),
    ]))
    contenido.append(tabla_firma)

    # Pie de página
    contenido.append(Spacer(1, 4*mm))
    contenido.append(HRFlowable(width="100%", thickness=0.5,
                                 color=colors.lightgrey, spaceAfter=2*mm))
    contenido.append(Paragraph(
        f"Contrato generado el {fmt_fecha(fecha_c)} | "
        f"{EMPRESA['nombre']} | {EMPRESA['telefono']} | {EMPRESA['email']}",
        ESTILO_SMALL
    ))

    doc.build(contenido)
    buffer.seek(0)
    return buffer.getvalue()

def generar_pdf_hoja_salida(hs, items):
    """Genera PDF de Hoja de Salida"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        rightMargin=15*mm, leftMargin=15*mm,
        topMargin=15*mm, bottomMargin=15*mm
    )
    contenido = []

    # ENCABEZADO
    datos_enc = [[
        Paragraph(EMPRESA['nombre'], ESTILO_TITULO),
        Paragraph(
            f"<b>HOJA DE SALIDA</b><br/>"
            f"<font size=14 color='#2e86c1'>{hs['folio']}</font>",
            ParagraphStyle('Folio', fontName='Helvetica-Bold',
                           fontSize=11, alignment=TA_RIGHT,
                           textColor=COLOR_PRIMARIO)
        )
    ]]
    t = Table(datos_enc, colWidths=[100*mm, 75*mm])
    t.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
    contenido.append(t)
    contenido.append(Paragraph(
        f"RFC: {EMPRESA['rfc']} | {EMPRESA['direccion']}",
        ESTILO_SMALL
    ))
    contenido.append(Paragraph(
        f"Tel: {EMPRESA['telefono']} | {EMPRESA['email']}",
        ESTILO_SMALL
    ))
    contenido.append(HRFlowable(width="100%", thickness=2,
                                color=COLOR_PRIMARIO, spaceAfter=4*mm))

    # DATOS GENERALES
    def fmt(f):
        if f and hasattr(f, 'strftime'):
            return f.strftime('%d/%m/%Y')
        return str(f)[:10] if f else '—'

    obra_txt = f"{hs.get('folio_obra','—')} — {hs.get('obra_nombre','')}" \
               if hs.get('obra_nombre') else "Sin obra asignada"

    datos_info = [
        [
            Paragraph("<b>DATOS DE ENTREGA</b>", ESTILO_SUBTITULO),
            Paragraph("<b>DATOS DEL DOCUMENTO</b>", ESTILO_SUBTITULO)
        ],
        [
            Paragraph(f"<b>Cliente:</b> {hs['cliente_nombre']}", ESTILO_NORMAL),
            Paragraph(f"<b>Folio HS:</b> {hs['folio']}", ESTILO_NORMAL)
        ],
        [
            Paragraph(f"<b>Contacto:</b> {hs.get('contacto_entrega') or '—'}", ESTILO_NORMAL),
            Paragraph(f"<b>Contrato:</b> {hs['contrato_folio']}", ESTILO_NORMAL)
        ],
        [
            Paragraph(f"<b>Teléfono:</b> {hs.get('telefono_entrega') or '—'}", ESTILO_NORMAL),
            Paragraph(f"<b>Fecha salida:</b> {fmt(hs['fecha_salida'])}", ESTILO_NORMAL)
        ],
        [
            Paragraph(f"<b>Obra:</b> {obra_txt}", ESTILO_NORMAL),
            Paragraph(f"<b>Chofer:</b> {hs.get('chofer') or '—'}", ESTILO_NORMAL)
        ],
        [
            Paragraph(f"<b>Dirección:</b> {hs.get('direccion_obra') or '—'}", ESTILO_NORMAL),
            Paragraph(f"<b>Peso total:</b> {float(hs['peso_total']):.1f} kg", ESTILO_NORMAL)
        ],
    ]
    tabla_info = Table(datos_info, colWidths=[100*mm, 75*mm])
    tabla_info.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BACKGROUND', (0,0), (-1,0), COLOR_GRIS),
        ('LINEBELOW', (0,0), (-1,0), 0.5, COLOR_SECUNDARIO),
        ('BOX', (0,0), (0,-1), 0.5, colors.lightgrey),
        ('BOX', (1,0), (1,-1), 0.5, colors.lightgrey),
        ('TOPPADDING', (0,0), (-1,-1), 1.5*mm),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1.5*mm),
    ]))
    contenido.append(tabla_info)
    contenido.append(Spacer(1, 4*mm))

    # TABLA DE DESPIECE
    contenido.append(Paragraph("DESPIECE DE EQUIPO", ESTILO_SUBTITULO))

    encabezados = [
        Paragraph("#", ESTILO_HEADER_TABLA),
        Paragraph("Código", ESTILO_HEADER_TABLA),
        Paragraph("Descripción", ESTILO_HEADER_TABLA),
        Paragraph("Cantidad", ESTILO_HEADER_TABLA),
        Paragraph("Peso Unit. kg", ESTILO_HEADER_TABLA),
        Paragraph("Peso Total kg", ESTILO_HEADER_TABLA),
    ]
    filas = [encabezados]
    total_piezas = 0
    total_peso   = 0
    for idx, item in enumerate(items, 1):
        cant = item['cantidad']
        peso_u = float(item['peso_unitario'] or 0)
        peso_t = float(item['peso_total'] or 0)
        total_piezas += cant
        total_peso   += peso_t
        filas.append([
            Paragraph(str(idx), ESTILO_CELDA),
            Paragraph(item['codigo'], ESTILO_CELDA),
            Paragraph(item['producto_nombre'], ESTILO_NORMAL),
            Paragraph(str(cant), ESTILO_CELDA),
            Paragraph(f"{peso_u:.2f}", ESTILO_CELDA),
            Paragraph(f"{peso_t:.2f}", ESTILO_CELDA),
        ])

    # Fila totales
    filas.append([
        Paragraph("", ESTILO_CELDA),
        Paragraph("", ESTILO_CELDA),
        Paragraph("<b>TOTALES</b>", ParagraphStyle(
            'Total', fontName='Helvetica-Bold', fontSize=9,
            textColor=COLOR_PRIMARIO, alignment=TA_RIGHT
        )),
        Paragraph(f"<b>{total_piezas}</b>", ParagraphStyle(
            'TotalN', fontName='Helvetica-Bold', fontSize=9,
            textColor=COLOR_PRIMARIO, alignment=TA_CENTER
        )),
        Paragraph("", ESTILO_CELDA),
        Paragraph(f"<b>{total_peso:.2f}</b>", ParagraphStyle(
            'TotalP', fontName='Helvetica-Bold', fontSize=9,
            textColor=COLOR_PRIMARIO, alignment=TA_CENTER
        )),
    ])

    tabla_items = Table(
        filas,
        colWidths=[8*mm, 22*mm, 70*mm, 18*mm, 22*mm, 22*mm]
    )
    tabla_items.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), COLOR_PRIMARIO),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, COLOR_GRIS]),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#eaf4fb')),
        ('GRID', (0,0), (-1,-1), 0.3, colors.lightgrey),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 2*mm),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2*mm),
    ]))
    contenido.append(tabla_items)
    contenido.append(Spacer(1, 6*mm))

    # OBSERVACIONES
    if hs.get('observaciones'):
        contenido.append(Paragraph("OBSERVACIONES", ESTILO_SUBTITULO))
        contenido.append(Paragraph(hs['observaciones'], ESTILO_NORMAL))
        contenido.append(Spacer(1, 4*mm))

    # FIRMA
    contenido.append(HRFlowable(width="100%", thickness=0.5,
                                color=colors.lightgrey, spaceAfter=6*mm))
    datos_firma = [
        [
            Paragraph("_______________________________", ESTILO_NORMAL),
            Paragraph("_______________________________", ESTILO_NORMAL),
        ],
        [
            Paragraph(f"<b>{EMPRESA['nombre']}</b>", ESTILO_NORMAL),
            Paragraph(f"<b>{hs['cliente_nombre']}</b>", ESTILO_NORMAL),
        ],
        [
            Paragraph("Entrega", ESTILO_SMALL),
            Paragraph("Recibe — Firma y sello", ESTILO_SMALL),
        ],
    ]
    tabla_firma = Table(datos_firma, colWidths=[87*mm, 87*mm])
    tabla_firma.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('TOPPADDING', (0,0), (-1,-1), 2*mm),
    ]))
    contenido.append(tabla_firma)

    # PIE
    contenido.append(Spacer(1, 4*mm))
    contenido.append(HRFlowable(width="100%", thickness=0.5,
                                color=colors.lightgrey, spaceAfter=2*mm))
    contenido.append(Paragraph(
        f"Hoja de Salida {hs['folio']} | Contrato {hs['contrato_folio']} | "
        f"{EMPRESA['nombre']} | {EMPRESA['telefono']}",
        ESTILO_SMALL
    ))

    doc.build(contenido)
    buffer.seek(0)
    return buffer.getvalue()


def generar_pdf_hoja_salida(hs, items):
    """Genera PDF de Hoja de Salida"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        rightMargin=15*mm, leftMargin=15*mm,
        topMargin=15*mm, bottomMargin=15*mm
    )
    contenido = []

    # ENCABEZADO
    datos_enc = [[
        Paragraph(EMPRESA['nombre'], ESTILO_TITULO),
        Paragraph(
            f"<b>HOJA DE SALIDA</b><br/>"
            f"<font size=14 color='#2e86c1'>{hs['folio']}</font>",
            ParagraphStyle('Folio', fontName='Helvetica-Bold',
                           fontSize=11, alignment=TA_RIGHT,
                           textColor=COLOR_PRIMARIO)
        )
    ]]
    t = Table(datos_enc, colWidths=[100*mm, 75*mm])
    t.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
    contenido.append(t)
    contenido.append(Paragraph(
        f"RFC: {EMPRESA['rfc']} | {EMPRESA['direccion']}",
        ESTILO_SMALL
    ))
    contenido.append(Paragraph(
        f"Tel: {EMPRESA['telefono']} | {EMPRESA['email']}",
        ESTILO_SMALL
    ))
    contenido.append(HRFlowable(width="100%", thickness=2,
                                color=COLOR_PRIMARIO, spaceAfter=4*mm))

    # DATOS GENERALES
    def fmt(f):
        if f and hasattr(f, 'strftime'):
            return f.strftime('%d/%m/%Y')
        return str(f)[:10] if f else '—'

    obra_txt = f"{hs.get('folio_obra','—')} — {hs.get('obra_nombre','')}" \
               if hs.get('obra_nombre') else "Sin obra asignada"

    datos_info = [
        [
            Paragraph("<b>DATOS DE ENTREGA</b>", ESTILO_SUBTITULO),
            Paragraph("<b>DATOS DEL DOCUMENTO</b>", ESTILO_SUBTITULO)
        ],
        [
            Paragraph(f"<b>Cliente:</b> {hs['cliente_nombre']}", ESTILO_NORMAL),
            Paragraph(f"<b>Folio HS:</b> {hs['folio']}", ESTILO_NORMAL)
        ],
        [
            Paragraph(f"<b>Contacto:</b> {hs.get('contacto_entrega') or '—'}", ESTILO_NORMAL),
            Paragraph(f"<b>Contrato:</b> {hs['contrato_folio']}", ESTILO_NORMAL)
        ],
        [
            Paragraph(f"<b>Teléfono:</b> {hs.get('telefono_entrega') or '—'}", ESTILO_NORMAL),
            Paragraph(f"<b>Fecha salida:</b> {fmt(hs['fecha_salida'])}", ESTILO_NORMAL)
        ],
        [
            Paragraph(f"<b>Obra:</b> {obra_txt}", ESTILO_NORMAL),
            Paragraph(f"<b>Chofer:</b> {hs.get('chofer') or '—'}", ESTILO_NORMAL)
        ],
        [
            Paragraph(f"<b>Dirección:</b> {hs.get('direccion_obra') or '—'}", ESTILO_NORMAL),
            Paragraph(f"<b>Peso total:</b> {float(hs['peso_total']):.1f} kg", ESTILO_NORMAL)
        ],
    ]
    tabla_info = Table(datos_info, colWidths=[100*mm, 75*mm])
    tabla_info.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BACKGROUND', (0,0), (-1,0), COLOR_GRIS),
        ('LINEBELOW', (0,0), (-1,0), 0.5, COLOR_SECUNDARIO),
        ('BOX', (0,0), (0,-1), 0.5, colors.lightgrey),
        ('BOX', (1,0), (1,-1), 0.5, colors.lightgrey),
        ('TOPPADDING', (0,0), (-1,-1), 1.5*mm),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1.5*mm),
    ]))
    contenido.append(tabla_info)
    contenido.append(Spacer(1, 4*mm))

    # TABLA DE DESPIECE
    contenido.append(Paragraph("DESPIECE DE EQUIPO", ESTILO_SUBTITULO))

    encabezados = [
        Paragraph("#", ESTILO_HEADER_TABLA),
        Paragraph("Código", ESTILO_HEADER_TABLA),
        Paragraph("Descripción", ESTILO_HEADER_TABLA),
        Paragraph("Cantidad", ESTILO_HEADER_TABLA),
        Paragraph("Peso Unit. kg", ESTILO_HEADER_TABLA),
        Paragraph("Peso Total kg", ESTILO_HEADER_TABLA),
    ]
    filas = [encabezados]
    total_piezas = 0
    total_peso   = 0
    for idx, item in enumerate(items, 1):
        cant  = item['cantidad']
        peso_u = float(item['peso_unitario'] or 0)
        peso_t = float(item['peso_total'] or 0)
        total_piezas += cant
        total_peso   += peso_t
        filas.append([
            Paragraph(str(idx), ESTILO_CELDA),
            Paragraph(item['codigo'], ESTILO_CELDA),
            Paragraph(item['producto_nombre'], ESTILO_NORMAL),
            Paragraph(str(cant), ESTILO_CELDA),
            Paragraph(f"{peso_u:.2f}", ESTILO_CELDA),
            Paragraph(f"{peso_t:.2f}", ESTILO_CELDA),
        ])

    # Fila totales
    filas.append([
        Paragraph("", ESTILO_CELDA),
        Paragraph("", ESTILO_CELDA),
        Paragraph("<b>TOTALES</b>", ParagraphStyle(
            'Total', fontName='Helvetica-Bold', fontSize=9,
            textColor=COLOR_PRIMARIO, alignment=TA_RIGHT
        )),
        Paragraph(f"<b>{total_piezas}</b>", ParagraphStyle(
            'TotalN', fontName='Helvetica-Bold', fontSize=9,
            textColor=COLOR_PRIMARIO, alignment=TA_CENTER
        )),
        Paragraph("", ESTILO_CELDA),
        Paragraph(f"<b>{total_peso:.2f}</b>", ParagraphStyle(
            'TotalP', fontName='Helvetica-Bold', fontSize=9,
            textColor=COLOR_PRIMARIO, alignment=TA_CENTER
        )),
    ])

    tabla_items = Table(
        filas,
        colWidths=[8*mm, 22*mm, 70*mm, 18*mm, 22*mm, 22*mm]
    )
    tabla_items.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), COLOR_PRIMARIO),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, COLOR_GRIS]),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#eaf4fb')),
        ('GRID', (0,0), (-1,-1), 0.3, colors.lightgrey),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 2*mm),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2*mm),
    ]))
    contenido.append(tabla_items)
    contenido.append(Spacer(1, 6*mm))

    # OBSERVACIONES
    if hs.get('observaciones'):
        contenido.append(Paragraph("OBSERVACIONES", ESTILO_SUBTITULO))
        contenido.append(Paragraph(hs['observaciones'], ESTILO_NORMAL))
        contenido.append(Spacer(1, 4*mm))

    # FIRMA
    contenido.append(HRFlowable(width="100%", thickness=0.5,
                                color=colors.lightgrey, spaceAfter=6*mm))
    datos_firma = [
        [
            Paragraph("_______________________________", ESTILO_NORMAL),
            Paragraph("_______________________________", ESTILO_NORMAL),
        ],
        [
            Paragraph(f"<b>{EMPRESA['nombre']}</b>", ESTILO_NORMAL),
            Paragraph(f"<b>{hs['cliente_nombre']}</b>", ESTILO_NORMAL),
        ],
        [
            Paragraph("Entrega", ESTILO_SMALL),
            Paragraph("Recibe — Firma y sello", ESTILO_SMALL),
        ],
    ]
    tabla_firma = Table(datos_firma, colWidths=[87*mm, 87*mm])
    tabla_firma.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('TOPPADDING', (0,0), (-1,-1), 2*mm),
    ]))
    contenido.append(tabla_firma)

    # PIE
    contenido.append(Spacer(1, 4*mm))
    contenido.append(HRFlowable(width="100%", thickness=0.5,
                                color=colors.lightgrey, spaceAfter=2*mm))
    contenido.append(Paragraph(
        f"Hoja de Salida {hs['folio']} | Contrato {hs['contrato_folio']} | "
        f"{EMPRESA['nombre']} | {EMPRESA['telefono']}",
        ESTILO_SMALL
    ))

    doc.build(contenido)
    buffer.seek(0)
    return buffer.getvalue()