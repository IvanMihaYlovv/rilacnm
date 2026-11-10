import secrets

from django.conf import settings


class SecurityHeadersMiddleware:
    """
    Adds a Content-Security-Policy and a Permissions-Policy to every response.

    Inline <script> tags must carry nonce="{{ request.csp_nonce }}"; any other inline
    script is refused by the browser, which blunts an XSS bug that slips through.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.csp_nonce = secrets.token_urlsafe(16)
        response = self.get_response(request)
        nonce = f"'nonce-{request.csp_nonce}'"
        policy = '; '.join(
            ' '.join([directive, *(nonce if s == '{nonce}' else s for s in sources)])
            for directive, sources in settings.CONTENT_SECURITY_POLICY.items()
        )
        response.headers.setdefault('Content-Security-Policy', policy)
        response.headers.setdefault('Permissions-Policy', settings.PERMISSIONS_POLICY)
        return response
