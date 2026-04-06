"""
WhatsApp Webhook Views
"""
import logging
from datetime import datetime, timedelta
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
from twilio.twiml.messaging_response import MessagingResponse
from twilio.request_validator import RequestValidator

from .models import WhatsAppConversation, WhatsAppMessage, PendingBooking
from .ai_handler import BookingAI
from .booking_handler import BookingSearcher

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
        current_state__in=['idle', 'selecting_language', 'collecting_info', 'showing_slots', 'confirming'],
        defaults={'current_state': 'idle'}
    )

    if created:
        logger.info(f"Created new conversation for {phone_number}")
    
    return conversation


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
3️⃣ Català (CA)
4️⃣ Українська (UK)

Reply with the number (1-4) or language code."""


def handle_language_selection(conversation: WhatsAppConversation, message: str) -> str:
    """Handle language selection from user"""
    message_clean = message.strip().lower()
    
    # Map selections to language codes
    language_map = {
        '1': 'es', 'español': 'es', 'spanish': 'es', 'es': 'es',
        '2': 'en', 'english': 'en', 'inglés': 'en', 'en': 'en',
        '3': 'ca', 'català': 'ca', 'catalan': 'ca', 'ca': 'ca',
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
    
    # Check if salon is already set
    if conversation.company:
        return get_message('welcome_with_salon', lang, company_name=conversation.company.name)
    
    return get_message('welcome_general', lang)


def detect_salon_code(conversation: WhatsAppConversation, message: str) -> str:
    """
    Detect salon-specific entry codes from QR codes or links
    
    Returns welcome message if salon detected, None otherwise
    """
    # Only check on first message or if no salon set
    if conversation.messages.count() > 1 and conversation.company:
        return None
    
    lang = conversation.conversation_state.get('language', 'es')
    
    # Check for simple format: "Hola [Company Name]"
    message_clean = message.strip()
    
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
        
        if salon_name:
            from companies.models import Company
            searcher = BookingSearcher()
            
            # Try to find company by name
            company = searcher.find_company(salon_name)
            
            if company:
                # Set salon in conversation
                conversation.company = company
                state = conversation.conversation_state
                state['company_name'] = company.name
                state['salon_auto_selected'] = True
                conversation.conversation_state = state
                conversation.save()
                
                logger.info(f"Auto-selected salon: {company.name} for {conversation.phone_number}")
                
                # Return personalized welcome in selected language
                return get_message('welcome_with_salon', lang, company_name=company.name)
    
    # Pattern 2: Legacy salon codes (backward compatibility)
    salon_codes = {
        'SALON_CENTRO': 'centro',
        'SALON_NORTE': 'norte', 
        'SALON_SUR': 'sur',
        'CENTRO': 'centro',
        'NORTE': 'norte',
        'SUR': 'sur',
    }
    
    message_upper = message.upper().strip()
    
    for code, salon_keyword in salon_codes.items():
        if code in message_upper or message_upper.startswith(code):
            from companies.models import Company
            searcher = BookingSearcher()
            
            # Try different variations
            possible_names = [
                salon_keyword,
                f"salon {salon_keyword}",
                f"peluqueria {salon_keyword}",
            ]
            
            company = None
            for name in possible_names:
                company = searcher.find_company(name)
                if company:
                    break
            
            if company:
                conversation.company = company
                state = conversation.conversation_state
                state['company_name'] = company.name
                state['salon_auto_selected'] = True
                conversation.conversation_state = state
                conversation.save()
                
                logger.info(f"Auto-selected salon (legacy code): {company.name} for {conversation.phone_number}")
                return get_message('welcome_with_salon', lang, company_name=company.name)
    
    return None


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
    
    # Update conversation state
    state = conversation.conversation_state
    if company_name:
        state['company_name'] = company_name
    if service_name:
        state['service_name'] = service_name
    if staff_name:
        state['staff_name'] = staff_name
    if date_str:
        state['date'] = date_str
    if time_str:
        state['time'] = time_str
    if time_after:
        state['time_after'] = time_after
    if time_before:
        state['time_before'] = time_before
    if time_preference:
        state['time_preference'] = time_preference
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
                'ca': f"A quin saló vols reservar?\n\n{salon_list}\n\nSi us plau, indica el nom.",
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
            service_list = "\n".join([f"• {s.name}" for s in services])
            messages_service = {
                'es': f"¿Qué servicio necesitas?\n\nServicios disponibles:\n{service_list}",
                'en': f"What service do you need?\n\nAvailable services:\n{service_list}",
                'ca': f"Quin servei necessites?\n\nServeis disponibles:\n{service_list}",
                'uk': f"Яка послуга вам потрібна?\n\nДоступні послуги:\n{service_list}"
            }
            return messages_service.get(lang, messages_service['es'])
        else:
            messages_no_service = {
                'es': "No hay servicios disponibles en este salón.",
                'en': "No services available in this salon.",
                'ca': "No hi ha serveis disponibles en aquest saló.",
                'uk': "Немає доступних послуг у цьому салоні."
            }
            return messages_no_service.get(lang, messages_no_service['es'])
    
    # Check date
    if not state.get('date'):
        lang = state.get('language', 'es')
        messages_date = {
            'es': "¿Para qué día quieres la cita? (ej: mañana, viernes, 15 de marzo)",
            'en': "What day would you like the appointment? (e.g., tomorrow, Friday, March 15)",
            'ca': "Per a quin dia vols la cita? (ex: demà, divendres, 15 de març)",
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
            'ca': "No he entès la data. Podries especificar-la? (ex: demà, pròxim dilluns, 15/03/2026)",
            'uk': "Я не зрозумів дату. Можете уточнити? (напр.: завтра, наступний понеділок, 15/03/2026)"
        }
        return messages_bad_date.get(lang, messages_bad_date['es'])
    
    # Check if date is in the past
    if booking_date < timezone.now().date():
        lang = state.get('language', 'es')
        messages_past_date = {
            'es': "Esa fecha ya pasó. Por favor, elige una fecha futura.",
            'en': "That date has already passed. Please choose a future date.",
            'ca': "Aquesta data ja ha passat. Si us plau, tria una data futura.",
            'uk': "Ця дата вже минула. Будь ласка, виберіть майбутню дату."
        }
        return messages_past_date.get(lang, messages_past_date['es'])
    
    # Find available slots
    try:
        slots = searcher.find_available_slots(
            company, 
            service, 
            booking_date, 
            state.get('time_preference')
        )
        
        # Apply time constraints if specified
        if state.get('time_after'):
            time_after = state['time_after']
            slots = [s for s in slots if s['time'] >= time_after]
        
        if state.get('time_before'):
            time_before = state['time_before']
            slots = [s for s in slots if s['time'] <= time_before]
        
        # Filter by specific staff member if requested
        if state.get('staff_name'):
            staff_name_lower = state['staff_name'].lower()
            slots = [s for s in slots if staff_name_lower in s['staff'].lower()]
            
    except Exception as e:
        logger.error(f"Error finding slots: {e}")
        lang = state.get('language', 'es')
        return get_message('service_error', lang)
    
    if not slots:
        lang = state.get('language', 'es')
        messages_no_slots = {
            'es': f"😔 Lo siento, no hay horarios disponibles para {service.name} el {booking_date.strftime('%d/%m/%Y')}.\n\n¿Quieres probar otra fecha?",
            'en': f"😔 Sorry, no times available for {service.name} on {booking_date.strftime('%d/%m/%Y')}.\n\nWant to try another date?",
            'ca': f"😔 Ho sento, no hi ha horaris disponibles per {service.name} el {booking_date.strftime('%d/%m/%Y')}.\n\nVols provar una altra data?",
            'uk': f"😔 Вибачте, немає доступних часів для {service.name} {booking_date.strftime('%d/%m/%Y')}.\n\nСпробувати іншу дату?"
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


def handle_slot_selection(conversation: WhatsAppConversation, slot_number: int) -> str:
    """Handle when user selects a time slot by number"""
    lang = conversation.conversation_state.get('language', 'es')
    
    try:
        pending = PendingBooking.objects.get(conversation=conversation)
    except PendingBooking.DoesNotExist:
        messages_no_pending = {
            'es': "⚠️ No encontré una reserva pendiente. Por favor, empieza de nuevo.",
            'en': "⚠️ I couldn't find a pending booking. Please start again.",
            'ca': "⚠️ No he trobat una reserva pendent. Si us plau, comença de nou.",
            'uk': "⚠️ Я не знайшов незавершене бронювання. Будь ласка, почніть спочатку."
        }
        return messages_no_pending.get(lang, messages_no_pending['es'])
    
    # Validate slot number
    if slot_number < 1 or slot_number > len(pending.available_slots):
        messages_invalid_slot = {
            'es': f"⚠️ Por favor, elige un número entre 1 y {len(pending.available_slots)}.",
            'en': f"⚠️ Please choose a number between 1 and {len(pending.available_slots)}.",
            'ca': f"⚠️ Si us plau, tria un número entre 1 i {len(pending.available_slots)}.",
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
            'ca': "✅ Perfecte! Quin és el teu nom complet?",
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
            'ca': f"❌ Hi ha hagut un error en crear la reserva: {str(e)}\n\nSi us plau, torna-ho a provar o contacta directament amb el saló.",
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
        'ca': """📋 Si us plau, confirma la teva reserva:

