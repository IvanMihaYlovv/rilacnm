from django.contrib import admin

from .models import News


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ['title', 'published_at', 'is_published']
    list_filter = ['is_published']
    search_fields = ['title', 'excerpt']
    date_hierarchy = 'published_at'
