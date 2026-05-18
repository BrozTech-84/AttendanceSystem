from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django import forms
from django.views.decorators.http import require_http_methods
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from io import BytesIO
from datetime import timedelta
import qrcode
import base64
import json
import csv

# Models
from StudentScanner.models import Course, Session, Attendance
from UserLogin.models import Program, CustomUser
from UserLogin.decorators import lecturer_required

# Geocoding setup 
try:
    from geopy.geocoders import Nominatim
    from geopy.extra.rate_limiter import RateLimiter
    GEOCODING_AVAILABLE = True
except ImportError:
    GEOCODING_AVAILABLE = False
    print("Warning: geopy not installed. Install with: pip install geopy")


def get_location_name(latitude, longitude):
    """
    Convert coordinates to a human-readable location name
    """
    if not latitude or not longitude:
        return "Location not specified"
    
    location_name = None
    
    # Using OpenStreetMap's Nominatim (Free, no API key needed)
    if GEOCODING_AVAILABLE:
        try:
            from geopy.extra.rate_limiter import RateLimiter
            geolocator = Nominatim(user_agent="attendance_system")
            
            # Fix: Use proper RateLimiter syntax
            reverse_geocode = RateLimiter(geolocator.reverse, min_delay_seconds=1)
            location = reverse_geocode(f"{latitude}, {longitude}")
            
            if location and location.raw:
                address = location.raw.get('address', {})
                
                parts = []
                if address.get('building'):
                    parts.append(address['building'])
                elif address.get('amenity'):
                    parts.append(address['amenity'])
                
                if address.get('road'):
                    parts.append(address['road'])
                elif address.get('pedestrian'):
                    parts.append(address['pedestrian'])
                
                if address.get('suburb'):
                    parts.append(address['suburb'])
                elif address.get('neighbourhood'):
                    parts.append(address['neighbourhood'])
                
                if address.get('city'):
                    parts.append(address['city'])
                elif address.get('town'):
                    parts.append(address['town'])
                
                if address.get('state'):
                    parts.append(address['state'])
                
                if parts:
                    location_name = ", ".join(parts[:4])
                else:
                    location_name = location.address.split(',')[0] if location.address else None
                    
        except Exception as e:
            print(f"Geocoding error: {e}")
            # Fallback to coordinates
            location_name = f"Lat: {latitude:.4f}, Lon: {longitude:.4f}"
    
    if not location_name:
        location_name = f"Lat: {latitude:.4f}, Lon: {longitude:.4f}"
    
    return location_name

@lecturer_required
def dashboard(request):
    courses = Course.objects.filter(program=request.user.program)
    sessions = Session.objects.filter(lecturer=request.user, is_active=True)
    return render(request, 'LecturerDashboard/dashboard.html', {
        'courses': courses,
        'sessions': sessions,
    })


@lecturer_required
def lecturer_dashboard(request):
    courses = Course.objects.filter(programs__in=request.user.programs.all()).distinct()
    sessions = Session.objects.filter(lecturer=request.user)

    course_students = {course.id: course.students.all() for course in courses}

    grouped_courses = {}
    for course in courses:
        for program in course.programs.all():
            grouped_courses.setdefault(program, []).append(course)

    return render(request, 'LecturerDashboard/lecturer_dashboard.html', {
        'grouped_courses': grouped_courses,
        'sessions': sessions,
        'course_students': course_students,
    })


