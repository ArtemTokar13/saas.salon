"""
WhatsApp Webhook Views
"""
import logging
from datetime import datetime, timedelta
from django.conf import settings
from django.db import models
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
from twilio.twiml.messaging_response import MessagingResponse
from twilio.request_validator import RequestValidator

from .models import WhatsAppConversation, WhatsAppMessage, PendingBooking
from .ai_handler import BookingAI
from .booking_handler import BookingSearcher
from bookings.models import Customer
from bookings.utils import normalize_phone_number

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def whatsapp_webhook(request):
    """
    Main webhook endpoint for incoming WhatsApp messages from Twilio
    
    Twilio will POST to this URL when a message is received
    """
    
    # Verify request is from Twilio (security)
    if not verify_twilio_request(request):
        logger.warning("Invalid Twilio request signature")
        return HttpResponse("Forbidden", status=403)
    
    # Extract message data
    from_number = request.POST.get('From', '')  # Format: whatsapp:+1234567890
    to_number = request.POST.get('To', '')
    message_body = request.POST.get('Body', '').strip()
    message_sid = request.POST.get('MessageSid', '')
    
    logger.info(f"Received WhatsApp message from {from_number}: {message_body}")
    
    # Get or create conversation
    conversation = get_or_create_conversation(from_number)
    
    # Try to find and link existing customer
    find_and_link_customer(conversation)
    
    # Log message
    WhatsAppMessage.objects.create(
        conversation=conversation,
        from_number=from_number,
        to_number=to_number,
        message_body=message_body,
        direction='inbound',
        message_sid=message_sid
    )
    
    # Process message and generate response
    response_text = process_message(conversation, message_body)
    
    # Send response via Twilio
    response = MessagingResponse()
    response.message(response_text)
    
    # Log outbound message
    WhatsAppMessage.objects.create(
        conversation=conversation,
        from_number=to_number,
        to_number=from_number,
        message_body=response_text,
        direction='outbound'
    )
    
    return HttpResponse(str(response), content_type='text/xml')


def verify_twilio_request(request):
    """Verify that request came from Twilio"""
    if settings.DEBUG:
        # Skip validation in debug mode for local testing
        return True
    
    auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
    if not auth_token:
        logger.error("TWILIO_AUTH_TOKEN not configured")
        return False
    
    validator = RequestValidator(auth_token)
    url = request.build_absolute_uri()
    signature = request.META.get('HTTP_X_TWILIO_SIGNATURE', '')
    
    return validator.validate(url, request.POST, signature)


def get_or_create_conversation(phone_number: str) -> WhatsAppConversation:
    """Get existing conversation or create new one"""
    # Clean up old conversations (older than 24 hours with idle state)
    cutoff_time = timezone.now() - timedelta(hours=24)
    WhatsAppConversation.objects.filter(
        phone_number=phone_number,
        current_state='idle',
        last_message_at__lt=cutoff_time
    ).delete()
    
    # Get or create active conversation
    conversation, created = WhatsAppConversation.objects.get_or_create(
        phone_number=phone_number,
        current_state__in=['idle', 'selecting_language', 'selecting_service', 'collecting_info', 'showing_slots', 'confirming'],
        defaults={'current_state': 'idle'}
    )

    if created:
        logger.info(f"Created new conversation for {phone_number}")
    
    return conversation


def find_and_link_customer(conversation: WhatsAppConversation) -> Customer:
    """
    Find existing customer by phone number and link to conversation
    Also set their preferred language if available
    
    Returns:
        Customer object if found, None otherwise
    """
    # Skip if already linked
    if conversation.customer:
        return conversation.customer
    
    # Normalize the WhatsApp phone number (format: whatsapp:+1234567890)
    phone = conversation.phone_number
    normalized_phone = normalize_phone_number(phone, '')
    
    # Try to find customer by phone number
    # Check both normalized and various formats
    customers = Customer.objects.filter(
        models.Q(phone=phone) | 
        models.Q(phone=normalized_phone) |
        models.Q(phone=phone.replace('whatsapp:', ''))
    ).first()
    
    if customers:
        # Link customer to conversation
        conversation.customer = customers
        
        # Set language preference from customer if available
        if customers.preferred_language:
            state = conversation.conversation_state
            if not state.get('language'):  # Only set if not already set
                state['language'] = customers.preferred_language
                conversation.conversation_state = state
                logger.info(f"Set language to {customers.preferred_language} for returning customer {customers.name}")
        
        conversation.save()
        logger.info(f"Linked conversation to existing customer: {customers.name}")
        return customers
    
    return None


