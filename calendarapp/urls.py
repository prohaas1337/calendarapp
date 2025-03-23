#urls.py
from django.urls import path
from . import views

app_name = 'calendarapp'

urlpatterns = [
    path('', views.calendar_view, name='calendar_view'),  # Alapértelmezett útvonal a naptár nézethez
    path('events/', views.events_api, name='events_api'),
    path('create/', views.create_event, name='create_event'),
    path('signup/', views.signup_event, name='signup_event'),
    path('cancel_signup/', views.unsubscribe_event, name='unsubscribe_event'),
    path('session_check/', views.session_check_view, name='session_check'),
    path('events/<int:event_id>/', views.event_detail, name='event_detail'),
    path('delete/<int:event_id>/', views.delete_event, name='delete_event'),
    path('edit/<int:event_id>/', views.edit_event, name='edit_event'),
]