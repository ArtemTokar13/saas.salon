#!/usr/bin/env python
"""
Test WhatsApp bot with StaffOutOfOffice periods
Usage: python test_whatsapp_out_of_office.py
"""
import os
import django
from datetime import datetime, timedelta, time

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from django.utils import timezone
from companies.models import Company, Service, Staff, StaffOutOfOffice
from whatsapp_bot.booking_handler import BookingSearcher


def test_out_of_office_blocking():
    """Test that StaffOutOfOffice periods block availability"""
    print("\n🧪 Testing WhatsApp Bot with StaffOutOfOffice periods")
    print("=" * 60)
    
    searcher = BookingSearcher()
    
    # Get a company and staff
    company = Company.objects.filter(online_appointments_enabled=True).first()
    if not company:
        print("❌ No company found")
        return
    
    print(f"✅ Company: {company.name}")
    
    # Get a service
    service = Service.objects.filter(company=company, is_active=True).first()
    if not service:
        print("❌ No service found")
        return
    
    print(f"✅ Service: {service.name}")
    
    # Get a staff member
    staff = Staff.objects.filter(company=company, is_active=True).first()
    if not staff:
        print("❌ No staff found")
        return
    
    print(f"✅ Staff: {staff.name}")
    print(f"   Working days: {staff.working_days}")
    
    # Find a date where staff has availability (check next 14 days)
    test_date = None
    slots_before = []
    
    print("\n--- Searching for a date with availability ---")
    for days_ahead in range(1, 15):
        candidate_date = (timezone.now() + timedelta(days=days_ahead)).date()
        day_of_week = candidate_date.weekday()
        
        # Skip if staff doesn't work on this day
        if staff.working_days and day_of_week not in staff.working_days:
            continue
        
        slots = searcher.find_available_slots(company, service, candidate_date)
        if slots:
            test_date = candidate_date
            slots_before = slots
            print(f"✅ Found availability on {test_date} ({candidate_date.strftime('%A')})")
            print(f"   {len(slots_before)} slots available")
            break
    
    if not test_date:
        print("❌ No availability found in the next 14 days")
        print("   This might be normal if staff is fully booked or has limited working hours")
        return
    
    # Add an out-of-office period for the entire test day
    print("\n--- Adding out-of-office period ---")
    out_start = timezone.make_aware(datetime.combine(test_date, time(0, 0)))
    out_end = timezone.make_aware(datetime.combine(test_date, time(23, 59)))
    
    out_of_office = StaffOutOfOffice.objects.create(
        staff=staff,
        start_datetime=out_start,
        end_datetime=out_end,
        reason="Test out of office"
    )
    print(f"✅ Created out-of-office period:")
    print(f"   {out_of_office.start_datetime.strftime('%Y-%m-%d %H:%M')} to {out_of_office.end_datetime.strftime('%Y-%m-%d %H:%M')}")
    
    # Check availability AFTER adding out-of-office period
    print("\n--- After adding out-of-office period ---")
    slots_after = searcher.find_available_slots(company, service, test_date)
    print(f"Found {len(slots_after)} slots")
    
    # Verify the fix works
    if len(slots_before) > 0 and len(slots_after) == 0:
        print("\n✅ SUCCESS! WhatsApp bot now respects StaffOutOfOffice periods")
        print(f"   Before: {len(slots_before)} slots")
        print(f"   After: {len(slots_after)} slots (correctly blocked)")
    else:
        print(f"\n❌ FAILED! Staff still shows {len(slots_after)} slots when should be blocked")
        print(f"   Expected 0 slots, but got {len(slots_after)}")
    
    # Clean up
    print("\n--- Cleaning up ---")
    out_of_office.delete()
    print("✅ Deleted test out-of-office period")
    print("\n" + "=" * 60)


if __name__ == '__main__':
    test_out_of_office_blocking()
