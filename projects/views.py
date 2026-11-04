from django.urls import reverse
from django.views.generic import DetailView, ListView

from core.seo import SeoPageMixin, item_list_node

from .models import Project


class ProjectListView(SeoPageMixin, ListView):
    template_name = 'projects/project_list.html'
    context_object_name = 'projects'
    page_type = 'CollectionPage'
    page_eyebrow = 'Проекти'
    kind = None
    list_url_name = None

    def get_queryset(self):
        return Project.objects.published().filter(kind=self.kind)

    def get_breadcrumbs(self):
        return [(self.page_heading, reverse(self.list_url_name))]

    def get_schema_nodes(self):
        return [item_list_node((p.title, p.get_absolute_url()) for p in self.object_list)]


class EuProjectListView(ProjectListView):
    kind = Project.Kind.EU_FUNDED
    list_url_name = 'projects:eu'
    page_title = 'Проекти с европейско финансиране'
    page_heading = 'Проекти с Европейско финансиране'
    page_lead = ('С подкрепата на европейските програми обновихме машинния парк, увеличихме капацитета '
                 'и подготвихме производството за кръгова икономика.')
    page_description = ('Проекти на РИЛА-СНМ ЕООД, съфинансирани от Европейския съюз по програмите '
                        '„Иновации и конкурентоспособност“ и „Конкурентоспособност и иновации“.')


class RealizedProjectListView(ProjectListView):
    kind = Project.Kind.CLIENT
    list_url_name = 'projects:realized'
    page_title = 'Реализирани проекти — метални конструкции и изделия'
    page_heading = 'Реализирани Проекти'
    page_lead = ('Метални конструкции и изделия, които сме произвели за общини, фирми и '
                 'строителни обекти — от чертежа до доставката.')
    page_description = ('Реализирани проекти на РИЛА-СНМ: метални конструкции и изделия, '
                        'произведени за общини и фирми в завода ни в гр. Рила.')

    def get_noindex(self):
        # An empty page would only be thin content; it joins the index with its first project.
        return not self.object_list


class ProjectDetailView(SeoPageMixin, DetailView):
    template_name = 'projects/project_detail.html'
    context_object_name = 'project'
    page_type = 'ItemPage'
    page_eyebrow = 'Проекти'
    list_view = None

    def get_queryset(self):
        return Project.objects.published().filter(kind=self.list_view.kind)

    def get_page_title(self):
        return self.object.title

    def get_page_lead(self):
        return self.object.summary

    def get_page_description(self):
        return self.object.seo_description

    def get_breadcrumbs(self):
        return [
            (self.list_view.page_heading, reverse(self.list_view.list_url_name)),
            (self.object.title, self.object.get_absolute_url()),
        ]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(list_url=reverse(self.list_view.list_url_name),
                   list_heading=self.list_view.page_heading,
                   others=self.get_queryset().exclude(pk=self.object.pk))
        return ctx


class EuProjectDetailView(ProjectDetailView):
    list_view = EuProjectListView


class RealizedProjectDetailView(ProjectDetailView):
    list_view = RealizedProjectListView
