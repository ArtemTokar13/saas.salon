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
        current_state__in=['idle', 'collecting_info', 'showing_slots', 'confirming'],
        defaults={'current_state': 'idle'}
    )
    
    if created:
        logger.info(f"Created new conversation for {phone_number}")
    
    return conversation


def process_message(conversation: WhatsAppConversation, message: str) -> str:
    """
    Process incoming message and return response
    
    Flow:
    1. Check if it's a simple number selection (confirming a slot)
    2. Use AI to extract intent
    3. Search for availability
    4. Generate response
    """
    
    # Check if user is confirming a slot selection
    if conversation.current_state == 'showing_slots':
        if message.isdigit():
            return handle_slot_selection(conversation, int(message))
    
    # Check for cancellation keywords
    if message.lower() in ['cancelar', 'cancel', 'stop', 'exit']:
        conversation.current_state = 'idle'
        conversation.conversation_state = {}
        conversation.save()
        return "❌ Conversación cancelada. Escribe cuando quieras hacer una reserva."
    
    # Use AI to extract intent
    try:
        ai = BookingAI()
        intent_data = ai.extract_booking_intent(message, conversation.conversation_state)
    except Exception as e:
        logger.error(f"AI error: {e}")
        return "⚠️ Lo siento, hay un problema con el servicio. Por favor, intenta más tarde o llama directamente al salón."
    
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


def handle_greeting(conversation: WhatsAppConversation) -> str:
    """Handle greeting message"""
    return """👋 ¡Hola! Soy tu asistente de reservas inteligente.

Puedo ayudarte a reservar una cita. Por ejemplo:
• "Quiero un corte de pelo mañana a las 3pm"
• "Disponibilidad para manicura el viernes"
• "Reserva masaje para el lunes por la tarde"

¿En qué puedo ayudarte?"""


def handle_booking_request(conversation: WhatsAppConversation, intent_data: dict) -> str:
    """Handle booking or availability check request"""
    searcher = BookingSearcher()
    
    # Extract information
    company_name = intent_data.get('company_name')
    service_name = intent_data.get('service')
    date_str = intent_data.get('date')
    time_str = intent_data.get('time')
    time_preference = intent_data.get('time_preference')
    customer_name = intent_data.get('customer_name')
    
    # Update conversation state
    state = conversation.conversation_state
    if company_name:
        state['company_name'] = company_name
    if service_name:
        state['service_name'] = service_name
    if date_str:
        state['date'] = date_str
    if time_str:
        state['time'] = time_str
    if time_preference:
        state['time_preference'] = time_preference
    if customer_name:
        state['customer_name'] = customer_name
    
    conversation.conversation_state = state
    conversation.save()
    
    # Find company
    company = None
    if state.get('company_name'):
        company = searcher.find_company(state['company_name'])
    
    if not company:
        # If only one company exists, use it
        from companies.models import Company
        companies = Company.objects.filter(online_appointments_enabled=True)
        if companies.count() == 1:
            company = companies.first()
        else:
            return "¿En qué salón te gustaría reservar? Por favor, indica el nombre."
    
    # Find service
    service = None
    if state.get('service_name'):
        service = searcher.find_service(company, state['service_name'])
    
    if not service:
        # List available services
        from companies.models import Service
        services = Service.objects.filter(company=company, is_active=True)[:10]
        if services.exists():
            service_list = "\n".join([f"• {s.name}" for s in services])
            return f"¿Qué servicio necesitas?\n\nServicios disponibles:\n{service_list}"
        else:
            return "No hay servicios disponibles en este salón."
    
    # Check date
    if not state.get('date'):
        return "¿Para qué día quieres la cita? (ej: mañana, viernes, 15 de marzo)"
    
    try:
        booking_date = datetime.strptime(state['date'], '%Y-%m-%d').date()
    except:
        return "No entendí la fecha. ¿Podrías especificarla? (ej: mañana, próximo lunes, 15/03/2026)"
    
    # Check if date is in the past
    if booking_date < timezone.now().date():
        return "Esa fecha ya pasó. Por favor, elige una fecha futura."
    
    # Find available slots
    try:
        slots = searcher.find_available_slots(
            company, 
            service, 
            booking_date, 
            state.get('time_preference')
        )
    except Exception as e:
        logger.error(f"Error finding slots: {e}")
        return f"⚠️ Hubo un problema buscando disponibilidad. Por favor, intenta de nuevo."
    
    if not slots:
        return f"😔 Lo siento, no hay horarios disponibles para {service.name} el {booking_date.strftime('%d/%m/%Y')}.\n\n¿Quieres probar otra fecha?"
    
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
    ai = BookingAI()
    response = ai.generate_response({
        'response_type': 'show_slots',
        'available_slots': slots[:5],
        'company': company,
        'service': service,
        'date': booking_date.strftime('%d/%m/%Y')
    })
    
    return response


def handle_slot_selection(conversation: WhatsAppConversation, slot_number: int) -> str:
    """Handle when user selects a time slot by number"""
    try:
        pending = PendingBooking.objects.get(conversation=conversation)
    except PendingBooking.DoesNotExist:
        return "⚠️ No encontré una reserva pendiente. Por favor, empieza de nuevo."
    
    # Validate slot number
    if slot_number < 1 or slot_number > len(pending.available_slots):
        return f"⚠️ Por favor, elige un número entre 1 y {len(pending.available_slots)}."
    
    # Get selected slot
    slot = pending.available_slots[slot_number - 1]
    
    # Check if we have customer name
    customer_name = conversation.conversation_state.get('customer_name')
    if not customer_name:
        # Extract name from phone or ask
        conversation.current_state = 'collecting_info'
        conversation.conversation_state['selected_slot'] = slot
        conversation.save()
        return "✅ Perfecto! ¿Cuál es tu nombre completo?"
    
    # Create booking
    return create_booking_from_pending(conversation, pending, slot, customer_name)


def create_booking_from_pending(conversation: WhatsAppConversation, 
                                pending: PendingBooking, 
                                slot: dict, 
                                customer_name: str) -> str:
    """Create the actual booking"""
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
        conversation.conversation_state = {}
        conversation.save()
        
        # Update pending booking
        pending.created_booking = booking
        pending.save()
        
        # Generate confirmation message
        ai = BookingAI()
        response = ai.generate_response({
            'response_type': 'booking_confirmed',
            'booking': booking
        })
        
        return response
        
    except Exception as e:
        logger.error(f"Error creating booking: {e}")
        return f"❌ Hubo un error al crear la reserva: {str(e)}\n\nPor favor, intenta de nuevo o contacta directamente con el salón."


def handle_question(conversation: WhatsAppConversation, message: str) -> str:
    """Handle general questions"""
    # You could use AI here to answer FAQs
    return """Puedo ayudarte a:
• Hacer una reserva
• Consultar disponibilidad
• Ver servicios disponibles

¿Qué necesitas?"""
