"""
Booking Handler - Find availability and create bookings
"""
import logging
from datetime import datetime, timedelta, time as dtime
from hashlib import md5
from django.utils import timezone
from django.db.models import Q
from fuzzywuzzy import fuzz
from companies.models import Company, Service, Staff, WorkingHours
from bookings.models import Booking, Customer

logger = logging.getLogger(__name__)


class BookingSearcher:
    """Search for available booking slots"""
    
    def find_company(self, company_name: str) -> Company:
        """
        Find company by name using fuzzy matching
        """
        if not company_name:
            return None
        
        companies = Company.objects.filter(online_appointments_enabled=True)
        
        # Try exact match first
        exact = companies.filter(name__iexact=company_name).first()
        if exact:
            return exact
        
        # Fuzzy matching
        best_match = None
        best_score = 0
        
        for company in companies:
            score = fuzz.ratio(company_name.lower(), company.name.lower())
            if score > best_score:
                best_score = score
                best_match = company
        
        # Return if confidence is high enough
        if best_score > 70:
            return best_match
        
        return None
    
    def find_service(self, company: Company, service_name: str) -> Service:
        """
        Find service by name using fuzzy matching
        """
        if not service_name or not company:
            return None
        
        services = Service.objects.filter(company=company, is_active=True)
        
        # Try exact match
        exact = services.filter(name__iexact=service_name).first()
        if exact:
            return exact
        
        # Fuzzy matching
        best_match = None
        best_score = 0
        
        for service in services:
            score = fuzz.ratio(service_name.lower(), service.name.lower())
            if score > best_score:
                best_score = score
                best_match = service
        
        if best_score > 60:  # Lower threshold for services
            return best_match
        
        return None
    
    def find_available_slots(self, company: Company, service: Service, 
                            date: datetime.date, time_preference: str = None) -> list:
        """
        Find available time slots for a service on a specific date
        
        Returns list of dicts:
        [
            {
                'time': '14:00',
                'staff': 'Maria',
                'staff_id': 1,
                'price': 25.00,
                'duration': 30,
                'end_time': '14:30'
            },
            ...
        ]
        """
        available_slots = []
        
        # Get staff who can perform this service
        staff_members = Staff.objects.filter(
            company=company,
            is_active=True,
            services=service
        )
        
        if not staff_members.exists():
            # If no staff assigned to service, check all staff
            staff_members = Staff.objects.filter(company=company, is_active=True)
        
        for staff in staff_members:
            slots = self._get_staff_available_times(staff, service, date)
            
            # Filter by time preference if specified
            if time_preference:
                slots = self._filter_by_time_preference(slots, time_preference)
            
            available_slots.extend(slots)
        
        # Sort by time
        available_slots.sort(key=lambda x: x['time'])
        
        return available_slots
    
    def _get_staff_available_times(self, staff: Staff, service: Service, date: datetime.date) -> list:
        """Get available time slots for a specific staff member"""
        day_of_week = date.weekday()
        
        # Check if staff works on this day
        if staff.working_days and day_of_week not in staff.working_days:
            return []
        
        # Check if staff is out of office
        if staff.out_of_office:
            if staff.out_of_office_start and staff.out_of_office_end:
                if staff.out_of_office_start <= date <= staff.out_of_office_end:
                    return []
        
        # Get working hours for this day
        working_hours = WorkingHours.objects.filter(
            company=staff.company,
            day_of_week=day_of_week,
            is_day_off=False
        ).first()
        
        if not working_hours:
            return []
        
        # Get existing bookings
        existing_bookings = Booking.objects.filter(
            staff=staff,
            date=date,
            status__in=[1, 3]  # Confirmed or PreBooked
        ).values_list('start_time', 'end_time')
        
        # Generate time slots
        available_times = []
        current_time = datetime.combine(date, working_hours.start_time)
        end_time = datetime.combine(date, working_hours.end_time)
        
        service_duration = timedelta(minutes=service.duration + service.time_for_servicing)
        
        while current_time < end_time:
            potential_end_time = current_time + service_duration
            
            if potential_end_time > end_time:
                break
            
            # Check break time
            if staff.break_start and staff.break_end:
                break_start_dt = datetime.combine(date, staff.break_start)
                break_end_dt = datetime.combine(date, staff.break_end)
                if current_time < break_end_dt and potential_end_time > break_start_dt:
                    current_time += timedelta(minutes=30)
                    continue
            
            # Check existing bookings
            is_available = True
            for booking_start, booking_end in existing_bookings:
                booking_start_dt = datetime.combine(date, booking_start)
                booking_end_dt = datetime.combine(date, booking_end)
                
                if current_time < booking_end_dt and potential_end_time > booking_start_dt:
                    is_available = False
                    break
            
            if is_available:
                available_times.append({
                    'time': current_time.strftime('%H:%M'),
                    'staff': staff.name,
                    'staff_id': staff.id,
                    'price': float(service.price),
                    'duration': service.duration,
                    'end_time': potential_end_time.strftime('%H:%M')
                })
            
            current_time += timedelta(minutes=30)
        
        return available_times
    
    def _filter_by_time_preference(self, slots: list, preference: str) -> list:
        """Filter slots by time preference"""
        if preference == 'morning':
            return [s for s in slots if int(s['time'].split(':')[0]) < 12]
        elif preference == 'afternoon':
            # Afternoon = 14:00-18:00 (after lunch)
            return [s for s in slots if 14 <= int(s['time'].split(':')[0]) < 18]
        elif preference == 'evening':
            return [s for s in slots if int(s['time'].split(':')[0]) >= 18]
        return slots
    
    def create_booking(self, company: Company, service: Service, staff_id: int,
                      customer_phone: str, customer_name: str, 
                      booking_date: datetime.date, booking_time: str,
                      customer_email: str = None) -> Booking:
        """
        Create a new booking
        """
        # Get or create customer
        customer, created = Customer.objects.get_or_create(
            phone=customer_phone,
            defaults={'name': customer_name, 'email': customer_email}
        )
        
        # Update customer info if needed
        if not customer.name or customer.name == customer_phone:
            customer.name = customer_name
            customer.save()
        
        # Get staff
        staff = Staff.objects.get(id=staff_id, company=company)
        
        # Parse time
        hour, minute = map(int, booking_time.split(':'))
        start_time = dtime(hour, minute)
        
        # Calculate end time
        duration = timedelta(minutes=service.duration + service.time_for_servicing)
        end_datetime = datetime.combine(booking_date, start_time) + duration
        end_time = end_datetime.time()
        
        # Generate delete_code for cancellation link
        delete_code = md5(f"{customer.email if customer.email else customer.phone}{timezone.now().timestamp()}".encode()).hexdigest()
        
        # Create booking
        booking = Booking.objects.create(
            company=company,
            staff=staff,
            service=service,
            customer=customer,
            date=booking_date,
            start_time=start_time,
            end_time=end_time,
            duration=service.duration,
            price=service.price,
            status=1 if not service.need_staff_confirmation else 3,  # Confirmed or PreBooked
            delete_code=delete_code,
            notes=f"Booking created via WhatsApp on {timezone.now().strftime('%Y-%m-%d %H:%M')}"
        )
        
        logger.info(f"Created booking: {booking.id} for {customer_name}")
        return booking
