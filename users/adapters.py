from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.adapter import DefaultAccountAdapter
from django.urls import reverse


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Custom adapter to handle social account signup and login
    """
    
    def get_login_redirect_url(self, request):
        """
        Redirect to dashboard if user has a company, otherwise create one and redirect to dashboard
        """
        from users.models import UserProfile
        from companies.models import Company
        
        user = request.user
        
        # Check if user is superuser/staff
        if user.is_superuser or user.is_staff:
            return reverse('admin_dashboard')
        
        # Get or create UserProfile
        profile, created = UserProfile.objects.get_or_create(user=user)
        
        # Create company if user doesn't have one
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
        
        # Always redirect to dashboard
        return reverse('company_dashboard')
    
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
