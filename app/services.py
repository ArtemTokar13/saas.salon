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


#########################################################################
import csv
import io
import calendar
from datetime import datetime, timedelta
from itertools import cycle

DAYS_MAP = {
    "Lunes": 0,
    "Martes": 1,
    "Miércoles": 2,
    "Jueves": 3,
    "Viernes": 4,
    "Sábado": 5,
    "Domingo": 6,
}

def next_month_dates(day_index):
    today = datetime.today()
    year = today.year + (1 if today.month == 12 else 0)
    month = 1 if today.month == 12 else today.month + 1

    _, last_day = calendar.monthrange(year, month)

    return [
        datetime(year, month, d)
        for d in range(1, last_day + 1)
        if datetime(year, month, d).weekday() == day_index
    ]

def slot_fits(hour, pref):
    if not pref:
        return True
    return pref["from"] <= hour < pref["to"]

def build_schedule_csv(payload):
    names = [n.strip() for n in payload["names"].split(";")]
    slots = [s.strip() for s in payload["slots"].split(";")]  # formato: "Monday-09"
    places = [p.strip() for p in payload["places"].split(";")]
    preferences = payload.get("preferences", {})

    if len(names) < 2:
        raise ValueError("Se necesitan al menos 2 nombres")

    # доповнюємо, якщо непарна кількість
    if len(names) % 2 != 0:
        names.append("—")

    pairs = [(names[i], names[i + 1]) for i in range(0, len(names), 2)]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["date", "day", "hour", "person_1", "person_2", "place"])

    last_place = {}
    place_cycle = cycle(places)

    for slot in slots:
        day, hour = slot.split("-")
        hour = int(hour)

        for date in next_month_dates(DAYS_MAP[day]):
            for p1, p2 in pairs:
                if not slot_fits(hour, preferences.get(p1)):
                    continue
                if not slot_fits(hour, preferences.get(p2)):
                    continue

                pair_key = tuple(sorted([p1, p2]))
                available = [p for p in places if p != last_place.get(pair_key)]
                place = available[0] if available else next(place_cycle)
                last_place[pair_key] = place

                writer.writerow([
                    date.strftime("%Y-%m-%d"),
                    day,
                    hour,
                    p1,
                    p2,
                    place,
                ])

    return output.getvalue()

#########################################################################