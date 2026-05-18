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
    
    
    try:
        # Parse request body
        try:
            data = json.loads(request.body.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            return JsonResponse({
                "error": f"Invalid request format: {str(e)}"
            }, status=400)
        
        qr_data = data.get("qr_data")
        student_lat = data.get("latitude")
        student_lon = data.get("longitude")
        device_info = data.get("device_info", "")
        
        if not qr_data:
            return JsonResponse({"error": "QR data required"}, status=400)
        
        # Parse QR payload - this is the critical part
        try:
            # First, try to parse as JSON
            qr_payload = json.loads(qr_data)
            session_id_from_qr = qr_payload.get("session_id")
        except json.JSONDecodeError:
            # If not JSON, try to extract session ID from string format
            # Check if it's the old format: "session-1-1234567890"
            if qr_data.startswith("session-"):
                parts = qr_data.split("-")
                if len(parts) >= 2:
                    try:
                        session_id_from_qr = int(parts[1])
                    except ValueError:
                        return JsonResponse({"error": "Invalid QR format"}, status=400)
                else:
                    return JsonResponse({"error": "Invalid QR format"}, status=400)
            else:
                return JsonResponse({"error": "Invalid QR format"}, status=400)
        
        # Validate session ID matches
        if session_id_from_qr != int(session_id):
            return JsonResponse({
                "error": f"QR does not match this session. Expected {session_id}, got {session_id_from_qr}"
            }, status=400)
        
        # Get the session
        try:
            session = Session.objects.get(id=session_id, is_active=True)
        except Session.DoesNotExist:
            return JsonResponse({"error": "Session not found or has ended"}, status=404)
        
        # Check if student is enrolled
        if not session.course.students.filter(id=request.user.id).exists():
            return JsonResponse({
                "error": "You are not enrolled in this course"
            }, status=403)
        
        # Check if already marked
        existing_attendance = Attendance.objects.filter(
            student=request.user, 
            session=session
        ).first()
        
        if existing_attendance:
            return JsonResponse({
                "success": True,
                "message": f"Attendance already marked as {existing_attendance.status} on {existing_attendance.timestamp.strftime('%H:%M:%S')}",
                "already_marked": True
            }, status=200)
        
        # Check QR expiry
        if timezone.now() > session.qr_expiry:
            return JsonResponse({
                "error": f"QR code expired at {session.qr_expiry.strftime('%H:%M:%S')}"
            }, status=400)
        
        # Validate location (if lecturer set location)
        if session.latitude and session.longitude:
            if not student_lat or not student_lon:
                return JsonResponse({
                    "error": "Location access required for this session"
                }, status=400)
            
            try:
                from geopy.distance import geodesic
                lecturer_coords = (session.latitude, session.longitude)
                student_coords = (float(student_lat), float(student_lon))
                
                distance = geodesic(lecturer_coords, student_coords).meters
                allowed_radius = getattr(session, 'allowed_radius', 50)
                
                if distance > allowed_radius:
                    return JsonResponse({
                        "error": f"Too far from session location ({distance:.0f}m away, max {allowed_radius}m)"
                    }, status=400)
            except Exception as e:
                print(f"Location validation error: {e}")
        
        # Determine if student is late (15 minutes after session start)
        status = 'present'
        late_threshold = session.created_at + timedelta(minutes=15)
        if timezone.now() > late_threshold:
            status = 'late'
        
        # Create attendance record
        attendance = Attendance.objects.create(
            student=request.user,
            session=session,
            status=status,
            marked_latitude=student_lat if student_lat else None,
            marked_longitude=student_lon if student_lon else None,
            device_info=device_info[:200] if device_info else "",
            ip_address=get_client_ip(request)
        )
        
        return JsonResponse({
            "success": True,
            "message": f"✓ Attendance marked as {status.upper()}!",
            "status": status,
            "timestamp": attendance.timestamp.isoformat()
        })
        
    except Exception as e:
        print(f"Unexpected error in mark_attendance: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            "error": f"Server error: {str(e)}"
        }, status=500)

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

def test_view(request):
    return JsonResponse({"status": "Working!", "message": "Student scanner app is accessible"})