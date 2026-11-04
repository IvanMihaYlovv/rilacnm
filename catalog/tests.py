from django.core.management import call_command
from django.test import TestCase

from .models import Category, Product


class CatalogTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_content', verbosity=0)
        cls.product = Product.objects.select_related('category').first()

    def test_list_shows_every_active_product(self):
        response = self.client.get('/produkti/')
        for product in Product.objects.select_related('category'):
            self.assertContains(response, f'href="{product.get_absolute_url()}"')

    def test_list_groups_by_category_with_bounded_queries(self):
        # categories, products, product images, footer categories
        with self.assertNumQueries(4):
            self.client.get('/produkti/')

    def test_category_page_shows_only_its_products(self):
        category = Category.objects.get(name='Кофи и съдове')
        response = self.client.get(category.get_absolute_url())
        self.assertContains(response, 'Метална кофа')
        self.assertNotContains(response, 'тип „Бобър“')

    def test_inactive_category_is_404(self):
        category = self.product.category
        Category.objects.filter(pk=category.pk).update(is_active=False)
        self.assertEqual(self.client.get(category.get_absolute_url()).status_code, 404)


class ProductPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_content', verbosity=0)
        cls.product = Product.objects.select_related('category').first()

    def test_renders_with_bounded_queries(self):
        # product+category, its images, related, related images, footer categories, form product choices
        with self.assertNumQueries(6):
            response = self.client.get(self.product.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'<h1 class="product-hero__title">{self.product.name}</h1>', html=False)

    def test_url_is_nested_under_the_category(self):
        self.assertEqual(self.product.get_absolute_url(),
                         f'/produkti/{self.product.category.slug}/{self.product.slug}/')

    def test_wrong_category_in_url_is_404(self):
        other = Category.objects.exclude(pk=self.product.category_id).first()
        response = self.client.get(f'/produkti/{other.slug}/{self.product.slug}/')
        self.assertEqual(response.status_code, 404)

    def test_every_characteristic_is_shown(self):
        product = Product.objects.get(slug='podvizhen-konteyner-tip-bobar')
        response = self.client.get(product.get_absolute_url())
        for key, value in product.specifications.items():
            self.assertContains(response, f'<th scope="row">{key}</th><td>{value}</td>')
        for item in product.standards_list + product.options_list:
            self.assertContains(response, f'<li>{item}</li>')
        self.assertEqual(product.key_specs[0], ('Обем', '1100 л'))

    def test_product_type_markup(self):
        html = self.client.get(self.product.get_absolute_url()).content.decode()
        self.assertIn('<meta property="og:type" content="product">', html)
        self.assertIn('"@type":"Product"', html)

    def test_inquiry_form_preselects_product(self):
        html = self.client.get(self.product.get_absolute_url()).content.decode()
        self.assertIn(f'<option value="{self.product.pk}" selected>', html)

    def test_inactive_product_is_404(self):
        Product.objects.filter(pk=self.product.pk).update(is_active=False)
        self.assertEqual(self.client.get(self.product.get_absolute_url()).status_code, 404)

    def test_home_links_to_product_pages(self):
        self.assertContains(self.client.get('/'), f'href="{self.product.get_absolute_url()}"')

    def test_sitemap_lists_products(self):
        self.assertContains(self.client.get('/sitemap.xml'), self.product.get_absolute_url())
