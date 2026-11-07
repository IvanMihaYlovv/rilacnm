from django.conf import settings
from django.db.models import Count, Q
from django.http import Http404, HttpResponse
from django.urls import reverse
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET
from django.views.generic import RedirectView, TemplateView

from catalog.models import Category, Product
from news.models import News

from .content import (ABOUT_TEXT, CAPACITY, COMPANY, FAQ, HISTORY, LEGACY_PAGES, LEGACY_PRODUCTS,
                      MISSION, PRODUCT_CERTIFICATES, QUALITY_POLICY, SERVICES, SERVICES_BY_SLUG, STATS)
from .seo import SeoPageMixin, faq_node, item_list_node, service_node


def service_url(service):
    return reverse('core:service', kwargs={'slug': service['slug']})


class SitePageView(SeoPageMixin, TemplateView):
    pass


class HomeView(SitePageView):
    template_name = 'core/home.html'
    page_description = ('Производител на контейнери за отпадъци, метални кофи, паркови кошчета и метални '
                        'конструкции по проект. Завод в гр. Рила от 1971 г. ISO 9001, 14001, 45001.')

    def get_full_title(self):
        return f"Метални контейнери и конструкции | {COMPANY['legal_name']}, гр. Рила"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        products = list(Product.objects.for_listing().filter(is_featured=True))
        category_ids = {p.category_id for p in products}
        categories = list(Category.objects.active()
                          .annotate(product_count=Count('products', filter=Q(products__is_active=True)))
                          .filter(product_count__gt=0))
        ctx.update(
            category_cards=categories,
            # Only categories that actually have something to show in the slider.
            slider_categories=[c for c in categories if c.pk in category_ids],
            products=products,
            news=list(News.objects.published()[:3]),
            services=SERVICES,
            stats=STATS,
        )
        return ctx


class AboutView(SitePageView):
    template_name = 'core/about.html'
    page_type = 'AboutPage'
    page_title = 'За нас — завод за метални изделия в гр. Рила от 1971 г.'
    page_heading = 'Повече от 50 години занаят. Същата грижа за всеки детайл.'
    page_eyebrow = 'За нас'
    page_description = ('Семейно предприятие и завод за метални изделия в подножието на Рила, основан '
                        'през 1971 г. Вижте историята, капацитета и мисията на РИЛА-СНМ.')
    extra_context = {'about_text': ABOUT_TEXT, 'history': HISTORY, 'capacity': CAPACITY,
                     'mission': MISSION, 'stats': STATS}

    def get_breadcrumbs(self):
        return [('За нас', reverse('core:about'))]


class ServicesView(SitePageView):
    template_name = 'core/services.html'
    page_type = 'CollectionPage'
    page_title = 'Услуги за метална обработка — рязане, огъване, заваряване'
    page_heading = 'Металообработка на ишлеме и изработка по проект'
    page_lead = ('Нямате нужда от готов продукт, а от детайл, възел или цяла конструкция? '
                 'Цехът ни поема цялата верига — от рулона ламарина до боядисаното изделие.')
    page_eyebrow = 'Услуги'
    page_description = ('Разкрой на рулони, абкант, гилотина, плазмено и лазерно рязане, заваряване, '
                        'прахово боядисване и метални конструкции по проект — завод в гр. Рила.')
    extra_context = {'services': SERVICES}

    def get_breadcrumbs(self):
        return [('Услуги', reverse('core:services'))]

    def get_schema_nodes(self):
        return [item_list_node((s['title'], service_url(s)) for s in SERVICES)]


class ServiceDetailView(SitePageView):
    template_name = 'core/service_detail.html'
    page_eyebrow = 'Услуги'

    def dispatch(self, request, *args, **kwargs):
        self.service = SERVICES_BY_SLUG.get(kwargs['slug'])
        if self.service is None:
            raise Http404
        return super().dispatch(request, *args, **kwargs)

    def get_page_title(self):
        return self.service['seo_title']

    def get_page_heading(self):
        return self.service['title']

    def get_page_lead(self):
        return self.service['text']

    def get_page_description(self):
        return self.service['seo_description']

    def get_breadcrumbs(self):
        return [('Услуги', reverse('core:services')), (self.service['title'], self.request.path)]

    def get_schema_nodes(self):
        return [service_node(self.service, self.request.path)]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(service=self.service,
                   other_services=[s for s in SERVICES if s is not self.service])
        return ctx


class FaqView(SitePageView):
    template_name = 'core/faq.html'
    page_type = 'CollectionPage'
    page_title = 'Често задавани въпроси за контейнери и метални изделия'
    page_heading = 'Добре е да знаете'
    page_lead = 'Отговори на въпросите, които общини, фирми и строители ни задават най-често.'
    page_eyebrow = 'Въпроси и отговори'
    page_description = ('Каква е разликата между контейнер „Бобър“ и „Ракла“, какви стандарти спазваме, '
                        'работим ли по проект и с обществени поръчки — отговори от РИЛА-СНМ.')
    extra_context = {'faq': FAQ}

    def get_breadcrumbs(self):
        return [('Въпроси и отговори', reverse('core:faq'))]

    def get_schema_nodes(self):
        return [faq_node(FAQ)]


class CertificatesView(SitePageView):
    template_name = 'core/certificates.html'
    page_title = 'Сертификати ISO 9001, 14001, 45001 и политика по качество'
    page_heading = 'Сертификати и политика по качество'
    page_lead = ('Качеството, опазването на околната среда и безопасността при работа в завода '
                 'са уредени в интегрирана система за управление, сертифицирана по три стандарта. '
                 'Продуктите ни имат и сертификати за съответствие.')
    page_eyebrow = 'Качество'
    page_description = ('РИЛА-СНМ работи по сертифицирана система за управление съгласно ISO 9001:2015, '
                        'ISO 14001:2015 и ISO 45001:2018. Вижте сертификатите и политиката ни.')
    extra_context = {'policy': QUALITY_POLICY, 'product_certificates': PRODUCT_CERTIFICATES}

    def get_breadcrumbs(self):
        return [('Сертификати', reverse('core:certificates'))]


class PrivacyView(SitePageView):
    template_name = 'core/privacy.html'
    page_title = 'Политика за поверителност'
    page_lead = 'Какви лични данни събираме чрез този сайт, защо и какви са правата ви.'
    page_eyebrow = 'Правна информация'
    page_description = ('Как РИЛА-СНМ ЕООД обработва личните данни, изпратени чрез формите за запитване '
                        'и контакт на сайта, и какви са правата ви съгласно GDPR.')

    def get_breadcrumbs(self):
        return [('Политика за поверителност', reverse('core:privacy'))]


class LegacyRedirectView(RedirectView):
    """Sends the old Google Sites addresses to their new home, so rankings carry over."""

    permanent = True

    def get_redirect_url(self, *args, old=None, **kwargs):
        if old in LEGACY_PAGES:
            return reverse(LEGACY_PAGES[old])
        if old in LEGACY_PRODUCTS:
            product = (Product.objects.select_related('category')
                       .filter(slug=LEGACY_PRODUCTS[old]).first())
            return product.get_absolute_url() if product else reverse('catalog:list')
        raise Http404


@require_GET
@cache_control(max_age=60 * 60 * 24, public=True)
def robots_txt(request):
    lines = [
        'User-agent: *',
        'Disallow: /admin/',
        'Disallow: /zapitvane/',
        'Disallow: /kontakt/',
        '',
        f'Sitemap: {settings.SITE_URL}/sitemap.xml',
    ]
    return HttpResponse('\n'.join(lines) + '\n', content_type='text/plain; charset=utf-8')
