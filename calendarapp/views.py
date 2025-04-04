#views.py
from django.views.decorators.csrf import csrf_protect
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.utils.dateparse import parse_datetime
from django.contrib.auth.decorators import permission_required
from .forms import EventForm
from datetime import timedelta, datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.timezone import now
from django.db.models import Count
from calendarapp.models import Event, Attendance
from django.core.mail import send_mail
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from .models import Event, Attendance
from .utils import get_edzo_emails
from django.utils.timezone import make_aware, localtime
from django.utils.timezone import make_aware


@login_required
def calendar_view(request):
    today = now().date()
    current_user = request.user
    user_display_name = current_user.get_display_name()
    # Hét kezdete és vége
    start_of_week = today - timedelta(days=today.weekday())  # Hétfő (mostantól korrekt)
    end_of_week = start_of_week + timedelta(days=6)  # Vasárnap

    # Időzóna figyelembevételével datetime objektummá alakítás
    start_of_week = make_aware(datetime.combine(start_of_week, datetime.min.time()))
    end_of_week = make_aware(datetime.combine(end_of_week, datetime.max.time()))

    if current_user.is_superuser or current_user.groups.filter(name="edzo").exists():
        events = Event.objects.all()
    else:
        # Sima user csak a vasárnaptól vasárnapig terjedő eseményeket látja
        events = Event.objects.filter(
            start_time__gte=start_of_week,
            start_time__lte=end_of_week
        )

    events_list = []
    current_user = request.user  # Aktuálisan bejelentkezett felhasználó

    #print("Start of week:", start_of_week)
    #print("End of week:", end_of_week)

    for event in events:
        # Lekérdezzük a felhasználókat, akik jelentkeztek
        attendees = Attendance.objects.filter(event=event)
        attendee_names = [attendee.user.username for attendee in attendees]


        events_list.append({
            'id': event.id,
            'title': event.title,
            'start': event.start_time.isoformat(),
            'end': event.end_time.isoformat(),
            'description': event.description,
            'attendees': attendee_names,  # Felhasználók listája
        })

    context = {
        'start_of_week': start_of_week,
        'end_of_week': end_of_week,
        'events': events_list,
        'user_display_name': user_display_name,
    }
    #for event in events:
    #    print(f"Esemény: {event.title}, Kezdés: {event.start_time}, Befejezés: {event.end_time}")

    return render(request, 'calendarapp/calendar.html', context)

@login_required
def event_detail(request, event_id):
    try:
        event = Event.objects.get(id=event_id)
        attendees = Attendance.objects.filter(event=event)
        attendee_names = [
            attendee.user.get_display_name() if hasattr(attendee.user,
                                                        "get_display_name") and attendee.user.get_display_name()
            else attendee.user.username
            for attendee in attendees
        ]

        event_data = {
            'id': event.id,
            'title': event.title,
            'start': event.start_time.isoformat(),
            'end': event.end_time.isoformat(),
            'description': event.description,
            'attendees': attendee_names,
            'is_signup_open': event.is_signup_open(),
            'is_cancel_allowed': event.is_cancel_allowed(),
        }

        return JsonResponse(event_data)

    except Event.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Az esemény nem található.'}, status=404)

@login_required
def events_api(request):
    current_user = request.user
    today = now().date()
    start_of_week = today - timedelta(days=today.weekday())  # Hétfő
    end_of_week = start_of_week + timedelta(days=6)  # Vasárnap

    start_of_week = make_aware(datetime.combine(start_of_week, datetime.min.time()))
    end_of_week = make_aware(datetime.combine(end_of_week, datetime.max.time()))

    if current_user.is_superuser or current_user.groups.filter(name="edzo").exists():
        events = Event.objects.all()
    else:
        # Sima user csak a vasárnaptól vasárnapig terjedő eseményeket látja
        events = Event.objects.filter(
            start_time__gte=start_of_week,
            start_time__lte=end_of_week
        )

    event_list = []
    for event in events:
        is_attending = Attendance.objects.filter(user=request.user, event=event).exists()
        # Jelentkezettek nevei a display_name vagy username alapján
        attendees = Attendance.objects.filter(event=event)
        attendee_names = [
            attendee.user.get_display_name() if hasattr(attendee.user,
                                                        "get_display_name") and attendee.user.get_display_name()
            else attendee.user.username
            for attendee in attendees
        ]
        event_list.append({
            'id': event.id,
            'title': event.title,
            'start': event.start_time.isoformat(),
            'end': event.end_time.isoformat(),
            'description': event.description,
            'user_is_attending': is_attending
        })

    return JsonResponse(event_list, safe=False)


