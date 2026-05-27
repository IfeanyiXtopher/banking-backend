from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, PasswordResetToken, EmailOTPToken, ProfileChangeRequest


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ['email', 'full_name', 'role', 'kyc_status', 'is_active', 'is_mfa_enabled', 'date_joined']
    list_filter = ['role', 'kyc_status', 'is_active', 'is_staff']
    search_fields = ['email', 'full_name', 'phone']
    ordering = ['-date_joined']
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('full_name', 'phone', 'address', 'date_of_birth', 'nationality', 'profile_picture')}),
        ('Role & Status', {'fields': ('role', 'kyc_status', 'kyc_document', 'is_active', 'is_locked', 'is_mfa_enabled')}),
        ('Permissions', {'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important Dates', {'fields': ('date_joined', 'last_login')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'full_name', 'password1', 'password2', 'role'),
        }),
    )


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = ['user', 'created_at', 'expires_at', 'is_used']
    list_filter = ['is_used']


@admin.register(EmailOTPToken)
class EmailOTPTokenAdmin(admin.ModelAdmin):
    list_display = ['user', 'purpose', 'created_at', 'expires_at', 'is_used']
    list_filter = ['purpose', 'is_used']


@admin.register(ProfileChangeRequest)
class ProfileChangeRequestAdmin(admin.ModelAdmin):
    list_display = ['user', 'status', 'proposed_full_name', 'created_at', 'reviewed_at']
    list_filter = ['status']
    search_fields = ['user__email', 'proposed_full_name', 'proposed_email']
    readonly_fields = ['created_at', 'reviewed_at', 'reviewed_by']
