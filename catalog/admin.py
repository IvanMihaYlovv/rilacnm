from django.contrib import admin
from django.db.models import Count

from .models import Category, Product, ProductImage


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'product_count', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    search_fields = ['name']
    fields = ['name', 'slug', 'description', 'body', 'meta_description', 'order', 'is_active']

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_product_count=Count('products'))

    @admin.display(description='продукти', ordering='_product_count')
    def product_count(self, obj):
        return obj._product_count


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ['image', 'alt_text', 'is_primary', 'order']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'highlight', 'order', 'is_featured', 'is_active']
    list_editable = ['order', 'is_featured', 'is_active']
    list_filter = ['category', 'is_active', 'is_featured']
    list_select_related = ['category']
    search_fields = ['name', 'short_description']
    inlines = [ProductImageInline]
    fieldsets = [
        (None, {'fields': ['category', 'name', 'slug', 'short_description', 'description',
                           'highlight', 'specifications', 'standards', 'options']}),
        ('Цветове и чертеж', {'fields': ['colors', 'drawing']}),
        ('Видимост', {'fields': ['is_active', 'is_featured', 'order']}),
        ('SEO', {'fields': ['meta_title', 'meta_description'], 'classes': ['collapse']}),
    ]