@login_required
@csrf_protect
@require_POST
def signup_event(request):
    event_id = request.POST.get('event_id')
    if not event_id:
        return JsonResponse({'status': 'error', 'message': 'Hiányzik az event_id.'}, status=400)

    event = get_object_or_404(Event, id=event_id)

    if not event.is_signup_open():
        return JsonResponse({'status': 'error', 'message': 'A jelentkezési határidő lejárt.'}, status=400,json_dumps_params={'ensure_ascii': False})

    attendance, created = Attendance.objects.get_or_create(user=request.user, event=event)
    if not created:
        return JsonResponse({'status': 'error', 'message': 'Már jelentkezett erre az eseményre!'}, status=400,json_dumps_params={'ensure_ascii': False})

    # Email küldése az edzőknek
    subject = f"Új jelentkezés: {event.title}"
    message = f"{request.user.username} jelentkezett az eseményre: {event.title}\nIdőpont: {event.start_time}"
    recipient_list = get_edzo_emails()

    if recipient_list:
        send_mail(subject, message, None, recipient_list, fail_silently=False)

    return JsonResponse({'status': 'success'})


@login_required
@csrf_protect
@require_POST
def unsubscribe_event(request):
    event_id = request.POST.get('event_id')
    if not event_id:
        return JsonResponse({'status': 'error', 'message': 'Hiányzik az event_id.'}, status=400)

    try:
        attendance = Attendance.objects.get(user=request.user, event_id=event_id)
        event = attendance.event

        if not event.is_cancel_allowed():
            return JsonResponse({'status': 'error', 'message': 'A lemondási határidő lejárt.'}, status=400,json_dumps_params={'ensure_ascii': False})

        attendance.delete()

        # Email küldése az edzőknek
        subject = f"Jelentkezés visszavonva: {event.title}"
        message = f"{request.user.username} visszavonta a jelentkezését az eseményről: {event.title}\nIdőpont: {event.start_time}"
        recipient_list = get_edzo_emails()

        if recipient_list:
            send_mail(subject, message, None, recipient_list, fail_silently=False)

        return JsonResponse({'status': 'success'})

    except Attendance.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Nem található a jelentkezés erre az eseményre.'},
                            status=404,json_dumps_params={'ensure_ascii': False})


from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from .models import Event

@login_required
@permission_required('calendarapp.delete_event', raise_exception=True)
def single_delete(request, event_id):
    # Az esemény lekérése az ID alapján
    event = get_object_or_404(Event, id=event_id)

    # Ha POST kérés érkezik, akkor töröljük az eseményt
    if request.method == 'POST':
        event.delete()
        return redirect('calendarapp:calendar_view')  # Visszairányítás a naptár nézetre

    # Ha nem POST, akkor csak a törlés megerősítését kérjük
    return render(request, 'calendarapp/confirm_delete.html', {'event': event})


@login_required
@permission_required('calendarapp.delete_event', raise_exception=True)
def delete_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    # Lekérjük az esemény időpontját
    event_start = event.start_time
    event_end = event.end_time

    # Listázzuk az összes jövőbeli ismétlődő eseményt (7 napos léptékkel)
    future_events_ids = []  # Az események ID-ját tároljuk
    current_time = event.start_time

    # Egy hónap max előretekintés
    max_future_time = current_time + timedelta(days=30)

    # Az események keresése, amik ugyanazon a napon és időpontban ismétlődnek
    while event_start >= current_time and event_start <= max_future_time:
        # Keressük meg az eseményt ugyanazon a napon és ugyanabban az időpontban
        future_event = Event.objects.filter(
            start_time__date=event_start.date(),
            end_time__date=event_end.date()
        )

        # Az ID-kat tároljuk el
        future_events_ids.extend(future_event.values_list('id', flat=True))

        # Kiíratjuk, hogy miket találunk
        print(f"Keresett esemény időpontja: {event_start} - {event_end}")
        print(f"Talált események ID-k: {future_events_ids}")

        # Hozzáadjuk a 7 napot a következő kereséshez
        event_start += timedelta(days=7)
        event_end += timedelta(days=7)

    # Törlés végrehajtása
    if request.method == 'POST':
        if 'delete_all' in request.POST:
            # Ha az összes jövőbeli eseményt töröljük
            Event.objects.filter(id__in=future_events_ids).delete()
        elif 'delete_single' in request.POST:
            # Ha csak ezt az egy eseményt töröljük
            event.delete()
        return redirect('calendarapp:calendar_view')

    return render(request, 'calendarapp/edit_event.html', {
        'event': event,
        'future_events_ids': future_events_ids  # Az ID-kat átadjuk a sablonnak
    })


