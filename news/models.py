from django.db import models
from django.urls import reverse
from django.utils import timezone

from core.models import SluggedModel


class NewsQuerySet(models.QuerySet):
    def published(self):
        return self.filter(is_published=True, published_at__lte=timezone.now())


class News(SluggedModel):
    SLUG_SOURCE = 'title'

    title = models.CharField('заглавие', max_length=200)
    excerpt = models.CharField('кратък текст', max_length=300)
    body = models.TextField('съдържание')
    cover = models.ImageField('корица', upload_to='news/%Y/%m/', blank=True)
    cover_alt = models.CharField('алтернативен текст', max_length=200, blank=True)
    published_at = models.DateTimeField('публикувана на', default=timezone.now, db_index=True)
    is_published = models.BooleanField('публикувана', default=True)
    meta_description = models.CharField('SEO описание', max_length=160, blank=True)

    objects = NewsQuerySet.as_manager()

    class Meta:
        ordering = ['-published_at']
        verbose_name = 'новина'
        verbose_name_plural = 'новини'

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('news:detail', kwargs={'slug': self.slug})

    @property
    def seo_description(self):
        return self.meta_description or self.excerpt[:160]
