from django.urls import path
from . import views

urlpatterns = [
    path('sessions/', views.session_list, name='session_list'),
    path('attendance/', views.attendance_list, name='attendance_list'),
    path('dashboard/', views.student_dashboard, name='student_dashboard'),
    path('mark-attendance/<int:session_id>/', views.mark_attendance, name='mark_attendance'),
]
