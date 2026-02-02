"""
URL configuration for app project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns
from app.views import Index, privacy_policy, terms_of_service, cookie_policy, cookie_settings, about_us, how_it_works, faq, contact, schedule_page, generate_schedule
from app import admin_views
from billing.views import stripe_webhook


urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
    # API endpoints (no i18n prefix)
    path('api/', include('api.urls')),
    path('billing/webhook/', stripe_webhook, name='stripe_webhook'),
]

urlpatterns += i18n_patterns(
    path('admin/', admin.site.urls),
    path('', Index, name='index'),
    path('companies/', include('companies.urls')),
    path('bookings/', include('bookings.urls')),
    path('users/', include('users.urls')),
    path('billing/', include('billing.urls')),
    
    # Static pages
    path('privacy-policy/', privacy_policy, name='privacy_policy'),
    path('terms-of-service/', terms_of_service, name='terms_of_service'),
    path('cookie-policy/', cookie_policy, name='cookie_policy'),
    path('cookie-settings/', cookie_settings, name='cookie_settings'),
    path('about-us/', about_us, name='about_us'),
    path('how-it-works/', how_it_works, name='how_it_works'),
    path('faq/', faq, name='faq'),
    path('contact/', contact, name='contact'),
    
    # Super admin dashboard
    path('platform-admin/', admin_views.admin_dashboard, name='admin_dashboard'),
    path('platform-admin/users/', admin_views.manage_users, name='manage_users'),
    path('platform-admin/companies/', admin_views.manage_companies, name='manage_companies'),
    path('platform-admin/plans/', admin_views.manage_plans, name='manage_plans'),
    path('platform-admin/subscriptions/', admin_views.manage_subscriptions, name='manage_subscriptions'),

    ################################################################
    path("schedule/", schedule_page, name="schedule_page"),
    path("schedule/generate/", generate_schedule, name="generate_schedule"),
)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
