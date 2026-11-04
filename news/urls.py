from django.urls import path

from . import views

app_name = 'news'

urlpatterns = [
    path('novini/', views.NewsListView.as_view(), name='list'),
    path('novini/<slug:slug>/', views.NewsDetailView.as_view(), name='detail'),
]
