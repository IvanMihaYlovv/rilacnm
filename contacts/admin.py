from django.contrib import admin
from django.db.models import Count
from django.template.defaultfilters import filesizeformat
from django.utils.html import format_html

from .models import ContactMessage, Inquiry, InquiryAttachment


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


class InquiryAttachmentInline(admin.TabularInline):
    """Files the visitor sent: read-only here, downloaded through the staff-only view."""

    model = InquiryAttachment
    extra = 0
    can_delete = False
    fields = ['download', 'file_size']
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False

    @admin.display(description='файл')
    def download(self, obj):
        return format_html('<a href="{}">{} ⬇</a>', obj.get_download_url(), obj.original_name)

    @admin.display(description='размер')
    def file_size(self, obj):
        return filesizeformat(obj.size)


@admin.register(Inquiry)
class InquiryAdmin(SubmissionAdmin):
    list_display = ['name', 'company', 'product', 'quantity', 'files', 'phone', 'created_at',
                    'is_processed']
    list_select_related = ['product']
    inlines = [InquiryAttachmentInline]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(file_count=Count('attachments'))

    @admin.display(description='файлове', ordering='file_count')
    def files(self, obj):
        return obj.file_count or '—'
    autocomplete_fields = ['product']


@admin.register(ContactMessage)
class ContactMessageAdmin(SubmissionAdmin):
    list_display = ['name', 'subject', 'email', 'phone', 'created_at', 'is_processed']
