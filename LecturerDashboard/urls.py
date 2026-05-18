# LecturerDashboard/urls.py
from django.urls import path
from django.http import HttpResponse
from . import views

urlpatterns = [
    path('dashboard/', views.lecturer_dashboard, name='lecturer_dashboard'),
    path('add-course/', views.add_course, name='add_course'),
    path('onboard-students/<int:course_id>/', views.onboard_students, name='onboard_students'),
    path('start-session/<int:course_id>/', views.start_session, name='start_session'),
    path('end-session/<int:session_id>/', views.end_session, name='end_session'),
    path("my-sessions/", views.my_sessions, name="my_sessions"),
    path('session-report/<int:session_id>/', views.session_attendance_report, name='session_attendance_report'),
    path('export-attendance/<int:session_id>/', views.export_attendance_csv, name='export_attendance_csv'),
    path('session-attendance-stats/<int:session_id>/', views.session_attendance_stats, name='session_attendance_stats'),
    path('refresh-qr/<int:session_id>/', views.refresh_qr, name='refresh_qr'),
    path('attendance-report/<int:session_id>/', views.attendance_report, name='attendance_report'),
    path('test/', lambda request: HttpResponse("Test URL works!")),
]