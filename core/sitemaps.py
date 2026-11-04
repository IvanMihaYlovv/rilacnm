from urllib.parse import urlsplit

from django.conf import settings
from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from catalog.models import Category, Product
from news.models import News
from projects.models import Project

from .content import SERVICES


class SiteSitemap(Sitemap):
    """Always lists the canonical origin, whatever host the request came in on."""

    protocol = 'https'

    def get_domain(self, site=None):
        return urlsplit(settings.SITE_URL).netloc


class StaticSitemap(SiteSitemap):
    changefreq = 'monthly'

    def items(self):
        names = ['core:home', 'core:about', 'core:services', 'core:faq', 'core:certificates',
                 'core:privacy', 'catalog:list', 'projects:eu', 'contacts:page']
        # Empty listings are noindex until there is something on them.
        if Project.objects.published().filter(kind=Project.Kind.CLIENT).exists():
            names.append('projects:realized')
        if News.objects.published().exists():
            names.append('news:list')
        return names

    def location(self, item):
        return reverse(item)


class ServiceSitemap(SiteSitemap):
    changefreq = 'monthly'

    def items(self):
        return SERVICES

    def location(self, item):
        return reverse('core:service', kwargs={'slug': item['slug']})


class CategorySitemap(SiteSitemap):
    changefreq = 'monthly'

    def items(self):
        return Category.objects.active().order_by('pk')

    def lastmod(self, category):
        return category.updated_at


class ProductSitemap(SiteSitemap):
    changefreq = 'monthly'

    def items(self):
        return (Product.objects.active().filter(category__is_active=True)
                .select_related('category').order_by('pk'))

    def lastmod(self, product):
        return product.updated_at


class ProjectSitemap(SiteSitemap):
    changefreq = 'yearly'

    def items(self):
        return Project.objects.published().order_by('pk')

    def lastmod(self, project):
        return project.updated_at


class NewsSitemap(SiteSitemap):
    changefreq = 'yearly'

    def items(self):
        return News.objects.published().order_by('pk')

    def lastmod(self, item):
        return item.updated_at


sitemaps = {
    'static': StaticSitemap,
    'services': ServiceSitemap,
    'categories': CategorySitemap,
    'products': ProductSitemap,
    'projects': ProjectSitemap,
    'news': NewsSitemap,
}
