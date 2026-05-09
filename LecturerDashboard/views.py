from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from StudentScanner.models import Course, Session, Attendance  # Combined imports
from UserLogin.models import Program, CustomUser  # Combined imports
from UserLogin.decorators import lecturer_required
from django import forms
from django.contrib import messages
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import qrcode
import base64
import json
import csv
from io import BytesIO
from datetime import timedelta

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
    Convert coordinates to a human-readable location name using multiple services
    Returns a string like "Computer Science Building, University of Nairobi"
    """
    if not latitude or not longitude:
        return "Location not specified"
    
    location_name = None
    
    # Using OpenStreetMap's Nominatim (Free, no API key needed)
    if GEOCODING_AVAILABLE:
        try:
            geolocator = Nominatim(user_agent="attendance_system")
            # Add rate limiting to respect OpenStreetMap's policy
            geocode = RateLimiter(geolocator.reverse, delay=1)
            location = geocode(f"{latitude}, {longitude}")
            
            if location and location.raw:
                address = location.raw.get('address', {})
                
                # Build a readable address
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
                    location_name = ", ".join(parts[:4])  # Limit to first 4 parts
                else:
                    location_name = location.address.split(',')[0] if location.address else None
                    
        except Exception as e:
            print(f"Geocoding error: {e}")
    
    # Fallback if geocoding failed
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
    # Get all courses linked to any of the lecturer's programs
    courses = Course.objects.filter(programs__in=request.user.programs.all()).distinct()
    sessions = Session.objects.filter(lecturer=request.user)

    # Collect enrolled students per course
    course_students = {course.id: course.students.all() for course in courses}

    # Group courses by program for clarity
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

    # Only students from the same program as the course
    students = CustomUser.objects.filter(program__in=course.programs.all(), role='student')

    if request.method == 'POST':
        selected_ids = request.POST.getlist('students')
        selected_students = CustomUser.objects.filter(id__in=selected_ids)
        course.students.set(selected_students)  # enroll selected students
        return redirect('lecturer_dashboard')

    return render(request, 'LecturerDashboard/onboard_students.html', {
        'course': course,
        'students': students
    })

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
        
        # Log if not provided
        if not lat or not lon:
            return JsonResponse({
                "error": "Location access is required to start a session. Please enable location permissions."
            }, status=400)

        # Get human-readable location name
        location_name = get_location_name(lat, lon)

        # Get additional location details
        topic = data.get("topic", "Lecture")
        duration_minutes = data.get("duration_minutes", 5)
        allowed_radius = data.get("allowed_radius", 50)  # in meters

        session = Session.objects.create(
            course=course,
            lecturer=request.user, 
            topic=topic,
            latitude=lat,
            longitude=lon,
            location_name=location_name,  # Make sure this field exists in your Session model
            allowed_radius=allowed_radius,  # Make sure this field exists in your Session model
            qr_expiry=timezone.now() + timedelta(minutes=duration_minutes),  # FIXED: use duration_minutes instead of hardcoded 1
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

    # Notify students
    channel_layer = get_channel_layer()
    if channel_layer:  # safety check
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
    """Get detailed info about a specific session for lecturer"""
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
            "allowed_radius": getattr(session, 'allowed_radius', 50)  # FIXED: use getattr
        })
    
    return render(request, 'LecturerDashboard/session_detail.html', {'session': session})

@lecturer_required
def session_attendance_report(request, session_id):
    """View attendance report for a specific session"""
    session = get_object_or_404(Session, id=session_id, lecturer=request.user)
    
    # Get enrolled students and their attendance status
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
    
    # Statistics
    total = enrolled_students.count()
    present = sum(1 for s in student_data if s['attended'])
    late = sum(1 for s in student_data if s['status'] == 'late')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'total': total,
            'present': present,
            'late': late,
            'absent': total - present - late,  # FIXED: subtract late as well
            'students': student_data
        })
    
    return render(request, 'LecturerDashboard/session_report.html', {
        'session': session,
        'student_data': student_data,
        'total': total,
        'present': present,
        'late': late,
        'absent': total - present - late  # FIXED: subtract late as well
    })

@lecturer_required
def export_attendance_csv(request, session_id):
    """Export attendance as CSV"""
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
    """Refresh QR code for an active session"""
    try:
        session = get_object_or_404(Session, id=session_id, lecturer=request.user)
        
        # Only refresh if session is active
        if not session.is_active:
            return JsonResponse({
                "error": "Session is not active",
                "success": False
            }, status=400)
        
        # Extend expiry by 1 minute
        session.qr_expiry = timezone.now() + timedelta(minutes=1)
        
        # Create payload for QR
        payload = {
            "session_id": session.id,
            "exp": session.qr_expiry.isoformat(),
            "location_name": getattr(session, 'location_name', 'Lecture Location')
        }
        
        # Add location if available
        if session.latitude and session.longitude:
            payload["lat"] = session.latitude
            payload["lon"] = session.longitude
        
        # Generate QR code
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
        
        # Save to session
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
            form.save_m2m()  # save selected programs
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

    # Build a dictionary: course → number of sessions
    course_sessions = []
    for course in courses:
        session_count = Session.objects.filter(course=course, lecturer=request.user).count()
        course_sessions.append({
            "course": course,
            "session_count": session_count
        })

    return render(request, "LecturerDashboard/my_sessions.html", {
        "course_sessions": course_sessions
    })

@lecturer_required
def session_attendance_stats(request, session_id):
    """Get live attendance statistics for a session"""
    from StudentScanner.models import Attendance
    
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


from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

@lecturer_required
def onboard_students(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    
    # Get all students from the program (efficient query)
    students_queryset = CustomUser.objects.filter(
        program__in=course.programs.all(), 
        role='student'
    ).only('id', 'username', 'email', 'first_name', 'last_name')  # Only fetch needed fields
    
    # Get already enrolled students IDs (for status display)
    enrolled_ids = set(course.students.values_list('id', flat=True))
    
    # Handle search
    search_query = request.GET.get('search', '')
    if search_query:
        students_queryset = students_queryset.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )
    
    # Pagination - 20 students per page for 1000+ students
    paginator = Paginator(students_queryset, 20)  # Adjust: 20, 50, or 100 per page
    page = request.GET.get('page', 1)
    
    try:
        students = paginator.page(page)
    except PageNotAnInteger:
        students = paginator.page(1)
    except EmptyPage:
        students = paginator.page(paginator.num_pages)
    
    # AJAX request for dynamic loading
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        students_data = []
        for student in students:
            students_data.append({
                'id': student.id,
                'username': student.username,
                'email': student.email,
                'full_name': student.get_full_name() or student.username,
                'initial': student.username[0].upper(),
                'is_enrolled': student.id in enrolled_ids
            })
        
        return JsonResponse({
            'students': students_data,
            'has_next': students.has_next(),
            'has_previous': students.has_previous(),
            'current_page': students.number,
            'total_pages': paginator.num_pages,
            'total_students': paginator.count,
            'enrolled_count': len(enrolled_ids)
        })
    
    # Regular request
    return render(request, 'LecturerDashboard/onboard_students.html', {
        'course': course,
        'students': students,
        'search_query': search_query,
        'enrolled_ids': enrolled_ids,
        'total_students': paginator.count,
        'enrolled_count': len(enrolled_ids)
    })

# Also add the bulk enrollment API endpoint
@lecturer_required
@require_http_methods(["POST"])
def bulk_enroll_students(request, course_id):
    """AJAX endpoint for bulk enrollment without page reload"""
    course = get_object_or_404(Course, id=course_id)
    
    try:
        data = json.loads(request.body)
        student_ids = data.get('student_ids', [])
        
        if not student_ids:
            return JsonResponse({'error': 'No students selected'}, status=400)
        
        # Bulk add students (efficient for many records)
        students_to_add = CustomUser.objects.filter(id__in=student_ids, role='student')
        course.students.add(*students_to_add)
        
        return JsonResponse({
            'success': True,
            'message': f'Successfully enrolled {len(students_to_add)} students',
            'enrolled_count': course.students.count()
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)