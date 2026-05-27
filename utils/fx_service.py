"""FX rate polling via Open Exchange Rates API."""
import requests
from django.conf import settings
from apps.transactions.models import ExchangeRate
import logging

logger = logging.getLogger(__name__)


def fetch_and_update_rates():
    api_key = settings.FX_RATES_API_KEY
    base_url = settings.FX_RATES_BASE_URL
    if not api_key:
        logger.warning('FX_RATES_API_KEY not configured, skipping rate fetch.')
        return

    try:
        response = requests.get(
            f'{base_url}/latest.json',
            params={'app_id': api_key},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        rates = data.get('rates', {})
        base = data.get('base', 'USD')

        updated = 0
        for currency, rate in rates.items():
            ExchangeRate.objects.update_or_create(
                from_currency=base,
                to_currency=currency,
                defaults={'rate': rate},
            )
            updated += 1

        logger.info(f'Updated {updated} exchange rates.')
    except Exception as e:
        logger.error(f'Failed to fetch FX rates: {e}')
        raise
