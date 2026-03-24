from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.adapter import DefaultAccountAdapter


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Custom adapter to handle social account signup and login
    """
    
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
        """
        user = super().save_user(request, sociallogin, form)
        
        # Update UserProfile with Google data
        if hasattr(user, 'userprofile'):
            profile = user.userprofile
            
            if sociallogin.account.provider == 'google':
                extra_data = sociallogin.account.extra_data
                
                # Set full name from Google
                full_name = extra_data.get('name', '')
                if full_name:
                    profile.full_name = full_name
                
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
