from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from UserLogin.decorators import student_required
from .models import Session, Attendance, Course
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json

def session_list(request):
    sessions = Session.objects.all()
    return render(request, 'StudentScanner/sessions.html', {'sessions': sessions})

def attendance_list(request):
    attendance = Attendance.objects.all()
    return render(request, 'StudentScanner/attendance.html', {'attendance': attendance})

@student_required
def student_dashboard(request):
    # ✅ Courses the student is enrolled in (via ManyToMany)
    courses = request.user.enrolled_courses.all()

    # Active sessions for those courses
    sessions = Session.objects.filter(course__in=courses, is_active=True)

    # Attendance history for this student
    attendance = Attendance.objects.filter(student=request.user).select_related('session', 'session__course')

    return render(request, 'StudentScanner/student_dashboard.html', {
        'courses': courses,
        'sessions': sessions,
        'attendance': attendance,
    })


@login_required
@csrf_exempt
def mark_attendance(request, session_id):
    if request.method == "POST":
        data = json.loads(request.body)
        qr_data = data.get("qr_data")

        session = get_object_or_404(Session, id=session_id)

        # ✅ Verify QR data matches session QR
        if qr_data == session.qr_code_data:
            Attendance.objects.get_or_create(student=request.user, session=session, defaults={"status": "Present"})
            return JsonResponse({"success": True})
        return JsonResponse({"success": False, "error": "Invalid QR"})
