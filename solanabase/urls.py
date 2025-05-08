from django.urls import path
from solanabase.views import frontend

app_name = 'solanabase'

urlpatterns = [
    path('', frontend, name='frontend'),
]