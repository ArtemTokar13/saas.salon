"""
Utility functions for bookings app
"""
import re
from app.constants import COUNTRY_CHOICES


def normalize_phone_number(phone):
    """
    Normalize phone number to E.164 format for WhatsApp/SMS
    
    Args:
        phone: Raw phone number (may contain spaces, dashes, parentheses, etc.)
        country_code: Country code (e.g., 'ES' for Spain, or '+34')
    
    Returns:
        Normalized phone number in format: +[country_code][number]
        Returns original if cannot normalize
    """
    if not phone:
        return phone
    
    # Remove whatsapp: prefix if present
    phone = phone.replace('whatsapp:', '').strip()
    
    # If phone already starts with +, just clean it
    if phone.startswith('+'):
        # Remove all non-digit characters except leading +
        cleaned = '+' + re.sub(r'\D', '', phone[1:])
        return cleaned
    
    # Remove all non-digit characters
    digits_only = re.sub(r'\D', '', phone)
    
    # Remove leading zeros (common in local formats)
    digits_only = digits_only.lstrip('0')
    
    if not digits_only:
        return phone  # Return original if nothing left
    
    # Get the country code prefix
    # country_prefix = ''
    # if country_code:
    #     # If country_code is already a prefix like '+34', use it
    #     if country_code.startswith('+'):
    #         country_prefix = country_code
    #     else:
    #         # Look up the prefix from COUNTRY_CHOICES
    #         for code, prefix in COUNTRY_CHOICES:
    #             if code == country_code:
    #                 country_prefix = prefix
    #                 break
    
    # If we have a country prefix, combine it with the number
    # if country_prefix:
    #     return f"{country_prefix}{digits_only}"
    
    # If number already looks like it has country code (long enough), just add +
    if len(digits_only) >= 10:
        return f"+{digits_only}"
    
    # Return original if we can't normalize confidently
    return phone


def get_country_prefix(country_code):
    """Get the phone prefix for a country code (e.g., 'ES' -> '+34')"""
    if not country_code:
        return ''
    
    if country_code.startswith('+'):
        return country_code
    
    for code, prefix in COUNTRY_CHOICES:
        if code == country_code:
            return prefix
    
    return ''
