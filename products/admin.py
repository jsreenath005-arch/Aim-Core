from django.contrib import admin

from .models import Category, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
	list_display = ('category_id', 'category_name', 'description')
	search_fields = ('category_name',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
	list_display = ('product_id', 'product_name', 'brand', 'category', 'price', 'stock', 'connectivity')
	list_filter = ('category', 'brand', 'connectivity')
	search_fields = ('product_name', 'brand', 'description')
	list_editable = ('price', 'stock')
