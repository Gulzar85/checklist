from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Get item from dictionary using key"""
    if dictionary and isinstance(dictionary, dict):
        return dictionary.get(key, {})
    return {}

@register.filter
def get_attr(obj, attr_name):
    """Get attribute from object"""
    if hasattr(obj, attr_name):
        return getattr(obj, attr_name)
    elif isinstance(obj, dict) and attr_name in obj:
        return obj[attr_name]
    return None

@register.filter
def multiply(value, arg):
    """Multiply value by argument"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def divide(value, arg):
    """Divide value by argument"""
    try:
        if float(arg) != 0:
            return float(value) / float(arg)
        return 0
    except (ValueError, TypeError):
        return 0

@register.filter
def percentage(value, total):
    """Calculate percentage"""
    try:
        if float(total) != 0:
            return (float(value) / float(total)) * 100
        return 0
    except (ValueError, TypeError):
        return 0

@register.filter
def get_item_nested(dictionary, keys):
    """Get nested item from dictionary"""
    if isinstance(dictionary, dict):
        return dictionary.get(keys, '')
    return ''


@register.filter
def filter_questions(responses, criteria):
    """Filter responses based on criteria string 'field,value'"""
    try:
        field, value = criteria.split(',')
        value = float(value) if value.isdigit() else value

        if field == 'is_critical':
            return [r for r in responses if r.question.is_critical and r.scored_points == value]
        return responses
    except:
        return responses


@register.filter
def critical_failures(responses):
    """Filter critical failures from responses"""
    if not responses:
        return []

    critical_failures_list = []
    for response in responses:
        if (hasattr(response, 'question') and
                response.question.is_critical and
                float(response.scored_points) == 0):
            critical_failures_list.append(response)

    return critical_failures_list


@register.filter
def needs_corrective_action(responses):
    """Filter responses that need corrective action"""
    if not responses:
        return []

    corrective_actions = []
    for response in responses:
        if response.needs_corrective_action:
            corrective_actions.append(response)

    return corrective_actions


@register.filter
def format_grade(grade):
    """Format grade with color classes"""
    grade_colors = {
        'A': 'success',
        'B': 'primary',
        'C': 'warning',
        'F': 'danger'
    }
    color = grade_colors.get(grade, 'secondary')
    return f'bg-{color}'


@register.filter
def format_percentage(percentage):
    """Format percentage with color classes"""
    if percentage >= 90:
        return 'success'
    elif percentage >= 80:
        return 'warning'
    else:
        return 'danger'

