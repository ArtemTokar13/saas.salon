import json
import logging
from hashlib import md5
from datetime import datetime, timedelta, time as dtime
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseRedirect
from django.utils import timezone
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from .models import Booking, Customer
from .forms import BookingForm
from companies.models import Company, Staff, Service, WorkingHours, EmailLog, StaffWorkingHours, StaffOutOfOffice
from users.models import UserProfile
from app.decorators import subscription_required


logger = logging.getLogger(__name__)


################### HELPER FUNCTIONS #####################
def is_staff_out_of_office_at_time(staff, check_datetime):
    """Check if staff is out of office at a specific datetime"""
    return StaffOutOfOffice.objects.filter(
        staff=staff,
        start_datetime__lte=check_datetime,
        end_datetime__gte=check_datetime
    ).exists()


def is_staff_out_all_day(staff, date, work_start_time, work_end_time):
    """Check if staff is out of office for the entire working day"""
    work_start = datetime.combine(date, work_start_time)
    work_end = datetime.combine(date, work_end_time)
    
    # Make timezone-aware if needed
    if StaffOutOfOffice.objects.filter(staff=staff).exists():
        first_period = StaffOutOfOffice.objects.filter(staff=staff).first()
        if timezone.is_aware(first_period.start_datetime):
            work_start = timezone.make_aware(work_start)
            work_end = timezone.make_aware(work_end)
    
    # Check if any out-of-office period completely covers the working hours
    covering_periods = StaffOutOfOffice.objects.filter(
        staff=staff,
        start_datetime__lte=work_start,
        end_datetime__gte=work_end
    )
    
    return covering_periods.exists()


################### BOOKING VIEWS #####################
def create_booking(request, company_id):
    """Customer-facing booking page"""
    company = get_object_or_404(Company, id=company_id)
    
    if request.method == 'POST':
        form = BookingForm(request.POST, company=company, user=request.user)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.delete_code = md5(f"{booking.customer.email}{timezone.now().timestamp()}".encode()).hexdigest()
            
            # Check if service requires staff confirmation
            if booking.service.need_staff_confirmation and (request.user.is_authenticated == False or (request.user.is_authenticated and request.user.userprofile.company != company)):
                booking.status = 3  # PreBooked
            else:
                booking.status = 1  # Confirmed normal confirmation
            
            if booking.price is None:
                booking.price = booking.service.price
            booking.save()
            booking_link = request.build_absolute_uri(
                redirect('booking_confirmation', booking_id=booking.id).url
            )
            cancel_link = request.build_absolute_uri(
                redirect("cancel_booking", booking_id=booking.id, delete_code=booking.delete_code).url
            )
            
            # Send email confirmation (only if customer has email)
            if booking.customer.email:
                subject = 'Your Booking Confirmation'
                html_message = render_to_string('email/booking_confirmation.html', {
                    'company': company,
                    'booking': booking,
                    'booking_link': booking_link,
                    'cancel_link': cancel_link,
                    'current_year': timezone.now().year,
                })
                from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None)
                recipient_list = [booking.customer.email]
                email_log = EmailLog.objects.create(
                    recipient_email=booking.customer.email,
                    subject=subject,
                    email_type='booking_confirmation',
                    status='pending'
                )
                try:
                    msg = EmailMultiAlternatives(subject, '', from_email, recipient_list)
                    msg.attach_alternative(html_message, "text/html")
                    msg.send()
                    email_log.status = 'sent'
                    email_log.sent_at = timezone.now()
                    email_log.save()
                except Exception as e:
                    email_log.status = 'failed'
                    email_log.error_message = str(e)
                    email_log.save()
                    logger.error(f"Failed to send booking confirmation email: {e}")
            
            messages.success(request, 'Booking created successfully! We will contact you soon.')
            return redirect('booking_confirmation', booking_id=booking.id)
    else:
        form = BookingForm(company=company, user=request.user)
    
    services = Service.objects.filter(company=company, is_active=True)
    
    context = {
        'company': company,
        'form': form,
        'services': services,
    }
    
    return render(request, 'bookings/create_booking.html', context)


# def check_staff_availability(request):
#     """API endpoint to check if a staff member is available for a given date and time"""
#     staff_id = request.GET.get('staff_id')
#     date_str = request.GET.get('date')
#     start_time_str = request.GET.get('start_time')
#     end_time_str = request.GET.get('end_time')
    
#     try:
#         date = datetime.strptime(date_str, '%Y-%m-%d').date()
#         sh, sm = map(int, start_time_str.split(':'))
#         eh, em = map(int, end_time_str.split(':'))
#         start_time = dtime(hour=sh, minute=sm)
#         end_time = dtime(hour=eh, minute=em)
        
#         overlapping_bookings = Booking.objects.filter(
#             staff_id=staff_id,
#             date=date,
#             status__in=[0, 1],  # Pending or Confirmed
#         ).filter(
#             Q(start_time__lt=end_time) & Q(end_time__gt=start_time)
#         )
        
#         is_available = not overlapping_bookings.exists()
        
#         return JsonResponse({'is_available': is_available})
    
#     except Exception as e:
#         return JsonResponse({'error': str(e)}, status=400)


def booking_confirmation(request, booking_id):
    """Booking confirmation page"""
    booking = get_object_or_404(Booking, id=booking_id)
    
    # Generate cancel link with delete_code
    cancel_link = request.build_absolute_uri(
        redirect("cancel_booking", booking_id=booking.id, delete_code=booking.delete_code).url
    )
    
    context = {
        'booking': booking,
        'cancel_link': cancel_link,
    }
    
    return render(request, 'bookings/confirmation.html', context)