def process_message(conversation: WhatsAppConversation, message: str) -> str:
    """
    Process incoming message and return response
    
    Flow:
    1. Check if user is selecting language (priority)
    2. Ask for language preference (if not set)
    3. Detect salon-specific entry codes (from QR/links)
    4. Check if it's a simple number selection (confirming a slot)
    5. Use AI to extract intent
    6. Search for availability
    7. Generate response
    """
    
    state = conversation.conversation_state
    
    # PRIORITY: Check if user is in the middle of selecting language
    if conversation.current_state == 'selecting_language':
        return handle_language_selection(conversation, message)
    
    # Check if this is first message (language not set)
    if not state.get('language'):
        # First message - ask for language
        return ask_language_preference(conversation, message)
    
    # Detect salon-specific entry codes (first message from QR/link)
    salon_detected = detect_salon_code(conversation, message)
    if salon_detected:
        return salon_detected  # Returns welcome message
    
    # Check if user is selecting a service by number
    if conversation.current_state == 'selecting_service':
        if message.isdigit():
            return handle_service_selection(conversation, int(message))
        else:
            # User wants to specify service by name instead
            conversation.current_state = 'idle'
            conversation.save()
            # Fall through to intent processing below
    
    # Check if user is confirming a slot selection
    if conversation.current_state == 'showing_slots':
        if message.isdigit():
            return handle_slot_selection(conversation, int(message))
        else:
            # User wants to refine search instead of selecting a slot
            # Reset to idle and reprocess the message
            conversation.current_state = 'idle'
            conversation.save()
            # Fall through to intent processing below
    
    # Check if user is confirming booking
    if conversation.current_state == 'confirming':
        return handle_booking_confirmation(conversation, message)
    
    # Check if user is collecting info (name)
    if conversation.current_state == 'collecting_info':
        # User provided their name
        state = conversation.conversation_state
        state['customer_name'] = message.strip()
        conversation.conversation_state = state
        conversation.save()
        
        # Now show confirmation
        try:
            pending = PendingBooking.objects.get(conversation=conversation)
            slot = state.get('selected_slot')
            if slot:
                return show_booking_confirmation_preview(conversation, pending, slot, message.strip())
        except:
            pass
    
    # Check for cancellation keywords
    cancel_keywords = ['cancelar', 'cancel', 'stop', 'exit', 'скасувати', 'зупинити']
    if message.lower() in cancel_keywords:
        conversation.current_state = 'idle'
        state['selected_slot'] = None
        conversation.conversation_state = state
        conversation.save()
        lang = state.get('language', 'es')
        return get_message('conversation_cancelled', lang)
    
    # Check for language change keywords
    language_keywords = ['language', 'idioma', 'язык', 'мова', 'lingua', 'lengua']
    if message.lower() in language_keywords:
        conversation.current_state = 'selecting_language'
        conversation.save()
        return """🌍 Please select your language / Elige tu idioma:

1️⃣ Español (ES)
2️⃣ English (EN)
3️⃣ Русский (RU)
4️⃣ Українська (UK)

Reply with the number (1-4) or language code."""
    
    # Use AI to extract intent
    try:
        ai = BookingAI()
        intent_data = ai.extract_booking_intent(message, conversation.conversation_state)
    except Exception as e:
        logger.error(f"AI error: {e}")
        lang = state.get('language', 'es')
        return get_message('service_error', lang)
    
    # Handle different intents
    intent = intent_data.get('intent')
    
    # Override intent if AI extracted a service name, even if classified as "question"
    # This handles cases where user just types service name without "I want" or "book"
    if intent == 'question' and conversation.company:
        # If AI extracted a service name, treat it as a booking request
        if intent_data.get('service'):
            intent = 'book'
            intent_data['intent'] = 'book'
    
    if intent == 'greeting':
        return handle_greeting(conversation)
    elif intent in ['book', 'check_availability']:
        return handle_booking_request(conversation, intent_data)
    elif intent == 'question':
        return handle_question(conversation, message)
    else:
        return handle_greeting(conversation)


def ask_language_preference(conversation: WhatsAppConversation, first_message: str) -> str:
    """Ask user to select their preferred language on first message"""
    # Update conversation state
    conversation.current_state = 'selecting_language'
    conversation.conversation_state['first_message'] = first_message
    conversation.save()
    
    # Ask in all supported languages
    return """🌍 Please select your language / Elige tu idioma:

1️⃣ Español (ES)
2️⃣ English (EN)
3️⃣ Русский (RU)
4️⃣ Українська (UK)

Reply with the number (1-4) or language code."""


def handle_language_selection(conversation: WhatsAppConversation, message: str) -> str:
    """Handle language selection from user"""
    message_clean = message.strip().lower()
    
    # Map selections to language codes
    language_map = {
        '1': 'es', 'español': 'es', 'spanish': 'es', 'es': 'es',
        '2': 'en', 'english': 'en', 'inglés': 'en', 'en': 'en',
        '3': 'ru', 'русский': 'ru', 'russian': 'ru', 'ru': 'ru',
        '4': 'uk', 'українська': 'uk', 'ukrainian': 'uk', 'uk': 'uk'
    }
    
    selected_language = language_map.get(message_clean)
    
    if not selected_language:
        return """⚠️ Invalid selection / Selección inválida

Please reply: 1, 2, 3, or 4
Por favor responde: 1, 2, 3, o 4"""
    
    # Save language preference
    state = conversation.conversation_state
    state['language'] = selected_language
    conversation.conversation_state = state
    conversation.current_state = 'idle'
    conversation.save()
    
    # Also save to customer record if linked
    if conversation.customer:
        conversation.customer.preferred_language = selected_language
        conversation.customer.save()
        logger.info(f"Saved language preference {selected_language} to customer {conversation.customer.name}")
    
    logger.info(f"Language set to {selected_language} for {conversation.phone_number}")
    
    # Now process the first message they sent
    first_message = state.get('first_message', '')
    
    # Detect salon from first message
    salon_detected = detect_salon_code(conversation, first_message)
    if salon_detected:
        return salon_detected
    
    # Return greeting in selected language
    return handle_greeting(conversation)


def handle_greeting(conversation: WhatsAppConversation) -> str:
    """Handle greeting message"""
    lang = conversation.conversation_state.get('language', 'es')
    
    # Get customer name if available
    customer_name = None
    if conversation.customer:
        customer_name = conversation.customer.name
    
    # Check if salon is already set
    if conversation.company:
        return get_message('welcome_with_salon', lang, company=conversation.company, company_name=conversation.company.name, customer_name=customer_name)
    
    return get_message('welcome_general', lang, company=None, customer_name=customer_name)


