from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary using a key"""
    try:
        # Handle case where dictionary is a string or None
        if dictionary is None:
            return []
        if isinstance(dictionary, str):
            return []
        if isinstance(dictionary, dict):
            return dictionary.get(key, [])
        # If it's a list or other object, try to access by index or attribute
        return []
    except (TypeError, KeyError, AttributeError):
        return []