def cancel_booking(request, booking_id, delete_code):
    """Customer-facing booking cancellation page"""
    booking = get_object_or_404(Booking, id=booking_id, delete_code=delete_code)
    
    if request.method == 'POST':
        booking.status = 2
        booking.save()

        # Send cancellation email to customer (only if they have an email)
        if booking.customer.email:
            subject = 'Your Booking Cancellation'
            html_message = render_to_string('email/booking_cancellation.html', {
                'booking': booking,
                'company': booking.company,
                'cancellation_date': timezone.now(),
                'booking_link': request.build_absolute_uri(f'/companies/{booking.company.id}/'),
                'current_year': timezone.now().year,
            })
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None)
            recipient_list = [booking.customer.email]
            email_log = EmailLog.objects.create(
                recipient_email=booking.customer.email,
                subject=subject,
                email_type='booking_cancellation',
                status='pending'
            )
            try:
                msg = EmailMultiAlternatives(subject, '', from_email, recipient_list)
                msg.attach_alternative(html_message, "text/html")
                msg.send()
                email_log.status = 'sent'
                email_log.sent_at = timezone.now()
                email_log.save()
            except Exception as e:
                email_log.status = 'failed'
                email_log.error_message = str(e)
                email_log.save()
                logger.error(f"Failed to send booking cancellation email: {e}")

        messages.success(request, 'Your booking has been cancelled.')
    return HttpResponseRedirect(f'/companies/{booking.company.id}/')


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


