from django.contrib import admin

from .models import ContactMessage, Inquiry


class SubmissionAdmin(admin.ModelAdmin):
    list_filter = ['is_processed', 'created_at']
    search_fields = ['name', 'email', 'phone', 'message']
    readonly_fields = ['created_at', 'ip_address', 'user_agent']
    date_hierarchy = 'created_at'
    actions = ['mark_processed']

    @admin.action(description='Маркирай като обработени')
    def mark_processed(self, request, queryset):
        updated = queryset.update(is_processed=True)
        self.message_user(request, f'Обработени: {updated}')


@admin.register(Inquiry)
class InquiryAdmin(SubmissionAdmin):
    list_display = ['name', 'company', 'product', 'quantity', 'phone', 'created_at', 'is_processed']
    list_select_related = ['product']
    autocomplete_fields = ['product']


@admin.register(ContactMessage)
class ContactMessageAdmin(SubmissionAdmin):
    list_display = ['name', 'subject', 'email', 'phone', 'created_at', 'is_processed']
