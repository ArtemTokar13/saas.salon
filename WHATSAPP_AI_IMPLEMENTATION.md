# WhatsApp AI Booking Integration Guide

## Overview
Enable clients to book appointments via WhatsApp using natural language like:
- "I want to book a haircut for tomorrow after lunch in the salon Peluqueria UJI"
- "Reserve a manicure for Friday at 3 PM"
- "Available times for massage next week?"

## Architecture

```
WhatsApp Message → Twilio → Your Django Webhook → OpenAI API → Parse Intent → 
Find Availability → Generate Response → Reply via Twilio → WhatsApp
```

## Step 1: Install Required Packages

```bash
pip install openai==1.56.0
# Twilio is already installed
```

## Step 2: Environment Variables

Add to your `.env` or settings:

```
OPENAI_API_KEY=sk-your-api-key
TWILIO_ACCOUNT_SID=your-account-sid
TWILIO_AUTH_TOKEN=your-auth-token
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
```

## Step 3: Create WhatsApp Integration App

Structure:
```
whatsapp_bot/
    __init__.py
    models.py          # Store conversations
    views.py           # Webhook handler
    ai_handler.py      # OpenAI integration
    booking_handler.py # Find availability
    urls.py
```

## Step 4: How It Works

### 4.1 Client sends message
```
"I want to book a haircut tomorrow at 2pm at Peluqueria UJI"
```

### 4.2 AI extracts information
Using OpenAI function calling to extract:
- Service: "haircut"
- Date: "tomorrow" → 2026-03-15
- Time preference: "2pm" → 14:00
- Company: "Peluqueria UJI"

### 4.3 Find availability
- Search for company by name
- Find "haircut" service
- Check available slots around 2pm
- Get available staff

### 4.4 AI generates response
```
"Great! I found these available times for haircut at Peluqueria UJI tomorrow:

1. 2:00 PM with Maria (€25, 30 min)
2. 2:30 PM with Juan (€25, 30 min)  
3. 3:00 PM with Maria (€25, 30 min)

Reply with the number to confirm your booking."
```

### 4.5 Client confirms
```
"1"
```

### 4.6 Create booking
System creates the booking and sends confirmation.

## Step 5: Twilio Setup

1. Sign up at https://www.twilio.com/
2. Get WhatsApp Sandbox (for testing) or approve production number
3. Configure webhook URL: `https://your-domain.com/whatsapp/webhook/`
4. Point "When a message comes in" to your webhook

## Step 6: Testing Flow

### Local Testing with ngrok:
```bash
ngrok http 8000
# Update Twilio webhook to: https://abc123.ngrok.io/whatsapp/webhook/
```

### Send test message:
Join your WhatsApp sandbox and send:
```
I want to book a haircut tomorrow at 3pm
```

## Benefits

✅ **Natural Language**: Clients write in their own words
✅ **Multilingual**: OpenAI supports Spanish, Catalan, Ukrainian, etc.
✅ **24/7 Availability**: AI responds instantly
✅ **Smart Matching**: Fuzzy matching for salon/service names
✅ **Contextual**: Maintains conversation context
✅ **Fallback**: If AI can't understand, escalates to staff

## Costs

- **OpenAI API**: ~$0.01-0.03 per conversation (GPT-4o-mini)
- **Twilio**: ~$0.005 per message
- **Total**: ~$0.02 per booking conversation

## Alternative: Use Claude API

You can also use Anthropic Claude instead of OpenAI:
```bash
pip install anthropic
```

More affordable and works similarly well.

## Security Considerations

- ✅ Verify Twilio webhook signatures
- ✅ Rate limiting (prevent spam)
- ✅ Store customer phone numbers securely
- ✅ GDPR compliance for EU customers
- ✅ Customer consent for WhatsApp communications

## Next Steps

1. Set up OpenAI account and get API key
2. Configure Twilio WhatsApp
3. Implement webhook handler
4. Test with ngrok
5. Deploy to production
6. Monitor and optimize prompts
