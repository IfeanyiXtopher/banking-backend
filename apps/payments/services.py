from decimal import Decimal

from .models import PaymentFeeSettings, PaymentManagementFeeOverride


def resolve_management_fee(service_id: str, biller_id: str) -> Decimal:
    service_id = (service_id or '').strip()
    biller_id = (biller_id or '').strip()
    if not service_id or not biller_id:
        raise ValueError('service_id and biller_id are required.')
    override = PaymentManagementFeeOverride.objects.filter(
        service_id=service_id,
        biller_id=biller_id,
    ).first()
    if override is not None:
        return Decimal(str(override.management_fee))
    return Decimal(str(PaymentFeeSettings.get_solo().default_management_fee))
