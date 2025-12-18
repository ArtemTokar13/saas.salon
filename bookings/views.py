from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q
from datetime import datetime, timedelta, time as dtime
import json
from .models import Booking, Customer
from .forms import BookingForm
from companies.models import Company, Staff, Service, WorkingHours
from users.models import UserProfile


def create_booking(request, company_id):
    """Customer-facing booking page"""
    company = get_object_or_404(Company, id=company_id)
    
    if request.method == 'POST':
        form = BookingForm(request.POST, company=company)
        if form.is_valid():
            booking = form.save()
            messages.success(request, 'Booking created successfully! We will contact you soon.')
            return redirect('booking_confirmation', booking_id=booking.id)
    else:
        form = BookingForm(company=company)
    
    services = Service.objects.filter(company=company, is_active=True)
    staff = Staff.objects.filter(company=company, is_active=True)
    
    context = {
        'company': company,
        'form': form,
        'services': services,
        'staff': staff,
    }
    
    return render(request, 'bookings/create_booking.html', context)


def booking_confirmation(request, booking_id):
    """Booking confirmation page"""
    booking = get_object_or_404(Booking, id=booking_id)
    
    context = {
        'booking': booking,
    }
    
    return render(request, 'bookings/confirmation.html', context)


def get_available_staff(request, company_id, service_id):
    """API endpoint to get staff members who can perform a specific service"""
    service = get_object_or_404(Service, id=service_id, company_id=company_id)
    staff = service.staff_members.filter(is_active=True)
    
    staff_data = [
        {
            'id': s.id,
            'name': s.name,
            'specialization': s.specialization,
            'avatar': s.avatar.url if s.avatar else None
        }
        for s in staff
    ]
    
    return JsonResponse({'staff': staff_data})


def get_available_times(request, company_id, staff_id, date_str):
    """API endpoint to get available time slots for a staff member on a specific date"""
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        staff = get_object_or_404(Staff, id=staff_id, company_id=company_id)
        company = staff.company
        
        # Get working hours for this day
        day_of_week = date.weekday()
        working_hours = WorkingHours.objects.filter(
            company=company,
            day_of_week=day_of_week,
            is_day_off=False
        ).first()
        
        if not working_hours:
            return JsonResponse({'available_times': []})
        
        # Get existing bookings for this staff member on this date
        existing_bookings = Booking.objects.filter(
            staff=staff,
            date=date,
            status__in=[0, 1]  # Pending or Confirmed
        ).values_list('start_time', 'end_time')
        
        # Generate time slots (every 30 minutes)
        available_times = []
        current_time = datetime.combine(date, working_hours.start_time)
        end_time = datetime.combine(date, working_hours.end_time)
        
        while current_time < end_time:
            time_str = current_time.strftime('%H:%M')
            
            # Check if this time slot is available
            is_available = True
            for booking_start, booking_end in existing_bookings:
                booking_start_dt = datetime.combine(date, booking_start)
                booking_end_dt = datetime.combine(date, booking_end)
                
                if booking_start_dt <= current_time < booking_end_dt:
                    is_available = False
                    break
            
            if is_available:
                available_times.append(time_str)
            
            current_time += timedelta(minutes=30)
        
        return JsonResponse({'available_times': available_times})
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def booking_calendar(request):
    """Calendar view for company administrators"""
    try:
        profile = request.user.userprofile
        if not profile.is_admin:
            messages.error(request, 'Access denied.')
            return redirect('home')
        
        company = profile.company
        
        today = timezone.now().date()
        date_str = request.GET.get('date')
        try:
            current_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else today
        except Exception:
            current_date = today

        # support quick prev/next day links
        if request.GET.get('prev'):
            current_date = current_date - timedelta(days=1)
        if request.GET.get('next'):
            current_date = current_date + timedelta(days=1)
        
        # We'll render a day-view schedule for `current_date` with columns per staff
        staff_list = list(Staff.objects.filter(company=company, is_active=True).order_by('name'))

        working_hours = WorkingHours.objects.filter(company=company, day_of_week=current_date.weekday()).first()
        if working_hours:
            day_start = dtime(hour=working_hours.start_time.hour, minute=0)
            day_end = dtime(hour=working_hours.end_time.hour, minute=0)
        else:
            day_start = dtime(hour=8, minute=0)
            day_end = dtime(hour=20, minute=0)

        # Get bookings for the selected date
        bookings = Booking.objects.filter(
            company=company,
            date=current_date,
            status__in=[0, 1]
        ).select_related('customer', 'staff', 'service').order_by('start_time')

        # Serialize staff and bookings into JSON-friendly structures
        staff_data = [
            {'id': s.id, 'title': s.name}
            for s in staff_list
        ]

        bookings_data = []
        for b in bookings:
            start_dt = datetime.combine(current_date, b.start_time)
            end_dt = datetime.combine(current_date, b.end_time)
            bookings_data.append({
                'id': b.id,
                'resourceId': b.staff_id,
                'title': f"{b.customer.name} — {b.service.name}",
                'start': start_dt.isoformat(),
                'end': end_dt.isoformat(),
                'backgroundColor': '#3b82f6' if b.status == 0 else '#10b981',
                'borderColor': '#1e40af' if b.status == 0 else '#047857',
                'extendedProps': {
                    'staff_id': b.staff_id,
                    'status': b.get_status_display(),
                    'service': b.service.name,
                    'customer': b.customer.name,
                }
            })

        context = {
            'company': company,
            'staff_list': staff_list,
            'resources_json': json.dumps(staff_data),
            'bookings': bookings,
            'events_json': json.dumps(bookings_data),
            'current_date': current_date,
            'day_start': day_start.strftime('%H:%M'),
            'day_end': day_end.strftime('%H:%M'),
            'today': today,
        }
        
        return render(request, 'bookings/calendar.html', context)
    
    except UserProfile.DoesNotExist:
        messages.error(request, 'User profile not found.')
        return redirect('home')


