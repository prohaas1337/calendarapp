#views.py
from django.utils.timezone import now
from datetime import timedelta
from django.views.decorators.csrf import csrf_protect
from django.http import HttpResponse
from django.shortcuts import render, redirect
from .forms import EventForm
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from .models import Event, Attendance
from django.http import JsonResponse
from django.utils.dateparse import parse_datetime
from django.contrib.auth.decorators import permission_required
from django.shortcuts import render, redirect
from .models import Event
from .forms import EventForm
from django.contrib.auth.decorators import permission_required
from django.shortcuts import get_object_or_404


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
    if request.method == 'POST':
        event.delete()
        return redirect('calendarapp:calendar_view')
    return render(request, 'calendarapp/delete_event_confirm.html', {'event': event})

@login_required
@permission_required('calendarapp.add_event', raise_exception=True)
def create_event(request):
    if request.method == 'POST':
        form = EventForm(request.POST)
        if form.is_valid():
            form.save()
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
