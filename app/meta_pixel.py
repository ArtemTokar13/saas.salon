from facebook_business.adobjects.adspixel import AdsPixel
from facebook_business.adobjects.serverside.event import Event
from facebook_business.adobjects.serverside.event_request import EventRequest
from facebook_business.adobjects.serverside.user_data import UserData
from facebook_business.api import FacebookAdsApi
from django.conf import settings
import time
import uuid


def send_fb_capi_event(user_email, user_agent, user_ip, event_name='CompleteRegistration'):
    FacebookAdsApi.init(access_token=settings.FB_ACCESS_TOKEN)
    user_data = UserData(
        email=user_email,
        client_ip_address=user_ip,
        client_user_agent=user_agent
    )
    event = Event(
        event_name=event_name,
        event_time=int(time.time()),
        user_data=user_data,
        event_source_url='https://reserva-ya.es/es/companies/register/'
    )
    event_request = EventRequest(
        pixel_id=settings.FB_PIXEL_ID,
        events=[event]
    )
    response = event_request.execute()
    print(f"CAPI response from Meta: {response}")
    return response