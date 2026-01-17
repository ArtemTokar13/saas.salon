from django.urls import path
from . import views

urlpatterns = [
    path('subscription/', views.subscription_details, name='subscription_details'),
    path('plans/', views.view_plans, name='view_plans'),
    path('change-plan/<int:plan_id>/', views.change_plan, name='change_plan'),
    path('cancel/', views.cancel_subscription, name='cancel_subscription'),
    path('payment-success/', views.payment_success, name='payment_success'),
    path('payment-cancelled/', views.payment_cancelled, name='payment_cancelled'),
    path('customer-portal/', views.customer_portal, name='customer_portal'),
    path('webhook/', views.stripe_webhook, name='stripe_webhook'),
]