@lecturer_required
def onboard_students(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    
    if request.method == 'POST':
        print("=" * 60)
        print("POST RECEIVED - Enrolling Students")
        print(f"Course: {course.name} (ID: {course.id})")
        
        selected_ids = request.POST.getlist('students')
        print(f"Selected student IDs: {selected_ids}")
        
        if selected_ids:
            # ONLY get users with role='student' - exclude admins and lecturers
            students_to_add = CustomUser.objects.filter(
                id__in=selected_ids, 
                role='student'  # Only students
            ).exclude(
                is_superuser=True  # Exclude superusers just in case
            )
            count = students_to_add.count()
            print(f"Found {count} valid students to enroll (filtered out admins/lecturers)")
            
            if count > 0:
                course.students.add(*students_to_add)
                messages.success(request, f'✅ Successfully enrolled {count} student(s) to {course.name}')
                print(f"Success! Added {count} students to course")
            else:
                messages.error(request, '❌ No valid students selected. Admins and lecturers cannot be enrolled as students.')
                print("No valid students found in selection - only admins/lecturers were selected")
        else:
            messages.error(request, '❌ Please select at least one student to enroll.')
            print("No students selected")
        
        print("Redirecting to lecturer dashboard...")
        return redirect('lecturer_dashboard')
    
    # GET request - display form
    print("=" * 60)
    print("GET REQUEST - Displaying enrollment form")
    
    # ONLY show users with role='student' - exclude admins, lecturers, and superusers
    students_list = CustomUser.objects.filter(
        role='student'  # Only students
    ).exclude(
        is_superuser=True  # Exclude superusers
    ).order_by('username')
    
    # Also filter by program (only show students from same program as course)
    # Uncomment if you want to restrict to same program:
    # students_list = students_list.filter(program__in=course.programs.all())
    
    enrolled_ids = set(course.students.values_list('id', flat=True))
    
    print(f"Total students available (students only, no admins): {students_list.count()}")
    print(f"Already enrolled: {len(enrolled_ids)}")
    
    # Debug: Check if any admins accidentally appear
    admin_in_list = students_list.filter(is_superuser=True).exists()
    if admin_in_list:
        print("WARNING: Admin users found in student list - check your filters!")
    
    context = {
        'course': course,
        'students': students_list,
        'enrolled_ids': enrolled_ids,
        'total_students': students_list.count(),
    }
    
    return render(request, 'LecturerDashboard/onboard_students.html', context)

@lecturer_required
def start_session(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        lat = data.get("latitude")
        lon = data.get("longitude")
        
        if not lat or not lon:
            return JsonResponse({
                "error": "Location access is required to start a session. Please enable location permissions."
            }, status=400)

        location_name = get_location_name(lat, lon)
        topic = data.get("topic", "Lecture")
        duration_minutes = data.get("duration_minutes", 5)
        allowed_radius = data.get("allowed_radius", 100)

        session = Session.objects.create(
            course=course,
            lecturer=request.user, 
            topic=topic,
            latitude=lat,
            longitude=lon,
            location_name=location_name,
            allowed_radius=allowed_radius,
            qr_expiry=timezone.now() + timedelta(minutes=duration_minutes),
            qr_code_data=f"session-{course.id}-{timezone.now().timestamp()}"
        )

        payload = {
            "session_id": session.id,
            "exp": session.qr_expiry.isoformat(),
            "location_name": location_name,
        }

        qr = qrcode.QRCode(
            version=1, 
            box_size=10, 
            border=4, 
            error_correction=qrcode.constants.ERROR_CORRECT_L
        )
        qr.add_data(json.dumps(payload))
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        qr_base64 = base64.b64encode(buffer.getvalue()).decode()

        session.qr_code_base64 = qr_base64
        session.save()

        return JsonResponse({
            "success": True,
            "qr_code_base64": qr_base64,
            "session_id": session.id,
            "expiry": session.qr_expiry.isoformat(),
            "location_name": location_name,
            "latitude": lat,
            "longitude": lon,
        })

    return render(request, "LecturerDashboard/start_session.html", {
        "course": course,
        "default_duration": 5
    })


@lecturer_required
def end_session(request, session_id):
    session = get_object_or_404(Session, id=session_id)
    session.is_active = False
    session.save()

    channel_layer = get_channel_layer()
    if channel_layer:
        active_sessions = Session.objects.filter(is_active=True)
        data = [
            {
                "id": s.id, 
                "course": s.course.name, 
                "topic": s.topic,
                "created_at": s.created_at.strftime("%Y-%m-%d %H:%M")
            }
            for s in active_sessions
        ]
        async_to_sync(channel_layer.group_send)(
            "sessions",
            {"type": "session_update", "sessions": data}
        )

    return redirect("lecturer_dashboard")


@lecturer_required
def session_detail(request, session_id):
    session = get_object_or_404(Session, id=session_id, lecturer=request.user)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            "id": session.id,
            "course": session.course.name,
            "course_code": session.course.code,
            "topic": session.topic,
            "created_at": session.created_at.isoformat(),
            "qr_expiry": session.qr_expiry.isoformat(),
            "is_active": session.is_active,
            "has_location": bool(session.latitude and session.longitude),
            "latitude": session.latitude,
            "longitude": session.longitude,
            "allowed_radius": getattr(session, 'allowed_radius', 50)
        })
    
    return render(request, 'LecturerDashboard/session_detail.html', {'session': session})


