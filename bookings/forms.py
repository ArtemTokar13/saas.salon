from datetime import datetime, timedelta
from django import forms
from django.utils import timezone
from django.utils.translation import gettext as _
from .models import Booking, Customer, COUNTRY_CHOICES
from companies.models import Company, Staff, Service


class BookingForm(forms.ModelForm):
    customer_name = forms.CharField(max_length=255, required=True)
    customer_phone = forms.CharField(max_length=50, required=True)
    customer_email = forms.EmailField(required=False)
    customer_country_code = forms.ChoiceField(
        choices=[('', _('Select Country'))] + list(COUNTRY_CHOICES), 
        required=True, 
        initial='ES'
    )
    
    class Meta:
        model = Booking
        fields = ['service', 'staff', 'date', 'start_time', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'notes': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': _('Add any notes about this booking...'),
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent'
            }),
        }

    def __init__(self, *args, company=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if company:
            self.fields['service'].queryset = Service.objects.filter(company=company, is_active=True)
            self.fields['staff'].queryset = Staff.objects.filter(company=company, is_active=True)
            self.fields['staff'].required = False  # Make staff optional
            self.company = company
        
        if user and user.is_authenticated and user.userprofile.company == company:
            self.fields['duration'] = forms.IntegerField(required=False, help_text="Duration in minutes")
            self.user = user

        # When editing existing booking, customer fields are not required (read-only in template)
        if self.instance and self.instance.pk:
            self.fields['customer_name'].required = False
            self.fields['customer_phone'].required = False
            self.fields['customer_email'].required = False
            self.fields['customer_country_code'].required = False
            
            # Pre-populate customer fields if editing existing booking
            if hasattr(self.instance, 'customer'):
                self.fields['customer_name'].initial = self.instance.customer.name
                self.fields['customer_phone'].initial = self.instance.customer.phone
                self.fields['customer_email'].initial = self.instance.customer.email
                self.fields['customer_country_code'].initial = self.instance.customer.country_code

    def clean_date(self):
        date = self.cleaned_data.get('date')
        # Allow past dates when editing existing bookings
        if date and date < timezone.now().date() and not self.instance.pk:
            raise forms.ValidationError("Cannot book in the past.")
        return date

    def save(self, commit=True):
        booking = super().save(commit=False)
        
        # If editing existing booking, keep the existing customer
        if self.instance.pk:
            # Customer stays the same, just update booking details
            pass
        else:
            # New booking - get or create customer
            customer, created = Customer.objects.get_or_create(
                phone=self.cleaned_data['customer_phone'],
                defaults={
                    'name': self.cleaned_data['customer_name'],
                    'email': self.cleaned_data.get('customer_email', ''),
                    'country_code': self.cleaned_data.get('customer_country_code', ''),
                }
            )
            
            # Update customer info if it changed
            if not created:
                customer.name = self.cleaned_data['customer_name']
                customer.email = self.cleaned_data.get('customer_email', '')
                customer.country_code = self.cleaned_data.get('customer_country_code', '')
                customer.save()
            
            booking.customer = customer
            booking.company = self.company
        
        # Calculate end time based on service duration or overridden duration (if provided)
        service = self.cleaned_data['service']
        start_datetime = datetime.combine(
            self.cleaned_data['date'],
            self.cleaned_data['start_time']
        )

        # If a duration field was provided in the form and filled, use it
        duration = None
        if 'duration' in self.fields:
            try:
                duration = self.cleaned_data.get('duration')
                if duration in (None, ''):
                    duration = None
                else:
                    duration = int(duration)
            except Exception:
                duration = None

        if not duration:
            duration = service.duration

        end_datetime = start_datetime + timedelta(minutes=duration)
        booking.end_time = end_datetime.time()
        booking.duration = duration

        if hasattr(self, 'user') and self.user.is_authenticated and (hasattr(self.user, 'userprofile') and self.user.userprofile.company == self.company):
            booking.status = 1  # Auto-confirm for staff users
        
        # Auto-assign staff if not selected
        if not self.cleaned_data.get('staff'):
            from companies.models import WorkingHours
            date = self.cleaned_data['date']
            start_time = self.cleaned_data['start_time']
            
            # Find available staff who can perform this service
            available_staff = self._find_available_staff(
                service, 
                date, 
                start_datetime, 
                end_datetime
            )
            
            if available_staff:
                booking.staff = available_staff[0]  # Assign first available
            else:
                raise forms.ValidationError(
                    "No staff available for the selected date and time. Please choose a different time."
                )
        
        if commit:
            booking.save()
        
        return booking
    
    def _find_available_staff(self, service, date, start_datetime, end_datetime):
        """Find staff members who can perform the service and are available at the given time"""
        from companies.models import WorkingHours
        
        # Get all staff who can perform this service
        staff_members = service.staff_members.filter(is_active=True)
        available_staff = []
        
        for staff in staff_members:
            # Check if staff is working on this day
            day_of_week = date.weekday()
            working_hours = WorkingHours.objects.filter(
                company=self.company,
                day_of_week=day_of_week,
                is_day_off=False
            ).first()
            
            if not working_hours:
                continue
            
            # Check if time is within working hours
            if (start_datetime.time() < working_hours.start_time or 
                end_datetime.time() > working_hours.end_time):
                continue
            
            # Check if staff has any conflicting bookings
            conflicting = Booking.objects.filter(
                staff=staff,
                date=date,
                status__in=[0, 1]  # Pending or Confirmed
            ).exclude(pk=self.instance.pk if self.instance.pk else None)
            
            has_conflict = False
            for booking in conflicting:
                booking_start = datetime.combine(date, booking.start_time)
                booking_end = datetime.combine(date, booking.end_time)
                
                # Check for overlap
                if start_datetime < booking_end and end_datetime > booking_start:
                    has_conflict = True
                    break
            
            if not has_conflict:
                available_staff.append(staff)
        
        return available_staff
