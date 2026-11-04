from django.db import models

from core.models import TimeStampedModel


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
