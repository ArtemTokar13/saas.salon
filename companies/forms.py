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
                  'phone', 'email', 'website', 'logo']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'email': forms.EmailInput(attrs={'readonly': 'readonly'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['email'].disabled = True


class CompanyStaffForm(forms.Form):
    name = forms.CharField(max_length=255, required=True)
    email = forms.EmailField(required=False)
    phone = forms.CharField(max_length=50, required=False)
    password1 = forms.CharField(widget=forms.PasswordInput, label="Password")
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirm Password")
    specialization = forms.CharField(max_length=255, required=False)
    avatar = forms.ImageField(required=False)
    break_start = forms.TimeField(required=False)
    break_end = forms.TimeField(required=False)
    out_of_office = forms.BooleanField(required=False)
    out_of_office_start = forms.DateField(required=False)
    out_of_office_end = forms.DateField(required=False)
    is_active = forms.BooleanField(initial=True, required=False)
    services = forms.ModelMultipleChoiceField(
        queryset=None,
        required=False,
        widget=forms.CheckboxSelectMultiple
    )
    
    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        if company:
            self.fields['services'].queryset = company.service_set.all()

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


class ServiceForm(forms.Form):
    name = forms.CharField(max_length=255, required=True)
    duration = forms.IntegerField(min_value=1, required=True, help_text="Duration in minutes")
    price = forms.DecimalField(max_digits=8, decimal_places=2, min_value=0, required=True)
    is_active = forms.BooleanField(initial=True, required=False)

    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)