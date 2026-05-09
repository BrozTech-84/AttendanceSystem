from django.utils import timezone
from django.db import models
from django.conf import settings
from UserLogin.models import Program, CustomUser

class Course(models.Model):
    programs = models.ManyToManyField(Program, related_name="courses")
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    students = models.ManyToManyField(CustomUser, related_name="enrolled_courses", blank=True)
    
    # Add room/campus location
    default_latitude = models.FloatField(null=True, blank=True)
    default_longitude = models.FloatField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.name} ({self.code})"


class Session(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="sessions")
    lecturer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    topic = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    # QR fields
    qr_code_data = models.CharField(max_length=255, unique=True)
    qr_code_base64 = models.TextField(null=True, blank=True)
    qr_expiry = models.DateTimeField(default=timezone.now)

    # Security fields
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    location_name = models.CharField(max_length=500, null=True, blank=True)  # Human-readable location

    # Allowed radius (in meters)
    allowed_radius = models.IntegerField(default=50)  # 50 meters default

    def __str__(self):
        return f"{self.course.name} - {self.topic}"
    


class Attendance(models.Model):
    STATUS_CHOICES = [
        ('present', 'Present'),
        ('late', 'Late'),
        ('absent', 'Absent'),
    ]
    
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='present')
    
    # Track location where attendance was marked
    marked_latitude = models.FloatField(null=True, blank=True)
    marked_longitude = models.FloatField(null=True, blank=True)
    
    # Track device info
    device_info = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        unique_together = ['student', 'session']  # Prevent duplicate attendance
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.student.username} - {self.session.course.name} ({self.timestamp})"