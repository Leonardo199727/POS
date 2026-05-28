import csv
import io
from typing import List, Dict, Any

class CSVExporter:
    """
    Exportador genérico de listas de diccionarios a CSV.
    No depende de modelos ni de lógica de negocio.
    """

    @staticmethod
    def export(data: List[Dict[str, Any]], include_headers: bool = True) -> bytes:
        """
        Genera un archivo CSV en memoria a partir de una lista de diccionarios.
        
        Args:
            data: Lista de diccionarios con los datos a exportar.
            include_headers: Si es True, incluye la primera fila con las llaves.
            
        Returns:
            bytes: El contenido del archivo CSV codificado en UTF-8 con BOM.
        """
        if not data:
            # Retornar un CSV vacío válido
            return b""

        output = io.StringIO()
        # Detectar headers del primer elemento
        headers = list(data[0].keys())
        writer = csv.DictWriter(output, fieldnames=headers)

        if include_headers:
            writer.writeheader()

        writer.writerows(data)

        # Obtener valor y codificar a bytes con BOM para compatibilidad Excel
        return output.getvalue().encode('utf-8-sig')
