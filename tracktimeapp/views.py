from django.shortcuts import render, redirect
from django.urls import reverse
from .models import Members, Duration
from django.utils import timezone


def register(request):
    """Registration page for first-time entry"""
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        name = request.POST.get('name')
        year_of_study = request.POST.get('year_of_study')
        team_name = request.POST.get('team_name')

        # Create or update member
        member, created = Members.objects.get_or_create(
            Student_ID=student_id,
            defaults={
                'Name': name,
                'YearOfStudy': year_of_study,
                'TeamName': team_name
            }
        )

        if not created:
            member.Name = name
            member.YearOfStudy = year_of_study
            member.TeamName = team_name
            member.save()

        # Record entry time
        Duration.objects.create(Student_ID=member, EntryTime=timezone.now())

        # Redirect to success page with query parameters
        success_url = f"{reverse('success')}?student_id={student_id}&action=entry"
        return redirect(success_url)

    return render(request, 'register.html')


def scan(request):
    """Scan page for entry/exit without requiring full details"""
    if request.method == 'POST':
        student_id = request.POST.get('student_id')

        try:
            member = Members.objects.get(Student_ID=student_id)
        except Members.DoesNotExist:
            # Redirect to registration if student not found
            return redirect('register')

        # Find the last session
        last_session = Duration.objects.filter(Student_ID=member).order_by('-EntryTime').first()

        # Determine if this is entry or exit
        if last_session is None or last_session.ExitTime is not None:
            # No open session, record a new entry
            Duration.objects.create(Student_ID=member, EntryTime=timezone.now())
            action = 'entry'
            time_spent = None
        else:
            # Close the existing session
            last_session.ExitTime = timezone.now()
            last_session.TimeSpent = last_session.ExitTime - last_session.EntryTime
            last_session.save()
            action = 'exit'
            time_spent = last_session.TimeSpent

        # build URL with query parameters since success view reads GET parameters
        success_url = f"{reverse('success')}?student_id={student_id}&action={action}"
        return redirect(success_url)

    return render(request, 'scan.html')


def success(request):
    """Success page showing entry/exit confirmation"""
    student_id = request.GET.get('student_id')
    action = request.GET.get('action', 'entry')

    try:
        member = Members.objects.get(Student_ID=student_id)
    except Members.DoesNotExist:
        return redirect('register')

    # Get the latest duration record
    latest_duration = Duration.objects.filter(Student_ID=member).order_by('-EntryTime').first()

    # Prepare context
    status_message = f"✓ Entry Recorded" if action == 'entry' else f"✓ Exit Recorded"
    time_spent = None
    timestamp = latest_duration.ExitTime if action == 'exit' else latest_duration.EntryTime

    if action == 'exit' and latest_duration.TimeSpent:
        time_spent = str(latest_duration.TimeSpent)

    context = {
        'status_message': status_message,
        'student_id': student_id,
        'student_name': member.Name,
        'time_spent': time_spent,
        'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S')
    }

    return render(request, 'success.html', context)

