from django import forms


class McDonaldDateInput(forms.DateInput):
    """Custom date input with McDonald's styling"""
    input_type = 'date'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attrs.update({
            'class': 'form-control',
            'style': 'border-color: #FF0000;'
        })


class McDonaldSelect(forms.Select):
    """Custom select with McDonald's styling"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attrs.update({
            'class': 'form-select',
            'style': 'border-color: #FF0000;'
        })


class RatingWidget(forms.NumberInput):
    """Custom widget for rating inputs"""
    input_type = 'number'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attrs.update({
            'class': 'form-control',
            'min': '0',
            'max': '5',
            'step': '0.5',
            'style': 'border-color: #FFCC00;'
        })


class CommentWidget(forms.Textarea):
    """Custom widget for comments with McDonald's styling"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attrs.update({
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Enter your comments...',
            'style': 'border-color: #FF0000;'
        })