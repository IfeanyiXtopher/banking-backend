import uuid
from django.db import models
from django.conf import settings


class LoanProduct(models.Model):
    class LoanType(models.TextChoices):
        PERSONAL = 'PERSONAL', 'Personal Loan'
        MORTGAGE = 'MORTGAGE', 'Mortgage / Home Loan'
        AUTO = 'AUTO', 'Auto Loan'
        BUSINESS = 'BUSINESS', 'Business Loan'
        EDUCATION = 'EDUCATION', 'Education Loan'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    loan_type = models.CharField(max_length=20, choices=LoanType.choices)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=4, help_text='Annual rate, e.g. 0.1200 = 12%')
    min_amount = models.DecimalField(max_digits=18, decimal_places=2)
    max_amount = models.DecimalField(max_digits=18, decimal_places=2)
    min_term_months = models.PositiveIntegerField(default=1)
    max_term_months = models.PositiveIntegerField()
    description = models.TextField(blank=True, help_text='Short summary on loan cards.')
    tagline = models.CharField(max_length=280, blank=True, help_text='One-line pitch in the product modal header.')
    full_description = models.TextField(blank=True, help_text='Long-form copy shown in the product detail modal.')
    hero_image = models.ImageField(upload_to='loans/products/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.name} ({self.loan_type})'


class LoanApplication(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        SUBMITTED = 'SUBMITTED', 'Submitted'
        UNDER_REVIEW = 'UNDER_REVIEW', 'Under Review'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
        DISBURSED = 'DISBURSED', 'Disbursed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='loan_applications'
    )
    product = models.ForeignKey(LoanProduct, on_delete=models.PROTECT, related_name='applications')
    requested_amount = models.DecimalField(max_digits=18, decimal_places=2)
    term_months = models.PositiveIntegerField()
    purpose = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='reviewed_loan_applications',
    )
    review_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.product.name} application by {self.applicant.email}'


class LoanAccount(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        PAID_OFF = 'PAID_OFF', 'Paid Off'
        DEFAULTED = 'DEFAULTED', 'Defaulted'
        WRITTEN_OFF = 'WRITTEN_OFF', 'Written Off'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.OneToOneField(LoanApplication, on_delete=models.PROTECT, related_name='loan_account')
    principal_amount = models.DecimalField(max_digits=18, decimal_places=2)
    outstanding_balance = models.DecimalField(max_digits=18, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=4)
    term_months = models.PositiveIntegerField()
    monthly_payment = models.DecimalField(max_digits=18, decimal_places=2)
    disbursement_account = models.ForeignKey(
        'accounts.Account', on_delete=models.PROTECT, related_name='loan_disbursements'
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    disbursed_at = models.DateTimeField(null=True, blank=True)
    next_payment_due = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Loan #{self.id} — {self.outstanding_balance} outstanding'


class RepaymentSchedule(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        PAID = 'PAID', 'Paid'
        OVERDUE = 'OVERDUE', 'Overdue'
        WAIVED = 'WAIVED', 'Waived'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    loan_account = models.ForeignKey(LoanAccount, on_delete=models.CASCADE, related_name='schedule')
    installment_number = models.PositiveIntegerField()
    due_date = models.DateField()
    principal_amount = models.DecimalField(max_digits=18, decimal_places=2)
    interest_amount = models.DecimalField(max_digits=18, decimal_places=2)
    total_amount = models.DecimalField(max_digits=18, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['installment_number']
        unique_together = ['loan_account', 'installment_number']

    def __str__(self):
        return f'Installment {self.installment_number} — {self.due_date}'
