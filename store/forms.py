from django import forms
from .models import Product, Category, PromoTheme, StoreReturnRequest, RefundReason

class ProductForm(forms.ModelForm):
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        empty_label="Select Category",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    promo_theme = forms.ModelChoiceField(
        queryset=PromoTheme.objects.all(),
        required=False,
        empty_label="Select Promotion / Celebration Event (Optional)",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    # Extra fields for multiple media handling - Fixed widget to prevent multi-file crash
    visual_search_tag = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        help_text="Keywords for photo/visual search matching."
    )
    additional_images = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control'}),
        help_text="Select product images for gallery display."
    )
    product_videos = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control'}),
        help_text="Select product review or demonstration videos."
    )

    class Meta:
        model = Product
        fields = [
            'name', 
            'category', 
            'description', 
            'price', 
            'discount_price',
            'promo_theme',
            'promo_price',
            'stock_quantity',
            'image', 
            'visual_search_tag',
            'internal_brand_tag',
            'allow_partial_payment',
            'partial_deposit_percentage',
            'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'price': forms.NumberInput(attrs={'class': 'form-control'}),
            'discount_price': forms.NumberInput(attrs={'class': 'form-control'}),
            'promo_price': forms.NumberInput(attrs={'class': 'form-control'}),
            'stock_quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'visual_search_tag': forms.TextInput(attrs={'class': 'form-control'}),
            'internal_brand_tag': forms.TextInput(attrs={'class': 'form-control'}),
            'allow_partial_payment': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'partial_deposit_percentage': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class CustomerReturnRequestForm(forms.ModelForm):
    """
    Form for customers to submit a return or refund request within 4 days of delivery.
    Explicitly uses standard form fields for media to avoid internal widget binding errors.
    """
    reason = forms.ModelChoiceField(
        queryset=RefundReason.objects.filter(is_active=True),
        empty_label="Select Reason for Refund",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    issue_description = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Describe the issue in detail...'})
    )

    image_1 = forms.FileField(widget=forms.FileInput(attrs={'class': 'form-control'}))
    image_2 = forms.FileField(widget=forms.FileInput(attrs={'class': 'form-control'}))
    image_3 = forms.FileField(widget=forms.FileInput(attrs={'class': 'form-control'}))
    video_proof = forms.FileField(widget=forms.FileInput(attrs={'class': 'form-control'}))

    class Meta:
        model = StoreReturnRequest
        fields = [
            'reason',
            'issue_description',
            'image_1',
            'image_2',
            'image_3',
            'video_proof'
        ]

    def clean(self):
        cleaned_data = super().clean()
        img1 = cleaned_data.get('image_1')
        img2 = cleaned_data.get('image_2')
        img3 = cleaned_data.get('image_3')
        video = cleaned_data.get('video_proof')

        if not (img1 and img2 and img3):
            raise forms.ValidationError("You must upload exactly 3 distinct images as proof of the issue.")
        
        if not video:
            raise forms.ValidationError("You must upload at least 1 video file demonstrating the product issue.")
            
        return cleaned_data