#!/usr/bin/env python
"""
Test booking availability to debug issues
Usage: python test_booking_availability.py
"""
import os
import django
import sys
from datetime import datetime, date

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from companies.models import Company, Service, Staff, WorkingHours, StaffWorkingHours
from whatsapp_bot.booking_handler import BookingSearcher
from whatsapp_bot.ai_handler import BookingAI


def test_availability(company_id, service_name, date_str, time_after=None):
    """
    Test availability for a specific service and date
    
    Args:
        company_id: ID of the company
        service_name: Name of the service (partial match OK)
        date_str: Date in YYYY-MM-DD format
        time_after: Optional time constraint in HH:MM format
    """
    print("=" * 70)
    print("BOOKING AVAILABILITY TEST")
    print("=" * 70)
    
    # Get company
    try:
        company = Company.objects.get(id=company_id)
        print(f"\n✅ Company: {company.name} (ID: {company.id})")
        print(f"   Online appointments enabled: {company.online_appointments_enabled}")
    except Company.DoesNotExist:
        print(f"\n❌ Company ID {company_id} not found")
        return
    
    # Get service
    service = Service.objects.filter(
        company=company, 
        name__icontains=service_name,
        is_active=True
    ).first()
    
    if not service:
        print(f"\n❌ Service matching '{service_name}' not found")
        print(f"\nAvailable services:")
        for s in Service.objects.filter(company=company, is_active=True):
            print(f"   - {s.name} (ID: {s.id})")
        return
    
    print(f"\n✅ Service: {service.name} (ID: {service.id})")
    print(f"   Duration: {service.duration} min")
    print(f"   Price: €{service.price}")
    
    # Parse date
    try:
        check_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        print(f"\n✅ Date: {check_date} ({check_date.strftime('%A')}, weekday={check_date.weekday()})")
    except:
        print(f"\n❌ Invalid date format. Use YYYY-MM-DD")
        return
    
    # Check staff
    staff_members = Staff.objects.filter(
        company=company,
        is_active=True,
        services=service
    )
    
    print(f"\n👥 Staff members for this service: {staff_members.count()}")
    if staff_members.count() == 0:
        print("   ⚠️  No staff specifically assigned. Will check all active staff.")
        staff_members = Staff.objects.filter(company=company, is_active=True)
    
    for staff in staff_members:
        print(f"\n   Staff: {staff.name}")
        print(f"   Working days: {staff.working_days}")
        
        # Check if works on this day
        day_of_week = check_date.weekday()
        if staff.working_days and day_of_week not in staff.working_days:
            print(f"   ❌ Does not work on {check_date.strftime('%A')} (weekday {day_of_week})")
            continue
        else:
            print(f"   ✅ Works on {check_date.strftime('%A')}")
        
        # Check staff-specific hours
        staff_hours = StaffWorkingHours.objects.filter(
            staff=staff,
            day_of_week=day_of_week,
            is_day_off=False
        ).first()
        
        if staff_hours:
            print(f"   ✅ Staff hours: {staff_hours.start_time} - {staff_hours.end_time}")
        else:
            # Check company hours
            company_hours = WorkingHours.objects.filter(
                company=company,
                day_of_week=day_of_week,
                is_day_off=False
            ).first()
            if company_hours:
                print(f"   ✅ Company hours: {company_hours.start_time} - {company_hours.end_time}")
            else:
                print(f"   ❌ No working hours for {check_date.strftime('%A')}")
    
    # Find available slots
    print(f"\n{'=' * 70}")
    print("FINDING AVAILABLE SLOTS")
    print(f"{'=' * 70}")
    
    searcher = BookingSearcher()
    slots = searcher.find_available_slots(company, service, check_date)
    
    print(f"\n✅ Found {len(slots)} slots BEFORE time filtering:")
    if len(slots) > 0:
        for i, slot in enumerate(slots[:10], 1):
            print(f"   {i}. {slot['time']} - {slot['staff']} (€{slot['price']})")
        if len(slots) > 10:
            print(f"   ... and {len(slots) - 10} more")
    
    # Apply time filter if specified
    if time_after:
        print(f"\n⏰ Applying time_after filter: >= {time_after}")
        filtered_slots = [s for s in slots if s['time'] >= time_after]
        print(f"✅ {len(filtered_slots)} slots AFTER filtering:")
        if len(filtered_slots) > 0:
            for i, slot in enumerate(filtered_slots[:10], 1):
                print(f"   {i}. {slot['time']} - {slot['staff']} (€{slot['price']})")
        else:
            print("   ❌ No slots available after this time")
            if len(slots) > 0:
                print(f"\n   💡 Hint: Latest available slot is at {slots[-1]['time']}")
    
    print(f"\n{'=' * 70}")
    print("TEST COMPLETE")
    print(f"{'=' * 70}\n")


def test_ai_extraction(message, language='ru'):
    """Test AI message extraction"""
    print("=" * 70)
    print("AI MESSAGE EXTRACTION TEST")
    print("=" * 70)
    print(f"\nMessage: '{message}'")
    print(f"Language: {language}")
    
    try:
        ai = BookingAI()
        result = ai.extract_booking_intent(message, {'language': language})
        
        print(f"\n✅ AI Extraction Result:")
        for key, value in result.items():
            if value:
                print(f"   {key}: {value}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    
    print(f"\n{'=' * 70}\n")


if __name__ == '__main__':
    # Example usage - modify these parameters
    if len(sys.argv) > 1:
        # Command line usage
        if sys.argv[1] == 'ai':
            # Test AI extraction
            message = ' '.join(sys.argv[2:])
            test_ai_extraction(message)
        else:
            print("Usage:")
            print("  python test_booking_availability.py ai <message>")
            print("  Or edit the script to set test parameters")
    else:
        # Interactive test - MODIFY THESE VALUES
        print("🔧 Edit this script to test your specific case\n")
        
        # Example: Test availability for company ID 6 (from screenshot)
        # Modify these values to match your production data:
        company_id = 3  # Change to your company ID
        service_name = "semipermanente"  # Partial name match
        date_str = "2026-04-21"  # Tuesday April 21, 2026
        time_after = "17:00"  # Optional: filter for after 17:00
        
        print(f"Testing with:")
        print(f"  Company ID: {company_id}")
        print(f"  Service: {service_name}")
        print(f"  Date: {date_str}")
        print(f"  Time after: {time_after or 'None'}")
        print()
        
        test_availability(company_id, service_name, date_str, time_after)
        
        # Also test AI extraction
        print("\n" + "=" * 70)
        print("Testing AI extraction for the user's message:")
        test_ai_extraction("На вторник после 17:00", language='ru')
        test_ai_extraction("Хочу на вторник на 14:00", language='ru')
