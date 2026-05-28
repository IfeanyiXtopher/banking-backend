"""Filter admin portal data for admins with SELECTED customer scope."""

from __future__ import annotations

import uuid
from typing import FrozenSet

from django.db.models import Q, QuerySet
from rest_framework.exceptions import PermissionDenied

from apps.accounts.models import Account
from apps.users.models import CustomUser, StaffCustomerAssignment


def staff_has_unrestricted_access(user: CustomUser) -> bool:
    if not user or not user.is_authenticated:
        return False
    if user.role == CustomUser.Role.SUPER_ADMIN:
        return True
    return user.admin_account_scope == CustomUser.AdminAccessScope.ALL


def staff_assigned_customer_ids(user: CustomUser) -> FrozenSet[uuid.UUID] | None:
    """None = unrestricted (all customers)."""
    if staff_has_unrestricted_access(user):
        return None
    return frozenset(
        StaffCustomerAssignment.objects.filter(staff=user).values_list('customer_id', flat=True),
    )


def staff_assigned_owner_ids(user: CustomUser) -> FrozenSet[uuid.UUID] | None:
    return staff_assigned_customer_ids(user)


def staff_assigned_account_ids(user: CustomUser) -> FrozenSet[uuid.UUID] | None:
    """All accounts owned by assigned customers."""
    customer_ids = staff_assigned_customer_ids(user)
    if customer_ids is None:
        return None
    if not customer_ids:
        return frozenset()
    return frozenset(
        Account.objects.filter(owner_id__in=customer_ids).values_list('id', flat=True),
    )


def filter_accounts(qs: QuerySet, user: CustomUser) -> QuerySet:
    customer_ids = staff_assigned_customer_ids(user)
    if customer_ids is None:
        return qs
    return qs.filter(owner_id__in=customer_ids)


def filter_transactions(qs: QuerySet, user: CustomUser) -> QuerySet:
    ids = staff_assigned_account_ids(user)
    if ids is None:
        return qs
    return qs.filter(Q(from_account_id__in=ids) | Q(to_account_id__in=ids)).distinct()


def filter_customers(qs: QuerySet, user: CustomUser) -> QuerySet:
    customer_ids = staff_assigned_customer_ids(user)
    if customer_ids is None:
        return qs
    return qs.filter(id__in=customer_ids)


def filter_compliance_fee_lines(qs: QuerySet, user: CustomUser) -> QuerySet:
    """Global lines (user=null) are visible only to super admins."""
    if user.role == CustomUser.Role.SUPER_ADMIN:
        return qs
    customer_ids = staff_assigned_customer_ids(user)
    if customer_ids is None:
        return qs.filter(user__isnull=False)
    return qs.filter(user_id__in=customer_ids)


def filter_regulated_sessions(qs: QuerySet, user: CustomUser) -> QuerySet:
    ids = staff_assigned_account_ids(user)
    if ids is None:
        return qs
    customer_ids = staff_assigned_customer_ids(user) or frozenset()
    return qs.filter(Q(from_account_id__in=ids) | Q(user_id__in=customer_ids))


def assert_account_in_scope(user: CustomUser, account_id) -> None:
    ids = staff_assigned_account_ids(user)
    if ids is None:
        return
    if account_id not in ids:
        raise PermissionDenied('This account is outside your assigned customers.')


def compliance_owner_id_from_validated(validated_data) -> uuid.UUID | None:
    """Resolve customer id from DRF validated_data (`user` instance or `user_id`)."""
    user = validated_data.get('user')
    if user is not None:
        return getattr(user, 'pk', user)
    if 'user_id' in validated_data:
        return validated_data.get('user_id')
    return None


def assert_owner_in_scope(user: CustomUser, owner_id) -> None:
    customer_ids = staff_assigned_customer_ids(user)
    if customer_ids is None:
        return
    if owner_id not in customer_ids:
        raise PermissionDenied('This customer is outside your assigned portfolio.')


def assert_transaction_in_scope(user: CustomUser, tx) -> None:
    ids = staff_assigned_account_ids(user)
    if ids is None:
        return
    from_id = getattr(tx, 'from_account_id', None)
    to_id = getattr(tx, 'to_account_id', None)
    if (from_id and from_id in ids) or (to_id and to_id in ids):
        return
    raise PermissionDenied('This transaction is outside your assigned customers.')


def assert_can_manage_global_compliance(user: CustomUser) -> None:
    if user.role == CustomUser.Role.SUPER_ADMIN:
        return
    raise PermissionDenied('Only super admins can manage global compliance fee lines.')


def assert_can_create_global_compliance(user: CustomUser) -> None:
    assert_can_manage_global_compliance(user)


def set_staff_customer_assignments(
    staff: CustomUser,
    customer_ids: list,
    assigned_by: CustomUser | None,
) -> None:
    StaffCustomerAssignment.objects.filter(staff=staff).delete()
    if not customer_ids:
        return
    customers = CustomUser.objects.filter(id__in=customer_ids, role=CustomUser.Role.CUSTOMER)
    StaffCustomerAssignment.objects.bulk_create(
        [
            StaffCustomerAssignment(staff=staff, customer=c, assigned_by=assigned_by)
            for c in customers
        ],
        ignore_conflicts=True,
    )


def assigned_customers_payload(staff: CustomUser) -> list[dict]:
    rows = (
        StaffCustomerAssignment.objects.filter(staff=staff)
        .select_related('customer')
        .order_by('customer__full_name')
    )
    result = []
    for row in rows:
        c = row.customer
        account_count = c.accounts.count()
        result.append({
            'id': str(c.id),
            'full_name': c.full_name,
            'email': c.email,
            'account_count': account_count,
        })
    return result
