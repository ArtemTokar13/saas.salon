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
    
    def _get_day_names_calendar(self, lang: str) -> tuple:
        """Generate calendar reference for date extraction"""
        from datetime import timedelta
        today = datetime.now().date()
        
        day_names = {
            0: {'es': 'lunes', 'en': 'Monday', 'ru': 'понедельник', 'uk': 'понеділок'},
            1: {'es': 'martes', 'en': 'Tuesday', 'ru': 'вторник', 'uk': 'вівторок'},
            2: {'es': 'miércoles', 'en': 'Wednesday', 'ru': 'среда', 'uk': 'середа'},
            3: {'es': 'jueves', 'en': 'Thursday', 'ru': 'четверг', 'uk': 'четвер'},
            4: {'es': 'viernes', 'en': 'Friday', 'ru': 'пятница', 'uk': 'п\'ятниця'},
            5: {'es': 'sábado', 'en': 'Saturday', 'ru': 'суббота', 'uk': 'субота'},
            6: {'es': 'domingo', 'en': 'Sunday', 'ru': 'воскресенье', 'uk': 'неділя'}
        }
        
        upcoming_dates = []
        for i in range(14):  # Next 14 days
            date = today + timedelta(days=i)
            day_num = date.weekday()
            day_name = day_names[day_num][lang]
            upcoming_dates.append(f"  - {day_name} = {date.strftime('%Y-%m-%d')}")
        
        dates_reference = "\n".join(upcoming_dates)
        today_name = day_names[today.weekday()][lang]
        
        return today, today_name, dates_reference
    
    def _build_date_extraction_prompt(self, dates_reference: str) -> str:
        """Build focused prompt for date extraction"""
        return f"""📅 DATE EXTRACTION RULES (PRIORITY ORDER):

Calendar Reference:
{dates_reference}

Rules:
1. DIRECT DATE NUMBER (highest priority): 
   - "27 апреля" = April 27 → use that exact number
   - "21 числа" = 21st → use that exact number
   - NEVER change the date number the user provides
   
2. DAY NAME ONLY (when no date number given):
   - "понедельник" → Find in calendar above → Use that exact date
   - "пятницу" → Find in calendar above → Use that exact date
   - MUST use calendar lookup, do NOT calculate

3. Extract BOTH date and time when present:
   - "На вторник после 17:00" -> date AND time_after"""
    
    def _build_time_extraction_prompt(self) -> str:
        """Build focused prompt for time extraction"""
        return """⏰ TIME EXTRACTION (only with specific times):

Extract time ONLY if user provides a specific time like "14:00" or "3pm".
Ignore vague words like "later", "позже" without specific times.

Types:
- EXACT TIME: "в 14:00" / "at 2pm" → time: "14:00"
  Keywords: "в", "на", "at", "a las"
  
- AFTER: "после 16:00" / "after 4pm" / "після 17:00" → time_after: "16:00"
  Keywords: "после", "після", "después de", "after"
  
- BEFORE: "до 17:00" / "before 5pm" → time_before: "17:00"
  Keywords: "до", "antes de", "before"

Examples:
  - "после 16:00" → time_after: "16:00"
  - "до 17:00" → time_before: "17:00"
  - "в 14:00" → time: "14:00"
  - "позже" (no time) → DO NOT EXTRACT"""
    
    def _build_service_extraction_prompt(self) -> str:
        """Build focused prompt for service name extraction"""
        return """💅 SERVICE NAME EXTRACTION:

CRITICAL: Extract the COMPLETE service name with ALL descriptive words.
Keep the ORIGINAL language - do NOT translate.
NEVER simplify or shorten.

Examples:
  ✅ CORRECT:
    - Spanish: "Manicura sin pintar" → "Manicura sin pintar"
    - Spanish: "Manicura semipermanente" → "Manicura semipermanente"
    - Russian: "японский маникюр" → "японский маникюр"
    - Russian: "маникюр без покрытия" → "маникюр без покрытия"
  
  ❌ WRONG:
    - "Manicura sin pintar" → "manicura" (missing words!)
    - "японский маникюр" → "маникюр" (missing adjective!)"""
    
    def _build_staff_extraction_prompt(self) -> str:
        """Build focused prompt for staff name extraction"""
        return """👤 STAFF NAME EXTRACTION:

Extract staff name ONLY if user EXPLICITLY mentions it.

Keywords indicating staff:
  - Spanish: "con", "de"
  - Russian: "с", "у"
  - Ukrainian: "в", "у", "з"
  - English: "with"

Examples:
  ✅ Extract: "с Анной", "con Maria", "у Наталії", "with Sarah"
  ❌ Do NOT extract: Just service name without staff mention"""
    
    def _build_output_format_prompt(self) -> str:
        """Build prompt for output format specification"""
        return """📤 OUTPUT FORMAT:

Return JSON with these fields (ONLY include fields mentioned in message):
  - service: service name (complete, original language)
  - staff_name: staff name (only if explicitly mentioned)
  - date: date in YYYY-MM-DD format
  - time: specific time in HH:MM format
  - time_after: minimum time in HH:MM
  - time_before: maximum time in HH:MM
  - customer_name: customer's name (if mentioned)

Do NOT include fields that are not mentioned in the message."""
    
    def _build_extraction_prompt(self, lang: str) -> str:
        """Build complete extraction prompt from modular components"""
        today, today_name, dates_reference = self._get_day_names_calendar(lang)
        
        return f"""You are a booking assistant AI. Extract booking information from user messages.
Current language: {lang}
Today is {today_name}, {today.strftime('%Y-%m-%d')}

TASK: Extract ONLY the booking details mentioned in the message.
Do NOT invent or assume information.

{self._build_date_extraction_prompt(dates_reference)}

{self._build_time_extraction_prompt()}

{self._build_service_extraction_prompt()}

{self._build_staff_extraction_prompt()}

{self._build_output_format_prompt()}"""
    
    def extract_booking_intent(self, message: str, conversation_state: dict) -> Dict[str, Any]:
        """
        Extract booking intent from natural language message
        
        Returns dict with extracted booking information
        """
        lang = conversation_state.get('language', 'es')
        
        # Build the system prompt from modular components
        system_prompt = self._build_extraction_prompt(lang)
        
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
        """Simple fallback if AI fails - just return empty dict"""
        return {}
    
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
            'ru': {
                'header': "✅ Доступное время для {service} {date}:\n\n",
                'slot': "{num}. {time} - {staff}\n",
                'footer': "\n📝 Ответьте номером вашего варианта (1-{count})."
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
                staff=slot['staff']
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

¡Nos vemos pronto! 👋""",
            'en': """✅ Booking confirmed!

📅 Date: {date}
🕐 Time: {time}
✂️ Service: {service}
👤 Specialist: {staff}
📍 Salon: {company}

See you soon! 👋""",
            'ru': """✅ Бронирование подтверждено!

📅 Дата: {date}
🕐 Время: {time}
✂️ Услуга: {service}
👤 Специалист: {staff}
📍 Салон: {company}

До встречи! 👋""",
            'uk': """✅ Бронювання підтверджено!

📅 Дата: {date}
🕐 Час: {time}
✂️ Послуга: {service}
👤 Спеціаліст: {staff}
📍 Салон: {company}

До зустрічі! 👋"""
        }
        
        template = messages.get(lang, messages['es'])
        
        # Generate booking URL
        from django.conf import settings
        booking_url = f"{settings.SITE_URL}/es/bookings/confirmation/{booking.id}/" if hasattr(settings, 'SITE_URL') else f"https://reserva-ya.es/es/bookings/confirmation/{booking.id}/"
        
        response = template.format(
            date=booking.date.strftime('%d/%m/%Y'),
            time=booking.start_time.strftime('%H:%M'),
            service=booking.service.name,
            staff=booking.staff.name,
            company=booking.company.name
        )
        
        # Add booking link
        link_messages = {
            'es': f"\n🔗 Ver detalles: {booking_url}",
            'en': f"\n🔗 View details: {booking_url}",
            'ru': f"\n🔗 Просмотреть детали: {booking_url}",
            'uk': f"\n🔗 Переглянути деталі: {booking_url}"
        }
        response += link_messages.get(lang, link_messages['es'])
        
        return response
    
    def _generate_generic_response(self, data: Dict[str, Any], lang: str) -> str:
        """Generate generic AI response"""
        # For now, return a simple message
        # You can enhance this with OpenAI later if needed
        messages = {
            'es': "¿En qué puedo ayudarte?",
            'en': "How can I help you?",
            'ru': "Чем могу помочь?",
            'uk': "Як я можу допомогти?"
        }
        return messages.get(lang, messages['es'])
