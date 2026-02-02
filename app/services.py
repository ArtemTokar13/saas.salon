import json
from twilio.rest import Client
from django.conf import settings
from django.utils.translation import get_language


def send_whatsapp_template(to, content_sid, variables):
    
    client = Client(
        settings.TWILIO_ACCOUNT_SID,
        settings.TWILIO_AUTH_TOKEN
    )

    try:
        message = client.messages.create(
            from_=settings.TWILIO_WHATSAPP_FROM,
            to=f'whatsapp:{to}',
            content_sid=content_sid,
            content_variables=json.dumps(variables),
        )
        print("WhatsApp message sent successfully.")
    except Exception as e:
        print(f"Failed to send WhatsApp message: {e}")
        return
    
    return message