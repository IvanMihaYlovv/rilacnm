"""Email the company when someone sends an inquiry or a message through the site."""
import logging

from django.conf import settings
from django.core.mail import EmailMessage
from django.template.defaultfilters import filesizeformat
from django.urls import reverse

from .models import Inquiry

log = logging.getLogger(__name__)


def _one_line(value, limit=120):
    """Visitor text placed in a header: no line breaks (header injection) and kept short."""
    return ' '.join(str(value).split())[:limit]


def _admin_url(submission):
    meta = submission._meta
    path = reverse(f'admin:{meta.app_label}_{meta.model_name}_change', args=[submission.pk])
    return f'{settings.SITE_URL}{path}'


def _body(submission):
    lines = [f'Име: {submission.name}']
    if isinstance(submission, Inquiry):
        if submission.company:
            lines.append(f'Фирма / община: {submission.company}')
        lines.append(f'Продукт: {submission.product or "не е избран / по проект"}')
        if submission.quantity:
            lines.append(f'Количество: {submission.quantity}')
        files = list(submission.attachments.all())
        if files:
            lines.append(f'Прикачени файлове ({len(files)}):')
            lines += [f'  • {f.original_name} ({filesizeformat(f.size)})' for f in files]
    elif submission.subject:
        lines.append(f'Тема: {submission.subject}')
    lines += [
        f'Имейл: {submission.email}',
        f'Телефон: {submission.phone or "—"}',
        '',
        submission.message,
        '',
        '—',
        'Отговорете директно на този имейл, за да пишете на подателя.',
        f'В администрацията: {_admin_url(submission)}',
    ]
    return '\n'.join(lines)


def _attach_files(email, inquiry):
    """Attach the visitor's files when they are small enough; otherwise the admin link is enough."""
    files = list(inquiry.attachments.all())
    if not files or sum(f.size for f in files) > settings.INQUIRY_EMAIL_ATTACH_MB * 1024 * 1024:
        if files:
            email.body += '\nФайловете са големи за имейл: изтеглете ги от администрацията.'
        return
    for f in files:
        with f.file.open('rb') as handle:
            email.attach(f.original_name, handle.read())


def notify_staff(submission):
    """
    Send the notification. A mail failure is logged, never shown to the visitor:
    the submission is already saved and stays visible in the admin.
    """
    recipients = settings.CONTACT_NOTIFY_EMAILS
    if not recipients:
        return False

    if isinstance(submission, Inquiry):
        about = submission.product or submission.company or 'по проект'
        subject = f'Запитване за оферта: {_one_line(about)} — {_one_line(submission.name, 60)}'
    else:
        subject = f'Съобщение от сайта: {_one_line(submission.subject or submission.name)}'

    email = EmailMessage(
        subject=subject,
        body=_body(submission),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=recipients,
        reply_to=[submission.email],
    )
    if isinstance(submission, Inquiry):
        _attach_files(email, submission)
    try:
        email.send()
    except Exception:  # SMTP down, wrong password, timeout...
        log.exception('Could not send the notification for %s #%s',
                      submission._meta.model_name, submission.pk)
        return False
    return True
