from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from .models import News


class NewsPagesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.item = News.objects.create(title='Нова машина', excerpt='Кратко.', body='Дълго.')
        cls.scheduled = News.objects.create(title='Бъдеща новина', excerpt='x', body='y',
                                            published_at=timezone.now() + timedelta(days=3))

    def test_list_hides_scheduled_news(self):
        response = self.client.get('/novini/')
        self.assertContains(response, self.item.title)
        self.assertNotContains(response, self.scheduled.title)

    def test_detail_has_article_markup(self):
        response = self.client.get(self.item.get_absolute_url())
        self.assertContains(response, '"@type":"NewsArticle"')
        self.assertContains(response, '<meta property="og:type" content="article">')

    def test_scheduled_detail_is_404(self):
        self.assertEqual(self.client.get(self.scheduled.get_absolute_url()).status_code, 404)

    def test_empty_list_is_noindex(self):
        News.objects.all().delete()
        self.assertContains(self.client.get('/novini/'), 'content="noindex, follow"')

    def test_month_names_are_lowercase(self):
        self.item.published_at = timezone.make_aware(timezone.datetime(2025, 9, 1, 12))
        self.item.save()
        self.assertContains(self.client.get(self.item.get_absolute_url()), '1 септември 2025')
