from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = 'projects'

urlpatterns = [
    path('proekti/', RedirectView.as_view(pattern_name='projects:eu', permanent=True), name='index'),
    path('proekti/evropeysko-finansirane/', views.EuProjectListView.as_view(), name='eu'),
    path('proekti/evropeysko-finansirane/<slug:slug>/', views.EuProjectDetailView.as_view(), name='eu_detail'),
    path('proekti/realizirani/', views.RealizedProjectListView.as_view(), name='realized'),
    path('proekti/realizirani/<slug:slug>/', views.RealizedProjectDetailView.as_view(), name='realized_detail'),
]
