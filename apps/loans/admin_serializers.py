from rest_framework import serializers

from .models import LoanApplication, LoanProduct


class LoanProductPublicSerializer(serializers.ModelSerializer):
    hero_image_url = serializers.SerializerMethodField()

    class Meta:
        model = LoanProduct
        fields = [
            'id', 'name', 'loan_type', 'interest_rate',
            'min_amount', 'max_amount', 'min_term_months', 'max_term_months',
            'description', 'tagline', 'full_description', 'hero_image_url', 'is_active',
        ]

    def get_hero_image_url(self, obj):
        if not obj.hero_image:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.hero_image.url)
        return obj.hero_image.url


class AdminLoanProductSerializer(serializers.ModelSerializer):
    hero_image_url = serializers.SerializerMethodField()
    application_count = serializers.SerializerMethodField()
    clear_hero_image = serializers.BooleanField(required=False, write_only=True, default=False)

    class Meta:
        model = LoanProduct
        fields = [
            'id', 'name', 'loan_type', 'interest_rate',
            'min_amount', 'max_amount', 'min_term_months', 'max_term_months',
            'description', 'tagline', 'full_description', 'hero_image', 'hero_image_url',
            'is_active', 'created_at', 'application_count', 'clear_hero_image',
        ]
        read_only_fields = ['id', 'created_at', 'hero_image_url', 'application_count']

    def update(self, instance, validated_data):
        clear_image = validated_data.pop('clear_hero_image', False)
        if clear_image and instance.hero_image:
            instance.hero_image.delete(save=False)
            instance.hero_image = None
        return super().update(instance, validated_data)

    def get_hero_image_url(self, obj):
        if not obj.hero_image:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.hero_image.url)
        return obj.hero_image.url

    def get_application_count(self, obj):
        return LoanApplication.objects.filter(product_id=obj.id).count()

    def validate(self, attrs):
        min_amount = attrs.get('min_amount', getattr(self.instance, 'min_amount', None))
        max_amount = attrs.get('max_amount', getattr(self.instance, 'max_amount', None))
        min_term = attrs.get('min_term_months', getattr(self.instance, 'min_term_months', None))
        max_term = attrs.get('max_term_months', getattr(self.instance, 'max_term_months', None))
        if min_amount is not None and max_amount is not None and min_amount > max_amount:
            raise serializers.ValidationError({'max_amount': 'Must be greater than or equal to minimum amount.'})
        if min_term is not None and max_term is not None and min_term > max_term:
            raise serializers.ValidationError({'max_term_months': 'Must be greater than or equal to minimum term.'})
        return attrs
