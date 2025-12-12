from django import forms
from .models import Plan, Subscription


class ChangePlanForm(forms.Form):
    plan = forms.ModelChoiceField(
        queryset=Plan.objects.all(),
        required=True,
        widget=forms.RadioSelect,
        label="Select Plan"
    )
