"""
URL configuration for AttendanceSystem project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView

urlpatterns = [
    path('', include('UserLogin.urls')),
    path('admin/', admin.site.urls),
    path('user/', include('UserLogin.urls')),
    path('scanner/', include('StudentScanner.urls')),
    path('lecturer/', include('LecturerDashboard.urls')),
    path('admin-dashboard/', include('AdminDashboard.urls')),
    path('qr/', include('QrCodeGenerator.urls')),

]

"""

from django.contrib import admin
from django.urls import path
from django.http import HttpResponse

def home_view(request):
    return HttpResponse("""
        <h1>Attendance System - Test Page</h1>
        <p>If you can see this, the server is working!</p>
        <p>✅ Deployment successful</p>
        <hr>
        <p><a href="/admin/">Admin Panel</a></p>
    """)

urlpatterns = [
    path('', home_view),
    path('admin/', admin.site.urls),
]