def detect_salon_code(conversation: WhatsAppConversation, message: str) -> str:
    """
    Detect salon-specific entry codes from QR codes or links
    
    Returns welcome message if salon detected, None otherwise
    """
    lang = conversation.conversation_state.get('language', 'es')
    message_clean = message.strip()
    
    from companies.models import Company
    searcher = BookingSearcher()
    company = None
    salon_name = None
    
    # Pattern 1: "Hola SalonName" or "Hola! SalonName"
    if message_clean.lower().startswith(('hola', 'hello', 'привіт')):
        # Extract potential salon name
        # Remove greeting words
        for greeting in ['hola', 'hello', 'привіт', 'hola!', 'hello!']:
            if message_clean.lower().startswith(greeting):
                salon_name = message_clean[len(greeting):].strip()
                break
        else:
            salon_name = message_clean
    # Pattern 2: Standalone salon name (e.g., just "ANIMA" when asked which salon)
    else:
        # Try to match as salon name directly
        salon_name = message_clean
    
    if salon_name:
        # Try to find company by name
        company = searcher.find_company(salon_name)
        
        if company:
            # Check if this is a salon switch (different from current)
            is_switch = conversation.company and conversation.company.id != company.id
            
            # Set salon in conversation
            conversation.company = company
            conversation.current_state = 'idle'  # Reset state
            state = conversation.conversation_state
            state['company_name'] = company.name
            state['salon_auto_selected'] = True
            conversation.conversation_state = state
            conversation.save()
            
            # Clear any pending bookings for old salon
            PendingBooking.objects.filter(conversation=conversation).delete()
            
            logger.info(f"{'Switched to' if is_switch else 'Auto-selected'} salon: {company.name} for {conversation.phone_number}")
            
            # Return personalized welcome in selected language
            if is_switch:
                messages_switch = {
                    'es': f'¡Perfecto! Ahora estás reservando en {company.name}. ¿En qué puedo ayudarte?',
                    'en': f'Perfect! You are now booking at {company.name}. How can I help you?',
                    'ru': f'Отлично! Теперь вы бронируете в {company.name}. Чем могу помочь?',
                    'uk': f'Чудово! Тепер ви бронюєте в {company.name}. Чим можу допомогти?'
                }
                return messages_switch.get(lang, messages_switch['es'])
            else:
                return get_message('welcome_with_salon', lang, company=company, company_name=company.name)
    
    return None  # No salon detected



