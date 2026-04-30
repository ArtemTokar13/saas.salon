"""
Booking Handler - Find availability and create bookings
"""
import logging
from datetime import datetime, timedelta, time as dtime
from hashlib import md5
from django.utils import timezone
from django.db.models import Q
from fuzzywuzzy import fuzz
from companies.models import Company, Service, Staff, WorkingHours, StaffOutOfOffice
from bookings.models import Booking, Customer
from bookings.utils import normalize_phone_number
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
        Find service by name using fuzzy matching with multilingual support
        """
        if not service_name or not company:
            return None
        
        services = Service.objects.filter(company=company, is_active=True)
        
        # Translation mapping for common service terms
        translations = {
            'маникюр': 'manicura',
            'манікюр': 'manicura',
            'педикюр': 'pedicura',
            'педікюр': 'pedicura',
            'стрижка': 'corte',
            'окрашивание': 'tinte',
            'фарбування': 'tinte',
            'японский': 'japonesa',
            'японська': 'japonesa',
            'полуперманентный': 'semipermanente',
            'напівперманентний': 'semipermanente',
            'без покрытия': 'sin pintar',
            'без покриття': 'sin pintar',
            'наращивание': 'extensión',
            'нарощування': 'extensión',
            'ногтей': 'uñas',
            'нігтів': 'uñas',
        }
        
        # Normalize search term and translate
        search_normalized = service_name.lower().strip()
        
        # Apply translations
        for ru_term, es_term in translations.items():
            search_normalized = search_normalized.replace(ru_term, es_term)
        
        # Remove parentheses
        search_normalized = search_normalized.replace('(', '').replace(')', '')
        
        logger.info(f"AI extracted: '{service_name}' → Normalized: '{search_normalized}'")
        
        # Try exact match first
        for service in services:
            service_normalized = service.name.replace('(', '').replace(')', '').lower().strip()
            if search_normalized == service_normalized:
                logger.info(f"✓ Exact match: {service.name}")
                return service
        
        # Fuzzy matching
        best_match = None
        best_score = 0
        
        for service in services:
            service_normalized = service.name.replace('(', '').replace(')', '').lower().strip()
            score = fuzz.token_sort_ratio(search_normalized, service_normalized)
            
            logger.info(f"  '{service.name}' = {score}%")
            
            if score > best_score:
                best_score = score
                best_match = service
        
        if best_score >= 75:
            logger.info(f"✓ Best fuzzy match: {best_match.name} ({best_score}%)")
            return best_match
        
        logger.warning(f"✗ No match found for: '{search_normalized}'")
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
        
        logger.info(f"Searching availability for '{service.name}' on {date}")
        
        if not staff_members.exists():
            # If no staff assigned to service, check all staff
            staff_members = Staff.objects.filter(company=company, is_active=True)
            logger.info(f"No staff assigned to service, checking all {staff_members.count()} staff")
        else:
            logger.info(f"Found {staff_members.count()} staff for this service")
        
        for staff in staff_members:
            slots = self._get_staff_available_times(staff, service, date)
            logger.info(f"  {staff.name}: {len(slots)} slots")
            
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
        logger.info(f"    Checking {staff.name} for {date} (weekday={day_of_week})")
        
        # Check if staff works on this day
        if staff.working_days and day_of_week not in staff.working_days:
            logger.info(f"    ✗ {staff.name} doesn't work on day {day_of_week}. Working days: {staff.working_days}")
            return []
        
        # Check if staff is out of office (legacy fields - for backward compatibility)
        if staff.out_of_office:
            if staff.out_of_office_start and staff.out_of_office_end:
                # Convert to date if these are datetime fields
                out_start = staff.out_of_office_start if isinstance(staff.out_of_office_start, datetime) else datetime.combine(staff.out_of_office_start, dtime.min)
                out_end = staff.out_of_office_end if isinstance(staff.out_of_office_end, datetime) else datetime.combine(staff.out_of_office_end, dtime.max)
                
                check_datetime_start = datetime.combine(date, dtime.min)
                check_datetime_end = datetime.combine(date, dtime.max)
                
                # Make timezone-aware if needed
                if timezone.is_aware(out_start):
                    check_datetime_start = timezone.make_aware(check_datetime_start)
                    check_datetime_end = timezone.make_aware(check_datetime_end)
                
                # Check if the date falls within the out-of-office period
                if out_start <= check_datetime_end and out_end >= check_datetime_start:
                    logger.info(f"    ✗ {staff.name} is out of office (legacy) {staff.out_of_office_start} to {staff.out_of_office_end}")
                    return []
        
        # Check if staff is out of office using the new StaffOutOfOffice model
        # This checks if the staff has any out-of-office periods that overlap with this date
        date_start = datetime.combine(date, dtime.min)
        date_end = datetime.combine(date, dtime.max)
        
        # Make timezone-aware if needed
        if StaffOutOfOffice.objects.filter(staff=staff).exists():
            first_period = StaffOutOfOffice.objects.filter(staff=staff).first()
            if timezone.is_aware(first_period.start_datetime):
                date_start = timezone.make_aware(date_start)
                date_end = timezone.make_aware(date_end)
        
        # Check if any out-of-office period overlaps with this entire day
        overlapping_periods = StaffOutOfOffice.objects.filter(
            staff=staff,
            start_datetime__lte=date_end,
            end_datetime__gte=date_start
        )
        
        if overlapping_periods.exists():
            # Staff has at least one out-of-office period that overlaps with this day
            # For simplicity, we'll exclude the entire day if any part is blocked
            # TODO: In the future, could check individual time slots against out-of-office periods
            period = overlapping_periods.first()
            logger.info(f"    ✗ {staff.name} is out of office from {period.start_datetime.strftime('%Y-%m-%d %H:%M')} to {period.end_datetime.strftime('%Y-%m-%d %H:%M')}")
            return []
        
        # Get working hours for this day
        # First check staff-specific hours, then fall back to company hours
        from companies.models import StaffWorkingHours
        
        staff_hours = StaffWorkingHours.objects.filter(
            staff=staff,
            day_of_week=day_of_week,
            is_day_off=False
        ).first()
        
        if staff_hours:
            # Use staff-specific working hours
            working_hours = staff_hours
            logger.info(f"    Using staff-specific hours: {working_hours.start_time} - {working_hours.end_time}")
        else:
            # Fall back to company working hours
            working_hours = WorkingHours.objects.filter(
                company=staff.company,
                day_of_week=day_of_week,
                is_day_off=False
            ).first()
            if working_hours:
                logger.info(f"    Using company hours: {working_hours.start_time} - {working_hours.end_time}")
        
        if not working_hours:
            logger.info(f"    ✗ No working hours found for day {day_of_week}")
            return []
        
        if hasattr(working_hours, 'is_day_off') and working_hours.is_day_off:
            logger.info(f"    ✗ Day marked as day off")
            return []
        
        # Get existing bookings
        existing_bookings = Booking.objects.filter(
            staff=staff,
            date=date,
            status__in=[1, 3]  # Confirmed or PreBooked
        ).values_list('start_time', 'end_time')
        
        logger.info(f"    Found {len(existing_bookings)} existing bookings")
        
        # Generate time slots
        available_times = []
        current_time = datetime.combine(date, working_hours.start_time)
        end_time = datetime.combine(date, working_hours.end_time)
        
        service_duration = timedelta(minutes=service.duration + service.time_for_servicing)
        logger.info(f"    Service duration: {service.duration + service.time_for_servicing} minutes")
        
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
        
        logger.info(f"    ✓ Generated {len(available_times)} available slots for {staff.name}")
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
        # Find or create customer (use filter().first() to handle duplicates)
        customer = Customer.objects.filter(phone=customer_phone).first()
        
        if customer:
            # Update customer info if needed
            if not customer.name or customer.name == customer_phone:
                customer.name = customer_name
            if customer_email:
                customer.email = customer_email
            customer.save()
        else:
            # Create new customer
            customer = Customer.objects.create(
                phone=customer_phone,
                name=customer_name,
                email=customer_email or ''
            )
        
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
            created_by='whatsapp',
            notes=f"Booking created via WhatsApp on {timezone.now().strftime('%Y-%m-%d %H:%M')}",
            booking_phone=normalize_phone_number(customer_phone, customer.country_code),  # Store normalized phone
            booking_country_code=customer.country_code  # Store country code
        )
        
        logger.info(f"Created booking: {booking.id} for {customer_name}")
        return booking
