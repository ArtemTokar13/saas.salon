from django import forms
from .models import Plan, Subscription, ClientBillingInfo, SellerBillingInfo, ManualInvoice


class ChangePlanForm(forms.Form):
    plan = forms.ModelChoiceField(
        queryset=Plan.objects.all(),
        required=True,
        widget=forms.RadioSelect,
        label="Select Plan"
    )


class ClientBillingInfoForm(forms.ModelForm):
    class Meta:
        model = ClientBillingInfo
        fields = ['billing_name', 'tax_id', 'address', 'city', 'province', 'postal_code', 'country', 'phone', 'email']
        widgets = {
            'billing_name': forms.TextInput(attrs={'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'tax_id': forms.TextInput(attrs={'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'address': forms.TextInput(attrs={'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'city': forms.TextInput(attrs={'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'province': forms.TextInput(attrs={'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'postal_code': forms.TextInput(attrs={'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'country': forms.TextInput(attrs={'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'phone': forms.TextInput(attrs={'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'email': forms.EmailInput(attrs={'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500'}),
        }


class ManualInvoiceForm(forms.ModelForm):
    """Simplified receipt form - billing details auto-filled from company"""
    class Meta:
        model = ManualInvoice
        fields = [
            'company', 'invoice_date', 'description', 
            'quantity', 'unit_price', 'payment_method', 'notes',
        ]
        widgets = {
            'company': forms.Select(attrs={'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'invoice_date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'description': forms.TextInput(attrs={'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500', 'placeholder': 'e.g. Connect Plan - 1 month'}),
            'quantity': forms.NumberInput(attrs={'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500', 'min': '1', 'value': '1'}),
            'unit_price': forms.NumberInput(attrs={'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500', 'step': '0.01'}),
            'payment_method': forms.TextInput(attrs={'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500', 'placeholder': 'e.g. Stripe - Mastercard 4985'}),
            'notes': forms.Textarea(attrs={'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500', 'rows': 2}),
        }
        labels = {
            'company': 'Client Company',
            'invoice_date': 'Payment Date',
            'description': 'Product / Service',
            'quantity': 'Qty',
            'unit_price': 'Amount (€)',
            'payment_method': 'Payment Method',
        }


class SellerBillingInfoForm(forms.ModelForm):
    class Meta:
        model = SellerBillingInfo
        fields = ['company_name', 'tax_id', 'address', 'city', 'province', 'postal_code', 'country', 'phone', 'email']
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'tax_id': forms.TextInput(attrs={'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'address': forms.TextInput(attrs={'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'city': forms.TextInput(attrs={'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'province': forms.TextInput(attrs={'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'postal_code': forms.TextInput(attrs={'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'country': forms.TextInput(attrs={'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'phone': forms.TextInput(attrs={'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'email': forms.EmailInput(attrs={'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500'}),
        }
