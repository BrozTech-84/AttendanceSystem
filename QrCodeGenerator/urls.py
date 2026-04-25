from django.urls import path
from . import views

urlpatterns = [
    path('generate/<str:data>/', views.generate_qr, name='generate_qr'),
]
