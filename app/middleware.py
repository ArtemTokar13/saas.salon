from datetime import date
from django.db import IntegrityError
from users.models import DailyVisit
from users.tools import get_client_ip

class VisitCounterMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        ip = get_client_ip(request)
        today = date.today()

        try:
            DailyVisit.objects.create(ip=ip, date=today)
        except IntegrityError:
            pass

        return self.get_response(request)
