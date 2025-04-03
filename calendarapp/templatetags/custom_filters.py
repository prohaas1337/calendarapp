from django import template

register = template.Library()

@register.filter
def display_name(user):
    """Visszaadja a felhasználó display_name-jét, ha van, különben a username-t."""
    if hasattr(user, "get_display_name") and user.get_display_name():
        return user.get_display_name()
    return user.username
