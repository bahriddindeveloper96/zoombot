from django.contrib import admin
from django.utils import timezone
from .models import ZoomMeeting, BookingRequest

@admin.register(ZoomMeeting)
class ZoomMeetingAdmin(admin.ModelAdmin):
    list_display = ['title', 'department', 'created_by', 'start_time', 'duration', 'status', 'is_active']
    list_filter = ['status', 'is_active', 'department', 'created_at']
    search_fields = ['title', 'created_by__first_name', 'created_by__last_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    date_hierarchy = 'start_time'
    
    fieldsets = (
        ('Asosiy ma\'lumotlar', {
            'fields': ('title', 'description', 'department', 'created_by')
        }),
        ('Uchrashuv tafsilotlari', {
            'fields': ('start_time', 'duration', 'status', 'is_active')
        }),
        ('Zoom ma\'lumotlari', {
            'fields': ('zoom_meeting_id', 'meeting_url', 'password')
        }),
        ('Vaqt belgilari', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

@admin.register(BookingRequest)
class BookingRequestAdmin(admin.ModelAdmin):
    list_display = ['title', 'department', 'requested_by', 'preferred_start_time', 'duration', 'status', 'created_at']
    list_filter = ['status', 'department', 'created_at']
    search_fields = ['title', 'requested_by__first_name', 'requested_by__last_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    date_hierarchy = 'preferred_start_time'
    
    actions = ['approve_requests', 'reject_requests']
    
    fieldsets = (
        ('Asosiy ma\'lumotlar', {
            'fields': ('title', 'description', 'department', 'requested_by')
        }),
        ('So\'rov tafsilotlari', {
            'fields': ('preferred_start_time', 'duration', 'status')
        }),
        ('Qayta ishlash', {
            'fields': ('processed_by', 'processed_at', 'rejection_reason'),
            'classes': ('collapse',)
        }),
        ('Vaqt belgilari', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def approve_requests(self, request, queryset):
        for req in queryset.filter(status='pending'):
            req.status = 'approved'
            req.processed_by = request.user.telegramuser
            req.processed_at = timezone.now()
            req.save()
    approve_requests.short_description = "Tanlangan so'rovlarni tasdiqlash"
    
    def reject_requests(self, request, queryset):
        for req in queryset.filter(status='pending'):
            req.status = 'rejected'
            req.processed_by = request.user.telegramuser
            req.processed_at = timezone.now()
            req.save()
    reject_requests.short_description = "Tanlangan so'rovlarni rad etish"
