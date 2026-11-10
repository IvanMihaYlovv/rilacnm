from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from core.sitemaps import sitemaps
from core.views import robots_txt

admin.site.site_header = 'РИЛА-СНМ · администрация'
admin.site.site_title = 'РИЛА-СНМ'

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path('robots.txt', robots_txt, name='robots_txt'),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps},
         name='django.contrib.sitemaps.views.sitemap'),
    path('', include('catalog.urls')),
    path('', include('projects.urls')),
    path('', include('news.urls')),
    path('', include('contacts.urls')),
    path('', include('core.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
