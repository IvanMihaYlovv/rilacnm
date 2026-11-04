from django.urls import reverse
from django.views.generic import DetailView, ListView

from core.seo import SeoPageMixin, news_node

from .models import News


class NewsListView(SeoPageMixin, ListView):
    template_name = 'news/news_list.html'
    context_object_name = 'news'
    paginate_by = 12
    page_type = 'CollectionPage'
    page_title = 'Новини от завода'
    page_lead = 'Нови машини, проекти и какво се случва в цеха.'
    page_eyebrow = 'Новини'
    page_description = ('Актуална информация от РИЛА-СНМ ЕООД: инвестиции, европейски проекти '
                        'и новини от завода в гр. Рила.')

    def get_queryset(self):
        return News.objects.published()

    def get_breadcrumbs(self):
        return [('Новини', reverse('news:list'))]

    def get_noindex(self):
        return not self.object_list


class NewsDetailView(SeoPageMixin, DetailView):
    template_name = 'news/news_detail.html'
    context_object_name = 'item'
    page_eyebrow = 'Новини'

    def get_queryset(self):
        return News.objects.published()

    def get_page_title(self):
        return self.object.title

    def get_page_description(self):
        return self.object.seo_description

    def get_breadcrumbs(self):
        return [('Новини', reverse('news:list')), (self.object.title, self.object.get_absolute_url())]

    def get_schema_nodes(self):
        return [news_node(self.object)]