@login_required
@permission_required('calendarapp.add_event', raise_exception=True)
def create_event(request):
    if request.method == 'POST':
        form = EventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            repeat_weekday = int(form.cleaned_data['repeat_weekday'])
            repeat_until = form.cleaned_data['repeat_until']

            start_datetime = form.cleaned_data['start_time']
            end_datetime = form.cleaned_data['end_time']

            if repeat_until == '1m':
                end_date_limit = start_datetime + timedelta(days=30)
            elif repeat_until == '3m':
                end_date_limit = start_datetime + timedelta(days=90)
            elif repeat_until == '6m':
                end_date_limit = start_datetime + timedelta(days=180)
            else:
                end_date_limit = start_datetime  # csak egy alkalom

            # Első esemény mentése
            Event.objects.create(
                title=event.title,
                description=event.description,
                start_time=start_datetime,
                end_time=end_datetime,
                max_capacity=event.max_capacity,
                cancel_limit_hours=event.cancel_limit_hours,
                signup_limit_hours=event.signup_limit_hours
            )

            # Ha nincs ismétlés, nincs további teendő
            if repeat_until == '0':
                return redirect('calendarapp:calendar_view')

            # További ismétlődő események létrehozása
            current_date = start_datetime + timedelta(days=1)
            while current_date <= end_date_limit:
                if current_date.weekday() == repeat_weekday:
                    Event.objects.create(
                        title=event.title,
                        description=event.description,
                        start_time=current_date,
                        end_time=current_date.replace(hour=end_datetime.hour, minute=end_datetime.minute),
                        max_capacity=event.max_capacity,
                        cancel_limit_hours=event.cancel_limit_hours,
                        signup_limit_hours=event.signup_limit_hours
                    )
                current_date += timedelta(days=1)

            return redirect('calendarapp:calendar_view')
    else:
        form = EventForm()
    return render(request, 'calendarapp/create_event.html', {'form': form})



@login_required
@permission_required('calendarapp.change_event', raise_exception=True)
def edit_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    if request.method == 'POST':
        form = EventForm(request.POST, instance=event)
        if form.is_valid():
            form.save()
            return redirect('calendarapp:calendar_view')
    else:
        form = EventForm(instance=event)
    return render(request, 'calendarapp/edit_event.html', {'form': form, 'event': event})


from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Attendance
from django.utils.timezone import now
from allauth.socialaccount.models import SocialAccount

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Attendance
from django.utils.timezone import now
from allauth.socialaccount.models import SocialAccount

@login_required
def profile_view(request):
    user = request.user
    registrations = Attendance.objects.filter(user=user).select_related('event')

    past_events = [att.event for att in registrations if att.event.end_time < now()]
    future_events = [att.event for att in registrations if att.event.end_time >= now()]

    # Check if the user has a linked Facebook account
    try:
        social_account = user.socialaccount_set.get(provider='facebook')
        user_data = social_account.extra_data
        name = user_data.get('name')
        picture_url = user_data.get('picture', {}).get('data', {}).get('url')
    except SocialAccount.DoesNotExist:
        # If no Facebook account is linked, use the default username
        name = user.username  # Default username from allauth registration
        picture_url = None

    return render(request, 'calendarapp/profile.html', {
        'past_events': past_events,
        'future_events': future_events,
        'name': name,
        'picture_url': picture_url,  # Profile picture URL
    })

from django.contrib import messages
from django.shortcuts import redirect

