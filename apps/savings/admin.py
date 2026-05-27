from django.contrib import admin

from .models import SavingsGoal


@admin.register(SavingsGoal)
class SavingsGoalAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'saved_balance', 'target_amount', 'status', 'created_at')
    list_filter = ('status', 'category')
    search_fields = ('title', 'owner__email')
