"""
AI Handler using OpenAI for natural language understanding
"""
import json
import logging
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI not installed. Run: pip install openai")


class BookingAI:
    """Handle AI-powered booking intent extraction and response generation"""
    
    def __init__(self):
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI package not installed")
        
        api_key = getattr(settings, 'OPENAI_API_KEY', None)
        if not api_key:
            raise ValueError("OPENAI_API_KEY not configured in settings")
        
        self.client = OpenAI(api_key=api_key)
        self.model = getattr(settings, 'OPENAI_MODEL', 'gpt-4o-mini')  # Cost-effective model
    
    def extract_booking_intent(self, message: str, conversation_context: dict = None) -> dict:
        """
        Extract booking information from natural language message
        
        Returns:
        {
            'intent': 'book' | 'check_availability' | 'cancel' | 'modify' | 'question',
            'service': str or None,
            'date': 'YYYY-MM-DD' or None,
            'time': 'HH:MM' or None,
            'time_preference': 'morning' | 'afternoon' | 'evening' or None,
            'company_name': str or None,
            'staff_name': str or None,
            'customer_name': str or None,
            'confidence': float (0-1)
        }
        """
        system_prompt = """You are a booking assistant for a salon/spa appointment system.
Extract booking information from user messages. Today's date is {today}.

Key Rules:
- Detect intent: book, check_availability, cancel, modify, or question
- Extract service type (haircut, manicure, massage, etc.)
- Parse dates: "tomorrow", "next Monday", "15th", specific dates
- Parse times: "2pm", "14:00", "after lunch", "morning"
- Extract salon/company name if mentioned
- Extract customer name if mentioned
- Determine confidence level based on completeness

Respond ONLY with JSON, no other text.
""".format(today=timezone.now().strftime('%Y-%m-%d, %A'))
        
        user_message = f"Extract booking info from: {message}"
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                functions=[{
                    "name": "extract_booking_info",
                    "description": "Extract booking information from message",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "intent": {
                                "type": "string",
                                "enum": ["book", "check_availability", "cancel", "modify", "question", "greeting"]
                            },
                            "service": {"type": "string", "description": "Type of service requested"},
                            "date": {"type": "string", "description": "Date in YYYY-MM-DD format"},
                            "time": {"type": "string", "description": "Time in HH:MM format"},
                            "time_preference": {
                                "type": "string",
                                "enum": ["morning", "afternoon", "evening"],
                                "description": "General time preference if exact time not specified"
                            },
                            "company_name": {"type": "string", "description": "Salon/company name"},
                            "staff_name": {"type": "string", "description": "Specific staff member name"},
                            "customer_name": {"type": "string", "description": "Customer's name"},
                            "confidence": {
                                "type": "number",
                                "description": "Confidence level 0-1"
                            }
                        },
                        "required": ["intent", "confidence"]
                    }
                }],
                function_call={"name": "extract_booking_info"}
            )
            
            result = json.loads(response.choices[0].message.function_call.arguments)
            logger.info(f"AI extracted intent: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error extracting intent: {e}")
            return {
                'intent': 'question',
                'confidence': 0.0,
                'error': str(e)
            }
    
    def generate_response(self, context: dict, language: str = 'es') -> str:
        """
        Generate a natural language response based on context
        
        context should include:
        - response_type: 'show_slots', 'booking_confirmed', 'need_more_info', etc.
        - available_slots: list of dicts with time, staff, price
        - company: company info
        - service: service info
        - error_message: if any error occurred
        """
        response_type = context.get('response_type')
        
        if response_type == 'show_slots':
            return self._generate_slots_message(context, language)
        elif response_type == 'booking_confirmed':
            return self._generate_confirmation_message(context, language)
        elif response_type == 'need_more_info':
            return self._generate_clarification_message(context, language)
        elif response_type == 'error':
            return self._generate_error_message(context, language)
        else:
            return self._generate_generic_response(context, language)
    
    def _generate_slots_message(self, context: dict, language: str) -> str:
        """Generate message showing available time slots"""
        slots = context.get('available_slots', [])
        company = context.get('company')
        service = context.get('service')
        date = context.get('date')
        
        if not slots:
            if language == 'es':
                return f"Lo siento, no hay horarios disponibles para {service.name} en {company.name} el {date}. ¿Quieres probar otra fecha?"
            else:
                return f"Sorry, no available times for {service.name} at {company.name} on {date}. Try another date?"
        
        if language == 'es':
            message = f"✅ Horarios disponibles para {service.name} en {company.name} el {date}:\n\n"
            for idx, slot in enumerate(slots[:5], 1):  # Show max 5 options
                message += f"{idx}. {slot['time']} con {slot['staff']} (€{slot['price']}, {slot['duration']} min)\n"
            message += f"\n💬 Responde con el número para confirmar tu reserva."
        else:
            message = f"✅ Available times for {service.name} at {company.name} on {date}:\n\n"
            for idx, slot in enumerate(slots[:5], 1):
                message += f"{idx}. {slot['time']} with {slot['staff']} (€{slot['price']}, {slot['duration']} min)\n"
            message += f"\n💬 Reply with the number to confirm."
        
        return message
    
    def _generate_confirmation_message(self, context: dict, language: str) -> str:
        """Generate booking confirmation message"""
        booking = context.get('booking')
        
        if language == 'es':
            return f"""✅ ¡Reserva confirmada!

📍 {booking.company.name}
💇 {booking.service.name}
👤 {booking.staff.name}
📅 {booking.date.strftime('%d/%m/%Y')}
🕐 {booking.start_time.strftime('%H:%M')}
💰 €{booking.price}

Recibirás un email de confirmación. Para cancelar, responde CANCELAR."""
        else:
            return f"""✅ Booking confirmed!

📍 {booking.company.name}
💇 {booking.service.name}
👤 {booking.staff.name}
📅 {booking.date.strftime('%Y-%m-%d')}
🕐 {booking.start_time.strftime('%H:%M')}
💰 €{booking.price}

You'll receive a confirmation email. To cancel, reply CANCEL."""
    
    def _generate_clarification_message(self, context: dict, language: str) -> str:
        """Ask for missing information"""
        missing = context.get('missing_fields', [])
        
        if language == 'es':
            if 'service' in missing:
                return "¿Qué servicio necesitas? (corte de pelo, manicura, masaje, etc.)"
            elif 'date' in missing:
                return "¿Para qué día quieres la cita?"
            elif 'company' in missing:
                return "¿En qué salón quieres reservar?"
            elif 'customer_name' in missing:
                return "¿Cuál es tu nombre?"
        else:
            if 'service' in missing:
                return "What service do you need? (haircut, manicure, massage, etc.)"
            elif 'date' in missing:
                return "What date do you want?"
            elif 'company' in missing:
                return "Which salon?"
            elif 'customer_name' in missing:
                return "What's your name?"
        
        return "Could you provide more details about your booking?"
    
    def _generate_error_message(self, context: dict, language: str) -> str:
        """Generate error message"""
        error = context.get('error_message', '')
        
        if language == 'es':
            return f"❌ Hubo un problema: {error}\n\nPor favor, intenta de nuevo o contacta con el salón directamente."
        else:
            return f"❌ There was a problem: {error}\n\nPlease try again or contact the salon directly."
    
    def _generate_generic_response(self, context: dict, language: str) -> str:
        """Generic helpful response"""
        if language == 'es':
            return """👋 ¡Hola! Soy tu asistente de reservas.

Puedes decirme algo como:
"Quiero reservar un corte de pelo mañana a las 3pm"
"Disponibilidad para manicura el viernes"

¿Cómo puedo ayudarte?"""
        else:
            return """👋 Hi! I'm your booking assistant.

You can say something like:
"I want to book a haircut tomorrow at 3pm"
"Availability for manicure on Friday"

How can I help?"""
