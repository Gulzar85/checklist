from django import template
from django.utils.safestring import mark_safe
from datetime import datetime, date
import math

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


@register.filter
def score_badge_class(score):
    """Return Bootstrap badge class based on score percentage"""
    try:
        score = float(score)
    except (ValueError, TypeError):
        score = 0

    if score >= 90:
        return "bg-success"
    elif score >= 80:
        return "bg-warning text-dark"
    return "bg-danger"


@register.filter
def grade_badge_class(grade):
    """Return Bootstrap badge class based on grade"""
    grade = str(grade).upper()
    if grade == 'A':
        return "bg-success"
    elif grade == 'B':
        return "bg-primary"
    elif grade == 'C':
        return "bg-warning text-dark"
    return "bg-danger"


@register.filter
def calculate_percentage(value, total):
    try:
        if total > 0:
            return (value / total) * 100
        return 0
    except (TypeError, ZeroDivisionError):
        return 0


@register.filter
def abs(value):
    try:
        return abs(value)
    except Exception:
        return value


@register.filter
def filter_critical_failures(responses):
    """Filter responses to show only critical failures (critical questions with 0 points)"""
    return [
        response for response in responses
        if response.question.is_critical and response.scored_points == 0
    ]


@register.filter
def filter_needs_corrective_action(responses):
    """Filter responses to show only those that need corrective action"""
    return [
        response for response in responses
        if response.needs_corrective_action
    ]


@register.filter
def selectattr(queryset, attr_name):
    """Filter a queryset based on an attribute being truthy"""
    return [item for item in queryset if getattr(item, attr_name, False)]


@register.filter
def selectattr_dict(list_of_dicts, key_name):
    """Filter a list of dictionaries based on a key being truthy"""
    return [item for item in list_of_dicts if item.get(key_name, False)]


# =========== NEW FILTERS ADDED ===========

@register.filter
def default_if_none(value, default_value='0'):
    """Return default value if the main value is None or empty"""
    if value is None:
        return default_value
    if isinstance(value, (str, list, dict, set)) and not value:
        return default_value
    return value


@register.filter
def round_number(value, decimals=1):
    """Round number to specified decimal places"""
    try:
        return round(float(value), decimals)
    except (ValueError, TypeError):
        return 0


@register.filter
def days_since(date_value):
    """Calculate days since given date"""
    if not date_value:
        return 'N/A'

    try:
        if isinstance(date_value, str):
            date_value = datetime.strptime(date_value, '%Y-%m-%d').date()

        delta = date.today() - date_value
        days = delta.days

        if days == 0:
            return 'Today'
        elif days == 1:
            return 'Yesterday'
        elif days < 30:
            return f'{days} days ago'
        elif days < 365:
            months = days // 30
            return f'{months} month{"s" if months > 1 else ""} ago'
        else:
            years = days // 365
            return f'{years} year{"s" if years > 1 else ""} ago'
    except Exception:
        return 'N/A'


@register.filter
def truncatechars_middle(value, max_length=20):
    """Truncate string from middle if too long"""
    if not value or len(str(value)) <= max_length:
        return value

    half = max_length // 2
    return f"{str(value)[:half]}...{str(value)[-half:]}"


@register.filter
def sort_by(queryset, field_name):
    """Sort queryset by field name"""
    if hasattr(queryset, 'order_by'):
        return queryset.order_by(field_name)
    return sorted(queryset, key=lambda x: getattr(x, field_name, 0))


@register.filter
def sort_dict_list(list_of_dicts, key_name):
    """Sort list of dictionaries by key"""
    if not list_of_dicts:
        return []
    return sorted(list_of_dicts, key=lambda x: x.get(key_name, 0))


@register.filter
def progress_bar_class(percentage):
    """Return progress bar class based on percentage"""
    try:
        perc = float(percentage)
        if perc >= 90:
            return "bg-success"
        elif perc >= 80:
            return "bg-warning"
        elif perc >= 70:
            return "bg-info"
        return "bg-danger"
    except:
        return "bg-secondary"


@register.filter
def risk_badge_class(risk_level):
    """Return badge class for risk levels"""
    risk_classes = {
        'critical': 'bg-danger',
        'high': 'bg-warning text-dark',
        'medium': 'bg-info',
        'low': 'bg-success',
        'none': 'bg-secondary'
    }
    return risk_classes.get(str(risk_level).lower(), 'bg-secondary')


