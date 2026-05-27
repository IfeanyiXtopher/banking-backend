from rest_framework.permissions import BasePermission
from apps.users.models import CustomUser


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == CustomUser.Role.SUPER_ADMIN


class IsAdminUser(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and CustomUser.is_staff_role(request.user.role)


class IsOperationsTeller(BasePermission):
    """Any bank admin (legacy name — loans, accounts, transactions)."""

    def has_permission(self, request, view):
        return IsAdminUser().has_permission(request, view)


class IsComplianceAuditor(BasePermission):
    def has_permission(self, request, view):
        return IsAdminUser().has_permission(request, view)


class IsLoanOfficer(BasePermission):
    def has_permission(self, request, view):
        return IsAdminUser().has_permission(request, view)


class IsSupportStaff(BasePermission):
    def has_permission(self, request, view):
        return IsAdminUser().has_permission(request, view)
