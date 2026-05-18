from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='admin_dashboard'),
    path('dashboard/', views.dashboard, name='admin_dashboard_alt'),
]