def handle_booking_request(conversation: WhatsAppConversation, intent_data: dict) -> str:
    """Handle booking or availability check request"""
    searcher = BookingSearcher()
    
    # Extract information
    company_name = intent_data.get('company_name')
    service_name = intent_data.get('service')
    staff_name = intent_data.get('staff_name')
    date_str = intent_data.get('date')
    time_str = intent_data.get('time')
    time_after = intent_data.get('time_after')
    time_before = intent_data.get('time_before')
    time_preference = intent_data.get('time_preference')
    customer_name = intent_data.get('customer_name')
    
    # If no service in new intent, clear old booking data (user wants to start fresh)
    state = conversation.conversation_state
    # Only clear if user is starting completely fresh (no booking-related data at all)
    has_booking_data = any([service_name, date_str, time_after, time_before, time_preference, staff_name])
    if not has_booking_data:
        # User is asking for services list or general question - clear old booking
        state.pop('service_name', None)
        state.pop('date', None)
        state.pop('staff_name', None)
        state.pop('time_after', None)
        state.pop('time_before', None)
        state.pop('time_preference', None)
    
    # Update conversation state with new data
    if company_name:
        state['company_name'] = company_name
    if service_name:
        # When a new service is specified, clear old time constraints
        if state.get('service_name') != service_name:
            state.pop('time_after', None)
            state.pop('time_before', None)
            state.pop('time_preference', None)
        state['service_name'] = service_name
    if staff_name:
        state['staff_name'] = staff_name
    if date_str:
        state['date'] = date_str
    if time_str:
        state['time'] = time_str
    
    # Handle time constraints - they are mutually exclusive
    if time_preference:
        # Clear conflicting time_after/time_before when time_preference is set
        state['time_preference'] = time_preference
        state.pop('time_after', None)
        state.pop('time_before', None)
    elif time_after or time_before:
        # Clear time_preference when specific time constraints are set
        if time_after:
            state['time_after'] = time_after
        if time_before:
            state['time_before'] = time_before
        state.pop('time_preference', None)
    
    if customer_name:
        state['customer_name'] = customer_name
    
    conversation.conversation_state = state
    conversation.save()
    
    # Find company - PRIORITY: 1) Pre-selected from QR/link, 2) From message, 3) Auto-select if only one
    company = None
    
    # Check if salon was auto-selected from QR code/link
    if conversation.company:
        company = conversation.company
        logger.info(f"Using pre-selected salon: {company.name}")
    elif state.get('company_name'):
        company = searcher.find_company(state['company_name'])
    
    if not company:
        # If only one company exists, use it
        from companies.models import Company
        companies = Company.objects.filter(online_appointments_enabled=True)
        if companies.count() == 1:
            company = companies.first()
        else:
            # List available salons
            salon_list = "\n".join([f"• {c.name}" for c in companies[:10]])
            lang = state.get('language', 'es')
            messages_salon = {
                'es': f"¿En qué salón te gustaría reservar?\n\n{salon_list}\n\nPor favor, indica el nombre.",
                'en': f"Which salon would you like to book at?\n\n{salon_list}\n\nPlease indicate the name.",
                'ru': f"В каком салоне вы хотите забронировать?\n\n{salon_list}\n\nПожалуйста, укажите название.",
                'uk': f"В якому салоні ви хочете забронювати?\n\n{salon_list}\n\nБудь ласка, вкажіть назву."
            }
            return messages_salon.get(lang, messages_salon['es'])
    
    # Find service
    service = None
    if state.get('service_name'):
        service = searcher.find_service(company, state['service_name'])
    
    if not service:
        # List available services
        from companies.models import Service
        services = Service.objects.filter(company=company, is_active=True)[:10]
        lang = state.get('language', 'es')
        if services.exists():
            # Store services in state for numbered selection
            service_list_data = [{'id': s.id, 'name': s.name} for s in services]
            state['service_list'] = service_list_data
            conversation.conversation_state = state
            conversation.current_state = 'selecting_service'
            conversation.save()
            
            # Create numbered list
            service_list = "\n".join([f"{i+1}️⃣ {s.name}" for i, s in enumerate(services)])
            
            # Add contact info for complex inquiries
            contact_info = ""
            if company.phone or company.email:
                contact_lines = {
                    'es': "\n\n💡 Para consultas sobre servicios específicos:",
                    'en': "\n\n💡 For specific service inquiries:",
                    'ru': "\n\n💡 Для вопросов о конкретных услугах:",
                    'uk': "\n\n💡 Для питань про конкретні послуги:"
                }
                contact_info = contact_lines.get(lang, contact_lines['es'])
                public_page_url = f"https://reserva-ya.es/companies/{company.id}/"
                contact_info += f"\n🌐 {public_page_url}"
                if company.phone:
                    contact_info += f"\n📞 {company.phone}"
            
            reply_instructions = {
                'es': "\n\n✏️ Responde con el número o el nombre del servicio. Solo puedes reservar un servicio a la vez.",
                'en': "\n\n✏️ Reply with the number or service name. You can only book one service at a time.",
                'ru': "\n\n✏️ Ответьте номером или названием услуги. Одновременно можно записаться на одну услугу.",
                'uk': "\n\n✏️ Відповідь номером або назвою послуги. Одночасно можна записатися лише на одну послугу."
            }
            
            messages_service = {
                'es': f"¿Qué servicio necesitas?\n\nServicios disponibles:\n{service_list}{reply_instructions['es']}{contact_info}",
                'en': f"What service do you need?\n\nAvailable services:\n{service_list}{reply_instructions['en']}{contact_info}",
                'ru': f"Какая услуга вам нужна?\n\nДоступные услуги:\n{service_list}{reply_instructions['ru']}{contact_info}",
                'uk': f"Яка послуга вам потрібна?\n\nДоступні послуги:\n{service_list}{reply_instructions['uk']}{contact_info}"
            }
            return messages_service.get(lang, messages_service['es'])
        else:
            messages_no_service = {
                'es': "No hay servicios disponibles en este salón.",
                'en': "No services available in this salon.",
                'ru': "В этом салоне нет доступных услуг.",
                'uk': "Немає доступних послуг у цьому салоні."
            }
            return messages_no_service.get(lang, messages_no_service['es'])
    
    # Check date
    if not state.get('date'):
        lang = state.get('language', 'es')
        messages_date = {
            'es': "¿Para qué día quieres la cita? (ej: mañana, viernes, 15 de marzo)",
            'en': "What day would you like the appointment? (e.g., tomorrow, Friday, March 15)",
            'ru': "На какой день вы хотите записаться? (напр.: завтра, пятница, 15 марта)",
            'uk': "На який день ви хочете записатися? (напр.: завтра, п'ятниця, 15 березня)"
        }
        return messages_date.get(lang, messages_date['es'])
    
    try:
        booking_date = datetime.strptime(state['date'], '%Y-%m-%d').date()
    except:
        lang = state.get('language', 'es')
        messages_bad_date = {
            'es': "No entendí la fecha. ¿Podrías especificarla? (ej: mañana, próximo lunes, 15/03/2026)",
            'en': "I didn't understand the date. Could you specify it? (e.g., tomorrow, next Monday, 03/15/2026)",
            'ru': "Я не понял дату. Можете уточнить? (напр.: завтра, следующий понедельник, 15/03/2026)",
            'uk': "Я не зрозумів дату. Можете уточнити? (напр.: завтра, наступний понеділок, 15/03/2026)"
        }
        return messages_bad_date.get(lang, messages_bad_date['es'])
    
    # Check if date is in the past
    if booking_date < timezone.now().date():
        lang = state.get('language', 'es')
        messages_past_date = {
            'es': "Esa fecha ya pasó. Por favor, elige una fecha futura.",
            'en': "That date has already passed. Please choose a future date.",
            'ru': "Эта дата уже прошла. Пожалуйста, выберите будущую дату.",
            'uk': "Ця дата вже минула. Будь ласка, виберіть майбутню дату."
        }
        return messages_past_date.get(lang, messages_past_date['es'])
    
    # Find available slots
    try:
        logger.info(f"=== SEARCHING SLOTS ===")
        logger.info(f"Company: {company.name} (ID: {company.id})")
        logger.info(f"Service: {service.name} (ID: {service.id})")
        logger.info(f"Date: {booking_date}")
        logger.info(f"Time preference: {state.get('time_preference')}")
        
        slots = searcher.find_available_slots(
            company, 
            service, 
            booking_date, 
            state.get('time_preference')
        )
        
        logger.info(f"Found {len(slots)} total slots before filtering")
        
        # Apply time constraints if specified
        if state.get('time_after'):
            time_after = state['time_after']
            slots = [s for s in slots if s['time'] >= time_after]
            logger.info(f"After time_after filter ({time_after}): {len(slots)} slots")
        
        if state.get('time_before'):
            time_before = state['time_before']
            slots = [s for s in slots if s['time'] <= time_before]
            logger.info(f"After time_before filter ({time_before}): {len(slots)} slots")
            
    except Exception as e:
        logger.error(f"Error finding slots: {e}", exc_info=True)
        lang = state.get('language', 'es')
        return get_message('service_error', lang)
    
    if not slots:
        lang = state.get('language', 'es')
        logger.warning(f"❌ NO SLOTS FOUND for {service.name} on {booking_date}")
        logger.warning(f"   Search criteria: time_after={state.get('time_after')}, time_before={state.get('time_before')}, time_preference={state.get('time_preference')}")
        
        # Build a more helpful message
        criteria_parts = []
        if state.get('time_after'):
            criteria_parts.append({
                'es': f"después de las {state['time_after']}",
                'en': f"after {state['time_after']}",
                'ru': f"после {state['time_after']}",
                'uk': f"після {state['time_after']}"
            })
        if state.get('time_before'):
            criteria_parts.append({
                'es': f"antes de las {state['time_before']}",
                'en': f"before {state['time_before']}",
                'ru': f"до {state['time_before']}",
                'uk': f"до {state['time_before']}"
            })
        
        criteria_text = ""
        if criteria_parts:
            criteria_text = {
                'es': f" {criteria_parts[0]['es']}",
                'en': f" {criteria_parts[0]['en']}",
                'ru': f" {criteria_parts[0]['ru']}",
                'uk': f" {criteria_parts[0]['uk']}"
            }
        
        messages_no_slots = {
            'es': f"😔 Lo siento, no hay horarios disponibles para {service.name} el {booking_date.strftime('%d/%m/%Y')}{criteria_text.get('es', '')}.\n\n¿Quieres probar otra fecha u horario?",
            'en': f"😔 Sorry, no times available for {service.name} on {booking_date.strftime('%d/%m/%Y')}{criteria_text.get('en', '')}.\n\nWant to try another date or time?",
            'ru': f"😔 Извините, нет доступного времени для {service.name} {booking_date.strftime('%d/%m/%Y')}{criteria_text.get('ru', '')}.\n\nПопробовать другую дату или время?",
            'uk': f"😔 Вибачте, немає доступних часів для {service.name} {booking_date.strftime('%d/%m/%Y')}{criteria_text.get('uk', '')}.\n\nСпробувати іншу дату або час?"
        }
        return messages_no_slots.get(lang, messages_no_slots['es'])
    
    # Store pending booking data
    pending, _ = PendingBooking.objects.get_or_create(conversation=conversation)
    pending.company = company
    pending.service = service
    pending.service_name = service.name
    pending.booking_date = booking_date
    pending.available_slots = slots[:5]  # Store top 5 slots
    pending.save()
    
    # Update conversation state
    conversation.current_state = 'showing_slots'
    conversation.save()
    
    # Generate response with AI
    lang = state.get('language', 'es')
    ai = BookingAI()
    response = ai.generate_response({
        'response_type': 'show_slots',
        'available_slots': slots[:5],
        'company': company,
        'service': service,
        'date': booking_date.strftime('%d/%m/%Y'),
        'language': lang
    })
    
    return response


