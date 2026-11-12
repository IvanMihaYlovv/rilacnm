import json
from urllib.parse import quote

from django.conf import settings
from django.urls import reverse
from django.utils.safestring import mark_safe

from .content import COMPANY

_JSON_ESCAPES = {ord('<'): '\\u003c', ord('>'): '\\u003e', ord('&'): '\\u0026'}


def ld_json(data) -> str:
    """Serialize schema.org data for safe embedding inside a <script> tag."""
    return mark_safe(json.dumps(data, ensure_ascii=False, separators=(',', ':')).translate(_JSON_ESCAPES))


def absolute(path: str) -> str:
    return f'{settings.SITE_URL}{path}'


def org_id() -> str:
    return absolute('/#organization')


def organization_node():
    c = COMPANY
    return {
        '@type': ['Organization', 'LocalBusiness'],
        '@id': org_id(),
        'name': c['legal_name'],
        'alternateName': c['name'],
        'url': absolute('/'),
        'logo': absolute(f'{settings.STATIC_URL}img/logo-512.png'),
        'image': absolute(f'{settings.STATIC_URL}img/og-cover.png'),
        'description': c['description'],
        'foundingDate': str(c['founded']),
        'email': c['email'],
        'telephone': c['phones'][0]['tel'],
        'faxNumber': c['fax'],
        'openingHours': c['hours_schema'],
        'address': {
            '@type': 'PostalAddress',
            'streetAddress': c['street'],
            'addressLocality': c['city'],
            'postalCode': c['postal_code'],
            'addressRegion': c['region'],
            'addressCountry': c['country'],
        },
        'geo': {'@type': 'GeoCoordinates', 'latitude': c['geo']['lat'], 'longitude': c['geo']['lng']},
        'areaServed': {'@type': 'Country', 'name': 'България'},
        'hasMap': f"https://www.google.com/maps/search/?api=1&query={quote(c['map_query'])}",
        'contactPoint': [
            {'@type': 'ContactPoint', 'telephone': p['tel'], 'contactType': p['label'],
             'availableLanguage': ['bg']}
            for p in c['phones']
        ],
        'hasCredential': [
            {'@type': 'EducationalOccupationalCredential', 'name': cert['name'],
             'credentialCategory': 'certification'}
            for cert in c['certifications']
        ],
    }


def website_node():
    return {
        '@type': 'WebSite',
        '@id': absolute('/#website'),
        'url': absolute('/'),
        'name': COMPANY['legal_name'],
        'inLanguage': 'bg-BG',
        'publisher': {'@id': org_id()},
    }


def breadcrumb_node(crumbs):
    return {
        '@type': 'BreadcrumbList',
        'itemListElement': [
            {'@type': 'ListItem', 'position': i, 'name': name, 'item': absolute(url)}
            for i, (name, url) in enumerate(crumbs, start=1)
        ],
    }


def item_list_node(entries):
    """`entries` are (name, path) pairs."""
    return {
        '@type': 'ItemList',
        'itemListElement': [
            {'@type': 'ListItem', 'position': i, 'name': name, 'url': absolute(path)}
            for i, (name, path) in enumerate(entries, start=1)
        ],
    }


def page_schema(path, title, description, page_type, crumbs, nodes=()):
    """The JSON-LD graph of one page: who we are, the page itself, and what's on it."""
    url = absolute(path)
    graph = [
        organization_node(),
        website_node(),
        {
            '@type': page_type,
            '@id': f'{url}#webpage',
            'url': url,
            'name': title,
            'description': description,
            'isPartOf': {'@id': absolute('/#website')},
            'about': {'@id': org_id()},
            'inLanguage': 'bg-BG',
        },
        *nodes,
    ]
    if len(crumbs) > 1:
        graph.append(breadcrumb_node(crumbs))
    return {'@context': 'https://schema.org', '@graph': graph}


