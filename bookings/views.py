from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q
from datetime import datetime, timedelta
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
    
    services = Service.objects.filter(company=company, active=True)
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
        
        # Get date range (default to current month)
        today = timezone.now().date()
        month = int(request.GET.get('month', today.month))
        year = int(request.GET.get('year', today.year))
        
        # Get first and last day of the month
        first_day = datetime(year, month, 1).date()
        if month == 12:
            last_day = datetime(year + 1, 1, 1).date() - timedelta(days=1)
        else:
            last_day = datetime(year, month + 1, 1).date() - timedelta(days=1)
        
        # Get all bookings for this month
        bookings = Booking.objects.filter(
            company=company,
            date__gte=first_day,
            date__lte=last_day
        ).select_related('customer', 'staff', 'service').order_by('date', 'start_time')
        
        # Group bookings by date
        bookings_by_date = {}
        for booking in bookings:
            date_str = booking.date.strftime('%Y-%m-%d')
            if date_str not in bookings_by_date:
                bookings_by_date[date_str] = []
            bookings_by_date[date_str].append(booking)
        
        # Calculate previous and next month
        if month == 1:
            prev_month = 12
            prev_year = year - 1
        else:
            prev_month = month - 1
            prev_year = year
        
        if month == 12:
            next_month = 1
            next_year = year + 1
        else:
            next_month = month + 1
            next_year = year
        
        context = {
            'company': company,
            'bookings': bookings,
            'bookings_by_date': bookings_by_date,
            'current_month': month,
            'current_year': year,
            'prev_month': prev_month,
            'prev_year': prev_year,
            'next_month': next_month,
            'next_year': next_year,
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
