from django.urls import path
from . import views

urlpatterns = [
    path('get_plan_price/', views.get_plan_price, name='get_plan_price'),
]