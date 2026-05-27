from django.contrib import admin
from .models import LoanProduct, LoanApplication, LoanAccount, RepaymentSchedule


@admin.register(LoanProduct)
class LoanProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'loan_type', 'interest_rate', 'min_amount', 'max_amount', 'is_active']
    list_filter = ['loan_type', 'is_active']


@admin.register(LoanApplication)
class LoanApplicationAdmin(admin.ModelAdmin):
    list_display = ['applicant', 'product', 'requested_amount', 'term_months', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['applicant__email', 'product__name']


@admin.register(LoanAccount)
class LoanAccountAdmin(admin.ModelAdmin):
    list_display = ['id', 'principal_amount', 'outstanding_balance', 'status', 'disbursed_at']
    list_filter = ['status']


@admin.register(RepaymentSchedule)
class RepaymentScheduleAdmin(admin.ModelAdmin):
    list_display = ['loan_account', 'installment_number', 'due_date', 'total_amount', 'status']
    list_filter = ['status']
