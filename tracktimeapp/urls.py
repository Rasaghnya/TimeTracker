from django.urls import path
from . import views
urlpatterns = [
    # path('', views.scan, name='home'),
    path('register/', views.register, name='register'),
    path('scan/', views.scan, name='scan'),
    path('success/', views.success, name='success'),
    
    # API endpoints for face recognition
    path('api/register_face/', views.register_face_api, name='register_face_api'),
    path('api/recognize_face/', views.recognize_face_api, name='recognize_face_api'),
    path('api/update_face/', views.update_face_api, name='update_face_api'),
]