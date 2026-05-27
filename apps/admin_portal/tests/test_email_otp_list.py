"""Admin portal can list all customer email OTPs (help desk)."""
import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.users.models import CustomUser, EmailOTPToken
from apps.users.email_otp import create_email_otp, PURPOSE_TRANSFER_AUTH


@pytest.fixture
def admin_user(db):
    return CustomUser.objects.create_user(
        email='admin@bank.test',
        full_name='Admin User',
        password='AdminPass123!',
        role=CustomUser.Role.SUPER_ADMIN,
    )


@pytest.fixture
def customer(db):
    return CustomUser.objects.create_user(
        email='customer@bank.test',
        full_name='Customer User',
        password='CustPass123!',
    )


@pytest.mark.django_db
class TestAdminEmailOTPList:
    def test_admin_lists_otp_plaintext(self, admin_user, customer):
        code = create_email_otp(customer, PURPOSE_TRANSFER_AUTH)
        client = APIClient()
        client.force_authenticate(user=admin_user)
        url = reverse('admin-email-otp-list')
        res = client.get(url, {'user': customer.email})
        assert res.status_code == 200
        results = res.data['results'] if isinstance(res.data, dict) else res.data
        assert any(r['token'] == code for r in results)
        assert any(r['purpose'] == PURPOSE_TRANSFER_AUTH for r in results)

    def test_customer_cannot_list_otps(self, customer):
        create_email_otp(customer, PURPOSE_TRANSFER_AUTH)
        client = APIClient()
        client.force_authenticate(user=customer)
        url = reverse('admin-email-otp-list')
        res = client.get(url)
        assert res.status_code == 403
