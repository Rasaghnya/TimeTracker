from django.shortcuts import render, redirect
from django.urls import reverse
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from .models import Members, Duration
from .face_utils import encode_face, serialize_encoding, recognize_face, find_best_match, deserialize_encoding
from django.utils import timezone
import json


def register(request):
    """Registration page for first-time entry"""
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        name = request.POST.get('name')
        year_of_study = request.POST.get('year_of_study')
        team_name = request.POST.get('team_name')
        face_image = request.POST.get('face_image')  # Base64-encoded face image

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

        # Handle face registration if provided
        if face_image:
            face_encoding = encode_face(face_image)
            if face_encoding is not None:
                member.face_encoding = serialize_encoding(face_encoding)
                member.face_registered = True
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
        # Check if this is a face-based scan or ID-based scan
        face_image = request.POST.get('face_image')  # Base64-encoded face image
        student_id = request.POST.get('student_id')   # Manual ID input
        scan_method = 'unknown'

        # Determine scan method and get student
        member = None
        
        if face_image:
            # Face-based scanning
            scan_method = 'face'
            # Build candidates dictionary of all registered faces
            candidates = {}
            for m in Members.objects.filter(face_registered=True):
                if m.face_encoding:
                    candidates[m.Student_ID] = m.face_encoding
            
            # Find best match
            matched_student_id, distance = find_best_match(face_image, candidates)
            
            if matched_student_id:
                try:
                    member = Members.objects.get(Student_ID=matched_student_id)
                except Members.DoesNotExist:
                    pass
            else:
                # No match found - return error
                return render(request, 'scan.html', {
                    'error': 'Face not recognized. Please use manual ID entry or register your face first.',
                    'scan_method': 'face'
                })
        
        elif student_id:
            # ID-based scanning
            scan_method = 'id'
            try:
                member = Members.objects.get(Student_ID=student_id)
            except Members.DoesNotExist:
                # Redirect to registration if student not found
                return redirect('register')
        
        else:
            # No scan method provided
            return render(request, 'scan.html', {
                'error': 'Please provide either a face image or student ID.',
                'scan_method': 'unknown'
            })

        # If member not found at this point, show error
        if not member:
            return render(request, 'scan.html', {
                'error': 'Student not found. Please register first.',
                'scan_method': scan_method
            })

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

        # Build URL with query parameters since success view reads GET parameters
        success_url = f"{reverse('success')}?student_id={member.Student_ID}&action={action}&scan_method={scan_method}"
        return redirect(success_url)

    return render(request, 'scan.html')


def success(request):
    """Success page showing entry/exit confirmation"""
    student_id = request.GET.get('student_id')
    action = request.GET.get('action', 'entry')
    scan_method = request.GET.get('scan_method', 'unknown')

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

    # Map scan method to display text
    scan_method_display = {
        'face': 'Face Recognition',
        'id': 'ID Scan',
        'unknown': 'Manual Entry'
    }.get(scan_method, 'Manual Entry')

    context = {
        'status_message': status_message,
        'student_id': student_id,
        'student_name': member.Name,
        'time_spent': time_spent,
        'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        'scan_method': scan_method_display
    }

    return render(request, 'success.html', context)


# API Endpoints for face recognition (AJAX calls)

@require_http_methods(["POST"])
@csrf_exempt
def register_face_api(request):
    """
    API endpoint to register or update a student's face.
    Expects JSON: {'student_id': '...', 'face_image': 'base64...'}
    """
    try:
        data = json.loads(request.body)
        student_id = data.get('student_id')
        face_image = data.get('face_image')

        if not student_id or not face_image:
            return JsonResponse({'success': False, 'message': 'Missing student_id or face_image'}, status=400)

        # Get student
        try:
            member = Members.objects.get(Student_ID=student_id)
        except Members.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Student not found'}, status=404)

        # Encode face
        face_encoding = encode_face(face_image)
        if face_encoding is None:
            return JsonResponse({'success': False, 'message': 'No face detected in image'}, status=400)

        # Store encoding
        member.face_encoding = serialize_encoding(face_encoding)
        member.face_registered = True
        member.save()

        return JsonResponse({'success': True, 'message': 'Face registered successfully'}, status=200)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@require_http_methods(["POST"])
@csrf_exempt
def recognize_face_api(request):
    """
    API endpoint to recognize a face.
    Expects JSON: {'face_image': 'base64...'}
    Returns: {'status': 'Match Found'|'No Match Found', 'student_id': '...', 'name': '...', 'distance': '...'}
    """
    try:
        data = json.loads(request.body)
        face_image = data.get('face_image')

        if not face_image:
            return JsonResponse({'success': False, 'message': 'Missing face_image'}, status=400)

        # Build candidates dictionary
        candidates = {}
        for member in Members.objects.filter(face_registered=True):
            if member.face_encoding:
                candidates[member.Student_ID] = member.face_encoding

        # Find best match
        matched_student_id, distance = find_best_match(face_image, candidates)

        if matched_student_id:
            try:
                member = Members.objects.get(Student_ID=matched_student_id)
                return JsonResponse({
                    'success': True,
                    'status': 'Match Found',
                    'student_id': member.Student_ID,
                    'name': member.Name,
                    'distance': float(distance)
                }, status=200)
            except Members.DoesNotExist:
                pass

        return JsonResponse({
            'success': True,
            'status': 'No Match Found',
            'student_id': None,
            'name': None,
            'distance': None
        }, status=200)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@require_http_methods(["PUT"])
@csrf_exempt
def update_face_api(request):
    """
    API endpoint to update a student's face.
    Expects JSON: {'student_id': '...', 'face_image': 'base64...'}
    """
    try:
        data = json.loads(request.body)
        student_id = data.get('student_id')
        face_image = data.get('face_image')

        if not student_id or not face_image:
            return JsonResponse({'success': False, 'message': 'Missing student_id or face_image'}, status=400)

        # Get student
        try:
            member = Members.objects.get(Student_ID=student_id)
        except Members.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Student not found'}, status=404)

        # Encode new face
        face_encoding = encode_face(face_image)
        if face_encoding is None:
            return JsonResponse({'success': False, 'message': 'No face detected in image'}, status=400)

        # Update encoding
        member.face_encoding = serialize_encoding(face_encoding)
        member.face_registered = True
        member.save()

        return JsonResponse({'success': True, 'message': 'Face updated successfully'}, status=200)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

