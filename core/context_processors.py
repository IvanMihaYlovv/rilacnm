from django.conf import settings
from django.utils.functional import SimpleLazyObject

from catalog.models import Category

from .content import COMPANY, SERVICES

# Which navbar item stays highlighted, by full view name or URL namespace.
_NAV_SECTIONS = {
    'core:home': 'home',
    'core:about': 'about',
    'core:services': 'services',
    'core:service': 'services',
    'catalog': 'products',
    'projects': 'projects',
    'contacts': 'contacts',
}


def _nav_section(request):
    match = getattr(request, 'resolver_match', None)
    if match is None:
        return ''
    return _NAV_SECTIONS.get(match.view_name) or _NAV_SECTIONS.get(match.namespace, '')


def site(request):
    return {
        'company': COMPANY,
        'site_url': settings.SITE_URL,
        'canonical_url': f'{settings.SITE_URL}{request.path}',
        'google_site_verification': settings.GOOGLE_SITE_VERIFICATION,
        'nav_section': _nav_section(request),
        'footer_categories': SimpleLazyObject(lambda: list(Category.objects.active())),
        'footer_services': SERVICES,
    }
