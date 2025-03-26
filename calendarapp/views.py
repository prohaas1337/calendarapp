#views.py
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_protect
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from .models import Event, Attendance
from django.http import JsonResponse
from django.utils.dateparse import parse_datetime
from django.contrib.auth.decorators import permission_required
from django.shortcuts import get_object_or_404
from django.shortcuts import render, redirect
from .models import Event
from .forms import EventForm
from datetime import timedelta
from django.shortcuts import get_object_or_404, render, redirect
from datetime import timedelta
from .models import Event


@login_required
def calendar_view(request):
    today = now()
    start_of_week = today - timedelta(days=today.weekday())  # Hétfő
    end_of_week = start_of_week + timedelta(days=6)  # Vasárnap

    events = Event.objects.filter(start_time__gte=start_of_week, end_time__lte=end_of_week)

    events_list = []
    current_user = request.user  # Aktuálisan bejelentkezett felhasználó

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
    }

    return render(request, 'calendarapp/calendar.html', context)


def event_detail(request, event_id):
    try:
        event = Event.objects.get(id=event_id)
        attendees = Attendance.objects.filter(event=event)
        attendee_names = [attendee.user.username for attendee in attendees]

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


def events_api(request):
    start = request.GET.get('start')
    end = request.GET.get('end')

    # Ellenőrizzük, hogy helyes formátumban vannak-e a dátumok
    start = parse_datetime(start)
    end = parse_datetime(end)

    # Ha nem sikerült a parszolás, akkor hibát jelezhetünk
    if not start or not end:
        return JsonResponse({'status': 'error', 'message': 'Hibás dátum formátum.'}, status=400)

    events = Event.objects.filter(start_time__gte=start, end_time__lte=end)

    event_list = []
    for event in events:
        is_attending = Attendance.objects.filter(user=request.user, event=event).exists()
        event_list.append({
            'id': event.id,
            'title': event.title,
            'start': event.start_time.isoformat(),
            'end': event.end_time.isoformat(),
            'description': event.description,
            'user_is_attending': is_attending  # Itt adjuk hozzá
        })

    print(event_list)  # Logoljuk az event_list-et a konzolra

    return JsonResponse(event_list, safe=False)


def session_check_view(request):
    session_id = request.session.session_key
    return HttpResponse(f'Session ID: {session_id}')

@login_required
@csrf_protect
@require_POST
def signup_event(request):
    event_id = request.POST.get('event_id')
    if not event_id:
        return JsonResponse({'status': 'error', 'message': 'Hiányzik az event_id.'}, status=400)

    try:
        event = Event.objects.get(id=event_id)
    except Event.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Az esemény nem található.'}, status=404)

    # Ellenőrizzük, hogy a jelentkezési idő még nyitott-e
    if not event.is_signup_open():
        return JsonResponse({'status': 'error', 'message': 'A jelentkezési határidő lejárt.'}, status=400)

    # Ellenőrizzük, hogy a felhasználó még nem jelentkezett-e
    attendance, created = Attendance.objects.get_or_create(user=request.user, event=event)
    if not created:
        return JsonResponse({'status': 'error', 'message': 'Már jelentkezett erre az eseményre!'}, status=400)

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
        # Lemondási határidő ellenőrzése
        if not event.is_cancel_allowed():
            return JsonResponse({'status': 'error', 'message': 'A lemondási határidő lejárt.'}, status=400)
        attendance.delete()
        return JsonResponse({'status': 'success'})
    except Attendance.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Nem található a jelentkezés erre az eseményre.'}, status=404)


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

            # Kezdő dátum
            start_datetime = form.cleaned_data['start_time']
            end_datetime = form.cleaned_data['end_time']

            # Meghatározzuk a vége dátumot
            if repeat_until == '1m':
                end_date_limit = start_datetime + timedelta(days=30)
            elif repeat_until == '3m':
                end_date_limit = start_datetime + timedelta(days=90)
            elif repeat_until == '6m':
                end_date_limit = start_datetime + timedelta(days=180)
            else:
                end_date_limit = start_datetime  # csak egy alkalom

            # Először beállítjuk az első alkalmat ha a nap egyezik
            current_date = start_datetime
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


from django.shortcuts import render, redirect, get_object_or_404
from django.utils.timezone import now
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Attendance, Event


@login_required
def profile_view(request):
    user = request.user
    registrations = Attendance.objects.filter(user=user).select_related('event')

    past_events = [att.event for att in registrations if att.event.end_time < now()]
    future_events = [att.event for att in registrations if att.event.end_time >= now()]

    return render(request, 'calendarapp/profile.html', {
        'past_events': past_events,
        'future_events': future_events,
    })


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Attendance, Event

@login_required
def cancel_registration(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    if not event.is_cancel_allowed():
        messages.error(request, "Az esemény túl közel van, már nem mondható le.")
        return redirect('profile')

    attendance = Attendance.objects.filter(user=request.user, event=event).first()
    if attendance:
        attendance.delete()
        messages.success(request, "Sikeresen lemondta az eseményt.")
    else:
        messages.error(request, "Nem található jelentkezés az adott eseményre.")

    return redirect('calendarapp:profile')