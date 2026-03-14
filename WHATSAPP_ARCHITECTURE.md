# WhatsApp AI Booking Bot - Architecture & Implementation

## 🎯 Overview

This integration enables clients to book salon appointments via WhatsApp using natural language. The AI understands messages like "I want a haircut tomorrow at 3pm" and automatically finds available slots and creates bookings.

## 📊 Architecture Diagram

```
┌─────────────────┐
│   WhatsApp      │
│     Client      │
└────────┬────────┘
         │ "I want haircut tomorrow 3pm"
         ▼
┌─────────────────┐
│  Twilio API     │  (WhatsApp Business API)
│  Message Gateway│
└────────┬────────┘
         │ HTTP POST
         ▼
┌─────────────────────────────────────────────────┐
│             Django Application                   │
│  ┌───────────────────────────────────────────┐  │
│  │  /whatsapp/webhook/                       │  │
│  │  - Verify Twilio signature                │  │
│  │  - Log message                            │  │
│  └─────────────┬─────────────────────────────┘  │
│                ▼                                 │
│  ┌───────────────────────────────────────────┐  │
│  │  AI Handler (OpenAI GPT-4o-mini)          │  │
│  │  - Extract intent (book/check/cancel)     │  │
│  │  - Parse: service, date, time, company    │  │
│  │  - NLP: "tomorrow" → 2026-03-15          │  │
│  └─────────────┬─────────────────────────────┘  │
│                ▼                                 │
│  ┌───────────────────────────────────────────┐  │
│  │  Booking Searcher                         │  │
│  │  - Fuzzy match company name               │  │
│  │  - Find service                           │  │
│  │  - Check staff availability               │  │
│  │  - Calculate time slots                   │  │
│  └─────────────┬─────────────────────────────┘  │
│                ▼                                 │
│  ┌───────────────────────────────────────────┐  │
│  │  Database (PostgreSQL)                    │  │
│  │  - Companies, Services, Staff             │  │
│  │  - Bookings, Working Hours                │  │
│  │  - Conversation State                     │  │
│  └─────────────┬─────────────────────────────┘  │
│                ▼                                 │
│  ┌───────────────────────────────────────────┐  │
│  │  Response Generator                       │  │
│  │  - Format available slots                 │  │
│  │  - Multilingual (ES/EN/CA/UK)            │  │
│  │  - Confirmation messages                  │  │
│  └─────────────┬─────────────────────────────┘  │
└────────────────┼─────────────────────────────────┘
                 │ TwiML Response
                 ▼
         ┌───────────────┐
         │  Twilio API   │
         └───────┬───────┘
                 │ "✅ Available times:
                 │  1. 2:00 PM with Maria..."
                 ▼
         ┌───────────────┐
         │   WhatsApp    │
         │     Client    │
         └───────────────┘
```

## 🔄 Conversation Flow Example

