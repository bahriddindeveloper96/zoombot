from django.urls import path
from . import views

app_name = 'booking'

urlpatterns = [
    path('login/', views.custom_login, name='login'),
    path('', views.dashboard, name='dashboard'),
    path('meetings/', views.meetings_list, name='meetings_list'),
    path('meetings/<uuid:meeting_id>/', views.meeting_detail, name='meeting_detail'),
    path('requests/', views.requests_list, name='requests_list'),
    path('requests/<uuid:request_id>/', views.request_detail, name='request_detail'),
    path('departments/', views.departments_list, name='departments_list'),
    path('departments/<int:department_id>/', views.department_detail, name='department_detail'),
    path('api/meeting-stats/', views.api_meeting_stats, name='api_meeting_stats'),
    path('api/department-stats/', views.api_department_stats, name='api_department_stats'),
]
