from django.db.models import Prefetch
from django.urls import reverse
from django.views.generic import DetailView, TemplateView

from contacts.forms import InquiryForm
from core.seo import SeoPageMixin, item_list_node, product_node

from .models import Category, Product

RELATED_LIMIT = 8


def _product_entries(products):
    return [(p.name, p.get_absolute_url()) for p in products]


class CatalogView(SeoPageMixin, TemplateView):
    template_name = 'catalog/product_list.html'
    page_type = 'CollectionPage'
    page_title = 'Метални контейнери, кофи и парково обзавеждане'
    page_heading = 'Метални изделия за града, дома и строежа'
    page_lead = ('Контейнери за отпадъци, метални кофи и парково обзавеждане — собствено производство '
                 'в гр. Рила, с ясни технически данни за всеки продукт.')
    page_eyebrow = 'Продукти'
    page_description = ('Каталог на РИЛА-СНМ: контейнери „Бобър“ и „Ракла“ 1100 л, стоманени контейнери, '
                        'метални кофи 110 л, паркови кошчета и пейки. Технически данни и оферта.')

    def get_breadcrumbs(self):
        return [('Продукти', reverse('catalog:list'))]

    def get_categories(self):
        categories = Category.objects.active().prefetch_related(
            Prefetch('products', queryset=Product.objects.for_listing(), to_attr='listed'))
        return [c for c in categories if c.listed]

    def get_context_data(self, **kwargs):
        self.categories = self.get_categories()
        ctx = super().get_context_data(**kwargs)
        ctx['categories'] = self.categories
        return ctx

    def get_schema_nodes(self):
        return [item_list_node(_product_entries(p for c in self.categories for p in c.listed))]


class CategoryView(SeoPageMixin, DetailView):
    template_name = 'catalog/category_detail.html'
    context_object_name = 'category'
    page_type = 'CollectionPage'
    page_eyebrow = 'Продукти'

    def get_queryset(self):
        return Category.objects.active()

    def get_page_title(self):
        return f'{self.object.name} — производител'

    def get_page_heading(self):
        return self.object.name

    def get_page_lead(self):
        return self.object.description

    def get_page_description(self):
        return self.object.seo_description

    def get_breadcrumbs(self):
        return [('Продукти', reverse('catalog:list')), (self.object.name, self.object.get_absolute_url())]

    def get_context_data(self, **kwargs):
        self.products = list(Product.objects.for_listing().filter(category=self.object))
        ctx = super().get_context_data(**kwargs)
        ctx.update(products=self.products,
                   other_categories=Category.objects.active().exclude(pk=self.object.pk))
        return ctx

    def get_schema_nodes(self):
        return [item_list_node(_product_entries(self.products))]


class ProductDetailView(SeoPageMixin, DetailView):
    template_name = 'catalog/product_detail.html'
    context_object_name = 'product'
    page_type = 'ItemPage'

    def get_queryset(self):
        return Product.objects.for_listing().filter(category__slug=self.kwargs['category'])

    def get_page_title(self):
        return self.object.seo_title

    def get_page_description(self):
        return self.object.seo_description

    def get_breadcrumbs(self):
        product = self.object
        return [
            ('Продукти', reverse('catalog:list')),
            (product.category.name, product.category.get_absolute_url()),
            (product.name, product.get_absolute_url()),
        ]

    def get_schema_nodes(self):
        return [product_node(self.object)]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        product = self.object
        ctx.update(
            images=list(product.images.all()),
            related=list(
                Product.objects.for_listing()
                .filter(category=product.category_id)
                .exclude(pk=product.pk)[:RELATED_LIMIT]
            ),
            inquiry_form=InquiryForm(initial={'product': product.pk}),
        )
        return ctx
