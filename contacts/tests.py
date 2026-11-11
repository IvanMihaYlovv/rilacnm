import shutil
import tempfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile

from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from catalog.models import Category, Product

from .models import ContactMessage, Inquiry, InquiryAttachment

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


class InquiryAttachmentTests(TestCase):
    """Drawings and photos attached to a quote request: private, validated, emailed."""

    def setUp(self):
        cache.clear()
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        field = InquiryAttachment._meta.get_field('file')
        patcher = patch.object(field, 'storage', FileSystemStorage(location=self.tmp))
        patcher.start()
        self.addCleanup(patcher.stop)

    def post(self, *files, **overrides):
        data = {'inq-name': 'Иван', 'inq-email': 'ivan@example.com', 'inq-message': 'По чертеж, моля.',
                'inq-attachments': list(files)}
        data.update(overrides)
        return self.client.post(reverse('contacts:inquiry'), data, **JSON)

    def test_files_are_saved_privately_and_emailed(self):
        response = self.post(SimpleUploadedFile('чертеж.pdf', b'%PDF-1.4 test'),
                             SimpleUploadedFile('snimka.JPG', b'jpeg'))
        self.assertTrue(response.json()['ok'])
        names = [a.original_name for a in Inquiry.objects.get().attachments.all()]
        self.assertEqual(names, ['чертеж.pdf', 'snimka.JPG'])
        stored = InquiryAttachment.objects.first().file.name
        self.assertTrue(stored.startswith('inquiries/') and stored.endswith('.pdf'))
        self.assertNotIn('чертеж', stored)
        email = mail.outbox[0]
        self.assertIn('Прикачени файлове (2)', email.body)
        self.assertEqual([a[0] for a in email.attachments], ['чертеж.pdf', 'snimka.JPG'])

    def test_inquiry_without_files_still_works(self):
        self.assertTrue(self.post().json()['ok'])
        self.assertFalse(InquiryAttachment.objects.exists())

    def test_rejects_unsafe_file_types(self):
        for name in ['page.html', 'logo.svg', 'run.exe', 'noext']:
            response = self.post(SimpleUploadedFile(name, b'x'))
            self.assertEqual(response.status_code, 400, name)
            self.assertIn('attachments', response.json()['errors'])
        self.assertFalse(Inquiry.objects.exists())

    @override_settings(INQUIRY_MAX_FILE_MB=1)
    def test_rejects_too_large_file(self):
        response = self.post(SimpleUploadedFile('big.pdf', b'x' * (1024 * 1024 + 1)))
        self.assertEqual(response.status_code, 400)

    @override_settings(INQUIRY_MAX_FILES=2)
    def test_rejects_too_many_files(self):
        response = self.post(*[SimpleUploadedFile(f'{i}.pdf', b'x') for i in range(3)])
        self.assertEqual(response.status_code, 400)

    @override_settings(INQUIRY_EMAIL_ATTACH_MB=0)
    def test_large_files_are_not_attached_to_the_email(self):
        self.post(SimpleUploadedFile('plan.pdf', b'%PDF'))
        email = mail.outbox[0]
        self.assertEqual(email.attachments, [])
        self.assertIn('изтеглете ги от администрацията', email.body)

    def test_download_is_staff_only_and_forced(self):
        self.post(SimpleUploadedFile('чертеж.pdf', b'%PDF-1.4 test'))
        url = InquiryAttachment.objects.get().get_download_url()
        self.assertEqual(self.client.get(url).status_code, 302)  # to the admin login

        User = get_user_model()
        staff = User.objects.create_user('staff', password='x', is_staff=True)
        self.client.force_login(staff)
        self.assertEqual(self.client.get(url).status_code, 404)  # staff without permission

        staff.user_permissions.add(Permission.objects.get(codename='view_inquiry'))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('attachment;', response['Content-Disposition'])
        self.assertEqual(response['Content-Type'], 'application/octet-stream')
        self.assertEqual(b''.join(response.streaming_content), b'%PDF-1.4 test')

    def test_admin_lists_the_files(self):
        self.post(SimpleUploadedFile('чертеж.pdf', b'%PDF'))
        admin_user = get_user_model().objects.create_superuser('admin', password='x')
        self.client.force_login(admin_user)
        inquiry = Inquiry.objects.get()
        response = self.client.get(reverse('admin:contacts_inquiry_change', args=[inquiry.pk]))
        self.assertContains(response, 'чертеж.pdf')
        self.assertContains(response, inquiry.attachments.get().get_download_url())

    def test_form_is_multipart(self):
        response = self.client.get(reverse('contacts:page'))
        self.assertContains(response, 'enctype="multipart/form-data"')
        self.assertContains(response, 'name="inq-attachments"')
