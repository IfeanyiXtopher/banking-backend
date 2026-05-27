from decimal import Decimal, ROUND_HALF_UP
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from django.db import transaction as db_transaction
from django.utils import timezone

from .models import LoanApplication, LoanAccount, RepaymentSchedule
from apps.transactions.services import deposit, withdraw
from apps.transactions.models import Transaction


def calculate_monthly_payment(principal: Decimal, annual_rate: Decimal, term_months: int) -> Decimal:
    if annual_rate == 0:
        return (principal / term_months).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    monthly_rate = annual_rate / 12
    payment = principal * (monthly_rate * (1 + monthly_rate) ** term_months) / ((1 + monthly_rate) ** term_months - 1)
    return payment.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def generate_repayment_schedule(loan_account: LoanAccount):
    principal = loan_account.principal_amount
    annual_rate = loan_account.interest_rate
    monthly_rate = annual_rate / 12
    term = loan_account.term_months
    monthly_payment = loan_account.monthly_payment
    start_date = loan_account.disbursed_at.date() if loan_account.disbursed_at else date.today()
    balance = principal
    schedules = []

    for i in range(1, term + 1):
        due_date = start_date + relativedelta(months=i)
        interest = (balance * monthly_rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        principal_portion = (monthly_payment - interest).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        if i == term:
            principal_portion = balance
            monthly_payment_final = principal_portion + interest
        else:
            monthly_payment_final = monthly_payment
        balance -= principal_portion
        schedules.append(RepaymentSchedule(
            loan_account=loan_account,
            installment_number=i,
            due_date=due_date,
            principal_amount=principal_portion,
            interest_amount=interest,
            total_amount=monthly_payment_final,
        ))

    RepaymentSchedule.objects.bulk_create(schedules)


@db_transaction.atomic
def disburse_loan(
    application_id: str,
    disbursement_account_id: str,
    initiated_by,
    enforce_applicant_account: bool = False,
) -> LoanAccount:
    application = LoanApplication.objects.select_for_update().get(id=application_id)
    if application.status != LoanApplication.Status.APPROVED:
        raise ValueError('Only approved loan applications can be disbursed.')

    from apps.accounts.models import Account
    disbursement_account = Account.objects.get(id=disbursement_account_id)

    if enforce_applicant_account and disbursement_account.owner_id != application.applicant_id:
        raise ValueError('Disbursement account must belong to the loan applicant.')

    monthly_payment = calculate_monthly_payment(
        application.requested_amount,
        application.product.interest_rate,
        application.term_months,
    )

    loan_account = LoanAccount.objects.create(
        application=application,
        principal_amount=application.requested_amount,
        outstanding_balance=application.requested_amount,
        interest_rate=application.product.interest_rate,
        term_months=application.term_months,
        monthly_payment=monthly_payment,
        disbursement_account=disbursement_account,
        disbursed_at=timezone.now(),
        next_payment_due=(date.today() + relativedelta(months=1)),
    )

    generate_repayment_schedule(loan_account)

    deposit(
        account_id=str(disbursement_account.id),
        amount=application.requested_amount,
        description=f'Loan disbursement — {application.product.name}',
        initiated_by=initiated_by,
    )

    application.status = LoanApplication.Status.DISBURSED
    application.save(update_fields=['status', 'updated_at'])

    return loan_account


@db_transaction.atomic
def make_loan_payment(loan_account_id: str, from_account_id: str, amount: Decimal, initiated_by) -> Transaction:
    loan_account = LoanAccount.objects.select_for_update().get(id=loan_account_id)
    if loan_account.status != LoanAccount.Status.ACTIVE:
        raise ValueError('Loan account is not active.')

    tx = withdraw(
        account_id=from_account_id,
        amount=amount,
        description=f'Loan payment — #{loan_account_id}',
        initiated_by=initiated_by,
    )

    loan_account.outstanding_balance -= amount
    if loan_account.outstanding_balance <= 0:
        loan_account.outstanding_balance = Decimal('0')
        loan_account.status = LoanAccount.Status.PAID_OFF

    next_schedule = loan_account.schedule.filter(
        status=RepaymentSchedule.Status.PENDING
    ).order_by('installment_number').first()
    if next_schedule:
        next_schedule.paid_amount = amount
        next_schedule.status = RepaymentSchedule.Status.PAID
        next_schedule.paid_at = timezone.now()
        next_schedule.save()

        upcoming = loan_account.schedule.filter(
            status=RepaymentSchedule.Status.PENDING
        ).order_by('installment_number').first()
        if upcoming:
            loan_account.next_payment_due = upcoming.due_date

    loan_account.save()
    return tx