def handle_service_selection(conversation: WhatsAppConversation, service_number: int) -> str:
    """Handle when user selects a service by number"""
    lang = conversation.conversation_state.get('language', 'es')
    state = conversation.conversation_state
    
    # Get service list from state
    service_list = state.get('service_list', [])
    
    if not service_list:
        messages_no_list = {
            'es': "⚠️ No encontré la lista de servicios. Por favor, empieza de nuevo.",
            'en': "⚠️ I couldn't find the service list. Please start again.",
            'ru': "⚠️ Я не нашел список услуг. Пожалуйста, начните заново.",
            'uk': "⚠️ Я не знайшов список послуг. Будь ласка, почніть спочатку."
        }
        conversation.current_state = 'idle'
        conversation.save()
        return messages_no_list.get(lang, messages_no_list['es'])
    
    # Validate service number
    if service_number < 1 or service_number > len(service_list):
        messages_invalid_service = {
            'es': f"⚠️ Por favor, elige un número entre 1 y {len(service_list)}.",
            'en': f"⚠️ Please choose a number between 1 and {len(service_list)}.",
            'ru': f"⚠️ Пожалуйста, выберите номер между 1 и {len(service_list)}.",
            'uk': f"⚠️ Будь ласка, виберіть номер між 1 та {len(service_list)}."
        }
        return messages_invalid_service.get(lang, messages_invalid_service['es'])
    
    # Get selected service
    selected_service = service_list[service_number - 1]
    
    # Update state with selected service
    state['service_name'] = selected_service['name']
    conversation.conversation_state = state
    conversation.current_state = 'idle'
    conversation.save()
    
    # Continue with booking flow - ask for date
    messages_date = {
        'es': f"✅ {selected_service['name']} seleccionado.\n\n¿Para qué día quieres la cita? (ej: mañana, viernes, 21 de abril)",
        'en': f"✅ {selected_service['name']} selected.\n\nWhat day would you like the appointment? (e.g., tomorrow, Friday, April 21)",
        'ru': f"✅ {selected_service['name']} выбран.\n\nНа какой день вы хотите записаться? (напр.: завтра, пятница, 21 апреля)",
        'uk': f"✅ {selected_service['name']} вибрано.\n\nНа який день ви хочете записатися? (напр.: завтра, п'ятниця, 21 квітня)"
    }
    return messages_date.get(lang, messages_date['es'])


