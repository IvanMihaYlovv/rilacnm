from django.db import models

from .utils import unique_slug


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField('създаден', auto_now_add=True)
    updated_at = models.DateTimeField('обновен', auto_now=True)

    class Meta:
        abstract = True


class SluggedModel(TimeStampedModel):
    """Auto-fills a transliterated, unique slug from `SLUG_SOURCE` on save."""

    SLUG_SOURCE = 'name'

    slug = models.SlugField('адрес (slug)', max_length=140, unique=True, blank=True,
                            help_text='Попълва се автоматично, ако е празно.')

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, getattr(self, self.SLUG_SOURCE))
        super().save(*args, **kwargs)
