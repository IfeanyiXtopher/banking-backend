class AuditMiddleware:
    """Attaches request IP and user-agent to thread-local for use in audit logging."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    @staticmethod
    def get_client_ip(request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')


class CustomerActivityAuditMiddleware:
    """Records successful customer API mutations in the audit log."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            from .customer_audit import maybe_audit_customer_request

            maybe_audit_customer_request(request, response)
        except Exception:
            pass
        return response
