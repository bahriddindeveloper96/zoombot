from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Q
from django.http import JsonResponse
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.urls import reverse
from .models import ZoomMeeting, BookingRequest
from telegram_bot.models import Department, TelegramUser
import json

def custom_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('booking:dashboard')
    else:
        form = AuthenticationForm()
    
    return render(request, 'booking/login.html', {'form': form})

@login_required
def dashboard(request):
    today = timezone.now().date()
    
    # Statistika
    total_meetings = ZoomMeeting.objects.filter(is_active=True).count()
    today_meetings = ZoomMeeting.objects.filter(
        start_time__date=today,
        is_active=True
    ).count()
    
    pending_requests = BookingRequest.objects.filter(status='pending').count()
    active_departments = Department.objects.filter(is_active=True).count()
    
    # Eng so'nggi uchrashuvlar
    recent_meetings = ZoomMeeting.objects.filter(
        is_active=True
    ).order_by('-created_at')[:5]
    
    # Kutilayotgan so'rovlar
    pending_requests_list = BookingRequest.objects.filter(
        status='pending'
    ).order_by('-created_at')[:5]
    
    # Bo'limlar bo'yicha statistika
    department_stats = ZoomMeeting.objects.filter(
        is_active=True
    ).values('department__name').annotate(
        count=Count('id')
    ).order_by('-count')[:5]
    
    context = {
        'total_meetings': total_meetings,
        'today_meetings': today_meetings,
        'pending_requests': pending_requests,
        'active_departments': active_departments,
        'recent_meetings': recent_meetings,
        'pending_requests_list': pending_requests_list,
        'department_stats': department_stats,
    }
    
    return render(request, 'booking/dashboard.html', context)

@login_required
def meetings_list(request):
    meetings = ZoomMeeting.objects.filter(is_active=True).order_by('-start_time')
    
    # Filtrlar
    status_filter = request.GET.get('status')
    department_filter = request.GET.get('department')
    date_filter = request.GET.get('date')
    
    if status_filter:
        meetings = meetings.filter(status=status_filter)
    
    if department_filter:
        meetings = meetings.filter(department_id=department_filter)
    
    if date_filter:
        meetings = meetings.filter(start_time__date=date_filter)
    
    departments = Department.objects.filter(is_active=True)
    
    context = {
        'meetings': meetings,
        'departments': departments,
        'status_choices': ZoomMeeting.STATUS_CHOICES,
    }
    
    return render(request, 'booking/meetings_list.html', context)

@login_required
def meeting_detail(request, meeting_id):
    meeting = get_object_or_404(ZoomMeeting, id=meeting_id, is_active=True)
    
    if request.method == 'POST' and request.user.is_staff:
        action = request.POST.get('action')
        
        if action == 'cancel':
            meeting.status = 'cancelled'
            meeting.save()
            messages.success(request, 'Uchrashuv muvaffaqiyatli bekor qilindi!')
        elif action == 'activate':
            meeting.status = 'active'
            meeting.save()
            messages.success(request, 'Uchrashuv faollashtirildi!')
        
        return redirect('meeting_detail', meeting_id=meeting_id)
    
    return render(request, 'booking/meeting_detail.html', {'meeting': meeting})

@staff_member_required
def requests_list(request):
    requests = BookingRequest.objects.all().order_by('-created_at')
    
    # Filtrlar
    status_filter = request.GET.get('status')
    department_filter = request.GET.get('department')
    
    if status_filter:
        requests = requests.filter(status=status_filter)
    
    if department_filter:
        requests = requests.filter(department_id=department_filter)
    
    departments = Department.objects.filter(is_active=True)
    
    context = {
        'requests': requests,
        'departments': departments,
        'status_choices': BookingRequest.STATUS_CHOICES,
    }
    
    return render(request, 'booking/requests_list.html', context)

@staff_member_required
def request_detail(request, request_id):
    booking_request = get_object_or_404(BookingRequest, id=request_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        rejection_reason = request.POST.get('rejection_reason', '')
        
        if action == 'approve':
            booking_request.status = 'approved'
            booking_request.processed_by = request.user.telegramuser
            booking_request.processed_at = timezone.now()
            booking_request.save()
            
            # Create Zoom meeting
            meeting = ZoomMeeting.objects.create(
                title=booking_request.title,
                description=booking_request.description,
                department=booking_request.department,
                created_by=booking_request.requested_by,
                start_time=booking_request.preferred_start_time,
                duration=booking_request.duration,
                status='scheduled'
            )
            
            messages.success(request, f'So\'rov tasdiqlandi va uchrashuv yaratildi: {meeting.id}')
            
        elif action == 'reject':
            booking_request.status = 'rejected'
            booking_request.rejection_reason = rejection_reason
            booking_request.processed_by = request.user.telegramuser
            booking_request.processed_at = timezone.now()
            booking_request.save()
            
            messages.success(request, 'So\'rov rad etildi!')
        
        return redirect('requests_list')
    
    return render(request, 'booking/request_detail.html', {'request': booking_request})

@staff_member_required
def departments_list(request):
    departments = Department.objects.all().order_by('name')
    
    # Statistika
    for dept in departments:
        dept.meeting_count = ZoomMeeting.objects.filter(
            department=dept,
            is_active=True
        ).count()
        dept.request_count = BookingRequest.objects.filter(
            department=dept
        ).count()
    
    return render(request, 'booking/departments_list.html', {'departments': departments})

@staff_member_required
def department_detail(request, department_id):
    department = get_object_or_404(Department, id=department_id)
    
    # Bo'lim uchun uchrashuvlar
    meetings = ZoomMeeting.objects.filter(
        department=department,
        is_active=True
    ).order_by('-start_time')
    
    # Bo'lim uchun so'rovlar
    requests = BookingRequest.objects.filter(
        department=department
    ).order_by('-created_at')
    
    # Bo'lim adminlari
    admins = department.departmentadmin_set.filter(is_active=True)
    
    context = {
        'department': department,
        'meetings': meetings,
        'requests': requests,
        'admins': admins,
    }
    
    return render(request, 'booking/department_detail.html', context)

@login_required
def api_meeting_stats(request):
    """API endpoint for meeting statistics"""
    today = timezone.now().date()
    
    stats = {
        'total': ZoomMeeting.objects.filter(is_active=True).count(),
        'today': ZoomMeeting.objects.filter(
            start_time__date=today,
            is_active=True
        ).count(),
        'this_week': ZoomMeeting.objects.filter(
            start_time__week=today.isocalendar()[1],
            start_time__year=today.year,
            is_active=True
        ).count(),
        'this_month': ZoomMeeting.objects.filter(
            start_time__month=today.month,
            start_time__year=today.year,
            is_active=True
        ).count(),
    }
    
    return JsonResponse(stats)

@login_required
def api_department_stats(request):
    """API endpoint for department statistics"""
    stats = list(
        ZoomMeeting.objects.filter(is_active=True)
        .values('department__name')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    
    return JsonResponse({'stats': stats})
