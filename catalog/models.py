import re

from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils.text import Truncator

from core.models import SluggedModel, TimeStampedModel
from core.validators import validate_image_size


KEY_SPECS = 3
HEX_COLOR = re.compile(r'#(?:[0-9a-fA-F]{3}){1,2}')


class ActiveQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)


class Category(SluggedModel):
    name = models.CharField('име', max_length=120, unique=True)
    description = models.TextField('описание', blank=True,
                                   help_text='Кратък увод в началото на страницата.')
    body = models.TextField('текст за категорията', blank=True,
                            help_text='Показва се под продуктите. Абзаците се разделят с празен ред.')
    meta_description = models.CharField('SEO описание', max_length=160, blank=True)
    order = models.PositiveSmallIntegerField('подредба', default=0, db_index=True)
    is_active = models.BooleanField('активна', default=True)

    objects = ActiveQuerySet.as_manager()

    class Meta:
        ordering = ['order', 'name']
        verbose_name = 'категория'
        verbose_name_plural = 'категории'

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('catalog:category', kwargs={'slug': self.slug})

    @property
    def seo_description(self):
        return self.meta_description or Truncator(self.description).chars(160)


def product_drawing_path(instance, filename):
    return f'products/{instance.slug}/drawing/{filename}'


class ProductQuerySet(ActiveQuerySet):
    def for_listing(self):
        return (
            self.active()
            .filter(category__is_active=True)
            .select_related('category')
            .prefetch_related('images')
        )


class Product(SluggedModel):
    category = models.ForeignKey(Category, on_delete=models.PROTECT,
                                 related_name='products', verbose_name='категория')
    name = models.CharField('име', max_length=160)
    short_description = models.CharField('кратко описание', max_length=255,
                                         help_text='Показва се в картата на продукта.')
    description = models.TextField('описание', blank=True)
    highlight = models.CharField('акцент', max_length=24, blank=True,
                                 help_text='Кратка стойност за картата, напр. „4 м³“ или „110 л“.')
    specifications = models.JSONField('характеристики', default=dict, blank=True,
                                      help_text='{"Обем": "4 м³", "Материал": "стомана"}. '
                                                'Първите три се показват като акценти.')
    standards = models.TextField('стандарти и документи', blank=True, help_text='По един на ред.')
    options = models.TextField('опции', blank=True, help_text='По една на ред.')
    colors = models.TextField(
        'цветове', blank=True,
        help_text='По един на ред: име | #код | бележка, напр. „Син | #1f5aa6 | хартия“. '
                  'Бележката не е задължителна. Оставете празно, ако продуктът няма избор на цвят.')
    drawing = models.ImageField(
        'чертеж с размери', upload_to=product_drawing_path, blank=True,
        validators=[validate_image_size],
        help_text='JPG или PNG. Показва се до характеристиките и в PDF спецификацията.')
    is_featured = models.BooleanField('на начална страница', default=True)
    is_active = models.BooleanField('активен', default=True)
    order = models.PositiveSmallIntegerField('подредба', default=0)
    meta_title = models.CharField('SEO заглавие', max_length=70, blank=True)
    meta_description = models.CharField('SEO описание', max_length=160, blank=True)

    objects = ProductQuerySet.as_manager()

    class Meta:
        ordering = ['order', 'name']
        verbose_name = 'продукт'
        verbose_name_plural = 'продукти'
        indexes = [models.Index(fields=['is_active', 'order'])]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('catalog:product', kwargs={'category': self.category.slug, 'slug': self.slug})

    @property
    def key_specs(self):
        return list(self.specifications.items())[:KEY_SPECS]

    @property
    def standards_list(self):
        return self.standards.splitlines()

    @property
    def options_list(self):
        return self.options.splitlines()

    @property
    def color_list(self):
        """`colors` lines as dicts: name, hex (None unless a valid #rgb/#rrggbb), note."""
        result = []
        for line in self.colors.splitlines():
            parts = [p.strip() for p in line.split('|')]
            if not parts[0]:
                continue
            hex_code = parts[1] if len(parts) > 1 else ''
            result.append({
                'name': parts[0],
                'hex': hex_code if HEX_COLOR.fullmatch(hex_code) else None,
                'note': parts[2] if len(parts) > 2 else '',
            })
        return result

    @property
    def color_on_request(self):
        """True when an option offers a colour of the customer's choice."""
        return any('цвят' in o.lower() for o in self.options_list)

    def get_spec_sheet_url(self):
        return reverse('catalog:spec_sheet', kwargs={'category': self.category.slug, 'slug': self.slug})

    @property
    def seo_title(self):
        return self.meta_title or f'{self.name} — {self.category.name}'

    @property
    def seo_description(self):
        return self.meta_description or self.short_description[:160]

    @property
    def primary_image(self):
        # Works off the prefetch cache, so no extra query per product.
        images = list(self.images.all())
        return next((i for i in images if i.is_primary), images[0] if images else None)


def product_image_path(instance, filename):
    # One folder per product, so the media directory mirrors the catalog.
    return f'products/{instance.product.slug}/{filename}'


class ProductImage(TimeStampedModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE,
                                related_name='images', verbose_name='продукт')
    image = models.ImageField('снимка', upload_to=product_image_path,
                              width_field='width', height_field='height',
                              validators=[validate_image_size])
    width = models.PositiveIntegerField(editable=False, null=True)
    height = models.PositiveIntegerField(editable=False, null=True)
    alt_text = models.CharField('алтернативен текст', max_length=200,
                                help_text='Описание на снимката за незрящи потребители и Google.')
    color = models.CharField('цвят', max_length=60, blank=True,
                             help_text='Името на цвета от списъка на продукта, напр. „Сив“. '
                                       'При избор на този цвят галерията показва тази снимка.')
    is_primary = models.BooleanField('основна', default=False)
    order = models.PositiveSmallIntegerField('подредба', default=0)

    class Meta:
        ordering = ['-is_primary', 'order', 'pk']
        verbose_name = 'снимка на продукт'
        verbose_name_plural = 'снимки на продукти'
        constraints = [
            models.UniqueConstraint(fields=['product'], condition=Q(is_primary=True),
                                    name='unique_primary_image_per_product'),
        ]

    def __str__(self):
        return self.alt_text