@never_cache
def get_available_dates(request, company_id, staff_id):
    """API endpoint to get available dates for a staff member (next 30 days)"""
    try:
        staff = get_object_or_404(Staff, id=staff_id, company_id=company_id)
        company = staff.company
        
        # Check if a service_id is provided to filter by service-specific dates
        service_id = request.GET.get('service_id')
        service = None
        if service_id:
            try:
                service = get_object_or_404(Service, id=service_id, company_id=company_id)
            except:
                pass
        
        available_dates = []
        today = timezone.now().date()
        
        # If service is restricted to specific dates, use those
        if service and service.restrict_to_available_dates and service.available_dates:
            # Filter available_dates to only future dates
            for date_str in service.available_dates:
                try:
                    date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    if date >= today:
                        day_of_week = date.weekday()
                        # Check if staff works on this day
                        if not staff.working_days or day_of_week in staff.working_days:
                            # Check if staff has working hours for this day
                            staff_hours = StaffWorkingHours.objects.filter(
                                staff=staff,
                                day_of_week=day_of_week,
                                is_day_off=False
                            ).first()
                            
                            # Determine working hours for this day
                            if staff_hours:
                                work_start = datetime.combine(date, staff_hours.start_time)
                                work_end = datetime.combine(date, staff_hours.end_time)
                            else:
                                # Check company working hours
                                working_hours = WorkingHours.objects.filter(
                                    company=company,
                                    day_of_week=day_of_week,
                                    is_day_off=False
                                ).first()
                                if not working_hours:
                                    continue
                                work_start_time = working_hours.start_time
                                work_end_time = working_hours.end_time
                                work_start = datetime.combine(date, work_start_time)
                                work_end = datetime.combine(date, work_end_time)
                            
                            # Only skip date if out-of-office covers ENTIRE working day
                            skip_date = is_staff_out_all_day(staff, date, work_start.time(), work_end.time())
                            
                            if not skip_date:
                                available_dates.append({
                                    'date': date.strftime('%Y-%m-%d'),
                                    'display': date.strftime('%a, %b %d')
                                })
                except ValueError:
                    continue
            return JsonResponse({'available_dates': available_dates})
        
        # Otherwise, check next 90 days (3 months) based on working hours
        for i in range(90):
            date = today + timedelta(days=i)
            
            day_of_week = date.weekday()
            
            # Check if staff member works on this day
            if not staff.working_days or day_of_week in staff.working_days:
                # Check if staff has custom working hours for this day
                staff_hours = StaffWorkingHours.objects.filter(
                    staff=staff,
                    day_of_week=day_of_week,
                    is_day_off=False
                ).first()
                
                # Determine working hours for this day
                if staff_hours:
                    work_start = datetime.combine(date, staff_hours.start_time)
                    work_end = datetime.combine(date, staff_hours.end_time)
                else:
                    # Check if company is open on this day
                    working_hours = WorkingHours.objects.filter(
                        company=company,
                        day_of_week=day_of_week,
                        is_day_off=False
                    ).first()
                    
                    if not working_hours:
                        continue
                    
                    work_start = datetime.combine(date, working_hours.start_time)
                    work_end = datetime.combine(date, working_hours.end_time)
                
                
                # Only skip date if out-of-office covers ENTIRE working day
                skip_date = is_staff_out_all_day(staff, date, work_start.time(), work_end.time())
                
                if not skip_date:
                    available_dates.append({
                        'date': date.strftime('%Y-%m-%d'),
                        'display': date.strftime('%a, %b %d')
                    })
        
        return JsonResponse({'available_dates': available_dates})
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@never_cache
def get_available_times(request, company_id, staff_id, service_id, date_str):
    """API endpoint to get available time slots for a staff member on a specific date"""
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        staff = get_object_or_404(Staff, id=staff_id, company_id=company_id)
        service = get_object_or_404(Service, id=service_id, company_id=company_id)
        company = staff.company
        
        # Note: We don't check if entire day is out-of-office here
        # Instead, we filter individual time slots below
        
        # Get working hours for this day
        day_of_week = date.weekday()
        
        # Check if staff works on this day
        if staff.working_days and day_of_week not in staff.working_days:
            return JsonResponse({'available_times': []})
        
        # Try to get staff-specific working hours for this day
        staff_hours = StaffWorkingHours.objects.filter(
            staff=staff,
            day_of_week=day_of_week,
            is_day_off=False
        ).first()
        
        if staff_hours:
            # Use staff-specific hours
            start_time = staff_hours.start_time
            end_time = staff_hours.end_time
        else:
            # Fall back to company working hours
            working_hours = WorkingHours.objects.filter(
                company=company,
                day_of_week=day_of_week,
                is_day_off=False
            ).first()
            
            if not working_hours:
                return JsonResponse({'available_times': []})
            
            start_time = working_hours.start_time
            end_time = working_hours.end_time
        
        # Get existing bookings for this staff member on this date
        # Exclude the current booking if editing (booking_id parameter)
        booking_id = request.GET.get('booking_id')
        bookings_query = Booking.objects.filter(
            staff=staff,
            date=date,
            status__in=[1]  # Confirmed or PreBooked
        )
        
        if booking_id:
            try:
                bookings_query = bookings_query.exclude(id=int(booking_id))
            except (ValueError, TypeError):
                pass
        
        existing_bookings = bookings_query.values_list('start_time', 'end_time')
        
        # Generate time slots based on company's calendar step setting
        available_times = []
        current_time = datetime.combine(date, start_time)
        end_time_dt = datetime.combine(date, end_time)
        time_step = timedelta(minutes=company.calendar_step_minutes)
        
        # Calculate the end time of the new booking based on service duration + time_for_servicing
        service_duration = timedelta(minutes=service.duration + service.time_for_servicing)
        
        while current_time < end_time_dt:
            time_str = current_time.strftime('%H:%M')
            
            # Calculate when this service would end
            potential_end_time = current_time + service_duration
            
            # Check if the service can fit within working hours
            if potential_end_time > end_time_dt:
                break  # Can't start a service that would end after working hours
            
            # Check if this time slot overlaps with any out-of-office period
            check_start = current_time
            check_end = potential_end_time
            
            # Make timezone-aware if needed
            if StaffOutOfOffice.objects.filter(staff=staff).exists():
                first_period = StaffOutOfOffice.objects.filter(staff=staff).first()
                if timezone.is_aware(first_period.start_datetime):
                    if timezone.is_naive(check_start):
                        check_start = timezone.make_aware(check_start)
                    if timezone.is_naive(check_end):
                        check_end = timezone.make_aware(check_end)
            
            # Skip if booking would overlap with any out-of-office period
            overlapping_periods = StaffOutOfOffice.objects.filter(
                staff=staff,
                start_datetime__lt=check_end,
                end_datetime__gt=check_start
            )
            if overlapping_periods.exists():
                current_time += time_step
                continue
            
            # Check if this time slot would overlap with staff break time
            if staff.break_start and staff.break_end:
                break_start_dt = datetime.combine(date, staff.break_start)
                break_end_dt = datetime.combine(date, staff.break_end)
                # Skip if the booking would overlap with break time
                if current_time < break_end_dt and potential_end_time > break_start_dt:
                    current_time += time_step
                    continue
            
            # Check if this time slot is available (no overlap with existing bookings)
            is_available = True
            for booking_start, booking_end in existing_bookings:
                booking_start_dt = datetime.combine(date, booking_start)
                booking_end_dt = datetime.combine(date, booking_end)
                
                # Check if the new booking would overlap with existing booking
                # Overlap occurs if: new_start < existing_end AND new_end > existing_start
                if current_time < booking_end_dt and potential_end_time > booking_start_dt:
                    is_available = False
                    break
            
            if is_available:
                available_times.append(time_str)
            
            current_time += time_step
        
        return JsonResponse({'available_times': available_times})
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@never_cache
def get_available_dates_any_staff(request, company_id, service_id):
    """API endpoint to get available dates for ANY staff member who can perform the service"""
    try:
        service = get_object_or_404(Service, id=service_id, company_id=company_id)
        company = get_object_or_404(Company, id=company_id)
        staff_members = service.staff_members.filter(is_active=True)
        
        if not staff_members.exists():
            return JsonResponse({'available_dates': []})
        
        available_dates = []
        today = timezone.now().date()
        
        # If service is restricted to specific dates, use those
        if service.restrict_to_available_dates and service.available_dates:
            # Filter available_dates to only future dates
            for date_str in service.available_dates:
                try:
                    date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    if date >= today:
                        day_of_week = date.weekday()
                        # Check if at least one staff member works on this day
                        for staff in staff_members:
                            # Check working days
                            if staff.working_days and day_of_week not in staff.working_days:
                                continue
                            
                            # Check if staff has working hours for this day (either staff-specific or company)
                            staff_hours = StaffWorkingHours.objects.filter(
                                staff=staff,
                                day_of_week=day_of_week,
                                is_day_off=False
                            ).first()
                            
                            # Determine working hours
                            if staff_hours:
                                work_start = datetime.combine(date, staff_hours.start_time)
                                work_end = datetime.combine(date, staff_hours.end_time)
                            else:
                                # Check company hours
                                company_hours = WorkingHours.objects.filter(
                                    company=company,
                                    day_of_week=day_of_week,
                                    is_day_off=False
                                ).first()
                                if not company_hours:
                                    continue
                                work_start = datetime.combine(date, company_hours.start_time)
                                work_end = datetime.combine(date, company_hours.end_time)
                            
                            # Only skip staff if out-of-office covers ENTIRE working day
                            skip_staff = is_staff_out_all_day(staff, date, work_start.time(), work_end.time())
                            
                            if not skip_staff:
                                # At least one staff member is available
                                available_dates.append(date_str)
                                break
                except ValueError:
                    continue
            return JsonResponse({'available_dates': available_dates})
        
        # Otherwise, check next 90 days (3 months) based on working hours
        for i in range(90):
            date = today + timedelta(days=i)
            day_of_week = date.weekday()
            
            # Check if company is open on this day
            working_hours = WorkingHours.objects.filter(
                company=company,
                day_of_week=day_of_week,
                is_day_off=False
            ).first()
            
            if working_hours:
                # Check if ANY staff member is available on this day
                for staff in staff_members:
                    # Check working days
                    if staff.working_days and day_of_week not in staff.working_days:
                        continue
                    
                    # Check if staff has working hours for this day
                    staff_hours = StaffWorkingHours.objects.filter(
                        staff=staff,
                        day_of_week=day_of_week,
                        is_day_off=False
                    ).first()
                    
                    # Determine working hours
                    if staff_hours:
                        work_start = datetime.combine(date, staff_hours.start_time)
                        work_end = datetime.combine(date, staff_hours.end_time)
                    else:
                        work_start = datetime.combine(date, working_hours.start_time)
                        work_end = datetime.combine(date, working_hours.end_time)
                    
                    # Only skip staff if out-of-office covers ENTIRE working day
                    skip_staff = is_staff_out_all_day(staff, date, work_start.time(), work_end.time())
                    
                    if not skip_staff:
                        # Check if staff has working hours for this day
                        staff_hours = StaffWorkingHours.objects.filter(
                            staff=staff,
                            day_of_week=day_of_week,
                            is_day_off=False
                        ).first()
                        
                        # If staff has specific hours, use those; otherwise use company hours
                        if staff_hours or not StaffWorkingHours.objects.filter(staff=staff, day_of_week=day_of_week).exists():
                            # Staff either has specific hours set (and not day off) or no override (use company hours)
                            available_dates.append(date.strftime('%Y-%m-%d'))
                            break  # At least one staff available, add this date
        
        return JsonResponse({'available_dates': available_dates})
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@never_cache
def get_available_times_any_staff(request, company_id, service_id, date_str):
    """API endpoint to get available time slots when ANY staff can perform the service"""
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        service = get_object_or_404(Service, id=service_id, company_id=company_id)
        company = get_object_or_404(Company, id=company_id)
        
        # Get working hours for this day
        day_of_week = date.weekday()
        working_hours = WorkingHours.objects.filter(
            company=company,
            day_of_week=day_of_week,
            is_day_off=False
        ).first()
        
        if not working_hours:
            return JsonResponse({'available_times': []})
        
        # Get all staff who can perform this service
        staff_members = service.staff_members.filter(is_active=True)
        
        if not staff_members.exists():
            return JsonResponse({'available_times': []})
        
        # Generate time slots based on company's calendar step setting
        available_times = []
        current_time = datetime.combine(date, working_hours.start_time)
        end_time = datetime.combine(date, working_hours.end_time)
        time_step = timedelta(minutes=company.calendar_step_minutes)
        service_duration = timedelta(minutes=service.duration + service.time_for_servicing)
        
        while current_time < end_time:
            time_str = current_time.strftime('%H:%M')
            potential_end_time = current_time + service_duration
            
            # Check if the service can fit within working hours
            if potential_end_time > end_time:
                break
            
            # Check if AT LEAST ONE staff member is available at this time
            is_available = False
            for staff in staff_members:
                # Check if staff is out of office during this time slot
                check_start = current_time
                check_end = potential_end_time
                
                # Make timezone-aware if needed
                if StaffOutOfOffice.objects.filter(staff=staff).exists():
                    first_period = StaffOutOfOffice.objects.filter(staff=staff).first()
                    if timezone.is_aware(first_period.start_datetime):
                        if timezone.is_naive(check_start):
                            check_start = timezone.make_aware(check_start)
                        if timezone.is_naive(check_end):
                            check_end = timezone.make_aware(check_end)
                
                # Skip if time slot overlaps with any out-of-office period
                overlapping_periods = StaffOutOfOffice.objects.filter(
                    staff=staff,
                    start_datetime__lt=check_end,
                    end_datetime__gt=check_start
                )
                if overlapping_periods.exists():
                    continue  # Skip this staff member
                
                # Skip staff who don't work on this day
                if staff.working_days and day_of_week not in staff.working_days:
                    continue
                
                # Check staff-specific working hours
                staff_hours = StaffWorkingHours.objects.filter(
                    staff=staff,
                    day_of_week=day_of_week,
                    is_day_off=False
                ).first()
                
                # Determine working hours for this staff member
                if staff_hours:
                    staff_start_time = datetime.combine(date, staff_hours.start_time)
                    staff_end_time = datetime.combine(date, staff_hours.end_time)
                else:
                    # Use company working hours as fallback
                    staff_start_time = datetime.combine(date, working_hours.start_time)
                    staff_end_time = datetime.combine(date, working_hours.end_time)
                
                # Check if this time slot is within staff's working hours
                if current_time < staff_start_time or potential_end_time > staff_end_time:
                    continue
                
                # Check if this time slot would overlap with staff break time
                if staff.break_start and staff.break_end:
                    break_start_dt = datetime.combine(date, staff.break_start)
                    break_end_dt = datetime.combine(date, staff.break_end)
                    # Skip this staff if the booking would overlap with their break time
                    if current_time < break_end_dt and potential_end_time > break_start_dt:
                        continue
                
                # Get existing bookings for this staff member on this date
                existing_bookings = Booking.objects.filter(
                    staff=staff,
                    date=date,
                    status__in=[1]  # Confirmed or PreBooked
                ).values_list('start_time', 'end_time')
                
                # Check if this time slot is available for this staff
                staff_available = True
                for booking_start, booking_end in existing_bookings:
                    booking_start_dt = datetime.combine(date, booking_start)
                    booking_end_dt = datetime.combine(date, booking_end)
                    
                    # Check for overlap
                    if current_time < booking_end_dt and potential_end_time > booking_start_dt:
                        staff_available = False
                        break
                
                if staff_available:
                    is_available = True
                    break  # At least one staff is available
            
            if is_available:
                available_times.append(time_str)
            
            current_time += time_step
        
        return JsonResponse({'available_times': available_times})
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
    
