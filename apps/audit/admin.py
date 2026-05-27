from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'actor', 'action', 'target_model', 'target_id', 'ip_address']
    list_filter = ['action', 'target_model']
    search_fields = ['actor__email', 'description', 'target_id']
    readonly_fields = ['id', 'actor', 'action', 'target_model', 'target_id', 'old_value', 'new_value', 'ip_address', 'timestamp']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