def faq_node(items):
    return {
        '@type': 'FAQPage',
        '@id': absolute(f"{reverse('core:faq')}#faq"),
        'mainEntity': [
            {'@type': 'Question', 'name': item['q'],
             'acceptedAnswer': {'@type': 'Answer', 'text': item['a']}}
            for item in items
        ],
    }


def service_node(service, path):
    return {
        '@type': 'Service',
        '@id': absolute(f'{path}#service'),
        'name': service['title'],
        'serviceType': service['title'],
        'description': service['text'],
        'url': absolute(path),
        'provider': {'@id': org_id()},
        'areaServed': {'@type': 'Country', 'name': 'България'},
    }


def product_node(product):
    url = absolute(product.get_absolute_url())
    data = {
        '@type': 'Product',
        '@id': f'{url}#product',
        'name': product.name,
        'description': product.description or product.short_description,
        'category': product.category.name,
        'url': url,
        'mainEntityOfPage': {'@id': f'{url}#webpage'},
        'brand': {'@type': 'Brand', 'name': COMPANY['name']},
        'manufacturer': {'@id': org_id()},
        'countryOfOrigin': {'@type': 'Country', 'name': COMPANY['country']},
        'subjectOf': {
            '@type': 'DigitalDocument',
            'name': f'{product.name} — техническа спецификация',
            'encodingFormat': 'application/pdf',
            'url': absolute(product.get_spec_sheet_url()),
        },
        'additionalProperty': [
            {'@type': 'PropertyValue', 'name': k, 'value': v}
            for k, v in product.specifications.items()
        ],
    }
    images = [absolute(i.image.url) for i in product.images.all()]
    if product.drawing:
        images.append(absolute(product.drawing.url))
    if images:
        data['image'] = images
    if product.color_list:
        data['color'] = ', '.join(c['name'] for c in product.color_list)
    standards = [s for s in product.standards_list if s.strip()]
    if standards:
        data['additionalProperty'].append(
            {'@type': 'PropertyValue', 'name': 'Стандарти и документи', 'value': '; '.join(standards)})
    return data


def news_node(item):
    url = absolute(item.get_absolute_url())
    data = {
        '@type': 'NewsArticle',
        '@id': f'{url}#article',
        'headline': item.title,
        'description': item.excerpt,
        'url': url,
        'datePublished': item.published_at.isoformat(),
        'dateModified': item.updated_at.isoformat(),
        'author': {'@id': org_id()},
        'publisher': {'@id': org_id()},
        'inLanguage': 'bg-BG',
    }
    if item.cover:
        data['image'] = [absolute(item.cover.url)]
    return data


class SeoPageMixin:
    """
    Gives a view its <title>, meta description, breadcrumbs and JSON-LD.

    Set the class attributes, or override the matching get_* method when the
    values come from an object. Breadcrumbs are (label, url) pairs below "Начало".
    """

    page_title = ''
    page_description = ''
    page_heading = ''
    page_lead = ''
    page_eyebrow = ''
    page_type = 'WebPage'
    noindex = False

    def get_page_title(self):
        return self.page_title

    def get_full_title(self):
        return f"{self.get_page_title()} | {COMPANY['name']}"

    def get_page_description(self):
        return self.page_description

    def get_page_heading(self):
        return self.page_heading or self.get_page_title()

    def get_page_lead(self):
        return self.page_lead

    def get_page_eyebrow(self):
        return self.page_eyebrow

    def get_breadcrumbs(self):
        return []

    def get_schema_nodes(self):
        return []

    def get_noindex(self):
        return self.noindex

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        title, description = self.get_full_title(), self.get_page_description()
        crumbs = [('Начало', reverse('core:home')), *self.get_breadcrumbs()]
        ctx.update(
            seo_title=title,
            seo_description=description,
            page_heading=self.get_page_heading(),
            page_lead=self.get_page_lead(),
            page_eyebrow=self.get_page_eyebrow(),
            crumbs=crumbs,
            noindex=self.get_noindex(),
            schema=ld_json(page_schema(self.request.path, title, description, self.page_type,
                                       crumbs, self.get_schema_nodes())),
        )
        return ctx