#################### END BOOKING VIEWS #####################


#################### ADMIN VIEWS #####################
@login_required
@subscription_required
def booking_calendar(request):
    """Calendar view for company administrators"""
    try:
        profile = request.user.userprofile
        company = profile.company

        status_in = [1, 3]  # Confirmed and PreBooked
        status = request.GET.get('status')
        if status:
            status_in = [int(status)]
        
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
        
        # We'll render a day-view schedule for `current_date` with columns per staff if user is admin
        if profile.is_admin:
            staff_list = list(Staff.objects.filter(company=company, is_active=True).order_by('name'))
        else:
            staff_list = list(Staff.objects.filter(company=company, id=profile.staff.id, is_active=True))

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
            status__in=status_in
        ).select_related('customer', 'staff', 'service').order_by('start_time')

        # Serialize staff and bookings into JSON-friendly structures
        staff_data = []
        for s in staff_list:
            # Get staff working hours for the current day
            staff_wh = StaffWorkingHours.objects.filter(
                staff=s, 
                day_of_week=current_date.weekday()
            ).first()
            
            staff_info = {
                'id': s.id, 
                'title': s.name,
                'avatar': s.avatar.url if s.avatar else None
            }
            
            # Add working hours for this staff member
            # First check staff-specific hours, then fall back to company hours
            if staff_wh and not staff_wh.is_day_off:
                # Staff has custom working hours for this day
                staff_info['workingHours'] = {
                    'start': staff_wh.start_time.strftime('%H:%M'),
                    'end': staff_wh.end_time.strftime('%H:%M'),
                    'isDayOff': False
                }
            elif working_hours and not working_hours.is_day_off:
                # Fall back to company working hours
                staff_info['workingHours'] = {
                    'start': working_hours.start_time.strftime('%H:%M'),
                    'end': working_hours.end_time.strftime('%H:%M'),
                    'isDayOff': False
                }
            else:
                # Both staff and company have this as a day off
                staff_info['workingHours'] = {
                    'isDayOff': True
                }
            
            staff_data.append(staff_info)

        bookings_data = []
        for b in bookings:
            start_dt = datetime.combine(current_date, b.start_time)
            end_dt = datetime.combine(current_date, b.end_time)
            # Default - Pending
            background_color = '#3b82f6'
            border_color = '#1e40af'
            if int(b.status) == 1:  # Confirmed
                background_color = '#10b981'
                border_color = '#047857'
            elif int(b.status) == 2:  # Cancelled
                background_color = '#ef4444'
                border_color = '#b91c1c'
            elif int(b.status) == 3:  # PreBooked
                background_color = '#f59e0b'
                border_color = '#d97706'
            bookings_data.append({
                'id': b.id,
                'resourceId': b.staff_id,
                'title': f"{b.customer.name} — {b.service.name}",
                'start': start_dt.isoformat(),
                'end': end_dt.isoformat(),
                'backgroundColor': background_color,
                'borderColor': border_color,
                'extendedProps': {
                    'staff_id': b.staff_id,
                    'status': b.status,
                    'service': b.service.name,
                    'customer': b.customer.name,
                    'booking_id': b.id,
                    'client_notes': b.client_notes or '',
                }
            })

        # Calculate occupancy for each staff member
        staff_occupancy = {}
        for staff in staff_list:
            # Get working hours for this staff member (use break times if available)
            staff_working_hours = working_hours
            if not staff_working_hours:
                # Default 8 hours if no working hours defined
                available_minutes = 12 * 60  # 12 hours default
            else:
                # Calculate available time considering breaks
                start_time = datetime.combine(current_date, staff_working_hours.start_time)
                end_time = datetime.combine(current_date, staff_working_hours.end_time)
                total_minutes = int((end_time - start_time).total_seconds() / 60)
                
                # Subtract break time if defined
                break_minutes = 0
                if staff.break_start and staff.break_end:
                    break_start = datetime.combine(current_date, staff.break_start)
                    break_end = datetime.combine(current_date, staff.break_end)
                    break_minutes = int((break_end - break_start).total_seconds() / 60)
                
                available_minutes = total_minutes - break_minutes
            
            # Calculate booked time for this staff member
            staff_bookings = bookings.filter(staff=staff)
            booked_minutes = 0
            for booking in staff_bookings:
                start = datetime.combine(current_date, booking.start_time)
                end = datetime.combine(current_date, booking.end_time)
                booked_minutes += int((end - start).total_seconds() / 60)
            
            # Calculate occupancy percentage
            if available_minutes > 0:
                occupancy = int((booked_minutes / available_minutes) * 100)
            else:
                occupancy = 0
            
            staff_occupancy[staff.id] = occupancy

        context = {
            'company': company,
            'staff_list': staff_list,
            'staff_occupancy': staff_occupancy,
            'resources_json': json.dumps(staff_data),
            'bookings': bookings,
            'events_json': json.dumps(bookings_data),
            'current_date': current_date,
            'day_start': day_start.strftime('%H:%M'),
            'day_end': day_end.strftime('%H:%M'),
            'today': today,
            'calendar_step_minutes': company.calendar_step_minutes,
            'ej_base_license_key': getattr(settings, 'EJ_BASE_LICENSE_KEY', ''),
        }
        
        return render(request, 'bookings/calendar.html', context)
    
    except UserProfile.DoesNotExist:
        messages.error(request, 'User profile not found.')
        return redirect('/')


