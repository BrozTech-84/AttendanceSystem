from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.http import HttpResponse


urlpatterns = [
    path('', include('UserLogin.urls')),
    path('admin/', admin.site.urls),
    path('lecturer/', include('LecturerDashboard.urls')),
    path('scanner/', include('StudentScanner.urls')),
]