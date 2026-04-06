"""
Test script to verify WhatsApp AI integration setup
Run: python test_whatsapp_setup.py
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from django.conf import settings
from companies.models import Company, Service, Staff, WorkingHours
from datetime import datetime


def test_environment_variables():
    """Check if all required environment variables are set"""
    print("🔍 Testing Environment Variables...")
    
    required_vars = {
        'OPENAI_API_KEY': settings.OPENAI_API_KEY,
        'TWILIO_ACCOUNT_SID': settings.TWILIO_ACCOUNT_SID,
        'TWILIO_AUTH_TOKEN': settings.TWILIO_AUTH_TOKEN,
        'TWILIO_WHATSAPP_FROM': settings.TWILIO_WHATSAPP_FROM,
    }
    
    all_set = True
    for var_name, var_value in required_vars.items():
        if var_value:
            print(f"  ✅ {var_name}: {var_value[:10]}...")
        else:
            print(f"  ❌ {var_name}: NOT SET")
            all_set = False
    
    return all_set


def test_packages():
    """Check if required packages are installed"""
    print("\n📦 Testing Packages...")
    
    packages = []
    
    try:
        import openai
        print(f"  ✅ openai: {openai.__version__}")
        packages.append(True)
    except ImportError:
        print("  ❌ openai: NOT INSTALLED - run: pip install openai")
        packages.append(False)
    
    try:
        import fuzzywuzzy
        print(f"  ✅ fuzzywuzzy: installed")
        packages.append(True)
    except ImportError:
        print("  ❌ fuzzywuzzy: NOT INSTALLED - run: pip install fuzzywuzzy python-Levenshtein")
        packages.append(False)
    
    try:
        from twilio.rest import Client
        print(f"  ✅ twilio: installed")
        packages.append(True)
    except ImportError:
        print("  ❌ twilio: NOT INSTALLED - run: pip install twilio")
        packages.append(False)
    
    return all(packages)


def test_database():
    """Check if database has required data"""
    print("\n💾 Testing Database...")
    
    companies = Company.objects.filter(online_appointments_enabled=True).count()
    services = Service.objects.filter(is_active=True).count()
    staff = Staff.objects.filter(is_active=True).count()
    working_hours = WorkingHours.objects.count()
    
    print(f"  📍 Companies: {companies}")
    print(f"  💇 Services: {services}")
    print(f"  👤 Staff: {staff}")
    print(f"  🕐 Working Hours: {working_hours}")
    
    if companies == 0:
        print("  ⚠️  No companies found. Create at least one company via admin.")
        return False
    if services == 0:
        print("  ⚠️  No services found. Create at least one service via admin.")
        return False
    if staff == 0:
        print("  ⚠️  No staff found. Create at least one staff member via admin.")
        return False
    
    return True


def test_ai_connection():
    """Test OpenAI API connection"""
    print("\n🤖 Testing OpenAI Connection...")
    
    if not settings.OPENAI_API_KEY:
        print("  ❌ OpenAI API key not set")
        return False
    
    try:
        from whatsapp_bot.ai_handler import BookingAI
        ai = BookingAI()
        
        # Test simple extraction
        result = ai.extract_booking_intent("I want to book a haircut tomorrow at 3pm")
        print(f"  ✅ AI Response: {result.get('intent', 'unknown')} (confidence: {result.get('confidence', 0):.2f})")
        return True
    except Exception as e:
        print(f"  ❌ OpenAI Error: {str(e)}")
        return False


def test_booking_search():
    """Test booking search functionality"""
    print("\n🔎 Testing Booking Search...")
    
    try:
        from whatsapp_bot.booking_handler import BookingSearcher
        from datetime import timedelta
        from django.utils import timezone
        
        searcher = BookingSearcher()
        
        # Get first company
        company = Company.objects.filter(online_appointments_enabled=True).first()
        if not company:
            print("  ❌ No company found")
            return False
        
        print(f"  ✅ Found company: {company.name}")
        
        # Get first service
        service = Service.objects.filter(company=company, is_active=True).first()
        if not service:
            print("  ❌ No service found for company")
            return False
        
        print(f"  ✅ Found service: {service.name}")
        
        # Check availability
        tomorrow = (timezone.now() + timedelta(days=1)).date()
        slots = searcher.find_available_slots(company, service, tomorrow)
        
        print(f"  ✅ Found {len(slots)} available slots for tomorrow")
        if slots:
            print(f"     First slot: {slots[0]['time']} with {slots[0]['staff']}")
        
        return True
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_webhook_url():
    """Show webhook URL info"""
    print("\n🌐 Webhook Configuration...")
    print("  📝 Set this URL in Twilio:")
    print("     For local testing with ngrok: https://YOUR_NGROK_URL.ngrok.io/whatsapp/webhook/")
    print("     For production: https://your-domain.com/whatsapp/webhook/")
    print("\n  🔧 Webhook configuration:")
    print("     Method: POST")
    print("     URL: [your-domain]/whatsapp/webhook/")


def main():
    print("=" * 60)
    print("  WhatsApp AI Integration - Setup Test")
    print("=" * 60)
    
    results = []
    
    results.append(("Environment Variables", test_environment_variables()))
    results.append(("Packages", test_packages()))
    results.append(("Database", test_database()))
    results.append(("OpenAI Connection", test_ai_connection()))
    results.append(("Booking Search", test_booking_search()))
    
    test_webhook_url()
    
    print("\n" + "=" * 60)
    print("  Summary")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status} - {test_name}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("  🎉 All tests passed! Ready to receive WhatsApp messages!")
        print("  Next steps:")
        print("  1. Start server: python manage.py runserver")
        print("  2. Start ngrok: ngrok http 8000")
        print("  3. Configure Twilio webhook")
        print("  4. Send test WhatsApp message")
    else:
        print("  ⚠️  Some tests failed. Check errors above and fix them.")
        print("  See WHATSAPP_SETUP.md for detailed instructions.")
    print("=" * 60)


if __name__ == '__main__':
    main()