@login_required
@subscription_required
def calendar_api(request):
    """API endpoint to get calendar data as JSON for date navigation"""
    try:
        profile = request.user.userprofile
        company = profile.company

        status_in = [1, 3]  # Pending and Confirmed
        status = request.GET.get('status')
        if status:
            status_in = [int(status)]
        
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
        
        # Get staff list
        if profile.is_admin:
            staff_list = list(Staff.objects.filter(company=company, is_active=True).order_by('name'))
        else:
            staff_list = list(Staff.objects.filter(company=company, id=profile.staff.id, is_active=True))

        working_hours = WorkingHours.objects.filter(
            company=company, 
            day_of_week=current_date.weekday(),
            is_day_off=False
        ).first()
        if working_hours:
            day_start = working_hours.start_time
            day_end = working_hours.end_time
        else:
            day_start = dtime(hour=8, minute=0)
            day_end = dtime(hour=20, minute=0)

        # Get bookings for the selected date
        bookings = Booking.objects.filter(
            company=company,
            date=current_date,
            status__in=status_in
        ).select_related('customer', 'staff', 'service').order_by('start_time')

        # Serialize bookings into JSON-friendly structures
        bookings_data = []
        for b in bookings:
            start_dt = datetime.combine(current_date, b.start_time)
            end_dt = datetime.combine(current_date, b.end_time)
            # Default - Pending
            background_color = '#3b82f6'
            border_color = '#1e40af'
            if int(b.status) == 1:  # Confirmed
                background_color = '#10b981'
                border_color = '#047857'
            elif int(b.status) == 2:  # Cancelled
                background_color = '#ef4444'
                border_color = '#b91c1c'
            elif int(b.status) == 3:  # PreBooked
                background_color = '#f59e0b'
                border_color = '#d97706'
            bookings_data.append({
                'id': b.id,
                'resourceId': b.staff_id,
                'title': f"{b.customer.name} — {b.service.name}",
                'start': start_dt.isoformat(),
                'end': end_dt.isoformat(),
                'backgroundColor': background_color,
                'borderColor': border_color,
                'extendedProps': {
                    'staff_id': b.staff_id,
                    'status': b.status,
                    'service': b.service.name,
                    'customer': b.customer.name,
                    'booking_id': b.id,
                    'client_notes': b.client_notes or '',
                }
            })

        # Calculate occupancy for each staff member
        staff_occupancy = {}
        for staff in staff_list:
            # Get working hours for this staff member
            staff_working_hours = working_hours
            if not staff_working_hours:
                available_minutes = 12 * 60
            else:
                start_time = datetime.combine(current_date, staff_working_hours.start_time)
                end_time = datetime.combine(current_date, staff_working_hours.end_time)
                total_minutes = int((end_time - start_time).total_seconds() / 60)
                
                break_minutes = 0
                if staff.break_start and staff.break_end:
                    break_start = datetime.combine(current_date, staff.break_start)
                    break_end = datetime.combine(current_date, staff.break_end)
                    break_minutes = int((break_end - break_start).total_seconds() / 60)
                
                available_minutes = total_minutes - break_minutes
            
            # Calculate booked time
            staff_bookings = bookings.filter(staff=staff)
            booked_minutes = 0
            for booking in staff_bookings:
                start = datetime.combine(current_date, booking.start_time)
                end = datetime.combine(current_date, booking.end_time)
                booked_minutes += int((end - start).total_seconds() / 60)
            
            if available_minutes > 0:
                occupancy = int((booked_minutes / available_minutes) * 100)
            else:
                occupancy = 0
            
            staff_occupancy[staff.id] = occupancy

        # Serialize staff data with occupancy and working hours
        staff_data = []
        for s in staff_list:
            # Get staff working hours for the current day
            staff_wh = StaffWorkingHours.objects.filter(
                staff=s, 
                day_of_week=current_date.weekday()
            ).first()
            
            staff_info = {
                'id': s.id,
                'title': s.name,
                'avatar': s.avatar.url if s.avatar else None,
                'occupancy': staff_occupancy.get(s.id, 0)
            }
            
            # Add working hours for this staff member
            # First check staff-specific hours, then fall back to company hours
            if staff_wh and not staff_wh.is_day_off:
                # Staff has custom working hours for this day
                staff_info['workingHours'] = {
                    'start': staff_wh.start_time.strftime('%H:%M'),
                    'end': staff_wh.end_time.strftime('%H:%M'),
                    'isDayOff': False
                }
            elif working_hours and not working_hours.is_day_off:
                # Fall back to company working hours
                staff_info['workingHours'] = {
                    'start': working_hours.start_time.strftime('%H:%M'),
                    'end': working_hours.end_time.strftime('%H:%M'),
                    'isDayOff': False
                }
            else:
                # Both staff and company have this as a day off
                staff_info['workingHours'] = {
                    'isDayOff': True
                }
            
            staff_data.append(staff_info)

        return JsonResponse({
            'bookings': bookings_data,
            'staff': staff_data,
            'dayStart': day_start.strftime('%H:%M'),
            'dayEnd': day_end.strftime('%H:%M'),
            'calendarStepMinutes': company.calendar_step_minutes
        })
    
    except Exception as e:
        logger.error(f"Calendar API error: {e}")
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@subscription_required
def edit_booking(request, booking_id):
    """Edit an existing booking"""
    try:
        profile = request.user.userprofile
           
        if profile.is_admin:
            staff_list = Staff.objects.filter(company=profile.company, is_active=True)
            services = Service.objects.filter(company=profile.company, is_active=True)
        else:
            staff_list = Staff.objects.filter(company=profile.company, id=profile.staff.id, is_active=True)
            services = Service.objects.filter(company=profile.company, is_active=True)

        booking = get_object_or_404(Booking, id=booking_id, company=profile.company)
        
        if request.method == 'POST':
            form = BookingForm(request.POST, instance=booking, company=profile.company, user=request.user)
            if form.is_valid():
                form.save()

                # Send notification email to customer about booking update (only if they have email)
                if booking.customer.email:
                    booking_link = request.build_absolute_uri(
                        redirect('booking_confirmation', booking_id=booking.id).url
                    )
                    subject = 'Your Booking Has Been Updated'
                    html_message = render_to_string('email/booking_update.html', {
                        'booking': booking,
                        'booking_link': booking_link,
                        'company': profile.company,
                        'current_year': timezone.now().year,
                    })
                    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None)
                    recipient_list = [booking.customer.email]
                    email_log = EmailLog.objects.create(
                        recipient_email=booking.customer.email,
                        subject=subject,
                        email_type='booking_update',
                        status='pending'
                    )
                    try:
                        msg = EmailMultiAlternatives(subject, '', from_email, recipient_list)
                        msg.attach_alternative(html_message, "text/html")
                        msg.send()
                        email_log.status = 'sent'
                        email_log.sent_at = timezone.now()
                        email_log.save()
                    except Exception as e:
                        email_log.status = 'failed'
                        email_log.error_message = str(e)
                        email_log.save()
                        logger.error(f"Failed to send booking update email: {e}")
                
                messages.success(request, 'Booking updated successfully.')
                return redirect('booking_calendar')
        else:
            form = BookingForm(instance=booking, company=profile.company, user=request.user)
        
        context = {
            'form': form,
            'booking': booking,
            'company': profile.company,
            'staff_list': staff_list,
            'services': services,
            'booking_phone': booking.booking_phone
        }
        
        return render(request, 'bookings/edit_booking.html', context)
    
    except UserProfile.DoesNotExist:
        messages.error(request, 'User profile not found.')
        return redirect('/')


