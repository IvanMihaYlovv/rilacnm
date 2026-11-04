import json
import re
from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from catalog.models import Category, Product
from news.models import News
from projects.models import Project

from .content import LEGACY_PAGES, LEGACY_PRODUCTS, SERVICES
from .templatetags.site_tags import money
from .utils import bg_slugify


def schema_types(html):
    raw = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S).group(1)
    types = []
    for node in json.loads(raw)['@graph']:
        types.extend(node['@type'] if isinstance(node['@type'], list) else [node['@type']])
    return types


class SlugTests(TestCase):
    def test_bulgarian_transliteration(self):
        self.assertEqual(bg_slugify('Щастлива Ябълка'), 'shtastliva-yabalka')

    def test_slug_is_unique(self):
        cat = Category.objects.create(name='Контейнери')
        a = Product.objects.create(category=cat, name='Кофа', short_description='x')
        b = Product.objects.create(category=cat, name='Кофа', short_description='y')
        self.assertEqual((a.slug, b.slug), ('kofa', 'kofa-2'))


class MoneyFilterTests(TestCase):
    def test_groups_thousands_the_bulgarian_way(self):
        self.assertEqual(money(Decimal('193822.75')), '193\u00a0822,75')
        self.assertEqual(money(Decimal('50000')), '50\u00a0000,00')
        self.assertEqual(money(None), '')


class SeededTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_content', verbosity=0)
        cls.product = Product.objects.select_related('category').first()

    def public_urls(self):
        urls = ['/', '/za-nas/', '/uslugi/', '/vaprosi/', '/sertifikati/', '/poveritelnost/',
                '/produkti/', '/proekti/evropeysko-finansirane/', '/proekti/realizirani/',
                '/kontakti/', '/novini/']
        urls += [reverse('core:service', kwargs={'slug': s['slug']}) for s in SERVICES]
        urls += [c.get_absolute_url() for c in Category.objects.all()]
        urls += [p.get_absolute_url() for p in Product.objects.select_related('category')]
        urls += [p.get_absolute_url() for p in Project.objects.all()]
        urls += [n.get_absolute_url() for n in News.objects.all()]
        return urls


class EveryPageTests(SeededTestCase):
    """The guarantees that have to hold on the whole site, not just on one page."""

    def pages(self):
        for url in self.public_urls():
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, url)
            yield url, response.content.decode()

    def test_seo_essentials(self):
        titles, descriptions = {}, {}
        for url, html in self.pages():
            self.assertIn('<html lang="bg"', html, url)
            self.assertEqual(html.count('<h1'), 1, url)
            self.assertIn(f'<link rel="canonical" href="https://www.rila-cnm.eu{url}">', html)
            self.assertIn('property="og:image"', html, url)
            schema_types(html)  # must parse

            title = re.search(r'<title>(.*?)</title>', html, re.S).group(1)
            description = re.search(r'<meta name="description" content="(.*?)">', html, re.S).group(1)
            self.assertTrue(title, url)
            self.assertTrue(description, url)
            # Escaped entities are slightly longer than what the visitor sees.
            self.assertLessEqual(len(re.sub(r'&[^;]+;', 'x', description)), 165, url)
            self.assertNotIn(title, titles, f'{url} repeats the title of {titles.get(title)}')
            self.assertNotIn(description, descriptions, f'{url} repeats {descriptions.get(description)}')
            titles[title], descriptions[description] = url, url

    def test_footer_has_contacts_everywhere(self):
        for url, html in self.pages():
            footer = html[html.index('<footer'):]
            for needle in ['2630 гр. Рила', 'tel:+35970542024', 'tel:+359896808086', 'tel:+359896629334',
                           'mailto:cnm_rila@abv.bg', '+359 7054 2028', '8:00']:
                self.assertIn(needle, footer, url)

    def test_navbar_links_to_separate_pages(self):
        html = self.client.get('/').content.decode()
        nav = html[html.index('<nav class="nav"'):html.index('</nav>')]
        for name in ['core:home', 'core:about', 'catalog:list', 'core:services', 'projects:eu',
                     'projects:realized', 'contacts:page']:
            self.assertIn(f'href="{reverse(name)}"', nav)
        self.assertFalse([href for href in re.findall(r'href="([^"]*)"', nav) if '#' in href])

    def test_projects_menu_is_a_dropdown_with_two_options(self):
        html = self.client.get('/').content.decode()
        menu = html[html.index('id="projects-menu"'):]
        menu = menu[:menu.index('</ul>')]
        self.assertIn('Проекти с Европейско финансиране', menu)
        self.assertIn('Реализирани Проекти', menu)
        self.assertEqual(menu.count('<li>'), 2)

    def test_home_is_not_the_whole_site_any_more(self):
        html = self.client.get('/').content.decode()
        self.assertNotIn('id="vaprosi"', html)
        self.assertNotIn('id="kontakti"', html)
        self.assertNotIn('<form', html)


