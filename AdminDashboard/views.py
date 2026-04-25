from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from UserLogin.models import Program, CustomUser
from StudentScanner.models import Course, Session, Attendance
from UserLogin.decorators import admin_required

@admin_required
def dashboard(request):
    programs = Program.objects.all()
    users = CustomUser.objects.all()
    courses = Course.objects.all()
    sessions = Session.objects.all()
    attendance = Attendance.objects.all()
    return render(request, 'AdminDashboard/dashboard.html', {
        'programs': programs,
        'users': users,
        'courses': courses,
        'sessions': sessions,
        'attendance': attendance,
    })


@admin_required
def admin_dashboard(request):
    return render(request, 'AdminDashboard/admin_dashboard.html', {
        'programs': Program.objects.all(),
        'users': CustomUser.objects.all(),
        'courses': Course.objects.all(),
        'sessions': Session.objects.all(),
        'attendance': Attendance.objects.all(),
    })