@login_required
@subscription_required
def update_booking_status(request, booking_id):
    """Update booking status (confirm or cancel)"""
    try:
        profile = request.user.userprofile
           
        if profile.is_admin:
            booking = get_object_or_404(Booking, id=booking_id, company=profile.company)
        else:
            booking = get_object_or_404(Booking, id=booking_id, company=profile.company, staff=profile.staff)
        
        if request.method == 'POST':
            status = json.loads(request.body).get('status')
            if status in ['0', '1', '2']:
                booking.status = status
                booking.save()
                return JsonResponse({'success': True, 'status': booking.get_status_display()})
        
        return JsonResponse({'error': 'Invalid request'}, status=400)
    
    except UserProfile.DoesNotExist:
        return JsonResponse({'error': 'User profile not found'}, status=403)
    

@login_required
@subscription_required
def guess_customer_data(request):
    """API endpoint to guess customer data based on phone or name input"""
    try:
        phone = request.GET.get('phone', '')
        name = request.GET.get('name', '')
        
        customers = Customer.objects.all()
        
        if phone:
            customers = customers.filter(phone__icontains=phone)
        elif name:
            customers = customers.filter(name__icontains=name)
        else:
            return JsonResponse({'customers': []})
        
        customers = customers.order_by('-id')[:7]
        customers_list = []
        for c in customers:
            customers_list.append({
                # 'country_code': c.country_code,
                'name': c.name,
                'email': c.email,
                'phone': c.phone,
            })
        return JsonResponse({'customers': customers_list})

    except UserProfile.DoesNotExist:
        return JsonResponse({'error': 'User profile not found'}, status=403)

