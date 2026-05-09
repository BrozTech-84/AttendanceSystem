from django.contrib import admin
from .models import CustomUser, Program

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'role')

@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ('code', 'name')
