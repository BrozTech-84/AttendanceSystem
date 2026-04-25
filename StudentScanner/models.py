from django.db import models
from django.conf import settings
from UserLogin.models import Program, CustomUser

class Course(models.Model):
    # ✅ Many-to-many so lecturers can link courses to whichever program(s) they want
    programs = models.ManyToManyField(Program, related_name="courses")
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    students = models.ManyToManyField(CustomUser, related_name="enrolled_courses", blank=True)

    def __str__(self):
        return f"{self.name} ({self.code})"


class Session(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="sessions")
    lecturer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    topic = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    qr_code_data = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return f"{self.course.name} - {self.topic}"

class Attendance(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.username} - {self.session.course.name} ({self.timestamp})"