def handle_slot_selection(conversation: WhatsAppConversation, slot_number: int) -> str:
    """Handle when user selects a time slot by number"""
    lang = conversation.conversation_state.get('language', 'es')
    
    try:
        pending = PendingBooking.objects.get(conversation=conversation)
    except PendingBooking.DoesNotExist:
        messages_no_pending = {
            'es': "⚠️ No encontré una reserva pendiente. Por favor, empieza de nuevo.",
            'en': "⚠️ I couldn't find a pending booking. Please start again.",
            'ru': "⚠️ Я не нашел незавершенное бронирование. Пожалуйста, начните заново.",
            'uk': "⚠️ Я не знайшов незавершене бронювання. Будь ласка, почніть спочатку."
        }
        return messages_no_pending.get(lang, messages_no_pending['es'])
    
    # Validate slot number
    if slot_number < 1 or slot_number > len(pending.available_slots):
        messages_invalid_slot = {
            'es': f"⚠️ Por favor, elige un número entre 1 y {len(pending.available_slots)}.",
            'en': f"⚠️ Please choose a number between 1 and {len(pending.available_slots)}.",
            'ru': f"⚠️ Пожалуйста, выберите номер между 1 и {len(pending.available_slots)}.",
            'uk': f"⚠️ Будь ласка, виберіть номер між 1 та {len(pending.available_slots)}."
        }
        return messages_invalid_slot.get(lang, messages_invalid_slot['es'])
    
    # Get selected slot
    slot = pending.available_slots[slot_number - 1]
    
    # Check if we have customer name
    customer_name = conversation.conversation_state.get('customer_name')
    if not customer_name:
        # Ask for name
        conversation.current_state = 'collecting_info'
        state = conversation.conversation_state
        state['selected_slot'] = slot
        conversation.conversation_state = state
        conversation.save()
        messages_ask_name = {
            'es': "✅ Perfecto! ¿Cuál es tu nombre completo?",
            'en': "✅ Perfect! What's your full name?",
            'ru': "✅ Отлично! Как ваше полное имя?",
            'uk': "✅ Чудово! Яке ваше повне ім'я?"
        }
        return messages_ask_name.get(lang, messages_ask_name['es'])
    
    # Show confirmation preview
    return show_booking_confirmation_preview(conversation, pending, slot, customer_name)


def create_booking_from_pending(conversation: WhatsAppConversation, 
                                pending: PendingBooking, 
                                slot: dict, 
                                customer_name: str) -> str:
    """Create the actual booking"""
    lang = conversation.conversation_state.get('language', 'es')
    searcher = BookingSearcher()
    
    try:
        booking = searcher.create_booking(
            company=pending.company,
            service=pending.service,
            staff_id=slot['staff_id'],
            customer_phone=conversation.phone_number,
            customer_name=customer_name,
            booking_date=pending.booking_date,
            booking_time=slot['time']
        )
        
        # Update conversation
        conversation.current_state = 'idle'
        conversation.conversation_state = {'language': lang}  # Keep language preference
        conversation.save()
        
        # Update pending booking
        pending.created_booking = booking
        pending.save()
        
        # Generate confirmation message
        ai = BookingAI()
        response = ai.generate_response({
            'response_type': 'booking_confirmed',
            'booking': booking,
            'language': lang
        })
        
        return response
        
    except Exception as e:
        logger.error(f"Error creating booking: {e}")
        messages_error = {
            'es': f"❌ Hubo un error al crear la reserva: {str(e)}\n\nPor favor, intenta de nuevo o contacta directamente con el salón.",
            'en': f"❌ There was an error creating the booking: {str(e)}\n\nPlease try again or contact the salon directly.",
            'ru': f"❌ Произошла ошибка при создании бронирования: {str(e)}\n\nПожалуйста, попробуйте еще раз или свяжитесь с салоном напрямую.",
            'uk': f"❌ Сталася помилка при створенні бронювання: {str(e)}\n\nБудь ласка, спробуйте ще раз або зв'яжіться безпосередньо з салоном."
        }
        return messages_error.get(lang, messages_error['es'])


def show_booking_confirmation_preview(conversation: WhatsAppConversation, pending: PendingBooking, slot: dict, customer_name: str) -> str:
    """Show booking preview and ask for confirmation"""
    lang = conversation.conversation_state.get('language', 'es')
    
    # Store selected slot
    state = conversation.conversation_state
    state['selected_slot'] = slot
    state['customer_name'] = customer_name
    conversation.conversation_state = state
    conversation.current_state = 'confirming'
    conversation.save()
    
    messages = {
        'es': """📋 Por favor confirma tu reserva:

📅 Fecha: {date}
🕐 Hora: {time}
✂️ Servicio: {service}
👤 Especialista: {staff}
👤 Cliente: {customer}
📍 Salón: {company}

✅ Responde 'sí' para confirmar
❌ Responde 'no' para cancelar""",
        'en': """📋 Please confirm your booking:

📅 Date: {date}
🕐 Time: {time}
✂️ Service: {service}
👤 Specialist: {staff}
👤 Customer: {customer}
📍 Salon: {company}

✅ Reply 'yes' to confirm
❌ Reply 'no' to cancel""",
        'ru': """📋 Пожалуйста, подтвердите бронирование:

📅 Дата: {date}
🕐 Время: {time}
✂️ Услуга: {service}
👤 Специалист: {staff}
👤 Клиент: {customer}
📍 Салон: {company}

✅ Ответьте 'да' для подтверждения
❌ Ответьте 'нет' для отмены""",
        'uk': """📋 Будь ласка, підтвердіть бронювання:

📅 Дата: {date}
🕐 Час: {time}
✂️ Послуга: {service}
👤 Спеціаліст: {staff}
👤 Клієнт: {customer}
📍 Салон: {company}

✅ Відповідайте 'так' для підтвердження
❌ Відповідайте 'ні' для скасування"""
    }
    
    template = messages.get(lang, messages['es'])
    return template.format(
        date=pending.booking_date.strftime('%d/%m/%Y'),
        time=slot['time'],
        service=pending.service.name,
        staff=slot['staff'],
        customer=customer_name,
        company=pending.company.name
    )


