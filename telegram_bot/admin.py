from django.contrib import admin
from django.utils.html import format_html
from .models import TelegramUser, Department, DepartmentAdmin as DepartmentAdminModel

@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = ['username', 'first_name', 'last_name', 'telegram_id', 'is_admin', 'is_active', 'created_at']
    list_filter = ['is_admin', 'is_active', 'created_at']
    search_fields = ['username', 'first_name', 'last_name', 'telegram_id']
    readonly_fields = ['telegram_id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Asosiy ma\'lumotlar', {
            'fields': ('user', 'telegram_id', 'username', 'first_name', 'last_name')
        }),
        ('Huquqlar', {
            'fields': ('is_admin', 'is_active')
        }),
        ('Vaqt belgilari', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'daily_limit', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Asosiy ma\'lumotlar', {
            'fields': ('name', 'description'),
            'description': 'Bo\'lim nomi va tavsifi'
        }),
        ('Sozlamalar', {
            'fields': ('daily_limit', 'is_active'),
            'description': 'Kunlik uchrashuvlar limiti va faollik holati'
        }),
        ('Vaqt belgilari', {
            'fields': ('created_at',),
            'classes': ('collapse',),
            'description': 'Yaratilgan vaqti (avtomatik to\'ldiriladi)'
        })
    )
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if 'name' in form.base_fields:
            form.base_fields['name'].widget.attrs.update({
                'class': 'vTextField',
                'placeholder': 'Bo\'lim nomini kiriting...'
            })
        if 'description' in form.base_fields:
            form.base_fields['description'].widget.attrs.update({
                'class': 'vLargeTextField',
                'rows': 3,
                'placeholder': 'Bo\'lim haqida qisqacha ma\'lumot...'
            })
        if 'daily_limit' in form.base_fields:
            form.base_fields['daily_limit'].widget.attrs.update({
                'class': 'vIntegerField',
                'min': 1,
                'max': 50,
                'placeholder': 'Kunlik uchrashuvlar soni...'
            })
        if 'is_active' in form.base_fields:
            form.base_fields['is_active'].widget.attrs.update({
                'class': 'form-check-input'
            })
        return form

@admin.register(DepartmentAdminModel)
class DepartmentAdminAdmin(admin.ModelAdmin):
    list_display = ['telegram_user', 'department', 'is_active', 'created_at']
    list_filter = ['is_active', 'department', 'created_at']
    search_fields = ['telegram_user__username', 'telegram_user__first_name', 'department__name']
    readonly_fields = ['created_at']
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if 'telegram_user' in form.base_fields:
            form.base_fields['telegram_user'].widget.attrs.update({
                'class': 'form-control'
            })
        if 'department' in form.base_fields:
            form.base_fields['department'].widget.attrs.update({
                'class': 'form-control'
            })
        if 'is_active' in form.base_fields:
            form.base_fields['is_active'].widget.attrs.update({
                'class': 'form-check-input'
            })
        return form
