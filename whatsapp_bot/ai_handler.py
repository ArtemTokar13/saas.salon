"""
AI Handler for WhatsApp Booking Bot
Uses OpenAI to extract booking intent and generate natural language responses
"""
import logging
from typing import Dict, Any
from datetime import datetime
import json
from django.conf import settings

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

logger = logging.getLogger(__name__)


class BookingAI:
    """AI-powered booking assistant"""
    
    def __init__(self):
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI library not installed. Install with: pip install openai")
        
        api_key = getattr(settings, 'OPENAI_API_KEY', None)
        if not api_key:
            raise ValueError("OPENAI_API_KEY not configured in settings")
        
        self.client = OpenAI(api_key=api_key)
        self.model = getattr(settings, 'OPENAI_MODEL', 'gpt-4o-mini')
    
    def extract_booking_intent(self, message: str, conversation_state: dict) -> Dict[str, Any]:
        """
        Extract booking intent from natural language message
        
        Returns:
        {
            'intent': 'greeting'|'book'|'check_availability'|'question',
            'company_name': str (optional),
            'service': str (optional),
            'date': str (optional, YYYY-MM-DD),
            'time': str (optional, HH:MM),
            'time_preference': 'morning'|'afternoon'|'evening' (optional),
            'customer_name': str (optional)
        }
        """
        lang = conversation_state.get('language', 'es')
        
        system_prompt = f"""You are a booking assistant AI. Extract booking information from user messages.
Current language: {lang}

Return JSON with these fields:
- intent: "greeting", "book", "check_availability", or "question"
- company_name: salon/company name (if mentioned)
- service: service type requested
- date: date in YYYY-MM-DD format
- time: specific time in HH:MM format
- time_preference: "morning" (before 12pm), "afternoon" (12pm-6pm), or "evening" (after 6pm)
- customer_name: customer's name

Examples of time expressions:
- "mañana" -> tomorrow's date
- "próximo viernes" -> next Friday's date
- "3pm" -> 15:00
- "por la tarde" -> time_preference: "afternoon"

Be flexible with service names:
- "corte", "corte de pelo", "haircut" -> "corte de pelo"
- "manicura", "manicure", "uñas" -> "manicura"
- "tinte", "color", "coloración" -> "tinte"

Current date: {datetime.now().strftime('%Y-%m-%d')}"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            logger.info(f"AI extracted intent: {result}")
            return result
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            # Fallback: simple intent detection
            return self._fallback_intent_detection(message)
    
    def _fallback_intent_detection(self, message: str) -> Dict[str, Any]:
        """Simple fallback if AI fails"""
        message_lower = message.lower()
        
        # Check for booking keywords
        booking_keywords = ['reservar', 'reserva', 'cita', 'book', 'appointment', 'agendar']
        if any(word in message_lower for word in booking_keywords):
            return {'intent': 'book'}
        
        # Check for greeting
        greeting_keywords = ['hola', 'hello', 'hi', 'buenos', 'buenas', 'привіт']
        if any(word in message_lower for word in greeting_keywords):
            return {'intent': 'greeting'}
        
        return {'intent': 'question'}
    
    def generate_response(self, data: Dict[str, Any]) -> str:
        """
        Generate natural language response based on conversation state
        
        data can contain:
        - response_type: 'show_slots', 'booking_confirmed', 'error'
        - available_slots: list of slots
        - booking: Booking object
        - company, service, date, etc.
        """
        response_type = data.get('response_type')
        lang = data.get('language', 'es')
        
        if response_type == 'show_slots':
            return self._generate_slots_message(
                data['available_slots'],
                data.get('company'),
                data.get('service'),
                data.get('date'),
                lang
            )
        elif response_type == 'booking_confirmed':
            return self._generate_confirmation_message(
                data['booking'],
                lang
            )
        
        return self._generate_generic_response(data, lang)
    
    def _generate_slots_message(self, slots: list, company, service, date: str, lang: str) -> str:
        """Generate available slots message"""
        messages = {
            'es': {
                'header': "✅ Horarios disponibles para {service} el {date}:\n\n",
                'slot': "{num}. {time} - {staff}\n",
                'footer': "\n📝 Responde con el número de tu opción preferida (1-{count})."
            },
            'en': {
                'header': "✅ Available times for {service} on {date}:\n\n",
                'slot': "{num}. {time} - {staff}\n",
                'footer': "\n📝 Reply with your preferred option number (1-{count})."
            },
            'ca': {
                'header': "✅ Horaris disponibles per {service} el {date}:\n\n",
                'slot': "{num}. {time} - {staff}\n",
                'footer': "\n📝 Respon amb el número de la teva opció preferida (1-{count})."
            },
            'uk': {
                'header': "✅ Доступні часи для {service} {date}:\n\n",
                'slot': "{num}. {time} - {staff}\n",
                'footer': "\n📝 Відповідайте номером вашого варіанту (1-{count})."
            }
        }
        
        templates = messages.get(lang, messages['es'])
        
        response = templates['header'].format(
            service=service.name if service else '',
            date=date
        )
        
        for idx, slot in enumerate(slots, 1):
            response += templates['slot'].format(
                num=idx,
                time=slot['time'],
                staff=slot['staff_name']
            )
        
        response += templates['footer'].format(count=len(slots))
        return response
    
    def _generate_confirmation_message(self, booking, lang: str) -> str:
        """Generate booking confirmation message"""
        messages = {
            'es': """✅ ¡Reserva confirmada!

📅 Fecha: {date}
🕐 Hora: {time}
✂️ Servicio: {service}
👤 Especialista: {staff}
📍 Salón: {company}

📧 Recibirás un email de confirmación.

¡Nos vemos pronto! 👋""",
            'en': """✅ Booking confirmed!

📅 Date: {date}
🕐 Time: {time}
✂️ Service: {service}
👤 Specialist: {staff}
📍 Salon: {company}

📧 You'll receive a confirmation email.

See you soon! 👋""",
            'ca': """✅ Reserva confirmada!

📅 Data: {date}
🕐 Hora: {time}
✂️ Servei: {service}
👤 Especialista: {staff}
📍 Saló: {company}

📧 Rebràs un correu de confirmació.

Ens veiem aviat! 👋""",
            'uk': """✅ Бронювання підтверджено!

📅 Дата: {date}
🕐 Час: {time}
✂️ Послуга: {service}
👤 Спеціаліст: {staff}
📍 Салон: {company}

📧 Ви отримаєте електронний лист з підтвердженням.

До зустрічі! 👋"""
        }
        
        template = messages.get(lang, messages['es'])
        
        return template.format(
            date=booking.date.strftime('%d/%m/%Y'),
            time=booking.start_time.strftime('%H:%M'),
            service=booking.service.name,
            staff=booking.staff.name,
            company=booking.company.name
        )
    
    def _generate_generic_response(self, data: Dict[str, Any], lang: str) -> str:
        """Generate generic AI response"""
        # For now, return a simple message
        # You can enhance this with OpenAI later if needed
        messages = {
            'es': "¿En qué puedo ayudarte?",
            'en': "How can I help you?",
            'ca': "En què puc ajudar-te?",
            'uk': "Як я можу допомогти?"
        }
        return messages.get(lang, messages['es'])
