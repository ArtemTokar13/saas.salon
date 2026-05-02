from django import template
from django.conf import settings
import re

register = template.Library()


@register.simple_tag(takes_context=True)
def get_path_without_language(context):
    """
    Returns the current path without the language prefix.
    This is useful for language switching where Django's set_language
    view will add the correct new language prefix.
    
    Examples:
        /uk/companies/6/ -> /companies/6/
        /es/bookings/new/ -> /bookings/new/
        /companies/6/ -> /companies/6/ (no change if no prefix)
    """
    request = context.get('request')
    if not request:
        return '/'
    
    path = request.get_full_path()
    
    # Get language codes from settings
    language_codes = [lang[0] for lang in settings.LANGUAGES]
    
    # Create pattern to match language prefix at the start of path
    # Pattern: /^\/({lang_code})\//
    pattern = r'^/(' + '|'.join(language_codes) + r')/'
    
    # Remove language prefix if it exists
    path_without_lang = re.sub(pattern, '/', path)
    
    return path_without_lang
