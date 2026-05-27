from rest_framework import serializers
from .models import Statement


class StatementSerializer(serializers.ModelSerializer):
    account_number = serializers.CharField(source='account.account_number', read_only=True)
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = Statement
        fields = ['id', 'account', 'account_number', 'period_start', 'period_end', 'generated_at', 'download_url']
        read_only_fields = ['id', 'generated_at']

    def get_download_url(self, obj):
        request = self.context.get('request')
        if obj.pdf_file and request:
            return request.build_absolute_uri(obj.pdf_file.url)
        return None


class StatementRequestSerializer(serializers.Serializer):
    account_id = serializers.UUIDField()
    period_start = serializers.DateField()
    period_end = serializers.DateField()
    email = serializers.EmailField(required=True)
    e_signed = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs):
        if attrs['period_start'] >= attrs['period_end']:
            raise serializers.ValidationError('period_start must be before period_end.')
        return attrs
