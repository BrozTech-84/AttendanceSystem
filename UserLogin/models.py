from django.contrib.auth.models import AbstractUser
from django.db import models

class Program(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return f"{self.code} - {self.name}"


class CustomUser(AbstractUser):
    # Students: one program
    program = models.ForeignKey(
        Program,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="student_users"   # ✅ unique reverse accessor
    )

    # Lecturers: multiple programs
    programs = models.ManyToManyField(
        Program,
        blank=True,
        related_name="customuser_lecturers"   # ✅ unique reverse accessor
    )

    ROLE_CHOICES = (
        ('student', 'Student'),
        ('lecturer', 'Lecturer'),
        ('admin', 'Admin'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')

    def __str__(self):
        return f"{self.username} ({self.role})"


class Lecturer(models.Model):
    username = models.CharField(max_length=100, unique=True)
    email = models.EmailField(unique=True)
    programs = models.ManyToManyField(
        Program,
        related_name="lecturer_profiles",   # ✅ unique reverse accessor
        blank=True
    )

    def __str__(self):
        return self.username