class HomePageTests(SeededTestCase):
    def test_renders_with_bounded_queries(self):
        # products, product images, categories, news, footer categories
        with self.assertNumQueries(5):
            response = self.client.get(reverse('core:home'))
        self.assertEqual(response.status_code, 200)

    def test_schema(self):
        types = schema_types(self.client.get('/').content.decode())
        self.assertIn('LocalBusiness', types)
        self.assertIn('WebSite', types)

    def test_seed_is_idempotent(self):
        before = Product.objects.count()
        call_command('seed_content', verbosity=0)
        self.assertEqual(Product.objects.count(), before)


class PageSchemaTests(SeededTestCase):
    def test_faq(self):
        self.assertIn('FAQPage', schema_types(self.client.get('/vaprosi/').content.decode()))

    def test_service(self):
        url = reverse('core:service', kwargs={'slug': SERVICES[0]['slug']})
        types = schema_types(self.client.get(url).content.decode())
        self.assertIn('Service', types)
        self.assertIn('BreadcrumbList', types)

    def test_contact(self):
        self.assertIn('ContactPage', schema_types(self.client.get('/kontakti/').content.decode()))

    def test_breadcrumb_urls_are_real_pages_not_fragments(self):
        html = self.client.get(self.product.get_absolute_url()).content.decode()
        raw = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S).group(1)
        crumbs = next(n for n in json.loads(raw)['@graph'] if n['@type'] == 'BreadcrumbList')
        items = [i['item'] for i in crumbs['itemListElement']]
        self.assertEqual(len(items), 4)
        self.assertFalse([i for i in items if '#' in i])

    def test_unknown_service_is_404(self):
        self.assertEqual(self.client.get('/uslugi/nyama-takava/').status_code, 404)


class LegacyUrlTests(SeededTestCase):
    def test_every_old_page_redirects_permanently_to_a_live_page(self):
        for old in [*(k for k in LEGACY_PAGES if k), *LEGACY_PRODUCTS]:
            for path in [f'/български/{old}', f'/български/{old}/']:
                response = self.client.get(path)
                self.assertEqual(response.status_code, 301, path)
                self.assertEqual(self.client.get(response['Location']).status_code, 200, path)

    def test_old_targets_are_specific_products(self):
        # A product page is a better match than the catalog fallback.
        for old, slug in LEGACY_PRODUCTS.items():
            self.assertTrue(Product.objects.filter(slug=slug).exists(), old)

    def test_old_home_redirects(self):
        self.assertRedirects(self.client.get('/български'), '/', status_code=301)

    def test_unknown_old_page_is_404(self):
        self.assertEqual(self.client.get('/български/няма-такава').status_code, 404)


class CrawlerFilesTests(SeededTestCase):
    def test_robots_txt(self):
        response = self.client.get('/robots.txt')
        self.assertEqual(response['Content-Type'], 'text/plain; charset=utf-8')
        self.assertContains(response, 'Sitemap: ')
        self.assertContains(response, 'Disallow: /admin/')

    def test_robots_does_not_block_public_pages(self):
        body = self.client.get('/robots.txt').content.decode()
        blocked = [line.split(': ')[1] for line in body.splitlines() if line.startswith('Disallow')]
        for url in self.public_urls():
            self.assertFalse([b for b in blocked if url.startswith(b)], url)

    def test_sitemap_lists_every_indexable_page_on_the_canonical_host(self):
        body = self.client.get('/sitemap.xml').content.decode()
        for url in self.public_urls():
            if url == '/proekti/realizirani/':
                continue
            self.assertIn(f'<loc>https://www.rila-cnm.eu{url}</loc>', body)
        self.assertNotIn('testserver', body)


class NotFoundPageTests(SeededTestCase):
    def test_404_is_helpful_and_not_indexed(self):
        with self.settings(DEBUG=False):
            response = self.client.get('/nyama-takava-stranitsa/')
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, 'noindex', status_code=404)
        self.assertContains(response, 'mailto:cnm_rila@abv.bg', status_code=404)
