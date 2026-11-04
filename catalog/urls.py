from django.urls import path

from . import views

app_name = 'catalog'

urlpatterns = [
    path('produkti/', views.CatalogView.as_view(), name='list'),
    path('produkti/<slug:slug>/', views.CategoryView.as_view(), name='category'),
    path('produkti/<slug:category>/<slug:slug>/', views.ProductDetailView.as_view(), name='product'),
]
