#models.py
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

class Event(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    max_capacity = models.PositiveIntegerField(default=18)
    cancel_limit_hours = models.PositiveIntegerField(default=3)
    signup_limit_hours = models.PositiveIntegerField(default=0)  # 0 = mindig lehet jelentkezni

    def is_signup_open(self):
        if self.signup_limit_hours == 0:
            return True
        limit_time = self.start_time - timezone.timedelta(hours=self.signup_limit_hours)
        return timezone.now() <= limit_time

    def is_cancel_allowed(self):
        return timezone.now() <= (self.start_time - timezone.timedelta(hours=self.cancel_limit_hours))

    def __str__(self):
        return self.title


class Attendance(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    checked_in = models.BooleanField(default=False)  # új mező


from django.contrib.auth.models import User
from django.db import models

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    display_name = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.display_name or self.user.username