```
┌──────────────────────────────────────────────────────────────┐
│ Step 1: Client sends natural language request                │
└──────────────────────────────────────────────────────────────┘
Client: "Quiero reservar un corte de pelo mañana a las 3pm 
         en Peluquería UJI"

         ↓ [Twilio receives & forwards to webhook]

┌──────────────────────────────────────────────────────────────┐
│ Step 2: AI extracts structured data                          │
└──────────────────────────────────────────────────────────────┘
OpenAI GPT-4o-mini analyzes message:
{
  "intent": "book",
  "service": "corte de pelo",
  "date": "2026-03-15",  # tomorrow
  "time": "15:00",       # 3pm
  "company_name": "Peluquería UJI",
  "confidence": 0.95
}

         ↓

┌──────────────────────────────────────────────────────────────┐
│ Step 3: Search for company & service                         │
└──────────────────────────────────────────────────────────────┘
Fuzzy matching finds:
  Company: "Peluqueria UJI" (98% match)
  Service: "Corte de Pelo" (exact match)

         ↓

┌──────────────────────────────────────────────────────────────┐
│ Step 4: Check availability                                   │
└──────────────────────────────────────────────────────────────┘
System checks:
  - Staff working on Friday (2026-03-15) ✅
  - Working hours: 9:00 - 19:00 ✅
  - Existing bookings ✅
  - Break times ✅
  - Service duration (30 min) ✅

Available slots found:
  14:30 - Maria
  15:00 - Maria
  15:30 - Juan
  16:00 - Maria

         ↓

┌──────────────────────────────────────────────────────────────┐
│ Step 5: Present options to client                            │
└──────────────────────────────────────────────────────────────┘
Bot: "✅ Horarios disponibles para Corte de Pelo en 
      Peluquería UJI el 15/03/2026:

      1. 14:30 con Maria (€25, 30 min)
      2. 15:00 con Maria (€25, 30 min)
      3. 15:30 con Juan (€25, 30 min)
      4. 16:00 con Maria (€25, 30 min)

      💬 Responde con el número para confirmar."

         ↓

┌──────────────────────────────────────────────────────────────┐
│ Step 6: Client selects option                                │
└──────────────────────────────────────────────────────────────┘
Client: "2"

         ↓

┌──────────────────────────────────────────────────────────────┐
│ Step 7: Confirm customer name                                │
└──────────────────────────────────────────────────────────────┘
Bot: "✅ Perfecto! ¿Cuál es tu nombre completo?"
Client: "Juan Pérez"

         ↓

┌──────────────────────────────────────────────────────────────┐
│ Step 8: Create booking in database                           │
└──────────────────────────────────────────────────────────────┘
System creates:
  - Customer record (Juan Pérez, +34...)
  - Booking record (confirmed)
  - Sends email confirmation

         ↓

┌──────────────────────────────────────────────────────────────┐
│ Step 9: Send confirmation                                    │
└──────────────────────────────────────────────────────────────┘
Bot: "✅ ¡Reserva confirmada!

      📍 Peluquería UJI
      💇 Corte de Pelo
      👤 Maria
      📅 15/03/2026
      🕐 15:00
      💰 €25

      Recibirás un email de confirmación. 
      Para cancelar, responde CANCELAR."
```

## 🗃️ Database Schema

### New Tables

```sql
-- WhatsApp Conversations (tracks conversation context)
whatsapp_bot_whatsappconversation
  - id
  - phone_number (e.g., whatsapp:+34612345678)
  - customer_id → bookings_customer
  - company_id → companies_company
  - conversation_state (JSON: parsed data)
  - current_state (idle/collecting_info/showing_slots/confirming)
  - created_at, updated_at, last_message_at

-- WhatsApp Messages (full message log)
whatsapp_bot_whatsappmessage
  - id
  - conversation_id → whatsapp_bot_whatsappconversation
  - from_number, to_number
  - message_body (TEXT)
  - direction (inbound/outbound)
  - message_sid (Twilio ID)
  - created_at

-- Pending Bookings (temporary storage while confirming)
whatsapp_bot_pendingbooking
  - id
  - conversation_id → whatsapp_bot_whatsappconversation
  - company_id, service_id, staff_id
  - booking_date, booking_time
  - available_slots (JSON array)
  - customer_name
  - created_booking_id → bookings_booking
  - created_at, updated_at
```

## 💡 Key Features

### 1. Natural Language Understanding
- **Multilingual**: Spanish, English, Catalan, Ukrainian
- **Flexible Input**: "tomorrow", "próximo lunes", "15/03/2026"
- **Fuzzy Matching**: "Peluqueria UjI" → "Peluquería UJI"
- **Context Aware**: Remembers previous messages in conversation

### 2. Smart Availability Search
- ✅ Checks staff working days
- ✅ Respects working hours
- ✅ Avoids existing bookings
- ✅ Handles break times
- ✅ Considers service duration
- ✅ Time preferences (morning/afternoon/evening)

### 3. Conversation State Management
- Tracks multi-step conversations
- Handles incomplete information gracefully
- Allows corrections and changes
- Timeout after 24 hours of inactivity

