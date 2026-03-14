"""
Tests for WhatsApp bot
"""
from django.test import TestCase
from django.utils import timezone
from datetime import datetime, timedelta
from companies.models import Company, Service, Staff, WorkingHours
from bookings.models import Customer
from .models import WhatsAppConversation, PendingBooking
from .booking_handler import BookingSearcher


class BookingSearcherTest(TestCase):
    """Test booking search functionality"""
    
    def setUp(self):
        # Create test data
        from django.contrib.auth.models import User
        user = User.objects.create_user('admin', 'admin@test.com', 'pass')
        
        self.company = Company.objects.create(
            administrator=user,
            name="Test Salon",
            address="Test St",
            city="Test City",
            online_appointments_enabled=True
        )
        
        self.service = Service.objects.create(
            company=self.company,
            name="Haircut",
            duration=30,
            price=25.00,
            is_active=True
        )
        
        self.staff = Staff.objects.create(
            company=self.company,
            name="Maria",
            working_days=[0, 1, 2, 3, 4],  # Mon-Fri
            is_active=True
        )
        self.staff.services.add(self.service)
        
        # Add working hours
        for day in range(5):  # Mon-Fri
            WorkingHours.objects.create(
                company=self.company,
                day_of_week=day,
                start_time="09:00",
                end_time="18:00"
            )
    
    def test_find_company(self):
        """Test company search"""
        searcher = BookingSearcher()
        
        # Exact match
        company = searcher.find_company("Test Salon")
        self.assertEqual(company.id, self.company.id)
        
        # Fuzzy match
        company = searcher.find_company("test saln")  # typo
        self.assertEqual(company.id, self.company.id)
    
    def test_find_service(self):
        """Test service search"""
        searcher = BookingSearcher()
        
        service = searcher.find_service(self.company, "haircut")
        self.assertEqual(service.id, self.service.id)
        
        # Fuzzy match
        service = searcher.find_service(self.company, "hair cut")
        self.assertEqual(service.id, self.service.id)
    
    def test_find_available_slots(self):
        """Test finding available time slots"""
        searcher = BookingSearcher()
        
        tomorrow = (timezone.now() + timedelta(days=1)).date()
        slots = searcher.find_available_slots(self.company, self.service, tomorrow)
        
        self.assertGreater(len(slots), 0)
        self.assertEqual(slots[0]['staff'], 'Maria')
        self.assertEqual(slots[0]['price'], 25.00)
