from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from telegram_bot.models import TelegramUser, Department
import uuid

class ZoomMeeting(models.Model):
    STATUS_CHOICES = [
        ('scheduled', 'Rejalashtirilgan'),
        ('active', 'Faol'),
        ('ended', 'Tugagan'),
        ('cancelled', 'Bekor qilingan'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    zoom_meeting_id = models.CharField(max_length=100, blank=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    created_by = models.ForeignKey(TelegramUser, on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    duration = models.PositiveIntegerField(help_text="Daqiqalarda")
    meeting_url = models.URLField(blank=True)
    password = models.CharField(max_length=50, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_time']

    def __str__(self):
        return f"{self.title} - {self.start_time.strftime('%Y-%m-%d %H:%M')}"

    @property
    def end_time(self):
        return self.start_time + timezone.timedelta(minutes=self.duration)

class BookingRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Kutilmoqda'),
        ('approved', 'Tasdiqlangan'),
        ('rejected', 'Rad etilgan'),
        ('cancelled', 'Bekor qilingan'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    requested_by = models.ForeignKey(TelegramUser, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    preferred_start_time = models.DateTimeField()
    duration = models.PositiveIntegerField(help_text="Daqiqalarda")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    rejection_reason = models.TextField(blank=True)
    processed_by = models.ForeignKey(TelegramUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_requests')
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.status}"
