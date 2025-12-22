from datetime import datetime, timedelta
from django import forms
from django.utils import timezone
from .models import Booking, Customer
from companies.models import Company, Staff, Service


class BookingForm(forms.ModelForm):
    customer_name = forms.CharField(max_length=255, required=True)
    customer_phone = forms.CharField(max_length=50, required=True)
    customer_email = forms.EmailField(required=False)
    
    class Meta:
        model = Booking
        fields = ['service', 'staff', 'date', 'start_time']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
        }

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        if company:
            self.fields['service'].queryset = Service.objects.filter(company=company, is_active=True)
            self.fields['staff'].queryset = Staff.objects.filter(company=company, is_active=True)
            self.company = company
        
        # When editing existing booking, customer fields are not required (read-only in template)
        if self.instance and self.instance.pk:
            self.fields['customer_name'].required = False
            self.fields['customer_phone'].required = False
            self.fields['customer_email'].required = False
            
            # Pre-populate customer fields if editing existing booking
            if hasattr(self.instance, 'customer'):
                self.fields['customer_name'].initial = self.instance.customer.name
                self.fields['customer_phone'].initial = self.instance.customer.phone
                self.fields['customer_email'].initial = self.instance.customer.email

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
                }
            )
            
            # Update customer info if it changed
            if not created:
                customer.name = self.cleaned_data['customer_name']
                customer.email = self.cleaned_data.get('customer_email', '')
                customer.save()
            
            booking.customer = customer
            booking.company = self.company
        
        # Calculate end time based on service duration
        service = self.cleaned_data['service']
        start_datetime = datetime.combine(
            self.cleaned_data['date'],
            self.cleaned_data['start_time']
        )
        end_datetime = start_datetime + timedelta(minutes=service.duration)
        booking.end_time = end_datetime.time()
        
        if commit:
            booking.save()
        
        return booking