@register.filter
def format_date(date_value, format_string='M d, Y'):
    """Format date with fallback"""
    if not date_value:
        return 'N/A'

    try:
        if hasattr(date_value, 'strftime'):
            return date_value.strftime(format_string.replace('M', '%b').replace('d', '%d').replace('Y', '%Y'))
        else:
            # Try to parse string date
            from django.utils.dateparse import parse_date
            parsed_date = parse_date(str(date_value))
            if parsed_date:
                return parsed_date.strftime(format_string.replace('M', '%b').replace('d', '%d').replace('Y', '%Y'))
            return 'N/A'
    except Exception:
        return 'N/A'


@register.filter
def humanize_number(value):
    """Humanize large numbers (e.g., 1500 -> 1.5K)"""
    try:
        value = int(value)
        if value >= 1000000:
            return f"{value / 1000000:.1f}M"
        elif value >= 1000:
            return f"{value / 1000:.1f}K"
        return str(value)
    except (ValueError, TypeError):
        return str(value)


@register.filter
def get_range(value):
    """Get range for template loops"""
    try:
        return range(int(value))
    except (ValueError, TypeError):
        return range(0)


@register.filter
def add(value, arg):
    """Add two numbers"""
    try:
        return float(value) + float(arg)
    except (ValueError, TypeError):
        try:
            return value + arg
        except:
            return value


@register.filter
def subtract(value, arg):
    """Subtract two numbers"""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        try:
            return value - arg
        except:
            return value


@register.filter
def safe_percentage_bar(percentage, width=100):
    """Create safe HTML percentage bar"""
    try:
        perc = float(percentage)
        if perc < 0:
            perc = 0
        elif perc > 100:
            perc = 100

        color_class = progress_bar_class(perc)

        return mark_safe(f'''
            <div class="progress" style="height: 8px; width: {width}px;">
                <div class="progress-bar {color_class}" role="progressbar" 
                     style="width: {perc}%" aria-valuenow="{perc}" 
                     aria-valuemin="0" aria-valuemax="100">
                </div>
            </div>
        ''')
    except:
        return mark_safe(f'''
            <div class="progress" style="height: 8px; width: {width}px;">
                <div class="progress-bar bg-secondary" role="progressbar" 
                     style="width: 0%" aria-valuenow="0" 
                     aria-valuemin="0" aria-valuemax="100">
                </div>
            </div>
        ''')


@register.filter
def get_restaurant_stats(restaurant, user):
    """Get restaurant statistics based on user role"""
    from .models import Audit  # Import here to avoid circular imports

    if user.is_superuser or getattr(user, 'role', None) == 'admin':
        audits = Audit.objects.filter(restaurant=restaurant, is_submitted=True)
    else:
        audits = Audit.objects.filter(restaurant=restaurant, is_submitted=True, auditor_name=user)

    return {
        'total_audits': audits.count(),
        'avg_score': audits.aggregate(avg=Avg('total_percentage'))['avg'] or 0,
        'critical_failures': audits.filter(has_critical_failure=True).count()
    }


@register.simple_tag
def calculate_trend(current_value, previous_value):
    """Calculate percentage trend between two values"""
    try:
        if previous_value == 0:
            return 100 if current_value > 0 else 0

        trend = ((current_value - previous_value) / previous_value) * 100
        return round(trend, 1)
    except:
        return 0


@register.simple_tag
def trend_icon(trend_value):
    """Get trend icon based on trend value"""
    try:
        trend = float(trend_value)
        if trend > 0:
            return mark_safe('<i class="fas fa-arrow-up text-success"></i>')
        elif trend < 0:
            return mark_safe('<i class="fas fa-arrow-down text-danger"></i>')
        else:
            return mark_safe('<i class="fas fa-minus text-secondary"></i>')
    except:
        return mark_safe('<i class="fas fa-minus text-secondary"></i>')


@register.filter
def group_by(queryset, field_name):
    """Group queryset by field name"""
    from itertools import groupby
    from operator import attrgetter

    if not queryset:
        return []

    sorted_queryset = sorted(queryset, key=attrgetter(field_name))
    return [(key, list(group)) for key, group in groupby(sorted_queryset, key=attrgetter(field_name))]