@lecturer_required
def session_attendance_report(request, session_id):
    session = get_object_or_404(Session, id=session_id, lecturer=request.user)
    
    enrolled_students = session.course.students.all()
    attendance_records = {a.student_id: a for a in Attendance.objects.filter(session=session)}
    
    student_data = []
    for student in enrolled_students:
        record = attendance_records.get(student.id)
        student_data.append({
            'student': student,
            'attended': bool(record),
            'timestamp': record.timestamp if record else None,
            'status': record.status if record else 'absent',
            'location': f"{record.marked_latitude},{record.marked_longitude}" if record and record.marked_latitude else None,
        })
    
    total = enrolled_students.count()
    present = sum(1 for s in student_data if s['attended'])
    late = sum(1 for s in student_data if s['status'] == 'late')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'total': total,
            'present': present,
            'late': late,
            'absent': total - present - late,
            'students': student_data
        })
    
    return render(request, 'LecturerDashboard/session_report.html', {
        'session': session,
        'student_data': student_data,
        'total': total,
        'present': present,
        'late': late,
        'absent': total - present - late
    })


@lecturer_required
def attendance_report(request, session_id):
    """View attendance report for a specific session"""
    session = get_object_or_404(Session, id=session_id, lecturer=request.user)
    
    # Get all enrolled students
    enrolled_students = session.course.students.all().order_by('username')
    
    # Get attendance records for this session
    attendance_records = {}
    for record in Attendance.objects.filter(session=session):
        attendance_records[record.student_id] = record
    
    # Prepare student data
    student_data = []
    for student in enrolled_students:
        record = attendance_records.get(student.id)
        student_data.append({
            'student': student,
            'status': record.status if record else 'absent',
            'timestamp': record.timestamp if record else None,
            'location': f"{record.marked_latitude:.6f}, {record.marked_longitude:.6f}" if record and record.marked_latitude else 'N/A',
            'device': record.device_info[:50] if record and record.device_info else 'N/A',
            'ip': record.ip_address if record else 'N/A'
        })
    
    # Statistics
    total_students = enrolled_students.count()
    present_count = sum(1 for s in student_data if s['status'] == 'present')
    late_count = sum(1 for s in student_data if s['status'] == 'late')
    absent_count = total_students - present_count - late_count
    attendance_percentage = (present_count + late_count) / total_students * 100 if total_students > 0 else 0
    
    context = {
        'session': session,
        'student_data': student_data,
        'total_students': total_students,
        'present_count': present_count,
        'late_count': late_count,
        'absent_count': absent_count,
        'attendance_percentage': round(attendance_percentage, 1),
    }
    
    # If AJAX request, return JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'total': total_students,
            'present': present_count,
            'late': late_count,
            'absent': absent_count,
            'percentage': round(attendance_percentage, 1),
            'students': [
                {
                    'name': s['student'].get_full_name() or s['student'].username,
                    'email': s['student'].email,
                    'status': s['status'],
                    'timestamp': s['timestamp'].strftime('%Y-%m-%d %H:%M:%S') if s['timestamp'] else None,
                    'location': s['location']
                } for s in student_data
            ]
        })
    
    return render(request, 'LecturerDashboard/attendance_report.html', context)


