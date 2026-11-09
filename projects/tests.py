from datetime import date, timedelta

from django.core.management import call_command
from django.test import TestCase

from .models import Project


class ProjectPagesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_content', verbosity=0)
        cls.eu_project = Project.objects.filter(kind=Project.Kind.EU_FUNDED).first()
        cls.client_project = Project.objects.create(
            title='Метална конструкция за склад', kind=Project.Kind.CLIENT,
            summary='Носеща конструкция.', client='Община Рила', location='гр. Рила')

    def test_index_redirects_to_first_option_of_the_menu(self):
        self.assertRedirects(self.client.get('/proekti/'), '/proekti/evropeysko-finansirane/',
                             status_code=301)

    def test_each_list_shows_only_its_kind(self):
        eu = self.client.get('/proekti/evropeysko-finansirane/')
        self.assertContains(eu, self.eu_project.title)
        self.assertNotContains(eu, self.client_project.title)

        realized = self.client.get('/proekti/realizirani/')
        self.assertContains(realized, self.client_project.title)
        self.assertNotContains(realized, self.eu_project.title)

    def test_detail_urls_do_not_cross_kinds(self):
        wrong = f'/proekti/realizirani/{self.eu_project.slug}/'
        self.assertEqual(self.client.get(wrong).status_code, 404)

    def test_eu_detail_keeps_the_funding_details(self):
        project = Project.objects.get(contract_number='BG16RFOP002-2.040-1567-C01')
        response = self.client.get(project.get_absolute_url())
        self.assertContains(response, 'BG16RFOP002-2.040-1567-C01')
        self.assertContains(response, project.funding_statement)
        self.assertContains(response, 'Публична покана')
        self.assertEqual(project.grant_share, 70)

    def test_eu_detail_shows_the_logos_of_its_programme_period(self):
        for prefix, expected, absent in [
            ('BG16RFPR', ['eu-cofunded.png', 'pkip-2021-2027.png'], 'opic-2014-2020.png'),
            ('BG16RFOP', ['eu-erdf.png', 'opic-2014-2020.png'], 'pkip-2021-2027.png'),
        ]:
            project = Project.objects.filter(contract_number__startswith=prefix).first()
            response = self.client.get(project.get_absolute_url())
            for logo in expected:
                self.assertContains(response, f'img/eu/{logo}')
            self.assertNotContains(response, absent)

    def test_realized_detail_has_no_programme_logos(self):
        self.assertNotContains(self.client.get(self.client_project.get_absolute_url()), 'img/eu/')

    def test_funding_parts_add_up_to_the_grant(self):
        for project in Project.objects.filter(kind=Project.Kind.EU_FUNDED):
            self.assertEqual(project.eu_amount + project.national_amount, project.grant_amount)

    def test_realized_detail_shows_client(self):
        self.assertContains(self.client.get(self.client_project.get_absolute_url()), 'Община Рила')

    def test_unpublished_is_404(self):
        Project.objects.filter(pk=self.eu_project.pk).update(is_published=False)
        self.assertEqual(self.client.get(self.eu_project.get_absolute_url()).status_code, 404)

    def test_status_follows_the_end_date(self):
        self.assertFalse(Project(end_date=None).is_finished)
        self.assertTrue(Project(end_date=date.today() - timedelta(days=2)).is_finished)
        self.assertFalse(Project(end_date=date.today() + timedelta(days=2)).is_finished)


class EmptyRealizedProjectsTests(TestCase):
    """Until the first client project is published, the page exists but stays out of Google."""

    @classmethod
    def setUpTestData(cls):
        call_command('seed_content', verbosity=0)

    def test_empty_page_is_noindex_and_not_in_sitemap(self):
        response = self.client.get('/proekti/realizirani/')
        self.assertContains(response, 'content="noindex, follow"')
        self.assertContains(response, 'Подготвяме портфолиото ни')
        self.assertNotContains(self.client.get('/sitemap.xml'), '/proekti/realizirani/<')

    def test_goes_live_with_the_first_project(self):
        Project.objects.create(title='Навес', kind=Project.Kind.CLIENT, summary='x')
        self.assertNotContains(self.client.get('/proekti/realizirani/'), 'content="noindex')
        self.assertContains(self.client.get('/sitemap.xml'), '/proekti/realizirani/<')
