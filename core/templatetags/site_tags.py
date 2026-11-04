from django import template

register = template.Library()


@register.filter
def money(value):
    """193822.75 → „193 822,75“, with a non-breaking space so amounts never wrap."""
    if value is None:
        return ''
    return f'{value:,.2f}'.replace(',', ' ').replace('.', ',')
