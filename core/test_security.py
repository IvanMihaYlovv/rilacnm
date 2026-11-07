import os
import subprocess
import sys

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse


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
        result = load_settings(DJANGO_SECRET_KEY='x' * 50)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.startswith('False'))

    def test_local_development_runs_without_a_key(self):
        result = load_settings(DJANGO_DEBUG='1')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.startswith('True'))

    def test_hsts_starts_short_and_narrow(self):
        result = load_settings(DJANGO_SECRET_KEY='x' * 50)
        self.assertEqual(result.stdout.split(), ['False', '3600', 'False', 'False'])

    def test_hsts_can_be_raised(self):
        result = load_settings(DJANGO_SECRET_KEY='x' * 50, DJANGO_HSTS_SECONDS='31536000',
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
