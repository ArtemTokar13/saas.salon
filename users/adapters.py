from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.adapter import DefaultAccountAdapter
from django.urls import reverse
from django.contrib import messages


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Custom adapter to handle social account signup and login
    """
    
    def get_login_redirect_url(self, request):
        """
        Redirect to dashboard if user has a company, otherwise create one and redirect.
        If session has onboarding_data (from get-started flow), apply it to the company.
        """
        from users.models import UserProfile
        from companies.models import Company, Staff, Service, WorkingHours

        user = request.user

        # Check if user is superuser/staff
        if user.is_superuser or user.is_staff:
            return reverse('admin_dashboard')

        # Get or create UserProfile
        profile, created = UserProfile.objects.get_or_create(user=user)

        # Create company if user doesn't have one
        if not profile.company:
            onboarding = request.session.pop('onboarding_data', None) or {}

            company_name = (onboarding.get('company_name') or '').strip() or \
                           user.get_full_name() or user.email.split('@')[0] or 'My Salon'

            company = Company.objects.create(
                administrator=user,
                name=company_name,
                address=(onboarding.get('company_address') or '').strip(),
                city=(onboarding.get('company_city') or '').strip(),
                phone=(onboarding.get('phone') or '').strip(),
                email=user.email,
                salon_type=onboarding.get('salon_type') or None,
            )

            profile.company = company
            profile.is_admin = True
            profile.save()

            # Apply service and staff from get-started session if present
            service_name = (onboarding.get('service_name') or '').strip()
            service = None
            if service_name:
                try:
                    duration = max(1, int(onboarding.get('service_duration') or 30))
                except (ValueError, TypeError):
                    duration = 30
                try:
                    price = float(onboarding.get('service_price') or 0)
                except (ValueError, TypeError):
                    price = 0.0
                service = Service.objects.create(
                    company=company, name=service_name, duration=duration, price=price,
                )

            owner_is_staff = onboarding.get('owner_is_staff') == 'true'
            staff_name = (user.get_full_name() or user.username if owner_is_staff
                          else (onboarding.get('staff_name') or '').strip())
            staff_spec = '' if owner_is_staff else (onboarding.get('staff_position') or '').strip()

            if staff_name:
                staff = Staff.objects.create(
                    company=company, name=staff_name, specialization=staff_spec,
                    working_days=[0, 1, 2, 3, 4, 5, 6],
                )
                if service:
                    staff.services.add(service)
                if owner_is_staff:
                    profile.staff = staff
                    profile.save()

            # Default working hours: Mon-Sat 9:00-18:00, Sun off
            from datetime import time as _time
            for day in range(7):
                WorkingHours.objects.create(
                    company=company,
                    day_of_week=day,
                    start_time=_time(9, 0),
                    end_time=_time(18, 0),
                    is_day_off=(day == 6),
                )

            # If came from get-started (has session data), go straight to calendar
            if onboarding:
                return reverse('booking_calendar')
            return reverse('registration_thank_you')

        # Existing user with company — go to calendar (most-used page after login)
        return reverse('booking_calendar')
    
    def get_signup_redirect_url(self, request):
        """
        Redirect after signup (new user via Google OAuth)
        Same as login redirect
        """
        return self.get_login_redirect_url(request)
    
    def populate_user(self, request, sociallogin, data):
        """
        Populates user information from social provider data
        """
        user = super().populate_user(request, sociallogin, data)
        
        # Get name from Google data
        if sociallogin.account.provider == 'google':
            extra_data = sociallogin.account.extra_data
            
            # Set first and last name if available
            if 'given_name' in extra_data:
                user.first_name = extra_data.get('given_name', '')
            if 'family_name' in extra_data:
                user.last_name = extra_data.get('family_name', '')
            
            # If no given/family name, try to get full name
            if not user.first_name and 'name' in extra_data:
                name_parts = extra_data.get('name', '').split(' ', 1)
                user.first_name = name_parts[0]
                if len(name_parts) > 1:
                    user.last_name = name_parts[1]
        
        return user
    
    def save_user(self, request, sociallogin, form=None):
        """
        Saves the user and updates UserProfile with social data
        Also creates a company automatically for new OAuth users
        """
        user = super().save_user(request, sociallogin, form)
        
        # Get or create UserProfile
        from users.models import UserProfile
        from companies.models import Company
        
        profile, profile_created = UserProfile.objects.get_or_create(user=user)
        
        # Update UserProfile with Google data
        if sociallogin.account.provider == 'google':
            extra_data = sociallogin.account.extra_data
            
            # Set full name from Google
            full_name = extra_data.get('name', '')
            if full_name:
                profile.full_name = full_name
        
        # Create a company if user doesn't have one
        if not profile.company:
            # Get user's name for company
            company_name = user.get_full_name() or user.email.split('@')[0] or "My Salon"
            
            company = Company.objects.create(
                administrator=user,
                name=company_name,
                email=user.email,
            )
            
            profile.company = company
            profile.is_admin = True
        
        profile.save()
        
        return user


class CustomAccountAdapter(DefaultAccountAdapter):
    """
    Custom adapter for account operations
    """
    
    def is_open_for_signup(self, request):
        """
        Whether to allow sign ups.
        """
        return True
