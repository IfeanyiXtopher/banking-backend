from rest_framework import serializers
from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.EmailField(source='actor.email', read_only=True, allow_null=True)
    actor_name = serializers.CharField(source='actor.full_name', read_only=True, allow_null=True)
    actor_role = serializers.CharField(source='actor.role', read_only=True, allow_null=True)

    class Meta:
        model = AuditLog
        fields = [
            'id', 'actor_email', 'actor_name', 'actor_role', 'action', 'target_model', 'target_id',
            'old_value', 'new_value', 'description', 'ip_address', 'timestamp',
        ]
        read_only_fields = fields