### 4. Security
- Verifies Twilio webhook signatures
- Rate limiting (prevent spam)
- CSRF exempt (Twilio webhook)
- Secure API key storage

## 📁 File Structure

```
whatsapp_bot/
├── __init__.py
├── apps.py                    # Django app config
├── models.py                  # Conversation, Message, PendingBooking
├── views.py                   # Webhook handler (main entry point)
├── ai_handler.py              # OpenAI integration
├── booking_handler.py         # Availability search & booking creation
├── urls.py                    # /whatsapp/webhook/
├── admin.py                   # Django admin interface
├── tests.py                   # Unit tests
└── migrations/
    └── 0001_initial.py        # Database schema
```

## 🔧 Configuration Files

```
/home/ubuntu/reserva-ya/
├── app/
│   ├── settings.py            # ✅ Updated: Added whatsapp_bot, OpenAI/Twilio config
│   └── urls.py                # ✅ Updated: Added /whatsapp/ route
├── requirements.txt           # ✅ Updated: Added openai, fuzzywuzzy
├── .env.example               # ✅ New: Environment variables template
├── WHATSAPP_AI_IMPLEMENTATION.md  # ✅ New: Strategy guide
├── WHATSAPP_SETUP.md          # ✅ New: Step-by-step setup
├── test_whatsapp_setup.py     # ✅ New: Verification script
└── whatsapp_bot/              # ✅ New: Complete integration
```

## 🚀 Quick Start Commands

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 3. Run migrations
python manage.py migrate

# 4. Test setup
python test_whatsapp_setup.py

# 5. Start server
python manage.py runserver

# 6. Start ngrok (separate terminal)
ngrok http 8000

# 7. Configure Twilio webhook
# Set: https://your-ngrok-url.ngrok.io/whatsapp/webhook/

# 8. Test!
# Send WhatsApp: "I want to book a haircut tomorrow at 3pm"
```

## 📊 Monitoring & Analytics

### Django Admin Dashboard
```
/admin/whatsapp_bot/whatsappconversation/
  - View active conversations
  - See conversation state
  - Track customer interactions

/admin/whatsapp_bot/whatsappmessage/
  - Full message history
  - Search by phone number
  - Filter by date/direction

/admin/whatsapp_bot/pendingbooking/
  - Bookings in progress
  - Conversion tracking
```

### Logs
```python
# Check webhook activity
tail -f logs/django.log | grep WhatsApp

# Check AI extractions
tail -f logs/django.log | grep "AI extracted"

# Check booking creation
tail -f logs/django.log | grep "Created booking"
```

## 💰 Cost Estimate

### For 100 bookings/month:
- **OpenAI GPT-4o-mini**: ~$2-3
  - ~3 API calls per booking
  - $0.025 per 1K input tokens
  - Average 200 tokens per call
- **Twilio WhatsApp**: ~$0.50
  - 3-5 messages per booking
  - $0.005 per message
- **Infrastructure**: $0 (uses existing server)

**Total: ~$3-4/month** for 100 bookings

Very cost-effective compared to:
- Manual booking: 5 min × €15/hour = €1.25 per booking
- Savings: €121/month for 100 bookings!

## 🎓 Learning Resources

### Twilio WhatsApp
- Docs: https://www.twilio.com/docs/whatsapp
- Sandbox: https://console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn
- Pricing: https://www.twilio.com/whatsapp/pricing

### OpenAI
- Platform: https://platform.openai.com/
- Function calling: https://platform.openai.com/docs/guides/function-calling
- Models: https://platform.openai.com/docs/models

### Alternative: Anthropic Claude
- Claude API: https://www.anthropic.com/api
- Often cheaper and better for Spanish

## 🤝 Contributing

To improve the AI bot:

1. **Add more examples** in `ai_handler.py` system prompt
2. **Handle edge cases** in `views.py`
3. **Add more languages** by updating prompts
4. **Improve fuzzy matching** thresholds in `booking_handler.py`

## 📝 License

Same as the main Reserva-Ya project.

---

Created for Reserva-Ya booking system - March 2026
