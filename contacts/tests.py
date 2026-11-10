from unittest.mock import patch

from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from catalog.models import Category, Product

from .models import ContactMessage, Inquiry

JSON = {'HTTP_ACCEPT': 'application/json'}


class SubmissionTests(TestCase):
    def setUp(self):
        cache.clear()

    def message(self, **overrides):
        data = {'msg-name': 'Иван', 'msg-email': 'ivan@example.com', 'msg-message': 'Здравейте!'}
        data.update(overrides)
        return data

    def test_valid_message_is_saved(self):
        response = self.client.post(reverse('contacts:contact'), self.message(), **JSON)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['ok'])
        msg = ContactMessage.objects.get()
        self.assertEqual(msg.ip_address, '127.0.0.1')

    def test_invalid_message_returns_field_errors(self):
        response = self.client.post(reverse('contacts:contact'), self.message(**{'msg-email': 'nope'}), **JSON)
        self.assertEqual(response.status_code, 400)
        self.assertIn('email', response.json()['errors'])
        self.assertFalse(ContactMessage.objects.exists())

    def test_honeypot_pretends_success_but_saves_nothing(self):
        response = self.client.post(reverse('contacts:contact'),
                                    self.message(**{'msg-website': 'http://spam'}), **JSON)
        self.assertTrue(response.json()['ok'])
        self.assertFalse(ContactMessage.objects.exists())

    def test_throttle(self):
        for _ in range(5):
            self.client.post(reverse('contacts:contact'), self.message(), **JSON)
        response = self.client.post(reverse('contacts:contact'), self.message(), **JSON)
        self.assertEqual(response.status_code, 429)
        self.assertEqual(ContactMessage.objects.count(), 5)

    def test_no_js_fallback_redirects_to_contact_form(self):
        response = self.client.post(reverse('contacts:inquiry'), {
            'inq-name': 'Община', 'inq-email': 'a@b.bg', 'inq-message': 'Оферта за 20 контейнера',
            'inq-quantity': 20,
        })
        self.assertRedirects(response, reverse('contacts:page') + '#formulyar')
        self.assertEqual(Inquiry.objects.get().quantity, 20)

    def test_no_js_fallback_returns_to_safe_next_url(self):
        response = self.client.post(reverse('contacts:contact'),
                                    self.message(next='/produkti/kofa/#zapitvane'))
        self.assertRedirects(response, '/produkti/kofa/#zapitvane', fetch_redirect_response=False)

    def test_no_js_fallback_ignores_external_next_url(self):
        response = self.client.post(reverse('contacts:contact'),
                                    self.message(next='https://evil.example/'))
        self.assertRedirects(response, reverse('contacts:page') + '#formulyar')

    def test_get_not_allowed(self):
        self.assertEqual(self.client.get(reverse('contacts:inquiry')).status_code, 405)


class ContactPageTests(TestCase):
    def test_has_both_forms_and_map(self):
        response = self.client.get(reverse('contacts:page'))
        self.assertContains(response, reverse('contacts:inquiry'))
        self.assertContains(response, reverse('contacts:contact'))
        self.assertContains(response, 'data-map')


class NotificationTests(TestCase):
    def setUp(self):
        cache.clear()

    def post_message(self, **overrides):
        data = {'msg-name': 'Иван', 'msg-email': 'ivan@example.com', 'msg-phone': '0888 123 456',
                'msg-subject': 'Ремонт на контейнери', 'msg-message': 'Здравейте!'}
        data.update(overrides)
        return self.client.post(reverse('contacts:contact'), data, **JSON)

    def test_message_emails_the_company_with_reply_to_the_visitor(self):
        self.post_message()
        email = mail.outbox[0]
        self.assertEqual(email.to, ['cnm_rila@abv.bg'])
        self.assertEqual(email.reply_to, ['ivan@example.com'])
        self.assertIn('Ремонт на контейнери', email.subject)
        self.assertIn('0888 123 456', email.body)
        msg = ContactMessage.objects.get()
        self.assertIn(reverse('admin:contacts_contactmessage_change', args=[msg.pk]), email.body)

    def test_inquiry_email_names_the_product_and_quantity(self):
        product = Product.objects.create(name='Контейнер Бобър', category=Category.objects.create(name='Контейнери'))
        self.client.post(reverse('contacts:inquiry'), {
            'inq-name': 'Община Рила', 'inq-email': 'obshtina@example.bg', 'inq-product': product.pk,
            'inq-quantity': 20, 'inq-message': 'Оферта, моля.'}, **JSON)
        email = mail.outbox[0]
        self.assertIn('Контейнер Бобър', email.subject)
        self.assertIn('Количество: 20', email.body)

    def test_line_breaks_cannot_inject_headers(self):
        self.post_message(**{'msg-subject': 'Здравейте\r\nBcc: victim@example.com'})
        email = mail.outbox[0]
        self.assertNotIn('\n', email.subject)
        self.assertEqual(email.bcc, [])
        self.assertIsNone(email.message()['Bcc'])

    def test_spam_sends_nothing(self):
        self.post_message(**{'msg-website': 'http://spam'})
        self.assertEqual(mail.outbox, [])

    def test_mail_failure_still_saves_and_thanks_the_visitor(self):
        with patch('django.core.mail.EmailMessage.send', side_effect=OSError('SMTP down')), \
                self.assertLogs('contacts.notifications', 'ERROR'):
            response = self.post_message()
        self.assertTrue(response.json()['ok'])
        self.assertTrue(ContactMessage.objects.exists())

    @override_settings(CONTACT_NOTIFY_EMAILS=[])
    def test_can_be_turned_off(self):
        self.post_message()
        self.assertEqual(mail.outbox, [])
        self.assertTrue(ContactMessage.objects.exists())
