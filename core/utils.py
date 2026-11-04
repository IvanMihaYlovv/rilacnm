from django.utils.text import slugify

# Official Bulgarian transliteration (Закон за транслитерацията, 2009),
# so URLs stay readable Latin slugs instead of percent-encoded Cyrillic.
_BG_TO_LATIN = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ж': 'zh',
    'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n',
    'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u', 'ф': 'f',
    'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sht', 'ъ': 'a',
    'ь': 'y', 'ю': 'yu', 'я': 'ya',
}


def transliterate(value: str) -> str:
    return ''.join(_BG_TO_LATIN.get(ch, ch) for ch in value.lower())


def bg_slugify(value: str, max_length: int = 140) -> str:
    return slugify(transliterate(value))[:max_length].strip('-')


def unique_slug(instance, value: str, field: str = 'slug') -> str:
    """Return a slug for `value` that is unique across the instance's model."""
    max_length = instance._meta.get_field(field).max_length
    base = bg_slugify(value, max_length) or 'item'
    slug, n = base, 2
    qs = type(instance)._default_manager.exclude(pk=instance.pk)
    while qs.filter(**{field: slug}).exists():
        suffix = f'-{n}'
        slug = f'{base[:max_length - len(suffix)]}{suffix}'
        n += 1
    return slug
