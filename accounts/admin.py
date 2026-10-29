from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
	list_display = ('email', 'name', 'role', 'is_staff', 'is_active')
	search_fields = ('email', 'name', 'username')
	list_filter = ('role', 'is_staff', 'is_active')
	ordering = ('email',)