@login_required
def update_booking_status(request, booking_id):
    """Update booking status (confirm or cancel)"""
    try:
        profile = request.user.userprofile
        if not profile.is_admin:
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        booking = get_object_or_404(Booking, id=booking_id, company=profile.company)
        
        if request.method == 'POST':
            status = request.POST.get('status')
            if status in ['0', '1', '2']:
                booking.status = status
                booking.save()
                return JsonResponse({'success': True, 'status': booking.get_status_display()})
        
        return JsonResponse({'error': 'Invalid request'}, status=400)
    
    except UserProfile.DoesNotExist:
        return JsonResponse({'error': 'User profile not found'}, status=403)


@login_required
def update_booking_ajax(request, booking_id):
    """AJAX endpoint to move a booking (change staff and/or start time). Expects POST with `staff_id` and `start_time` (HH:MM)."""
    try:
        profile = request.user.userprofile
        if not profile.is_admin:
            return JsonResponse({'error': 'Access denied'}, status=403)

        booking = get_object_or_404(Booking, id=booking_id, company=profile.company)

        if request.method != 'POST':
            return JsonResponse({'error': 'Invalid method'}, status=400)

        staff_id = request.POST.get('staff_id')
        start_time_str = request.POST.get('start_time')

        if not staff_id or not start_time_str:
            return JsonResponse({'error': 'Missing parameters'}, status=400)

        try:
            new_staff = Staff.objects.get(id=int(staff_id), company=profile.company)
        except Staff.DoesNotExist:
            return JsonResponse({'error': 'Staff not found'}, status=404)

        # parse start_time
        try:
            h, m = map(int, start_time_str.split(':'))
            new_start = dtime(hour=h, minute=m)
        except Exception:
            return JsonResponse({'error': 'Invalid start_time format'}, status=400)

        # compute new end_time based on service duration
        duration = booking.service.duration
        dt_start = datetime.combine(booking.date, new_start)
        dt_end = dt_start + timedelta(minutes=duration)

        booking.staff = new_staff
        booking.start_time = new_start
        booking.end_time = dt_end.time()
        booking.save()

        return JsonResponse({'success': True, 'start_time': booking.start_time.strftime('%H:%M'), 'end_time': booking.end_time.strftime('%H:%M'), 'staff_id': booking.staff_id})

    except UserProfile.DoesNotExist:
        return JsonResponse({'error': 'User profile not found'}, status=403)
