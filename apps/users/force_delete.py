"""Cascade-delete a user and all banking data linked to them (admin force delete)."""

from __future__ import annotations

from django.db import transaction
from django.db.models import Q

from apps.accounts.models import Account
from apps.loans.models import LoanAccount, LoanApplication, RepaymentSchedule
from apps.support.models import SupportTicket, TicketMessage
from apps.transactions.admin_transaction import admin_delete_transactions
from apps.transactions.models import Transaction
from apps.transactions.regulated_models import RegulatedTransferSession
from apps.users.models import CustomUser, StaffCustomerAssignment


def _delete_regulated_sessions(session_qs, *, actor) -> None:
    for session in session_qs.select_related('transfer_transaction').prefetch_related('lines'):
        tx_ids = []
        if session.transfer_transaction_id:
            tx_ids.append(str(session.transfer_transaction_id))
        for line in session.lines.all():
            if line.fee_transaction_id:
                tx_ids.append(str(line.fee_transaction_id))
        if tx_ids:
            admin_delete_transactions(tx_ids, actor=actor)
        session.delete()


def _delete_loan_application(application: LoanApplication, *, actor) -> None:
    _delete_regulated_sessions(
        RegulatedTransferSession.objects.filter(loan_application_id=application.id),
        actor=actor,
    )
    try:
        loan_account = application.loan_account
    except LoanAccount.DoesNotExist:
        loan_account = None
    if loan_account:
        RepaymentSchedule.objects.filter(loan_account=loan_account).delete()
        loan_account.delete()
    application.delete()


@transaction.atomic
def force_delete_user(user: CustomUser, *, actor) -> dict:
    """
    Permanently remove user and linked portfolio (accounts, transactions, loans, tickets, etc.).
    Returns counts for audit logging.
    """
    user_id = user.id
    account_ids = list(Account.objects.filter(owner_id=user_id).values_list('id', flat=True))

    _delete_regulated_sessions(
        RegulatedTransferSession.objects.filter(
            Q(user_id=user_id)
            | Q(from_account__owner_id=user_id)
            | Q(loan_application__applicant_id=user_id),
        ),
        actor=actor,
    )

    for application in LoanApplication.objects.filter(applicant_id=user_id):
        _delete_loan_application(application, actor=actor)

    tx_filter = Q(initiated_by_id=user_id) | Q(reversed_by_id=user_id)
    if account_ids:
        tx_filter |= Q(from_account_id__in=account_ids) | Q(to_account_id__in=account_ids)
    tx_ids = [str(pk) for pk in Transaction.objects.filter(tx_filter).values_list('id', flat=True)]
    deleted_tx_count = admin_delete_transactions(tx_ids, actor=actor) if tx_ids else 0

    customer_ticket_ids = list(
        SupportTicket.objects.filter(customer_id=user_id).values_list('id', flat=True),
    )
    if customer_ticket_ids:
        TicketMessage.objects.filter(ticket_id__in=customer_ticket_ids).delete()
        SupportTicket.objects.filter(id__in=customer_ticket_ids).delete()
    TicketMessage.objects.filter(author_id=user_id).delete()

    StaffCustomerAssignment.objects.filter(Q(staff_id=user_id) | Q(assigned_by_id=user_id)).delete()

    deleted_accounts, _ = Account.objects.filter(owner_id=user_id).delete()

    email = user.email
    user.delete()

    return {
        'email': email,
        'deleted_transactions': deleted_tx_count,
        'deleted_accounts': deleted_accounts,
    }
