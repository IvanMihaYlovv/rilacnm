from django.urls import path, re_path

from . import views

app_name = 'core'

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('za-nas/', views.AboutView.as_view(), name='about'),
    path('uslugi/', views.ServicesView.as_view(), name='services'),
    path('uslugi/<slug:slug>/', views.ServiceDetailView.as_view(), name='service'),
    path('vaprosi/', views.FaqView.as_view(), name='faq'),
    path('sertifikati/', views.CertificatesView.as_view(), name='certificates'),
    path('poveritelnost/', views.PrivacyView.as_view(), name='privacy'),
    # Addresses of the previous Google Sites website.
    re_path(r'^български(?:/(?P<old>[^/]+))?/?$', views.LegacyRedirectView.as_view(), name='legacy'),
]