def handle_booking_confirmation(conversation: WhatsAppConversation, message: str) -> str:
    """Handle yes/no confirmation for booking"""
    lang = conversation.conversation_state.get('language', 'es')
    message_lower = message.strip().lower()
    
    # Check for affirmative responses
    yes_keywords = ['sí', 'si', 'yes', 'yeah', 'yep', 'так', 'да', 'ok', 'okay', 'confirmar', 'confirm']
    no_keywords = ['no', 'нет', 'ні', 'cancel', 'cancelar']
    
    if any(word in message_lower for word in yes_keywords):
        # Confirm and create booking
        try:
            pending = PendingBooking.objects.get(conversation=conversation)
            state = conversation.conversation_state
            slot = state.get('selected_slot')
            customer_name = state.get('customer_name')
            
            if not slot or not customer_name:
                return get_message('service_error', lang)
            
            return create_booking_from_pending(conversation, pending, slot, customer_name)
        except Exception as e:
            logger.error(f"Error confirming booking: {e}")
            return get_message('service_error', lang)
    
    elif any(word in message_lower for word in no_keywords):
        # Cancel the booking
        conversation.current_state = 'idle'
        state = conversation.conversation_state
        state.pop('selected_slot', None)
        conversation.conversation_state = state
        conversation.save()
        
        messages_cancelled = {
            'es': "❌ Reserva cancelada.\n\n¿Quieres buscar otro hora rio o servicio?",
            'en': "❌ Booking cancelled.\n\nWould you like to search for another time or service?",
            'ru': "❌ Бронирование отменено.\n\nХотите найти другое время или услугу?",
            'uk': "❌ Бронювання скасовано.\n\nБажаєте знайти інший час або послугу?"
        }
        return messages_cancelled.get(lang, messages_cancelled['es'])
    
    else:
        # Unclear response
        messages_unclear = {
            'es': "⚠️ Por favor responde 'sí' para confirmar o 'no' para cancelar.",
            'en': "⚠️ Please reply 'yes' to confirm or 'no' to cancel.",
            'ru': "⚠️ Пожалуйста, ответьте 'да' для подтверждения или 'нет' для отмены.",
            'uk': "⚠️ Будь ласка, відповідайте 'так' для підтвердження або 'ні' для скасування."
        }
        return messages_unclear.get(lang, messages_unclear['es'])


def handle_question(conversation: WhatsAppConversation, message: str) -> str:
    """Handle general questions - provide salon contact for complex inquiries"""
    lang = conversation.conversation_state.get('language', 'es')
    
    # If salon is known, provide contact information
    if conversation.company:
        company = conversation.company
        
        # Build public page URL
        public_page_url = f"https://reserva-ya.es/companies/{company.id}/"
        
        contact_messages = {
            'es': f"""Para consultas específicas sobre servicios, precios o disponibilidad:

🌐 Ver servicios y precios: {public_page_url}
📞 Teléfono: {company.phone if company.phone else 'No disponible'}

¿O prefieres que te ayude a hacer una reserva?""",
            'en': f"""For specific questions about services, prices or availability:

🌐 View services and prices: {public_page_url}
📞 Phone: {company.phone if company.phone else 'Not available'}

Or would you like me to help you make a booking?""",
            'ru': f"""Для конкретных вопросов об услугах, ценах или доступности:

🌐 Посмотреть услуги и цены: {public_page_url}
📞 Телефон: {company.phone if company.phone else 'Недоступно'}

Или хотите, чтобы я помог вам сделать бронирование?""",
            'uk': f"""Для конкретних питань про послуги, ціни або доступність:

🌐 Переглянути послуги та ціни: {public_page_url}
📞 Телефон: {company.phone if company.phone else 'Недоступно'}

Або хочете, щоб я допоміг вам зробити бронювання?"""
        }
        return contact_messages.get(lang, contact_messages['es'])
    
    # If no salon set, show general help
    return get_message('help_message', lang)



def get_service_examples(company, lang: str) -> list:
    """Generate dynamic service examples based on company's actual services"""
    from companies.models import Service
    
    if not company:
        return []
    
    # Get up to 3 active services from the company
    services = Service.objects.filter(company=company, is_active=True)[:3]
    
    if not services:
        return []
    
    # Time examples in different languages
    time_examples = {
        'es': ['mañana a las 3pm', 'el viernes después de las 5pm', 'el lunes a las 2pm'],
        'en': ['tomorrow at 3pm', 'on Friday after 5pm', 'Monday at 2pm'],
        'ru': ['завтра в 3pm', 'в пятницу после 17:00', 'в понедельник в 14:00'],
        'uk': ['завтра о 3pm', "в п'ятницю після 17:00", 'на понеділок о 14:00'],
    }
    
    # Action phrases in different languages
    action_phrases = {
        'es': ['Quiero', 'Disponibilidad para', 'Reserva'],
        'en': ['I want', 'Availability for', 'Book'],
        'ru': ['Хочу', 'Доступность для', 'Забронировать'],
        'uk': ['Хочу', 'Доступність для', 'Забронюйте'],
    }
    
    times = time_examples.get(lang, time_examples['es'])
    actions = action_phrases.get(lang, action_phrases['es'])
    
    examples = []
    for i, service in enumerate(services):
        if i < len(times) and i < len(actions):
            examples.append(f'{actions[i]} {service.name.lower()} {times[i]}')
    
    return examples


