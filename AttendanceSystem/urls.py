from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.http import HttpResponse

# Temporary home page - you can replace with your actual homepage
def home_view(request):
    return HttpResponse("""
        <!DOCTYPE html>
        <html>
        <head><title>QR Attendance System</title></head>
        <body style="font-family: Arial; text-align: center; padding: 50px;">
            <h1>📱 QR Attendance System</h1>
            <p>System is running successfully!</p>
            <div style="margin-top: 30px;">
                <a href="/lecturer/dashboard/" style="display: inline-block; margin: 10px; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px;">
                    👨‍🏫 Lecturer Dashboard
                </a>
                <a href="/scanner/dashboard/" style="display: inline-block; margin: 10px; padding: 10px 20px; background: #28a745; color: white; text-decoration: none; border-radius: 5px;">
                    📱 Student Dashboard
                </a>
                <a href="/admin/" style="display: inline-block; margin: 10px; padding: 10px 20px; background: #6c757d; color: white; text-decoration: none; border-radius: 5px;">
                    🔐 Admin Panel
                </a>
            </div>
        </body>
        </html>
    """)

urlpatterns = [
    path('', home_view, name='home'),
    path('admin/', admin.site.urls),
    path('', include('UserLogin.urls')),
    path('lecturer/', include('LecturerDashboard.urls')),
    path('scanner/', include('StudentScanner.urls')),
]