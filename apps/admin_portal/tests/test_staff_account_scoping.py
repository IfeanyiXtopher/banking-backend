"""Admin customer-scope: assigned admins only see their customers' data."""
import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import Account
from apps.accounts.services import provision_primary_bank_account
from apps.users.models import CustomUser, StaffCustomerAssignment


@pytest.fixture
def super_admin(db):
    return CustomUser.objects.create_user(
        email='super@bank.test',
        full_name='Super Admin',
        password='AdminPass123!',
        role=CustomUser.Role.SUPER_ADMIN,
        is_staff=True,
    )


@pytest.fixture
def scoped_admin(db):
    return CustomUser.objects.create_user(
        email='scoped@bank.test',
        full_name='Scoped Admin',
        password='StaffPass123!',
        role=CustomUser.Role.ADMIN,
        is_staff=True,
        admin_account_scope=CustomUser.AdminAccessScope.SELECTED,
    )


@pytest.fixture
def customer_a(db):
    user = CustomUser.objects.create_user(
        email='customer-a@bank.test',
        full_name='Customer A',
        password='CustPass123!',
    )
    provision_primary_bank_account(user)
    return user


@pytest.fixture
def customer_b(db):
    user = CustomUser.objects.create_user(
        email='customer-b@bank.test',
        full_name='Customer B',
        password='CustPass123!',
    )
    provision_primary_bank_account(user)
    return user


@pytest.fixture
def assign_admin_to_customer_a(scoped_admin, customer_a):
    StaffCustomerAssignment.objects.create(staff=scoped_admin, customer=customer_a)
    return customer_a


@pytest.mark.django_db
class TestStaffCustomerScoping:
    def test_scoped_admin_sees_all_accounts_for_assigned_customer(
        self, scoped_admin, customer_a, customer_b, assign_admin_to_customer_a,
    ):
        client = APIClient()
        client.force_authenticate(user=scoped_admin)
        url = reverse('admin-account-list')
        res = client.get(url)
        assert res.status_code == 200
        results = res.data['results'] if isinstance(res.data, dict) else res.data
        numbers = {r['account_number'] for r in results}
        assert customer_a.accounts.first().account_number in numbers
        assert customer_b.accounts.first().account_number not in numbers

    def test_admin_with_all_scope_cannot_create_global_compliance(self, super_admin, db):
        admin_all = CustomUser.objects.create_user(
            email='admin-all@bank.test',
            full_name='Admin All',
            password='StaffPass123!',
            role=CustomUser.Role.ADMIN,
            is_staff=True,
            admin_account_scope=CustomUser.AdminAccessScope.ALL,
        )
        client = APIClient()
        client.force_authenticate(user=admin_all)
        url = reverse('admin-compliance-fee-line-list')
        res = client.post(
            url,
            {
                'code': 'admin-all-global',
                'name': 'Test',
                'flat_amount': '10.00',
                'percentage': '0',
                'min_amount': '0',
                'max_amount': '0',
                'is_active': True,
                'sort_order': 0,
            },
            format='json',
        )
        assert res.status_code == 403

    def test_scoped_admin_cannot_create_global_compliance_fee(
        self, scoped_admin, assign_admin_to_customer_a,
    ):
        client = APIClient()
        client.force_authenticate(user=scoped_admin)
        url = reverse('admin-compliance-fee-line-list')
        res = client.post(
            url,
            {
                'code': 'scoped-global-block',
                'name': 'Test',
                'flat_amount': '10.00',
                'percentage': '0',
                'min_amount': '0',
                'max_amount': '0',
                'is_active': True,
                'sort_order': 0,
            },
            format='json',
        )
        assert res.status_code == 403
        assert 'global' in str(res.data.get('detail', '')).lower()

    def test_super_admin_creates_scoped_admin(self, super_admin, customer_a):
        client = APIClient()
        client.force_authenticate(user=super_admin)
        url = reverse('admin-user-create-staff')
        res = client.post(
            url,
            {
                'email': 'newscoped@bank.test',
                'full_name': 'New Admin',
                'password': 'NewStaffPass123!',
                'password_confirm': 'NewStaffPass123!',
                'role': 'ADMIN',
                'admin_account_scope': 'SELECTED',
                'assigned_customer_ids': [str(customer_a.id)],
            },
            format='json',
        )
        assert res.status_code == 201
        user = CustomUser.objects.get(email='newscoped@bank.test')
        assert user.role == CustomUser.Role.ADMIN
        assert user.admin_account_scope == CustomUser.AdminAccessScope.SELECTED
        assert StaffCustomerAssignment.objects.filter(staff=user, customer=customer_a).exists()

    def test_delete_admin(self, super_admin, scoped_admin):
        client = APIClient()
        client.force_authenticate(user=super_admin)
        url = reverse('admin-user-detail', kwargs={'pk': scoped_admin.id})
        res = client.delete(url)
        assert res.status_code == 200

    def test_admin_impersonates_customer(self, super_admin, customer_a):
        client = APIClient()
        client.force_authenticate(user=super_admin)
        url = reverse('admin-impersonate-customer', kwargs={'pk': customer_a.id})
        res = client.post(url)
        assert res.status_code == 200
        assert res.data['access']
        assert res.data['refresh']
        assert res.data['user']['email'] == customer_a.email
        assert res.data['user']['role'] == 'CUSTOMER'

    def test_scoped_admin_cannot_impersonate_unassigned_customer(
        self, scoped_admin, customer_a, customer_b,
    ):
        client = APIClient()
        client.force_authenticate(user=scoped_admin)
        url = reverse('admin-impersonate-customer', kwargs={'pk': customer_b.id})
        res = client.post(url)
        assert res.status_code == 403

    def test_force_delete_customer_with_account(self, super_admin, customer_a):
        assert customer_a.accounts.exists()
        client = APIClient()
        client.force_authenticate(user=super_admin)
        url = reverse('admin-user-detail', kwargs={'pk': customer_a.id})
        res = client.delete(url)
        assert res.status_code == 200
        assert not CustomUser.objects.filter(pk=customer_a.id).exists()
        assert not Account.objects.filter(owner_id=customer_a.id).exists()