def get_message(key: str, lang: str, company=None, **kwargs) -> str:
    """Get predefined message in specified language"""
    
    # Generate dynamic service examples if company is provided
    service_examples = get_service_examples(company, lang) if company else []
    
    # Build examples string
    if service_examples:
        examples_str = '\n'.join([f'• "{ex}"' for ex in service_examples])
    else:
        # Fallback to generic examples
        generic_examples = {
            'es': '• "Quiero una cita mañana a las 3pm"\n• "Disponibilidad el viernes después de las 5pm"\n• "Reserva para el lunes a las 2pm"',
            'en': '• "I want an appointment tomorrow at 3pm"\n• "Availability on Friday after 5pm"\n• "Book for Monday at 2pm"',
            'ru': '• "Хочу запись завтра в 3pm"\n• "Доступность в пятницу после 17:00"\n• "Забронировать на понедельник в 14:00"',
            'uk': '• "Хочу відвідування завтра о 3pm"\n• "Доступність в п\'ятницю після 17:00"\n• "Забронюйте на понеділок о 14:00"',
        }
        examples_str = generic_examples.get(lang, generic_examples['es'])
    
    messages = {
        'welcome_with_salon': {
            'es': "👋 ¡Hola{name_greeting}! Bienvenido a {company_name}.\n\nPuedo ayudarte a reservar una cita. Por ejemplo:\n{examples}\n\n¿En qué puedo ayudarte?",
            'en': "👋 Hello{name_greeting}! Welcome to {company_name}.\n\nI can help you book an appointment. For example:\n{examples}\n\nHow can I help you?",
            'ru': "👋 Здравствуйте{name_greeting}! Добро пожаловать в {company_name}.\n\nЯ могу помочь вам забронировать визит. Например:\n{examples}\n\nЧем могу помочь?",
            'uk': "👋 Привіт{name_greeting}! Ласкаво просимо до {company_name}.\n\nЯ можу допомогти вам забронювати візит. Наприклад:\n{examples}\n\nЯк я можу допомогти?",
        },
        'welcome_general': {
            'es': "👋 ¡Hola{name_greeting}! Soy tu asistente de reservas inteligente.\n\nPuedo ayudarte a reservar una cita. Por ejemplo:\n{examples}\n\n¿En qué puedo ayudarte?",
            'en': "👋 Hello{name_greeting}! I'm your smart booking assistant.\n\nI can help you book an appointment. For example:\n{examples}\n\nHow can I help you?",
            'ru': "👋 Здравствуйте{name_greeting}! Я ваш умный помощник по бронированию.\n\nЯ могу помочь вам забронировать визит. Например:\n{examples}\n\nЧем могу помочь?",
            'uk': "👋 Привіт{name_greeting}! Я ваш розумний асистент бронювання.\n\nЯ можу допомогти забронювати візит. Наприклад:\n{examples}\n\nЯк я можу допомогти?",
        },
        'conversation_cancelled': {
            'es': "❌ Conversación cancelada. Escribe cuando quieras hacer una reserva.",
            'en': "❌ Conversation cancelled. Write when you want to make a booking.",
            'ru': "❌ Разговор отменен. Пишите, когда захотите сделать бронирование.",
            'uk': "❌ Розмову скасовано. Напишіть, коли захочете зробити бронювання.",
        },
        'service_error': {
            'es': "⚠️ Lo siento, hay un problema con el servicio. Por favor, intenta más tarde o llama directamente al salón.",
            'en': "⚠️ Sorry, there's a problem with the service. Please try again later or call the salon directly.",
            'ru': "⚠️ Извините, проблема с сервисом. Пожалуйста, попробуйте позже или позвоните в салон напрямую.",
            'uk': "⚠️ Вибачте, проблема з сервісом. Будь ласка, спробуйте пізніше або зателефонуйте безпосередньо до салону.",
        },
        'help_message': {
            'es': "Puedo ayudarte a:\n• Hacer una reserva\n• Consultar disponibilidad\n• Ver servicios disponibles\n\nEscribe 'idioma' para cambiar el idioma.\n\n¿Qué necesitas?",
            'en': "I can help you:\n• Make a booking\n• Check availability\n• See available services\n\nType 'language' to change language.\n\nWhat do you need?",
            'ru': "Я могу помочь вам:\n• Сделать бронирование\n• Проверить доступность\n• Посмотреть доступные услуги\n\nНапишите 'язык' чтобы изменить язык.\n\nЧто вам нужно?",
            'uk': "Я можу допомогти вам:\n• Зробити бронювання\n• Перевірити доступність\n• Переглянути доступні послуги\n\nНапишіть 'мова' щоб змінити мову.\n\nЩо вам потрібно?",
        },
    }
    
    message_dict = messages.get(key, {})
    template = message_dict.get(lang, message_dict.get('es', ''))
    
    # Add examples to kwargs for welcome messages
    if key in ['welcome_with_salon', 'welcome_general']:
        kwargs['examples'] = examples_str
        
        # Add personalized name greeting if customer name is provided
        customer_name = kwargs.get('customer_name')
        if customer_name:
            # Format: ", [Name]" (e.g., "¡Hola, Maria!")
            kwargs['name_greeting'] = f", {customer_name}"
        else:
            kwargs['name_greeting'] = ""
    
    # Format with kwargs if provided
    if kwargs:
        return template.format(**kwargs)
    return template
