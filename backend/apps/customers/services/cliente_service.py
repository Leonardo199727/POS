from decimal import Decimal
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from apps.customers.models import Cliente, MovimientoCredito
from rest_framework.exceptions import ValidationError

class ClienteService:
    """
    Servicio de dominio para operaciones relacionadas con Clientes.
    Encapsula las reglas de negocio, manteniendo los modelos anémicos
    y los controladores limpios, alineado con Clean Architecture y Layered Architecture.
    """

    @staticmethod
    @transaction.atomic
    def registrar_cargo_manual(
        *,
        cliente_id: int,
        monto: str | Decimal,
        concepto: str,
        usuario,
    ) -> MovimientoCredito:
        """
        Registra un cargo manual (Ajuste/Penalidad) a la cuenta de crédito de un cliente.
        
        Aumenta el saldo_actual del cliente y registra un MovimientoCredito
        de tipo AJUSTE que refleja el incremento de la deuda.
        
        Args:
            cliente_id: El ID del cliente a afectar.
            monto: Monto a cargar (debe ser estricta y positivamente decimal).
            concepto: Razón o motivo del manual.
            usuario: Usuario que realiza el movimiento u operación (para auditoría).
            
        Raises:
            ValidationError: Si el monto es inválido, menor o igual a 0, 
                             o si la longitud del concepto es nula.
            Cliente.DoesNotExist: Si el cliente no existe.
        """
        try:
            monto_decimal = Decimal(str(monto))
        except (ValueError, TypeError, KeyboardInterrupt):
            raise ValidationError(_("El monto especificado no es un número válido."))
            
        if monto_decimal <= 0:
            raise ValidationError(_("El monto del cargo debe ser mayor a cero."))
            
        concepto = concepto.strip()
        if not concepto:
            raise ValidationError(_("Debe especificar un concepto o justificación para el cargo manual."))

        # Bloqueo optimista de la fila del cliente en base de datos 
        # (previene race conditions durante concurrencia de transacciones)
        cliente = Cliente.objects.select_for_update().get(pk=cliente_id)
        
        saldo_anterior = cliente.saldo_actual
        saldo_nuevo = saldo_anterior + monto_decimal
        
        # 1. Actualizar desnormalizado en el cliente
        cliente.saldo_actual = saldo_nuevo
        cliente.save(update_fields=['saldo_actual', 'updated_at'])
        
        # 2. Registrar el movimiento en el Ledger (Auditoría inmutable)
        movimiento = MovimientoCredito.objects.create(
            cliente=cliente,
            tipo=MovimientoCredito.TipoMovimiento.AJUSTE,
            monto=monto_decimal,
            saldo_anterior=saldo_anterior,
            saldo_nuevo=saldo_nuevo,
            descripcion=f"Cargo Manual: {concepto}",
            usuario=usuario,
        )
        
        return movimiento

    @staticmethod
    def obtener_movimientos_recientes(cliente_id: int, limite: int = 50) -> list[dict]:
        """
        CQRS Read Model: Obtiene y unifica los movimientos recientes
        de un cliente en un formato de abstracción simple ideal para la UI.
        Prioritiza la lectura de MovimientoCredito ordenado por fecha.
        """
        # Obtenemos los movimientos optimizando joins si es necesario
        movimientos = MovimientoCredito.objects.filter(
            cliente_id=cliente_id
        ).select_related('venta').order_by('-fecha')[:limite]

        resultados = []
        for mov in movimientos:
            # Determinar el concepto optimizado para la pantalla
            concepto = mov.descripcion
            if mov.venta_id:
                # Si está ligado a una venta directamente, darle prioridad al folio
                concepto = f"VENTA {mov.venta.folio}" if hasattr(mov.venta, 'folio') else f"VENTA #{mov.venta.id}"

            # Determinar el signo matemático
            # Un Abono disminuye la deuda, por lo tanto matemáticamente para el UI es negativo o simplemente "ABONO"
            # Un Cargo/Ajuste incrementa la deuda.
            es_abono = mov.tipo == MovimientoCredito.TipoMovimiento.ABONO_PAGO
            monto_ui = -mov.monto if es_abono else mov.monto

            # Etiqueta para frontend
            etiqueta_tipo = "ABONO" if es_abono else "CARGO"
            if mov.tipo == MovimientoCredito.TipoMovimiento.AJUSTE:
                etiqueta_tipo = "AJUSTE"

            resultados.append({
                "id": str(mov.id),
                "fecha": mov.fecha.isoformat(),
                "concepto": concepto,
                "monto": str(monto_ui),
                "tipo": etiqueta_tipo
            })
            
        return resultados
