from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import Truncator

from core.models import SluggedModel


# Publicity logos per programming period, keyed by the contract-number prefix
# (taken from the company's previous website).
PROGRAMME_LOGOS = {
    'BG16RFPR': [  # 2021–2027, Програма „Конкурентоспособност и иновации в предприятията“
        ('img/eu/eu-cofunded.png', 'Съфинансирано от Европейския съюз', 375, 79),
        ('img/eu/pkip-2021-2027.png',
         'Програма „Конкурентоспособност и иновации в предприятията“', 378, 105),
    ],
    'BG16RFOP': [  # 2014–2020, Оперативна програма „Иновации и конкурентоспособност“
        ('img/eu/eu-erdf.png', 'Европейски съюз, Европейски фонд за регионално развитие', 437, 400),
        ('img/eu/opic-2014-2020.png',
         'Оперативна програма „Иновации и конкурентоспособност“', 437, 400),
    ],
}


class ProjectQuerySet(models.QuerySet):
    def published(self):
        return self.filter(is_published=True)


class Project(SluggedModel):
    SLUG_SOURCE = 'title'

    class Kind(models.TextChoices):
        EU_FUNDED = 'eu', 'Европейско финансиране'
        CLIENT = 'client', 'Реализиран проект'

    title = models.CharField('заглавие', max_length=220)
    kind = models.CharField('вид', max_length=12, choices=Kind.choices, default=Kind.CLIENT)
    summary = models.TextField('резюме')
    body = models.TextField('подробно описание', blank=True,
                            help_text='Абзаците се разделят с празен ред.')
    client = models.CharField('възложител', max_length=160, blank=True)
    location = models.CharField('местоположение', max_length=160, blank=True)
    programme = models.CharField('програма', max_length=220, blank=True)
    contract_number = models.CharField('договор №', max_length=60, blank=True)
    total_value = models.DecimalField('обща стойност (лв.)', max_digits=12, decimal_places=2,
                                      null=True, blank=True)
    grant_amount = models.DecimalField('безвъзмездна помощ (лв.)', max_digits=12,
                                       decimal_places=2, null=True, blank=True)
    eu_amount = models.DecimalField('европейско съфинансиране (лв.)', max_digits=12,
                                    decimal_places=2, null=True, blank=True)
    national_amount = models.DecimalField('национално съфинансиране (лв.)', max_digits=12,
                                          decimal_places=2, null=True, blank=True)
    funding_statement = models.TextField(
        'текст за публичност', blank=True,
        help_text='Задължителното изречение за финансирането по договора.')
    documents = models.JSONField('документи', default=list, blank=True,
                                 help_text='[{"title": "Публична покана", "url": "https://..."}]')
    start_date = models.DateField('начало', null=True, blank=True)
    end_date = models.DateField('край', null=True, blank=True)
    image = models.ImageField('снимка', upload_to='projects/%Y/', blank=True)
    image_alt = models.CharField('алтернативен текст', max_length=200, blank=True)
    is_published = models.BooleanField('публикуван', default=True)
    order = models.PositiveSmallIntegerField('подредба', default=0)

    objects = ProjectQuerySet.as_manager()

    class Meta:
        ordering = ['order', '-start_date']
        verbose_name = 'проект'
        verbose_name_plural = 'проекти'

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        name = 'eu_detail' if self.kind == self.Kind.EU_FUNDED else 'realized_detail'
        return reverse(f'projects:{name}', kwargs={'slug': self.slug})

    @property
    def is_finished(self):
        return bool(self.end_date and self.end_date < timezone.localdate())

    @property
    def programme_logos(self):
        """The EU and programme logos required on this project's publicity."""
        logos = PROGRAMME_LOGOS.get(self.contract_number[:8], [])
        return [dict(src=src, alt=alt, width=w, height=h, square=w < 2 * h)
                for src, alt, w, h in logos]

    @property
    def grant_share(self):
        """Grant as a percentage of the project's value, for the funding bar."""
        if not self.total_value or not self.grant_amount:
            return None
        return round(self.grant_amount / self.total_value * 100)

    @property
    def seo_description(self):
        return Truncator(self.summary).chars(160)
