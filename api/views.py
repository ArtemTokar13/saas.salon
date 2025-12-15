from django.shortcuts import render
from django.http import JsonResponse
from billing.models import Plan
from decimal import Decimal
import json


def get_plan_price(request):
    """API endpoint to get plan price based on selected period"""

    plan_id = request.GET.get('plan_id')
    period = request.GET.get('period')

    try:
        plan = Plan.objects.get(id=plan_id)
        price = plan.get_price_for_period(period)
        price_formatted = f"${price:.2f}"
        return JsonResponse({'price': str(price), 'price_formatted': price_formatted})
    except Plan.DoesNotExist:
        return JsonResponse({'error': 'Plan not found'}, status=404)