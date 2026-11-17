from django import template
from django.utils.html import format_html

from core import thumbs

register = template.Library()

# Rendered widths per use, in CSS px; each is offered at 1x and 2x.
IMAGE_SIZES = {
    'card': ((400, 800), '(min-width: 1100px) 320px, (min-width: 640px) 46vw, 92vw'),
    'gallery': ((800, 1400), '(min-width: 1000px) 660px, 100vw'),
    'thumb': ((160, 320), '140px'),
}


@register.simple_tag
def responsive(image, use):
    """` srcset="…" sizes="…"` for a ProductImage, so phones and cards skip the full-size file.

    Empty when the photo is already small or no copy could be made: `src` then does the job.
    """
    widths, sizes = IMAGE_SIZES[use]
    value = thumbs.srcset(image.image.name, image.width, widths)
    return format_html(' srcset="{}" sizes="{}"', value, sizes) if value else ''


@register.filter
def money(value):
    """193822.75 → „193 822,75“, with a non-breaking space so amounts never wrap."""
    if value is None:
        return ''
    return f'{value:,.2f}'.replace(',', ' ').replace('.', ',')
