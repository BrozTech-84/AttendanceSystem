from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import HttpResponse
from StudentScanner.models import Course, Session
from UserLogin.models import Program 
from UserLogin.decorators import lecturer_required
from django import forms
from UserLogin.models import CustomUser
from django.contrib import messages

import qrcode
import io

@lecturer_required
def dashboard(request):
    courses = Course.objects.filter(program=request.user.program)
    sessions = Session.objects.filter(lecturer=request.user)
    return render(request, 'LecturerDashboard/dashboard.html', {
        'courses': courses,
        'sessions': sessions,
    })



@lecturer_required
def onboard_students(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    # ✅ Only students from the same program as the course
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
    qr_data = f"{course.code}|{timezone.now().isoformat()}"
    session = Session.objects.create(
        course=course,
        lecturer=request.user,
        topic=f"Lecture for {course.name}",
        qr_code_data=qr_data
    )

    qr = qrcode.make(qr_data)
    buffer = io.BytesIO()
    qr.save(buffer, format="PNG")
    buffer.seek(0)

    return HttpResponse(buffer.getvalue(), content_type="image/png")

@login_required
def lecturer_dashboard(request):
    # ✅ Get all courses linked to any of the lecturer’s programs
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
            form.save_m2m()  # ✅ save selected programs
            messages.success(request, f"Course '{course.name}' added successfully!")
            return redirect('lecturer_dashboard')
        else:
            messages.error(request, "There was a problem adding the course. Please check the form.")
    else:
        form = CourseForm()
    return render(request, 'LecturerDashboard/add_course.html', {'form': form})