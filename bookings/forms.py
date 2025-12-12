from django import forms
from .models import Booking, Customer
from companies.models import Company, Staff, Service
from django.utils import timezone
from datetime import datetime, timedelta


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
            self.fields['service'].queryset = Service.objects.filter(company=company, active=True)
            self.fields['staff'].queryset = Staff.objects.filter(company=company, is_active=True)
            self.company = company

    def clean_date(self):
        date = self.cleaned_data.get('date')
        if date and date < timezone.now().date():
            raise forms.ValidationError("Cannot book in the past.")
        return date

    def save(self, commit=True):
        booking = super().save(commit=False)
        
        # Get or create customer
        customer, created = Customer.objects.get_or_create(
            phone=self.cleaned_data['customer_phone'],
            defaults={
                'name': self.cleaned_data['customer_name'],
                'email': self.cleaned_data.get('customer_email', '')
            }
        )
        
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
