from django.urls import path
from . import views
urlpatterns = [
 # path('', views.scan, name='home'),
    path('register/', views.register, name='register'),
    path('scan/', views.scan, name='scan'),
    path('success/', views.success, name='success'),
]