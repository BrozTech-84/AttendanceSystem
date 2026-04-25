from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.lecturer_dashboard, name='lecturer_dashboard'),
    path('add-course/', views.add_course, name='add_course'),
    path('onboard-students/<int:course_id>/', views.onboard_students, name='onboard_students'),
    path('start-session/<int:course_id>/', views.start_session, name='start_session'),
]
