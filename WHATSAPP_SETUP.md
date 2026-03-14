# WhatsApp AI Bot - Quick Setup Guide

This guide will help you set up the WhatsApp AI booking integration in 30 minutes.

## Prerequisites
- Python environment with Django already set up
- OpenAI account (or Anthropic Claude)
- Twilio account
- ngrok (for local testing)

## Step 1: Install New Dependencies

```bash
source venv/bin/activate
pip install -r requirements.txt
```

New packages installed:
- `openai==1.56.0` - AI for natural language processing
- `fuzzywuzzy==0.18.0` - Fuzzy string matching for company/service names
- `python-Levenshtein==0.26.1` - Fast fuzzy matching

## Step 2: Get API Keys

### 2.1 OpenAI API Key
1. Go to https://platform.openai.com/api-keys
2. Create account (if new)
3. Click "Create new secret key"
4. Copy key (starts with `sk-...`)
5. Cost: ~$0.01-0.03 per booking conversation

### 2.2 Twilio WhatsApp Setup
1. Go to https://www.twilio.com/console
2. Sign up (free trial gives $15 credit)
3. Go to "Messaging" → "Try it out" → "Send a WhatsApp message"
4. Get your:
   - Account SID (starts with `AC...`)
   - Auth Token (hidden by default, click to reveal)
   - WhatsApp number (format: `whatsapp:+14155238886`)

## Step 3: Configure Environment Variables

Add to your `.env` file or export:

```bash
# WhatsApp AI Integration
OPENAI_API_KEY=sk-your-openai-key-here
OPENAI_MODEL=gpt-4o-mini
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your-twilio-auth-token
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
```

## Step 4: Run Migrations

```bash
python manage.py makemigrations whatsapp_bot
python manage.py migrate
```

## Step 5: Test Locally with ngrok

### 5.1 Install ngrok
```bash
# Linux
wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz
tar xvzf ngrok-v3-stable-linux-amd64.tgz
sudo mv ngrok /usr/local/bin/
```

### 5.2 Start Django server
```bash
python manage.py runserver
```

### 5.3 Start ngrok (in another terminal)
```bash
ngrok http 8000
```

You'll see output like:
```
Forwarding  https://abc123.ngrok.io -> http://localhost:8000
```

### 5.4 Configure Twilio Webhook
1. Copy the ngrok URL: `https://abc123.ngrok.io`
2. Go to Twilio Console → Messaging → WhatsApp sandbox settings
3. Set "When a message comes in" to: `https://abc123.ngrok.io/whatsapp/webhook/`
4. HTTP Method: POST
5. Save

## Step 6: Join WhatsApp Sandbox

1. In Twilio Console → Messaging → Try it out → WhatsApp
2. You'll see instructions like: "Send 'join abc-def' to +1 415 523 8886"
3. Send that message from your phone to join the sandbox

## Step 7: Test the Bot!

Send a WhatsApp message to the Twilio number:

```
I want to book a haircut tomorrow at 3pm
```

The bot should respond with available times! 🎉

## Step 8: Production Deployment

### Option A: Deploy with your production server

1. Set environment variables in production:
```bash
export OPENAI_API_KEY=sk-...
export TWILIO_ACCOUNT_SID=AC...
export TWILIO_AUTH_TOKEN=...
export TWILIO_WHATSAPP_NUMBER=whatsapp:+...
```

2. Update Twilio webhook to production URL:
```
https://your-domain.com/whatsapp/webhook/
```

3. Restart server

### Option B: Request Production WhatsApp Number

For production (not sandbox):
1. Go to Twilio Console → Messaging → Senders → WhatsApp senders
2. Request to use your own WhatsApp Business number
3. Submit business info for approval (takes 1-3 days)
4. Once approved, update `TWILIO_WHATSAPP_NUMBER`

## Monitoring

### Django Admin Dashboard
Go to: `https://your-domain.com/admin/whatsapp_bot/`

You can see:
- **WhatsApp Conversations** - Active conversations with clients
- **WhatsApp Messages** - Full message history
- **Pending Bookings** - Bookings in progress

### Logs
```bash
tail -f logs/django.log
```

Look for:
- `Received WhatsApp message from...`
- `AI extracted intent: ...`
- `Created booking: ...`

## Troubleshooting

### Bot not responding?

1. **Check ngrok is running**:
   ```bash
   curl https://your-ngrok-url.ngrok.io/whatsapp/webhook/
   ```
   Should return 405 (Method Not Allowed) - that's good, means endpoint exists

2. **Check Twilio webhook logs**:
   - Go to Twilio Console → Monitor → Logs → Errors
   - Look for webhook failures

3. **Check Django logs**:
   ```bash
   python manage.py runserver
   ```
   Send test message, watch for errors

4. **Verify environment variables**:
   ```python
   python manage.py shell
   >>> from django.conf import settings
   >>> print(settings.OPENAI_API_KEY[:10])  # Should show first 10 chars
   >>> print(settings.TWILIO_ACCOUNT_SID[:10])
   ```

### AI not understanding messages?

The AI uses OpenAI GPT-4o-mini. To improve understanding:

1. **Check the prompt** in `whatsapp_bot/ai_handler.py`
2. **Add examples** to the system prompt
3. **Switch to GPT-4** (more expensive but better):
   ```bash
   export OPENAI_MODEL=gpt-4
   ```

### No available slots found?

1. **Check company has working hours**:
   - Admin → Companies → Working Hours
   - Make sure hours are set for the requested day

2. **Check staff is assigned to service**:
   - Admin → Companies → Staff → Select staff → Services
   - Make sure staff can perform the requested service

3. **Check staff working days**:
   - Admin → Companies → Staff → Working days
   - Make sure staff works on the requested day

## Cost Breakdown

For 100 bookings/month:

- **OpenAI API**: ~$2-3 (at $0.025 per booking)
- **Twilio WhatsApp**: ~$0.50 (at $0.005 per message × 2 messages per booking)
- **ngrok** (if using): $0 (free tier) or $8/month (paid)
- **Total**: ~$3-12/month

Very affordable for the automation value!

## Advanced Features (Optional)

### 1. Multiple Languages
The AI already supports Spanish, Catalan, and Ukrainian automatically!

### 2. Custom Greetings
Edit `handle_greeting()` in `whatsapp_bot/views.py`

### 3. Business Hours Check
Add a check to only respond during business hours:
```python
from django.utils import timezone
now = timezone.now()
if now.hour < 8 or now.hour > 20:
    return "Thanks for your message! We'll respond during business hours (8am-8pm)."
```

### 4. Use Claude Instead of OpenAI
Install Anthropic:
```bash
pip install anthropic
```

Edit `whatsapp_bot/ai_handler.py` to use Claude API.

## Next Steps

✅ Test with real bookings
✅ Monitor message logs in admin
✅ Train staff on how system works
✅ Collect customer feedback
✅ Optimize AI prompts based on real usage

## Support

Questions? Check:
- Twilio docs: https://www.twilio.com/docs/whatsapp
- OpenAI docs: https://platform.openai.com/docs
- Django logs and admin panel

Happy automating! 🚀
