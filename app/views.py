from django.http import HttpResponse
from django.shortcuts import render
from billing.models import Plan


def Index(request):
    # plans = Plan.objects.all()
    plans = None
    return render(request, 'Index.html', {'plans': plans})