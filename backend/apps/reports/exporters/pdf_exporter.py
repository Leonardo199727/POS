import io
from datetime import datetime
from typing import List, Dict, Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

class PDFExporter:
    """
    Exportador genérico de listas de diccionarios a PDF.
    Genera tablas automáticas y no depende de modelos.
    """

    @staticmethod
    def export(data: List[Dict[str, Any]], title: str) -> bytes:
        """
        Genera un PDF en memoria con una tabla de datos.

        Args:
            data: Lista de diccionarios con los datos.
            title: Título del reporte.

        Returns:
            bytes: Contenido del archivo PDF.
        """
        buffer = io.BytesIO()
        # Usamos landscape para tener más ancho disponible para tablas
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(letter),
            rightMargin=30,
            leftMargin=30,
            topMargin=30,
            bottomMargin=18
        )
        elements = []
        styles = getSampleStyleSheet()

        # Estilo personalizado para el título
        title_style = styles['Title']
        title_style.fontSize = 18
        title_style.spaceAfter = 12

        # Estilo para metadatos (fecha)
        meta_style = styles['Normal']
        meta_style.fontSize = 10
        meta_style.textColor = colors.grey

        # 1. Título y Fecha
        elements.append(Paragraph(title, title_style))
        fecha_str = datetime.now().strftime("%d/%m/%Y %H:%M")
        elements.append(Paragraph(f"Generado el: {fecha_str}", meta_style))
        elements.append(Spacer(1, 20))

        if not data:
            elements.append(Paragraph("Sin datos disponibles", styles['Normal']))
            doc.build(elements)
            return buffer.getvalue()

        # 2. Prepara datos para la tabla
        headers = list(data[0].keys())
        # Primera fila: encabezados (convertidos a mayúsculas o limpios si se desea, 
        # pero mantenemos keys originales por requisito 'genérico')
        table_data = [headers]  

        for row in data:
            # Convertir todo a string para reporte
            row_data = [str(row.get(h, '')) for h in headers]
            table_data.append(row_data)

        # 3. Crear Tabla
        table = Table(table_data)

        # 4. Estilos de Tabla
        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.2, 0.4, 0.6)), # Azul oscuro
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            # Cuerpo
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ])
        
        # Zebra striping (filas alternas)
        # len(table_data) incluye header
        for i in range(1, len(table_data)):
            if i % 2 == 0:
                style.add('BACKGROUND', (0, i), (-1, i), colors.whitesmoke)

        table.setStyle(style)
        elements.append(table)

        # 5. Generar PDF
        doc.build(elements)
        return buffer.getvalue()