@csrf_exempt
@login_required
@subscription_required
def update_booking_ajax(request, booking_id):
    """AJAX endpoint to move a booking (change staff and/or start time). Expects POST with `staff_id` and `start_time` (HH:MM)."""
    try:
        profile = request.user.userprofile
        if profile.is_admin:
            booking = get_object_or_404(Booking, id=booking_id, company=profile.company)
        else:
            booking = get_object_or_404(Booking, id=booking_id, company=profile.company, staff=profile.staff)

        if request.method != 'POST':
            return JsonResponse({'error': f'Invalid method: {request.method}, Content-Type: {request.content_type}'}, status=400)

        try:
            data = json.loads(request.body)
            start_time_str = data.get('start_time')
            end_time_str = data.get('end_time')
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        if not start_time_str or not end_time_str:
            return JsonResponse({'error': 'Missing parameters'}, status=400)

        try:
            sh, sm = map(int, start_time_str.split(':'))
            new_start = dtime(hour=sh, minute=sm)
            eh, em = map(int, end_time_str.split(':'))
            new_end = dtime(hour=eh, minute=em)
        except Exception:
            return JsonResponse({'error': 'Invalid start_time format'}, status=400)

        booking.start_time = new_start
        booking.end_time = new_end
        booking.save()

        # Send email notification for booking update (only if customer has email)
        if booking.customer.email:
            booking_link = request.build_absolute_uri(
                redirect('booking_confirmation', booking_id=booking.id).url
            )
            subject = 'Your Booking Has Been Updated'
            html_message = render_to_string('email/booking_update.html', {
                'booking': booking,
                'booking_link': booking_link,
                'company': profile.company,
                'current_year': timezone.now().year,
            })
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None)
            recipient_list = [booking.customer.email]
            email_log = EmailLog.objects.create(
                recipient_email=booking.customer.email,
                subject=subject,
                email_type='booking_update',
                status='pending'
            )
            try:
                msg = EmailMultiAlternatives(subject, '', from_email, recipient_list)
                msg.attach_alternative(html_message, "text/html")
                msg.send()
                email_log.status = 'sent'
                email_log.sent_at = timezone.now()
                email_log.save()
            except Exception as e:
                email_log.status = 'failed'
                email_log.error_message = str(e)
                email_log.save()
                logger.error(f"Failed to send booking update email: {e}")
        
        return JsonResponse({'success': True, 'start_time': booking.start_time.strftime('%H:%M'), 'end_time': booking.end_time.strftime('%H:%M'), 'staff_id': booking.staff_id})

    except UserProfile.DoesNotExist:
        return JsonResponse({'error': 'User profile not found'}, status=403)


