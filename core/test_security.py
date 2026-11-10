import os
import subprocess
import sys

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse


PROD = {'DJANGO_SECRET_KEY': 'k' * 30 + 'abcdefghijklmnopqrst', 'DJANGO_ALLOWED_HOSTS': 'www.rila-cnm.eu'}


def load_settings(**env):
    """Import settings in a clean process with no DJANGO_* variables and no .env file."""
    base = {k: v for k, v in os.environ.items() if not k.startswith('DJANGO_')}
    names = ('DEBUG', 'SECURE_HSTS_SECONDS', 'SECURE_HSTS_INCLUDE_SUBDOMAINS', 'SECURE_HSTS_PRELOAD')
    code = ('import dotenv; dotenv.load_dotenv = lambda *a, **k: None; '
            'from rilacnm import settings as s; '
            f'print(*(getattr(s, n, None) for n in {names}))')
    return subprocess.run([sys.executable, '-c', code], cwd=settings.BASE_DIR, capture_output=True,
                          text=True, env={**base, **env})


class ProductionDefaultsTests(SimpleTestCase):
    def test_refuses_to_start_without_a_secret_key(self):
        result = load_settings()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('DJANGO_SECRET_KEY', result.stderr)

    def test_debug_is_off_unless_asked_for(self):
        result = load_settings(**PROD)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.startswith('False'))

    def test_refuses_a_weak_secret_key(self):
        for key in ('short', 'django-insecure-' + 'a' * 50):
            result = load_settings(**{**PROD, 'DJANGO_SECRET_KEY': key})
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('too weak', result.stderr)

    def test_refuses_to_start_without_allowed_hosts(self):
        result = load_settings(DJANGO_SECRET_KEY=PROD['DJANGO_SECRET_KEY'])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('DJANGO_ALLOWED_HOSTS', result.stderr)

    def test_local_development_runs_without_a_key(self):
        result = load_settings(DJANGO_DEBUG='1')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.startswith('True'))

    def test_hsts_starts_short_and_narrow(self):
        result = load_settings(**PROD)
        self.assertEqual(result.stdout.split(), ['False', '3600', 'False', 'False'])

    def test_hsts_can_be_raised(self):
        result = load_settings(**PROD, DJANGO_HSTS_SECONDS='31536000',
                               DJANGO_HSTS_PRELOAD='1')
        self.assertEqual(result.stdout.split(), ['False', '31536000', 'True', 'True'])


class PasswordPolicyTests(SimpleTestCase):
    def test_short_password_rejected(self):
        with self.assertRaises(ValidationError):
            validate_password('Xk9#mQ2$vL7')  # 11 characters

    def test_long_password_accepted(self):
        validate_password('Xk9#mQ2$vL7!')  # 12 characters


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class AdminLoginLockoutTests(TestCase):
    def setUp(self):
        self.password = 'correct-horse-battery'
        get_user_model().objects.create_superuser('admin', 'a@example.com', self.password)
        self.url = reverse('admin:login')

    def attempt(self, password, ip='203.0.113.5'):
        return self.client.post(self.url, {'username': 'admin', 'password': password},
                                REMOTE_ADDR=ip)

    def test_locked_out_after_five_failures(self):
        for _ in range(4):
            self.assertEqual(self.attempt('wrong').status_code, 200)
        self.assertEqual(self.attempt('wrong').status_code, 429)
        # Even the right password is refused during the lockout.
        self.assertEqual(self.attempt(self.password).status_code, 429)

    def test_lockout_does_not_block_other_addresses(self):
        for _ in range(5):
            self.attempt('wrong')
        self.assertEqual(self.attempt(self.password, ip='203.0.113.9').status_code, 302)

    def test_success_clears_earlier_failures(self):
        for _ in range(4):
            self.attempt('wrong')
        self.assertEqual(self.attempt(self.password).status_code, 302)
        self.client.logout()
        for _ in range(4):
            self.assertEqual(self.attempt('wrong').status_code, 200)


class ClientIpTests(SimpleTestCase):
    def ip(self, remote, forwarded=None, proxies=0):
        from django.test import RequestFactory
        from core.utils import client_ip
        meta = {'REMOTE_ADDR': remote}
        if forwarded is not None:
            meta['HTTP_X_FORWARDED_FOR'] = forwarded
        with self.settings(TRUSTED_PROXY_COUNT=proxies):
            return client_ip(RequestFactory().get('/', **meta))

    def test_without_a_proxy_the_header_is_ignored(self):
        self.assertEqual(self.ip('198.51.100.7', '1.2.3.4'), '198.51.100.7')

    def test_behind_one_proxy_uses_the_address_it_saw(self):
        self.assertEqual(self.ip('10.0.0.1', '198.51.100.7', proxies=1), '198.51.100.7')

    def test_forged_entries_to_the_left_are_ignored(self):
        self.assertEqual(self.ip('10.0.0.1', '6.6.6.6, 198.51.100.7', proxies=1), '198.51.100.7')

    def test_garbage_falls_back_to_the_socket_address(self):
        self.assertEqual(self.ip('10.0.0.1', 'not-an-ip', proxies=1), '10.0.0.1')
        self.assertEqual(self.ip('10.0.0.1', '', proxies=1), '10.0.0.1')


class SecurityHeadersTests(TestCase):
    def test_pages_send_csp_with_a_fresh_nonce(self):
        first, second = self.client.get('/'), self.client.get('/')
        csp = first.headers['Content-Security-Policy']
        self.assertIn("object-src 'none'", csp)
        self.assertIn("frame-ancestors 'none'", csp)
        nonce = first.wsgi_request.csp_nonce
        self.assertIn(f"'nonce-{nonce}'", csp)
        self.assertContains(first, f'<script nonce="{nonce}">')
        self.assertNotEqual(nonce, second.wsgi_request.csp_nonce)
        self.assertIn('camera=()', first.headers['Permissions-Policy'])

    def test_every_inline_script_carries_the_nonce(self):
        import re
        html = self.client.get('/').content.decode()
        for tag in re.findall(r'<script(?![^>]*\ssrc=)[^>]*>', html):
            if 'application/ld+json' not in tag:
                self.assertIn('nonce=', tag)

    def test_cdn_files_are_pinned_with_integrity_hashes(self):
        import re
        html = self.client.get('/').content.decode()
        tags = re.findall(r'<(?:script|link)[^>]+cdn\.jsdelivr\.net/npm/[^>]+>', html)
        self.assertTrue(tags)
        for tag in tags:
            self.assertIn('integrity="sha384-', tag)


class UploadValidationTests(SimpleTestCase):
    def test_document_links_must_be_http(self):
        from core.validators import validate_documents
        validate_documents([{'title': 'Покана', 'url': 'https://example.com/a.pdf'}])
        for bad in ('javascript:alert(1)', 'data:text/html,x', '//evil'):
            with self.assertRaises(ValidationError):
                validate_documents([{'title': 'x', 'url': bad}])

    def test_images_over_the_limit_are_rejected(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from core.validators import validate_image_size
        big = SimpleUploadedFile('big.jpg', b'0' * (10 * 1024 * 1024 + 1))
        with self.assertRaises(ValidationError):
            validate_image_size(big)
        validate_image_size(SimpleUploadedFile('ok.jpg', b'0' * 1024))
