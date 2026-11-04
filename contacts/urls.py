from django.urls import path

from . import views

app_name = 'contacts'

urlpatterns = [
    path('kontakti/', views.ContactPageView.as_view(), name='page'),
    path('zapitvane/', views.inquiry, name='inquiry'),
    path('kontakt/', views.contact, name='contact'),
]