@login_required
@subscription_required
def update_booking_notes(request, booking_id):
    """AJAX endpoint to auto-save booking notes"""
    try:
        profile = request.user.userprofile
        if profile.is_admin:
            booking = get_object_or_404(Booking, id=booking_id, company=profile.company)
        else:
            booking = get_object_or_404(Booking, id=booking_id, company=profile.company, staff=profile.staff)

        if request.method != 'GET':
            return JsonResponse({'error': 'Invalid method'}, status=400)

        notes = request.GET.get('notes', '')
        booking.notes = notes
        booking.save()

        return JsonResponse({'success': True, 'message': 'Notes saved'})

    except UserProfile.DoesNotExist:
        return JsonResponse({'error': 'User profile not found'}, status=403)


@csrf_exempt
@login_required
@subscription_required
def delete_booking_ajax(request, booking_id):
    """AJAX endpoint to delete a booking"""
    try:
        profile = request.user.userprofile
        if profile.is_admin:
            booking = get_object_or_404(Booking, id=booking_id, company=profile.company)
        else:
            booking = get_object_or_404(Booking, id=booking_id, company=profile.company, staff=profile.staff)

        if request.method != 'DELETE':
            return JsonResponse({'error': f'Invalid method: {request.method}'}, status=400)

        booking.delete()
        return JsonResponse({'success': True})

    except UserProfile.DoesNotExist:
        return JsonResponse({'error': 'User profile not found'}, status=403)


@login_required
@subscription_required
def confirm_prebooked_booking(request, booking_id):
    """Staff/Admin view to confirm a prebooked booking with duration and price"""
    booking = get_object_or_404(Booking, id=booking_id, status=3)  # PreBooked status
    
    try:
        profile = request.user.userprofile
        # Check permission - only admin or staff assigned to this booking
        if not profile.is_admin and profile.staff != booking.staff:
            messages.error(request, 'You do not have permission to confirm this booking.')
            return redirect('/')
    except UserProfile.DoesNotExist:
        messages.error(request, 'User profile not found.')
        return redirect('/')
    
    if request.method == 'POST':
        duration = request.POST.get('duration')
        price = request.POST.get('price')
        
        if not duration or not price:
            messages.error(request, 'Duration and price are required.')
            return redirect('confirm_prebooked_booking', booking_id=booking_id)
        
        try:
            duration = int(duration)
            price = float(price)
            
            # Calculate end time based on duration
            from datetime import datetime, timedelta
            start = datetime.combine(booking.date, booking.start_time)
            end = start + timedelta(minutes=duration)
            
            booking.duration = duration
            booking.price = price
            booking.end_time = end.time()
            booking.status = 1  # Confirmed
            booking.confirmed_at = timezone.now()
            booking.confirmed_by = request.user
            booking.save()
            
            messages.success(request, 'Booking confirmed successfully!')
            return redirect('bookings_list')
        except (ValueError, TypeError):
            messages.error(request, 'Invalid duration or price format.')
            return redirect('confirm_prebooked_booking', booking_id=booking_id)
    
    context = {
        'booking': booking,
    }
    return render(request, 'bookings/confirm_prebooked.html', context)


@login_required
@subscription_required
def bookings_list(request):
    """List of bookings for staff/admin"""
    try:
        profile = request.user.userprofile
        # Base queryset
        if profile.is_admin:
            bookings = Booking.objects.filter(company=profile.company).select_related('customer', 'staff', 'service')
        else:
            bookings = Booking.objects.filter(company=profile.company, staff=profile.staff).select_related('customer', 'staff', 'service')

        # Tabs: status filter
        status_filter = request.GET.get('status', 'confirmed')
        if status_filter == 'confirmed':
            bookings = bookings.filter(status=1)  # Confirmed
        elif status_filter == 'prebooked':
            bookings = bookings.filter(status=3)  # PreBooked

        # Search
        search_query = request.GET.get('search', '').strip()
        if search_query:
            bookings = bookings.filter(
                Q(customer__name__icontains=search_query) |
                Q(customer__phone__icontains=search_query) |
                Q(customer__email__icontains=search_query)
            )

        # Filter by date range
        date_from = request.GET.get('date_from', '').strip()
        date_to = request.GET.get('date_to', '').strip()
        from datetime import datetime
        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
                bookings = bookings.filter(date__gte=date_from_obj)
            except Exception:
                pass
        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
                bookings = bookings.filter(date__lte=date_to_obj)
            except Exception:
                pass

        # Filter by service
        service_filter = request.GET.get('service', '').strip()
        if service_filter:
            bookings = bookings.filter(service__id=service_filter)

        bookings = bookings.order_by('-date', '-start_time')

        # Pagination
        from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
        page = request.GET.get('page', 1)
        paginator = Paginator(bookings, 25)
        try:
            bookings_page = paginator.page(page)
        except (PageNotAnInteger, EmptyPage):
            bookings_page = paginator.page(1)

        # For service filter dropdown
        services = Service.objects.filter(company=profile.company, is_active=True)

        context = {
            'bookings': bookings_page,
            'company': profile.company,
            'search_query': search_query,
            'date_from': date_from,
            'date_to': date_to,
            'service_filter': service_filter,
            'services': services,
            'status_filter': status_filter,
        }
        return render(request, 'bookings/bookings_list.html', context)
    except UserProfile.DoesNotExist:
        messages.error(request, 'User profile not found.')
        return redirect('/')