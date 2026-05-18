from django.shortcuts import render
from UserLogin.models import Program, CustomUser
from StudentScanner.models import Course, Session, Attendance
from UserLogin.decorators import admin_required

@admin_required
def dashboard(request):
    """Admin dashboard - consolidated view"""
    programs = Program.objects.all()
    users = CustomUser.objects.all()
    courses = Course.objects.all()
    sessions = Session.objects.all()
    attendance = Attendance.objects.all()
    
    context = {
        'programs': programs,
        'users': users,
        'courses': courses,
        'sessions': sessions,
        'attendance': attendance,
        'total_programs': programs.count(),
        'total_users': users.count(),
        'total_courses': courses.count(),
        'total_sessions': sessions.count(),
        'total_attendance': attendance.count(),
    }
    
    return render(request, 'AdminDashboard/dashboard.html', context)


admin_dashboard = dashboard  # Alias for backward compatibility