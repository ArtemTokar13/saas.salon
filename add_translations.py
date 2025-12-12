#!/usr/bin/env python3
"""
Add common translations to key template files.
This updates the main user-facing templates with trans tags.
"""

import re
from pathlib import Path

# Template files to update with their translation mappings
TEMPLATES_TRANS = {
    'templates/Index.html': [
        ('Salon Booking Platform', 'Salon Booking Platform'),
        ('Manage Your Salon Bookings', 'Manage Your Salon Bookings'),
        ('The complete booking platform for salons, spas, and service businesses.', 
         'The complete booking platform for salons, spas, and service businesses.'),
        ('Accept appointments online 24/7.', 'Accept appointments online 24/7.'),
        ('Start Free Trial', 'Start Free Trial'),
        ('Sign In', 'Sign In'),
        ('Everything You Need', 'Everything You Need'),
        ('Simple, powerful tools to grow your business', 'Simple, powerful tools to grow your business'),
        ('Online Booking', 'Online Booking'),
        ('Let customers book appointments 24/7 from any device.', 
         'Let customers book appointments 24/7 from any device.'),
        ('Automatic confirmations and reminders.', 'Automatic confirmations and reminders.'),
    ],
    'templates/users/login.html': [
        ('Login', 'Login'),
        ('Sign in to your account', 'Sign in to your account'),
        ('Or', 'Or'),
        ('create a new company account', 'create a new company account'),
        ('Username', 'Username'),
        ('Password', 'Password'),
        ('Remember me', 'Remember me'),
        ('Forgot password?', 'Forgot password?'),
        ('Sign in', 'Sign in'),
        ('Please correct the errors below.', 'Please correct the errors below.'),
        ('Enter your username', 'Enter your username'),
        ('Enter your password', 'Enter your password'),
    ],
}

def wrap_in_trans(text):
    """Wrap text in {% trans "..." %} tag"""
    # Escape quotes in text
    escaped = text.replace('"', '\\"')
    return f'{{% trans "{escaped}" %}}'

def update_template(file_path, translations):
    """Update a template file with translations"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if already has i18n loaded
        if '{% load i18n %}' not in content:
            content = '{% load i18n %}\n' + content
        
        # Replace each text with trans tag
        for original, _ in translations:
            # Skip if already wrapped
            if f'{{% trans "{original}"' in content or f"{{% trans '{original}'" in content:
                continue
            
            # Pattern to match the text not already in tags
            # This is a simple replacement - in production you'd want more sophisticated parsing
            trans_tag = wrap_in_trans(original)
            
            # Replace in common contexts
            content = content.replace(f'>{original}<', f'>{trans_tag}<')
            content = content.replace(f'"{original}"', f'"{trans_tag}"')
            content = content.replace(f"'{original}'", f"'{trans_tag}'")
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"Updated: {file_path}")
        return True
    except Exception as e:
        print(f"Error updating {file_path}: {e}")
        return False

if __name__ == '__main__':
    for template, translations in TEMPLATES_TRANS.items():
        update_template(template, translations)
    
    print("\nDone! Now run: python manage.py makemessages -l es -l ca -l uk --ignore=venv")
