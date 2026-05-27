"""Default card tier / design for each account product (matches customer CardWidget variants)."""
from apps.accounts.models import Account


def default_card_tier_for_account_type(account_type: str) -> str:
    if account_type == Account.AccountType.SAVINGS:
        return 'CREDIT_LINE'
    if account_type in (Account.AccountType.CREDIT, Account.AccountType.BUSINESS):
        return 'PREMIUM'
    return 'STANDARD'


def widget_variant_for_tier(tier: str) -> str:
    """Map stored tier to frontend CardWidget variant prop."""
    if tier == 'CREDIT_LINE':
        return 'credit'
    if tier == 'PREMIUM':
        return 'premium'
    return 'standard'
