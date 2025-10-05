# store/forms.py
from django import forms
from django.contrib.auth.models import User
from .models import Category, Product, ProductVariant, ProductImage, Coupon, CustomerProfile

# ----------------------
# Category Form
# ----------------------
class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'parent', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Category Name'}),
            'parent': forms.Select(attrs={'class': 'select'}),
            'description': forms.Textarea(attrs={'class': 'textarea', 'placeholder': 'Description'}),
        }


# store/forms.py

class CustomerProfileForm(forms.ModelForm):
    full_name = forms.CharField(
        required=True,
        label="Full Name",
        widget=forms.TextInput(attrs={
            'class': 'border border-gray-300 rounded px-3 py-2 w-full focus:outline-none focus:ring-2 focus:ring-gold',
            'placeholder': 'Full Name'
        })
    )

    class Meta:
        model = CustomerProfile
        fields = ['full_name', 'phone_number', 'address']
        widgets = {
            'phone_number': forms.TextInput(attrs={
                'class': 'border border-gray-300 rounded px-3 py-2 w-full focus:outline-none focus:ring-2 focus:ring-gold',
                'placeholder': 'Phone Number'
            }),
            'address': forms.Textarea(attrs={
                'class': 'border border-gray-300 rounded px-3 py-2 w-full focus:outline-none focus:ring-2 focus:ring-gold',
                'rows': 3,
                'placeholder': 'Address'
            }),
        }

    def __init__(self, *args, **kwargs):
        # Pop the 'user' argument before calling super
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Prefill full_name from profile or fallback to username
        if self.user:
            profile_instance = kwargs.get('instance')
            if profile_instance and profile_instance.full_name:
                self.fields['full_name'].initial = profile_instance.full_name
            else:
                self.fields['full_name'].initial = self.user.username

    def save(self, commit=True):
        profile = super().save(commit=False)
        if self.user:
            # Save full_name to profile
            profile.full_name = self.cleaned_data.get('full_name', '')
        if commit:
            profile.save()
        return profile




# ----------------------
# Product Form
# ----------------------
class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'category', 'description', 'price', 'discounted_price', 'is_featured', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Product Name'}),
            'category': forms.Select(attrs={'class': 'select'}),
            'description': forms.Textarea(attrs={'class': 'textarea'}),
            'price': forms.NumberInput(attrs={'class': 'input'}),
            'discounted_price': forms.NumberInput(attrs={'class': 'input'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'checkbox'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'checkbox'}),
        }

# ----------------------
# Product Variant Form
# ----------------------
class ProductVariantForm(forms.ModelForm):
    class Meta:
        model = ProductVariant
        fields = ['product', 'sku', 'size', 'color', 'price', 'stock', 'is_active']
        widgets = {
            'product': forms.Select(attrs={'class': 'select'}),
            'sku': forms.TextInput(attrs={'class': 'input'}),
            'size': forms.Select(attrs={'class': 'select'}),
            'color': forms.TextInput(attrs={'class': 'input'}),
            'price': forms.NumberInput(attrs={'class': 'input'}),
            'stock': forms.NumberInput(attrs={'class': 'input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'checkbox'}),
        }

# ----------------------
# Product Image Form
# ----------------------
class ProductImageForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ['product', 'image', 'alt_text', 'is_primary', 'color']
        widgets = {
            'product': forms.Select(attrs={'class': 'select'}),
            'image': forms.ClearableFileInput(attrs={'class': 'file-input'}),
            'alt_text': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Alt Text'}),
            'is_primary': forms.CheckboxInput(attrs={'class': 'checkbox'}),
            'color': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Color Variant'}),
        }

# ----------------------
# Coupon Form
# ----------------------
class CouponForm(forms.ModelForm):
    class Meta:
        model = Coupon
        fields = ['code', 'discount_percent', 'min_amount', 'start_date', 'end_date', 'active']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Coupon Code'}),
            'discount_percent': forms.NumberInput(attrs={'class': 'input'}),
            'min_amount': forms.NumberInput(attrs={'class': 'input'}),
            'start_date': forms.DateTimeInput(attrs={'class': 'input', 'type': 'datetime-local'}),
            'end_date': forms.DateTimeInput(attrs={'class': 'input', 'type': 'datetime-local'}),
            'active': forms.CheckboxInput(attrs={'class': 'checkbox'}),
        }

class ApplyCouponForm(forms.Form):
    code = forms.CharField(max_length=30, required=True, label="Coupon Code")

# ----------------------
# Checkout Form
# ----------------------

class CheckoutForm(forms.Form):
    full_name = forms.CharField(
        max_length=100,
        label="Full Name",
        widget=forms.TextInput(attrs={
            'class': 'w-full border rounded-lg px-3 py-2',
            'placeholder': 'Full Name'
        })
    )
    phone_number = forms.CharField(
        max_length=10,
        label="Phone Number",
        widget=forms.TextInput(attrs={
            'class': 'w-full border rounded-lg px-3 py-2',
            'placeholder': 'Phone Number'
        })
    )
    address = forms.CharField(
        max_length=255,
        label="Address",
        widget=forms.Textarea(attrs={
            'class': 'w-full border rounded-lg px-3 py-2',
            'rows': 3,
            'placeholder': 'Shipping Address'
        })
    )

# ----------------------
# Add to Cart Form
# ----------------------

class AddToCartForm(forms.Form):
    variant_id = forms.IntegerField()
    quantity = forms.IntegerField(min_value=1)

