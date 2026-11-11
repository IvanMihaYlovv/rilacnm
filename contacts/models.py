import os
import uuid

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.urls import reverse

from core.models import TimeStampedModel


def private_storage():
    """Storage outside MEDIA_ROOT with no public URL. A callable, so the path stays out of migrations."""
    return FileSystemStorage(location=settings.PRIVATE_MEDIA_ROOT, base_url=None)


class Submission(TimeStampedModel):
    name = models.CharField('име', max_length=120)
    email = models.EmailField('имейл')
    phone = models.CharField('телефон', max_length=32, blank=True)
    message = models.TextField('съобщение', max_length=4000)
    is_processed = models.BooleanField('обработено', default=False, db_index=True)
    ip_address = models.GenericIPAddressField('IP адрес', null=True, blank=True, editable=False)
    user_agent = models.CharField('браузър', max_length=300, blank=True, editable=False)

    class Meta:
        abstract = True
        ordering = ['is_processed', '-created_at']

    def __str__(self):
        return f'{self.name} <{self.email}>'


class Inquiry(Submission):
    """Request for a quote, optionally tied to a specific product."""

    company = models.CharField('фирма / община', max_length=160, blank=True)
    product = models.ForeignKey('catalog.Product', on_delete=models.SET_NULL, null=True,
                                blank=True, related_name='inquiries', verbose_name='продукт')
    quantity = models.PositiveIntegerField('количество', null=True, blank=True)

    class Meta(Submission.Meta):
        verbose_name = 'запитване'
        verbose_name_plural = 'запитвания'


class ContactMessage(Submission):
    subject = models.CharField('тема', max_length=160, blank=True)

    class Meta(Submission.Meta):
        verbose_name = 'контактно съобщение'
        verbose_name_plural = 'контактни съобщения'


def _attachment_path(instance, filename):
    # A random name on disk: the visitor's file name is kept only in the database.
    ext = os.path.splitext(filename)[1].lower()
    return f'inquiries/{instance.inquiry_id}/{uuid.uuid4().hex}{ext}'


class InquiryAttachment(models.Model):
    """A drawing, sketch or photo the visitor attached to a quote request."""

    inquiry = models.ForeignKey(Inquiry, on_delete=models.CASCADE, related_name='attachments',
                                verbose_name='запитване')
    file = models.FileField('файл', upload_to=_attachment_path, storage=private_storage)
    original_name = models.CharField('име на файла', max_length=255)
    size = models.PositiveIntegerField('размер (байта)')

    class Meta:
        verbose_name = 'прикачен файл'
        verbose_name_plural = 'прикачени файлове'
        ordering = ['pk']

    def __str__(self):
        return self.original_name

    def get_download_url(self):
        return reverse('contacts:attachment', args=[self.pk])

    def delete(self, *args, **kwargs):
        self.file.delete(save=False)
        return super().delete(*args, **kwargs)