@lecturer_required
def export_attendance_csv(request, session_id):
    session = get_object_or_404(Session, id=session_id, lecturer=request.user)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="attendance_{session.course.code}_{session.created_at.date()}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Student ID', 'Student Name', 'Email', 'Status', 'Timestamp', 'Location'])
    
    enrolled_students = session.course.students.all()
    attendance_records = {a.student_id: a for a in Attendance.objects.filter(session=session)}
    
    for student in enrolled_students:
        record = attendance_records.get(student.id)
        writer.writerow([
            student.username,
            student.get_full_name() or student.username,
            student.email,
            record.status if record else 'absent',
            record.timestamp.isoformat() if record else '',
            f"{record.marked_latitude},{record.marked_longitude}" if record and record.marked_latitude else ''
        ])
    
    return response


@lecturer_required
def refresh_qr(request, session_id):
    try:
        session = get_object_or_404(Session, id=session_id, lecturer=request.user)
        
        if not session.is_active:
            return JsonResponse({
                "error": "Session is not active",
                "success": False
            }, status=400)
        
        session.qr_expiry = timezone.now() + timedelta(minutes=1)
        
        payload = {
            "session_id": session.id,
            "exp": session.qr_expiry.isoformat(),
            "location_name": getattr(session, 'location_name', 'Lecture Location')
        }
        
        if session.latitude and session.longitude:
            payload["lat"] = session.latitude
            payload["lon"] = session.longitude
        
        qr = qrcode.QRCode(
            version=1,
            box_size=10,
            border=4,
            error_correction=qrcode.constants.ERROR_CORRECT_L
        )
        qr.add_data(json.dumps(payload))
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        qr_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        session.qr_code_base64 = qr_base64
        session.save()
        
        return JsonResponse({
            "qr_code_base64": qr_base64,
            "expiry": session.qr_expiry.isoformat(),
            "success": True
        })
        
    except Exception as e:
        return JsonResponse({
            "error": str(e),
            "success": False
        }, status=500)


class CourseForm(forms.ModelForm):
    programs = forms.ModelMultipleChoiceField(
        queryset=Program.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label="Link Course to Program(s)"
    )

    class Meta:
        model = Course
        fields = ['name', 'code', 'programs']


@lecturer_required
def add_course(request):
    if request.method == 'POST':
        form = CourseForm(request.POST)
        if form.is_valid():
            course = form.save(commit=False)
            course.save()
            form.save_m2m()
            messages.success(request, f"Course '{course.name}' added successfully!")
            return redirect('lecturer_dashboard')
        else:
            messages.error(request, "There was a problem adding the course. Please check the form.")
    else:
        form = CourseForm()
    return render(request, 'LecturerDashboard/add_course.html', {'form': form})


@lecturer_required
def my_sessions(request):
    # Get all courses linked to the lecturer
    courses = Course.objects.filter(programs__in=request.user.programs.all()).distinct()

    # Build a list with courses and their sessions
    course_sessions = []
    total_sessions = 0
    active_sessions_count = 0
    
    for course in courses:
        sessions = Session.objects.filter(course=course, lecturer=request.user).order_by('-created_at')
        session_count = sessions.count()
        total_sessions += session_count
        active_sessions_count += sessions.filter(is_active=True).count()
        
        course_sessions.append({
            "course": course,
            "session_count": session_count,
            "sessions": sessions
        })

    return render(request, "LecturerDashboard/my_sessions.html", {
        "course_sessions": course_sessions,
        "total_sessions": total_sessions,
        "active_sessions_count": active_sessions_count,
    })

@lecturer_required
def session_attendance_stats(request, session_id):
    session = get_object_or_404(Session, id=session_id, lecturer=request.user)
    enrolled_students = session.course.students.all()
    
    attendance_records = Attendance.objects.filter(session=session)
    
    total = enrolled_students.count()
    present = attendance_records.filter(status='present').count()
    late = attendance_records.filter(status='late').count()
    
    return JsonResponse({
        'total': total,
        'present': present,
        'late': late,
        'absent': total - present - late
    })