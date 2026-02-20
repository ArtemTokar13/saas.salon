from django.urls import path
from . import views
from . import stripe_connect_views
from . import stripe_connect_webhooks

urlpatterns = [
    # Platform subscription URLs (existing)
    path('subscription/', views.subscription_details, name='subscription_details'),
    path('plans/', views.view_plans, name='view_plans'),
    path('change-plan/<int:plan_id>/', views.change_plan, name='change_plan'),
    path('cancel/', views.cancel_subscription, name='cancel_subscription'),
    path('payment-success/', views.payment_success, name='payment_success'),
    path('payment-cancelled/', views.payment_cancelled, name='payment_cancelled'),
    path('customer-portal/', views.customer_portal, name='customer_portal'),
    path('webhook/', views.stripe_webhook, name='stripe_webhook'),
    
    # Stripe Connect URLs (salon payment onboarding)
    path('connect/onboard/', stripe_connect_views.stripe_connect_onboard, name='stripe_connect_onboard'),
    path('connect/return/', stripe_connect_views.stripe_connect_return, name='stripe_connect_return'),
    path('connect/dashboard/', stripe_connect_views.stripe_connect_dashboard, name='stripe_connect_dashboard'),
    path('connect/dashboard-link/', stripe_connect_views.stripe_connect_dashboard_link, name='stripe_connect_dashboard_link'),
    path('connect/toggle-payments/', stripe_connect_views.toggle_online_payments, name='toggle_online_payments'),
    
    # Booking payment URLs
    path('booking/<int:booking_id>/pay/', stripe_connect_views.create_booking_payment, name='create_booking_payment'),
    path('booking/<int:booking_id>/payment-success/', stripe_connect_views.booking_payment_success, name='booking_payment_success'),
    path('booking/<int:booking_id>/payment-cancel/', stripe_connect_views.booking_payment_cancel, name='booking_payment_cancel'),
    
    # Webhooks
    path('webhook/connect/', stripe_connect_webhooks.stripe_connect_webhook, name='stripe_connect_webhook'),
]

