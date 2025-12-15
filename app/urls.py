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
from app.views import Index
from app import admin_views

urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
]

urlpatterns += i18n_patterns(
    path('admin/', admin.site.urls),
    path('', Index, name='index'),
    path('companies/', include('companies.urls')),
    path('bookings/', include('bookings.urls')),
    path('users/', include('users.urls')),
    path('billing/', include('billing.urls')),
    path('api/', include('api.urls')),
    
    # Super admin dashboard
    path('platform-admin/', admin_views.admin_dashboard, name='admin_dashboard'),
    path('platform-admin/users/', admin_views.manage_users, name='manage_users'),
    path('platform-admin/companies/', admin_views.manage_companies, name='manage_companies'),
    path('platform-admin/plans/', admin_views.manage_plans, name='manage_plans'),
    path('platform-admin/subscriptions/', admin_views.manage_subscriptions, name='manage_subscriptions'),
)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
