from django import template

register = template.Library()

@register.filter
def get_range(value):
    return range(value)

@register.filter
def format_location(location_code):
    location_map = {
        'SHANNON': 'Shannon Library',
        'CLEMONS': 'Clemons Library',
        'BROWN': 'Brown Science and Engineering Library',
        'ON_LOAN': 'On Loan'
    }
    return location_map.get(location_code, location_code)