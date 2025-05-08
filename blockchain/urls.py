# biodata/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('students/', views.student_list, name='student_list'),
    path('students/add/', views.add_student, name='add_student'),
    path('students/<str:student_id>/', views.view_student, name='view_student'),
    path('students/<str:student_id>/update/', views.update_student, name='update_student'),
    path('validate/', views.validate_blockchain, name='validate_blockchain'),
    path('generate-key/', views.generate_key, name='generate_key'),
]