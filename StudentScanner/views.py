# StudentScanner/views.py
import json
import hashlib
from datetime import timedelta
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.core.cache import cache
from geopy.distance import geodesic
from UserLogin.decorators import student_required
from .models import Session, Attendance, Course

# ============ ADD THESE MISSING FUNCTIONS ============

def session_list(request):
    """List all sessions (for admin/debugging)"""
    sessions = Session.objects.all().order_by('-created_at')
    return render(request, 'StudentScanner/sessions.html', {'sessions': sessions})

def attendance_list(request):
    """List all attendance records (for admin/debugging)"""
    attendance = Attendance.objects.all().select_related('student', 'session').order_by('-timestamp')
    return render(request, 'StudentScanner/attendance.html', {'attendance': attendance})

# ============ MAIN STUDENT VIEWS ============

@student_required
def student_dashboard(request):
    courses = request.user.enrolled_courses.all()
    sessions = Session.objects.filter(course__in=courses, is_active=True)
    attendance = Attendance.objects.filter(student=request.user).select_related('session', 'session__course')
    
    return render(request, 'StudentScanner/student_dashboard.html', {
        'courses': courses,
        'sessions': sessions,
        'attendance': attendance,
    })

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def mark_attendance(request, session_id):
    """Single unified attendance marking view with location + QR validation"""
    
    # Rate limiting: prevent spam (5 attempts per minute)
    rate_limit_key = f"attendance_rate_{request.user.id}_{session_id}"
    if cache.get(rate_limit_key):
        return JsonResponse({"error": "Too many attempts. Please wait."}, status=429)
    cache.set(rate_limit_key, True, 60)  # 1 minute cooldown
    
    try:
        data = json.loads(request.body)
        qr_data = data.get("qr_data")
        student_lat = data.get("latitude")
        student_lon = data.get("longitude")
        device_info = data.get("device_info", "")
        
        if not qr_data:
            return JsonResponse({"error": "QR data required"}, status=400)
        
        # Parse QR payload
        try:
            qr_payload = json.loads(qr_data)
            session_id_from_qr = qr_payload.get("session_id")
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid QR format"}, status=400)
        
        # Validate session
        if session_id_from_qr != session_id:
            return JsonResponse({"error": "QR does not match this session"}, status=400)
        
        session = get_object_or_404(Session, id=session_id, is_active=True)
        
        # Check if student is enrolled
        if not session.course.students.filter(id=request.user.id).exists():
            return JsonResponse({"error": "You are not enrolled in this course"}, status=403)
        
        # Check if already marked
        if Attendance.objects.filter(student=request.user, session=session).exists():
            return JsonResponse({"error": "Attendance already marked for this session"}, status=400)
        
        # Check QR expiry
        if timezone.now() > session.qr_expiry:
            return JsonResponse({"error": "QR code has expired"}, status=400)
        
        # Validate location (if lecturer set location)
        location_valid = True
        if session.latitude and session.longitude:
            if not student_lat or not student_lon:
                return JsonResponse({"error": "Location access required"}, status=400)
            
            lecturer_coords = (session.latitude, session.longitude)
            student_coords = (float(student_lat), float(student_lon))
            
            distance = geodesic(lecturer_coords, student_coords).meters
            if distance > session.allowed_radius:
                return JsonResponse({
                    "error": f"Outside allowed location ({distance:.0f}m / {session.allowed_radius}m)"
                }, status=400)
        
        # Determine if student is late (e.g., 15 minutes after session start)
        status = 'present'
        if session.created_at + timedelta(minutes=15) < timezone.now():
            status = 'late'
        
        # Create attendance record
        attendance = Attendance.objects.create(
            student=request.user,
            session=session,
            status=status,
            marked_latitude=student_lat,
            marked_longitude=student_lon,
            device_info=device_info,
            ip_address=get_client_ip(request)
        )
        
        return JsonResponse({
            "success": True,
            "message": f"Attendance marked as {status}",
            "status": status
        })
        
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

def get_client_ip(request):
    """Extract client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

@login_required
def active_sessions_api(request):
    """API endpoint for active sessions (with student enrollment check)"""
    if request.user.role == 'student':
        courses = request.user.enrolled_courses.all()
        sessions = Session.objects.filter(course__in=courses, is_active=True)
    else:
        sessions = Session.objects.filter(is_active=True)
    
    data = [{
        "id": s.id,
        "course": s.course.name,
        "course_code": s.course.code,
        "topic": s.topic,
        "lecturer": s.lecturer.get_full_name() or s.lecturer.username,
        "created_at": s.created_at.strftime("%Y-%m-%d %H:%M"),
        "qr_expires_at": s.qr_expiry.strftime("%Y-%m-%d %H:%M:%S"),
        "has_location": bool(s.latitude and s.longitude)
    } for s in sessions]
    
    return JsonResponse(data, safe=False)

@login_required
def session_detail(request, session_id):
    """Get detailed info about a specific session"""
    session = get_object_or_404(Session, id=session_id)
    
    # Check if user has access
    if request.user.role == 'student' and not session.course.students.filter(id=request.user.id).exists():
        return JsonResponse({"error": "Access denied"}, status=403)
    
    return JsonResponse({
        "id": session.id,
        "course": session.course.name,
        "topic": session.topic,
        "created_at": session.created_at.isoformat(),
        "qr_expiry": session.qr_expiry.isoformat(),
        "has_location": bool(session.latitude and session.longitude),
        "allowed_radius": session.allowed_radius,
        "is_active": session.is_active
    })