@login_required
def cancel_registration(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    if not event.is_cancel_allowed():
        messages.error(request, "Az esemény túl közel van, már nem mondható le.")
        return redirect('calendarapp:profile')

    attendance = Attendance.objects.filter(user=request.user, event=event).first()
    if attendance:
        attendance.delete()
        messages.success(request, "Sikeresen lemondta az eseményt.")

        # Email küldése az edzőknek
        subject = f"Jelentkezés visszavonva: {event.title}"
        message = f"{request.user.username} visszavonta a jelentkezését az eseményről: {event.title}\nIdőpont: {event.start_time}"
        recipient_list = get_edzo_emails()

        if recipient_list:
            send_mail(subject, message, None, recipient_list, fail_silently=False)

    else:
        messages.error(request, "Nem található jelentkezés az adott eseményre.")

    return redirect('calendarapp:profile')


def is_admin_or_group_leader(user):
    return user.is_authenticated and (user.is_superuser or user.groups.filter(name="edzo").exists())

@login_required
@user_passes_test(is_admin_or_group_leader)
def event_attendance_summary(request):
    month = request.GET.get("month", now().month)
    year = request.GET.get("year", now().year)

    events = Event.objects.filter(
        start_time__year=year,
        start_time__month=month
    ).annotate(attendee_count=Count('attendance'))

    return render(request, "calendarapp/event_summary.html", {
        "events": events,
        "selected_month": int(month),
        "selected_year": int(year)
    })


@login_required
@user_passes_test(is_admin_or_group_leader)
def user_attendance_summary(request):
    month = request.GET.get("month", now().month)
    year = request.GET.get("year", now().year)

    # Lekérdezzük a felhasználók részvételét adott hónapra
    attendance_records = Attendance.objects.filter(
        event__start_time__year=year,
        event__start_time__month=month
    ).select_related('user', 'event')

    # Adatok struktúrázása felhasználónként
    user_attendance = {}
    for record in attendance_records:
        user = record.user
        event = record.event
        if user not in user_attendance:
            user_attendance[user] = {
                'events': [],
                'total_count': 0,  # Jelentkezések száma
                'checked_in_count': 0  # Részvételek száma (checked_in=True)
            }
        user_attendance[user]['events'].append(event)
        user_attendance[user]['total_count'] += 1
        if record.checked_in:
            user_attendance[user]['checked_in_count'] += 1

    return render(request, "calendarapp/user_summary.html", {
        "user_attendance": user_attendance,
        "selected_month": int(month),
        "selected_year": int(year)
    })

from django.shortcuts import render, get_object_or_404, redirect
from .models import Event, Attendance
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods

@user_passes_test(is_admin_or_group_leader)
@login_required
@require_http_methods(["GET", "POST"])
def event_checkin_view(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    attendances = Attendance.objects.filter(event=event).select_related('user')

    if request.method == "POST":
        for attendance in attendances:
            checkbox_name = f"checkin_{attendance.user.id}"
            attendance.checked_in = checkbox_name in request.POST
            attendance.save()
        return redirect('calendarapp:checkin_event', event_id=event.id)

    return render(request, "calendarapp/event_checkin.html", {
        "event": event,
        "attendances": attendances,
    })

from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_http_methods
from django.db.models import Count, Q
from .models import Attendance
from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_http_methods
from .models import Attendance

@user_passes_test(is_admin_or_group_leader)
@login_required
@require_http_methods(["GET"])
def jelentkezesek_listaja(request):
    statisztika = User.objects.annotate(
        jelentkezesek_szama=Count('attendance'),
        checkinek_szama=Count('attendance', filter=Q(attendance__checked_in=True))
    ).order_by('-jelentkezesek_szama')

    return render(request, "calendarapp/jelentkezesek_listaja.html", {
        "statisztika": statisztika
    })

from django.shortcuts import render, redirect
from .forms import UserProfileForm
from .utils import get_facebook_name


def update_user_profile_name(user):
    facebook_name = get_facebook_name(user)
    if facebook_name:
        user.userprofile.display_name = facebook_name
        user.userprofile.save()

from django.shortcuts import render, redirect
from .forms import UserProfileForm
from .models import UserProfile


def update_profile(request):
    # Ellenőrizzük, hogy létezik-e a UserProfile
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=user_profile)
        if form.is_valid():
            form.save()
            return redirect('calendarapp:profile')  # Itt állítsd be a megfelelő profiloldali URL-t
    else:
        form = UserProfileForm(instance=user_profile)

    return render(request, 'calendarapp/update_profile.html', {'form': form})