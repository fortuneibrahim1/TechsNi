import re
from django import forms
from django.forms import inlineformset_factory
from .models import Job, Quotation, QuotationItem, Invoice, InvoiceItem, User, JobType, SiteConfiguration

NIGERIAN_STATES = [
    ('', '-- Select State --'),
    ('Abia', 'Abia'),
    ('Adamawa', 'Adamawa'),
    ('Akwa Ibom', 'Akwa Ibom'),
    ('Anambra', 'Anambra'),
    ('Bauchi', 'Bauchi'),
    ('Bayelsa', 'Bayelsa'),
    ('Benue', 'Benue'),
    ('Borno', 'Borno'),
    ('Cross River', 'Cross River'),
    ('Delta', 'Delta'),
    ('Ebonyi', 'Ebonyi'),
    ('Edo', 'Edo'),
    ('Ekiti', 'Ekiti'),
    ('Enugu', 'Enugu'),
    ('FCT', 'Federal Capital Territory (Abuja)'),
    ('Gombe', 'Gombe'),
    ('Imo', 'Imo'),
    ('Jigawa', 'Jigawa'),
    ('Kaduna', 'Kaduna'),
    ('Kano', 'Kano'),
    ('Katsina', 'Katsina'),
    ('Kebbi', 'Kebbi'),
    ('Kogi', 'Kogi'),
    ('Kwara', 'Kwara'),
    ('Lagos', 'Lagos'),
    ('Nasarawa', 'Nasarawa'),
    ('Niger', 'Niger'),
    ('Ogun', 'Ogun'),
    ('Ondo', 'Ondo'),
    ('Osun', 'Osun'),
    ('Oyo', 'Oyo'),
    ('Plateau', 'Plateau'),
    ('Rivers', 'Rivers'),
    ('Sokoto', 'Sokoto'),
    ('Taraba', 'Taraba'),
    ('Yobe', 'Yobe'),
    ('Zamfara', 'Zamfara'),
]


class CustomUserRegistrationForm(forms.ModelForm):
    country = forms.CharField(
        initial='Nigeria',
        widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'countryInput', 'readonly': 'readonly'})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'id': 'emailInput', 'placeholder': 'name@example.com'})
    )
    phone_number = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'phoneInput', 'placeholder': '8031234567'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'id': 'passwordInput', 'placeholder': 'Password'})
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'id': 'confirmPasswordInput', 'placeholder': 'Confirm Password'})
    )
    
    referred_by = forms.ModelChoiceField(
        queryset=User.objects.filter(role='marketer'),
        required=False,
        empty_label="-- Select Marketer (Optional) --",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'username', 'email', 'country',
            'phone_number', 'state', 'capital', 'lga', 'address',
            'referred_by', 'password', 'confirm_password',
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Unique Username'}),
            'state': forms.Select(choices=NIGERIAN_STATES, attrs={'class': 'form-control', 'id': 'stateSelect'}),
            'capital': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'lga': forms.Select(attrs={'class': 'form-control', 'id': 'lgaSelect'}, choices=[('', '-- Select State First --')]),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Address...'}),
        }

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if len(password) < 7:
            raise forms.ValidationError('Password must be at least 7 characters long.')
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError('Passwords do not match.')
        return cleaned_data


class JobRequestForm(forms.ModelForm):
    job_type = forms.ModelChoiceField(
        queryset=JobType.objects.filter(is_active=True),
        empty_label="-- Select Job Type / Service --",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Job
        fields = ['job_type', 'is_po_job', 'po_number', 'model_type', 'serial_number', 'condition', 'description', 'image1', 'image2', 'image3']
        widgets = {
            'is_po_job': forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'isPoJobCheckbox'}),
            'po_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Corporate PO Number (if PO Job)'}),
            'model_type': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., iPhone 13, Hikvision CCTV'}),
            'serial_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Device Serial Number'}),
            'condition': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Cracked screen'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'image1': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'image2': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'image3': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }


class QuotationForm(forms.ModelForm):
    validity_days = forms.IntegerField(
        initial=5, 
        required=True, 
        label="Validity Duration (Days)",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'value': 5})
    )

    class Meta:
        model = Quotation
        fields = ['discount_amount', 'vat_amount', 'deposit_percentage', 'quotation_pdf']
        widgets = {
            'discount_amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Discount Amount (₦)', 'value': '0.00'}),
            'vat_amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'VAT / Tax (₦)', 'value': '0.00'}),
            'deposit_percentage': forms.NumberInput(attrs={'class': 'form-control', 'value': '50'}),
            'quotation_pdf': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }


class QuotationItemForm(forms.ModelForm):
    class Meta:
        model = QuotationItem
        fields = ['description', 'serial_number', 'quantity', 'amount']
        widgets = {
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Item or Service Description'}),
            'serial_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Serial Number'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control quantity-input', 'min': '1', 'value': '1'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control amount-input', 'placeholder': '0.00'}),
        }


# Dynamic inline formset for adding multi-lines on quotations
QuotationItemFormSet = inlineformset_factory(
    Quotation,
    QuotationItem,
    form=QuotationItemForm,
    extra=1,
    can_delete=True
)


class InvoiceItemForm(forms.ModelForm):
    class Meta:
        model = InvoiceItem
        fields = ['description', 'serial_number', 'quantity', 'amount']
        widgets = {
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Item or Service Description'}),
            'serial_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Serial Number'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control quantity-input', 'min': '1', 'value': '1'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control amount-input', 'placeholder': '0.00'}),
        }


InvoiceItemFormSet = inlineformset_factory(
    Invoice,
    InvoiceItem,
    form=InvoiceItemForm,
    extra=1,
    can_delete=True
)


class SiteConfigurationForm(forms.ModelForm):
    class Meta:
        model = SiteConfiguration
        fields = [
            'company_name',
            'company_address', 
            'contact_phone', 
            'contact_email', 
            'commission_percentage', 
            'about_text', 
            'policy_text', 
            'about_pdf', 
            'policy_pdf'
        ]
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'commission_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'about_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'policy_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'about_pdf': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'policy_pdf': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }