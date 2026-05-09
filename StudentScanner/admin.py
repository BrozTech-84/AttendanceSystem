from django.contrib import admin
from .models import Course, Session, Attendance

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('name', 'code')

@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ('course', 'lecturer', 'created_at')

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('student', 'session', 'timestamp')
