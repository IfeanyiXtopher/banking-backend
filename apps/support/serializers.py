from rest_framework import serializers
from .models import SupportTicket, TicketMessage


class TicketMessageSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.full_name', read_only=True)
    is_staff = serializers.BooleanField(source='author.is_staff', read_only=True)

    class Meta:
        model = TicketMessage
        fields = ['id', 'author_name', 'is_staff', 'body', 'attachment', 'created_at']
        read_only_fields = ['id', 'author_name', 'is_staff', 'created_at']


class SupportTicketSerializer(serializers.ModelSerializer):
    messages = TicketMessageSerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)

    class Meta:
        model = SupportTicket
        fields = [
            'id', 'ticket_number', 'customer_name', 'subject', 'status',
            'priority', 'related_transaction', 'messages', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'ticket_number', 'status', 'customer_name', 'created_at', 'updated_at']


class SupportTicketCreateSerializer(serializers.ModelSerializer):
    initial_message = serializers.CharField(write_only=True)

    class Meta:
        model = SupportTicket
        fields = ['subject', 'priority', 'related_transaction', 'initial_message']

    def create(self, validated_data):
        initial_message = validated_data.pop('initial_message')
        ticket = SupportTicket.objects.create(**validated_data)
        TicketMessage.objects.create(
            ticket=ticket,
            author=validated_data.get('customer') or self.context['request'].user,
            body=initial_message,
        )
        return ticket


class AddMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketMessage
        fields = ['body', 'attachment']
