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
        
        # Generate upcoming dates with day names for context
        from datetime import timedelta
        today = datetime.now().date()
        upcoming_dates = []
        day_names = {
            0: {'es': 'lunes', 'en': 'Monday', 'ru': 'понедельник', 'uk': 'понеділок'},
            1: {'es': 'martes', 'en': 'Tuesday', 'ru': 'вторник', 'uk': 'вівторок'},
            2: {'es': 'miércoles', 'en': 'Wednesday', 'ru': 'среда', 'uk': 'середа'},
            3: {'es': 'jueves', 'en': 'Thursday', 'ru': 'четверг', 'uk': 'четвер'},
            4: {'es': 'viernes', 'en': 'Friday', 'ru': 'пятница', 'uk': 'п\'ятниця'},
            5: {'es': 'sábado', 'en': 'Saturday', 'ru': 'суббота', 'uk': 'субота'},
            6: {'es': 'domingo', 'en': 'Sunday', 'ru': 'воскресенье', 'uk': 'неділя'}
        }
        
        for i in range(14):  # Next 14 days
            date = today + timedelta(days=i)
            day_num = date.weekday()
            day_name = day_names[day_num][lang]
            upcoming_dates.append(f"  - {day_name} = {date.strftime('%Y-%m-%d')}")
        
        dates_reference = "\n".join(upcoming_dates)
        today_name = day_names[today.weekday()][lang]
        
        system_prompt = f"""You are a booking assistant AI. Extract booking information from user messages.
Current language: {lang}
Today is {today_name}, {today.strftime('%Y-%m-%d')}

CRITICAL - Date/Day Reference Calendar:
{dates_reference}

DATE EXTRACTION RULES (PRIORITY ORDER):
1. DIRECT DATE NUMBER (highest priority): 
   - "27 апреля" = April 27 → date: "2026-04-27"
   - "21 апреля" = April 21 → date: "2026-04-21"
   - "20 числа" = 20th → date: "2026-04-20"
   - If user gives a number (20, 21, 27), use THAT number as the day of April 2026
   
2. DAY NAME ONLY (when no date number given):
   - "понедельник" → Find "понедельник" in calendar above → Use that exact date
   - "пятницу" → Find "пятница" in calendar above → Use that exact date
   - MUST use calendar lookup, do NOT calculate

3. NEVER change the date number the user provides

Return JSON with these fields:
- intent: "greeting", "book", "check_availability", or "question"
- company_name: salon/company name (if mentioned)
- service: service type requested
- staff_name: ONLY extract if user EXPLICITLY mentions a staff member name (e.g., "с Анной", "with Anna", "у Наталії"). DO NOT extract if no staff mentioned!
- date: date in YYYY-MM-DD format
- time: specific exact time in HH:MM format (e.g., "15:00", "3pm"->"15:00")
- time_after: minimum time constraint in HH:MM format (e.g., "після 16:00"->"16:00", "after 3pm"->"15:00")
- time_before: maximum time constraint in HH:MM format (e.g., "до 17:00"->"17:00", "before 5pm"->"17:00")
- time_preference: "morning" (before 12pm), "afternoon" (12pm-6pm), or "evening" (after 6pm) - ONLY if no specific time/time_after/time_before
- customer_name: customer's name

INTENT CLASSIFICATION:
- "greeting": ONLY first-time hello/hi messages like "Привіт", "Hello", "Hola"
- "book": ANY booking-related request like "Хочу записаться", "Сделать бронирование", "Book", "Reservar", "Make booking"
- "check_availability": When asking about availability without booking
- "question": General questions about services, prices, etc.

Time extraction priority:
1. SPECIFIC TIME CONSTRAINTS: "після 16:00"/"after 16:00" -> time_after="16:00"
2. EXACT TIME: "о 15:00"/"at 3pm" -> time="15:00"
3. GENERAL PREFERENCE: "пізніше"/"later" -> time_preference="afternoon"

Multilingual booking keywords:
- Spanish: "reservar", "reserva", "cita", "agendar"
- English: "book", "booking", "appointment", "schedule"
- Russian: "забронировать", "бронирование", "записаться", "запись"
- Ukrainian: "забронювати", "бронювання", "записатися"

Multilingual examples:
- "після 16:00" -> time_after: "16:00"
- "после 16:00" -> time_after: "16:00"
- "after 4pm" -> time_after: "16:00"
- "до 17:00" -> time_before: "17:00"
- "antes de las 5" -> time_before: "17:00"
- "в Наталі" / "у Наталі" / "con Natali" / "with Natali" -> staff_name: "Natali"

Service name extraction (CRITICAL - PRESERVE ALL WORDS):
1. Extract the COMPLETE service name with ALL descriptive words
2. Keep the ORIGINAL language - do NOT translate service names
3. Examples of CORRECT extraction:
   - Spanish: "Manicura sin pintar" -> "Manicura sin pintar" (NOT just "manicura")
   - Spanish: "Manicura semipermanente" -> "Manicura semipermanente"
   - Spanish: "Manicura japonesa" -> "Manicura japonesa"
   - Russian: "японский маникюр" -> "японский маникюр" (NOT just "маникюр")
   - Russian: "маникюр без покрытия" -> "маникюр без покрытия"
   - Ukrainian: "японський манікюр" -> "японський манікюр"
4. NEVER simplify or shorten - keep ALL words the user provides"""
        
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
