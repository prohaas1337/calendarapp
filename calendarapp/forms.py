# forms.py
from django import forms
from .models import Event


class EventForm(forms.ModelForm):
    WEEKDAYS = [
        ('0', 'Hétfő'),
        ('1', 'Kedd'),
        ('2', 'Szerda'),
        ('3', 'Csütörtök'),
        ('4', 'Péntek'),
        ('5', 'Szombat'),
        ('6', 'Vasárnap'),
    ]

    REPEAT_CHOICES = [
        ('0', 'ne ismétlődjön'),
        ('1m', '1 hónap'),
        ('3m', '3 hónap'),
        ('6m', '6 hónap'),
    ]

    repeat_weekday = forms.ChoiceField(choices=WEEKDAYS, label='Melyik nap ismétlődjön?')
    repeat_until = forms.ChoiceField(choices=REPEAT_CHOICES, required=False, label='Ismétlés időtartama')

    class Meta:
        model = Event
        fields = ['title', 'description', 'start_time', 'end_time', 'repeat_weekday', 'repeat_until','max_capacity', 'cancel_limit_hours',
                  'signup_limit_hours']
        labels = {
            'title': 'Cím',
            'description': 'Leírás',
            'start_time': 'Kezdés időpontja',
            'end_time': 'Befejezés időpontja',
            'max_capacity': 'Maximális létszám',
            'cancel_limit_hours': 'Lemondási határidő (előtte, órában)',
            'signup_limit_hours': 'Jelentkezési határidő (előtte, órában)',
        }
        widgets = {
            'start_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'end_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }