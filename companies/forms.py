from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Company
from billing.models import Plan


class CompanyRegistrationForm(forms.Form):
    # User information
    username = forms.CharField(max_length=150, required=True)
    email = forms.EmailField(required=True)
    password1 = forms.CharField(widget=forms.PasswordInput, label="Password")
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirm Password")
    
    # Company information
    company_name = forms.CharField(max_length=255, required=True)
    company_description = forms.CharField(widget=forms.Textarea, required=False)
    company_address = forms.CharField(max_length=255, required=True)
    company_city = forms.CharField(max_length=100, required=True)
    company_phone = forms.CharField(max_length=50, required=False)
    company_email = forms.EmailField(required=False)
    company_logo = forms.ImageField(required=False)
    
    # Subscription plan
    plan = forms.ModelChoiceField(queryset=Plan.objects.all(), required=True)

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Username already exists.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Email already registered.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match.")
        
        return cleaned_data


class CompanyProfileForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ['name', 'description', 'address', 'city', 'map_location', 
                  'phone', 'email', 'website', 'social_media', 'logo']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'social_media': forms.Textarea(attrs={'rows': 3}),
        }
