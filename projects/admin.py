from django.contrib import admin

from .models import Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['title', 'kind', 'is_custom', 'client', 'contract_number', 'start_date', 'order', 'is_published']
    list_editable = ['order', 'is_published']
    list_filter = ['kind', 'is_custom', 'is_published']
    search_fields = ['title', 'client', 'contract_number', 'programme']
    date_hierarchy = 'start_date'
