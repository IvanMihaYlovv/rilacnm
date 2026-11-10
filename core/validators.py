from urllib.parse import urlsplit

from django.conf import settings
from django.core.exceptions import ValidationError


def validate_image_size(file):
    limit = settings.MAX_UPLOAD_MB * 1024 * 1024
    if file.size > limit:
        raise ValidationError(f'Файлът е твърде голям: максимумът е {settings.MAX_UPLOAD_MB} MB.')


def validate_documents(value):
    """Project documents: a list of {"title", "url"} with http(s) links only (no javascript:)."""
    if not isinstance(value, list):
        raise ValidationError('Документите трябва да са списък.')
    for doc in value:
        if not isinstance(doc, dict) or not doc.get('title') or not doc.get('url'):
            raise ValidationError('Всеки документ трябва да има "title" и "url".')
        if urlsplit(str(doc['url'])).scheme not in ('http', 'https'):
            raise ValidationError(f'Невалиден адрес на документ: {doc["url"]}')
