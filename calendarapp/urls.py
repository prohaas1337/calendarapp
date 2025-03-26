#urls.py
from django.urls import path
from . import views
from calendarapp.views import event_attendance_summary
from calendarapp.views import user_attendance_summary

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
    path('profile/', views.profile_view, name='profile'),
    path('cancel_registration/<int:event_id>/', views.cancel_registration, name='cancel_registration'),
    path("event-summary/", event_attendance_summary, name="event_summary"),
    path("user-summary/", user_attendance_summary, name="user_summary"),
]