📅 Data: {date}
🕐 Hora: {time}
✂️ Servei: {service}
👤 Especialista: {staff}
👤 Client: {customer}
📍 Saló: {company}

✅ Respon 'sí' per confirmar
❌ Respon 'no' per cancel·lar""",
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
    yes_keywords = ['sí', 'si', 'yes', 'yeah', 'yep', 'так', 'ok', 'okay', 'confirmar', 'confirm']
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
            'ca': "❌ Reserva cancel·lada.\n\nVols buscar un altre horari o servei?",
            'uk': "❌ Бронювання скасовано.\n\nБажаєте знайти інший час або послугу?"
        }
        return messages_cancelled.get(lang, messages_cancelled['es'])
    
    else:
        # Unclear response
        messages_unclear = {
            'es': "⚠️ Por favor responde 'sí' para confirmar o 'no' para cancelar.",
            'en': "⚠️ Please reply 'yes' to confirm or 'no' to cancel.",
            'ca': "⚠️ Si us plau respon 'sí' per confirmar o 'no' per cancel·lar.",
            'uk': "⚠️ Будь ласка, відповідайте 'так' для підтвердження або 'ні' для скасування."
        }
        return messages_unclear.get(lang, messages_unclear['es'])


def handle_question(conversation: WhatsAppConversation, message: str) -> str:
    """Handle general questions"""
    lang = conversation.conversation_state.get('language', 'es')
    return get_message('help_message', lang)


def get_message(key: str, lang: str, **kwargs) -> str:
    """Get predefined message in specified language"""
    messages = {
        'welcome_with_salon': {
            'es': "👋 ¡Hola! Bienvenido a {company_name}.\n\nPuedo ayudarte a reservar una cita. Por ejemplo:\n• \"Quiero un corte de pelo mañana a las 3pm\"\n• \"Disponibilidad para manicura el viernes\"\n• \"Reserva masaje para el lunes por la tarde\"\n\n¿En qué puedo ayudarte?",
            'en': "👋 Hello! Welcome to {company_name}.\n\nI can help you book an appointment. For example:\n• \"I want a haircut tomorrow at 3pm\"\n• \"Availability for manicure on Friday\"\n• \"Book a massage for Monday afternoon\"\n\nHow can I help you?",
            'ca': "👋 Hola! Benvingut a {company_name}.\n\nPuc ajudar-te a fer una reserva. Per exemple:\n• \"Vull un tall de cabell demà a les 3pm\"\n• \"Disponibilitat per a manicura el divendres\"\n• \"Reserva massatge per dilluns a la tarda\"\n\nEn què puc ajudar-te?",
            'uk': "👋 Привіт! Ласкаво просимо до {company_name}.\n\nЯ можу допомогти вам забронювати візит. Наприклад:\n• \"Хочу стрижку завтра о 3pm\"\n• \"Доступність для манікюру в п'ятницю\"\n• \"Забронюйте масаж на понеділок після обіду\"\n\nЯк я можу допомогти?",
        },
        'welcome_general': {
            'es': "👋 ¡Hola! Soy tu asistente de reservas inteligente.\n\nPuedo ayudarte a reservar una cita. Por ejemplo:\n• \"Quiero un corte de pelo mañana a las 3pm\"\n• \"Disponibilidad para manicura el viernes\"\n\n¿En qué puedo ayudarte?",
            'en': "👋 Hello! I'm your smart booking assistant.\n\nI can help you book an appointment. For example:\n• \"I want a haircut tomorrow at 3pm\"\n• \"Availability for manicure on Friday\"\n\nHow can I help you?",
            'ca': "👋 Hola! Sóc el teu assistent de reserves intel·ligent.\n\nPuc ajudar-te a fer una reserva. Per exemple:\n• \"Vull un tall de cabell demà a les 3pm\"\n• \"Disponibilitat per a manicura el divendres\"\n\nEn què puc ajudar-te?",
            'uk': "👋 Привіт! Я ваш розумний асистент бронювання.\n\nЯ можу допомогти забронювати візит. Наприклад:\n• \"Хочу стрижку завтра о 3pm\"\n• \"Доступність для манікюру в п'ятницю\"\n\nЯк я можу допомогти?",
        },
        'conversation_cancelled': {
            'es': "❌ Conversación cancelada. Escribe cuando quieras hacer una reserva.",
            'en': "❌ Conversation cancelled. Write when you want to make a booking.",
            'ca': "❌ Conversa cancel·lada. Escriu quan vulguis fer una reserva.",
            'uk': "❌ Розмову скасовано. Напишіть, коли захочете зробити бронювання.",
        },
        'service_error': {
            'es': "⚠️ Lo siento, hay un problema con el servicio. Por favor, intenta más tarde o llama directamente al salón.",
            'en': "⚠️ Sorry, there's a problem with the service. Please try again later or call the salon directly.",
            'ca': "⚠️ Ho sento, hi ha un problema amb el servei. Si us plau, torna-ho a provar més tard o truca directament al saló.",
            'uk': "⚠️ Вибачте, проблема з сервісом. Будь ласка, спробуйте пізніше або зателефонуйте безпосередньо до салону.",
        },
        'help_message': {
            'es': "Puedo ayudarte a:\n• Hacer una reserva\n• Consultar disponibilidad\n• Ver servicios disponibles\n\n¿Qué necesitas?",
            'en': "I can help you:\n• Make a booking\n• Check availability\n• See available services\n\nWhat do you need?",
            'ca': "Puc ajudar-te a:\n• Fer una reserva\n• Consultar disponibilitat\n• Veure serveis disponibles\n\nQue necessites?",
            'uk': "Я можу допомогти вам:\n• Зробити бронювання\n• Перевірити доступність\n• Переглянути доступні послуги\n\nЩо вам потрібно?",
        },
    }
    
    message_dict = messages.get(key, {})
    template = message_dict.get(lang, message_dict.get('es', ''))
    
    # Format with kwargs if provided
    if kwargs:
        return template.format(**kwargs)
    return template
