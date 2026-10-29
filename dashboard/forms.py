from django import forms
from accounts.models import User
from orders.models import PaymentQR, UPISettings
from products.models import Category, Product, ProductImage


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleImageField(forms.ImageField):
    widget = MultipleFileInput

    def clean(self, data, initial=None):
        if not data:
            return []
        files = data if isinstance(data, (list, tuple)) else [data]
        return [super().clean(image, None) for image in files]


class ProductForm(forms.ModelForm):
    image_url = forms.CharField(required=False, label='Image URL or local static path')
    additional_images = MultipleImageField(
        required=False,
        label='Additional product images',
        help_text='Select one or more images to show in the product detail gallery.',
    )

    class Meta:
        model = Product
        fields = (
            'category', 'product_name', 'subtitle', 'brand', 'price', 'discount_percentage',
            'special_feature', 'dpi',
            'connectivity', 'battery_life', 'weight', 'buttons', 'rgb', 'stock',
            'description', 'image', 'image_url',
        )
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
			'discount_percentage': forms.NumberInput(attrs={'min': 0, 'max': 100, 'step': '0.01'}),
			'subtitle': forms.TextInput(attrs={'placeholder': 'e.g. LIGHTSPEED Wireless Gaming Mouse'}),
			'special_feature': forms.Textarea(attrs={
				'rows': 3,
				'placeholder': 'Enter each special feature on a new line',
			}),
			'connectivity': forms.TextInput(attrs={'placeholder': 'e.g. 2.4 GHz wireless, Bluetooth, USB-C'}),
			'battery_life': forms.TextInput(attrs={'placeholder': 'e.g. Up to 70 hours'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['product_name'].disabled = True

    def save(self, commit=True):
        product = super().save(commit=commit)
        if commit:
            self._save_additional_images(product)
        else:
            save_m2m = self.save_m2m

            def save_related():
                save_m2m()
                self._save_additional_images(product)

            self.save_m2m = save_related
        return product

    def _save_additional_images(self, product):
        ProductImage.objects.bulk_create([
            ProductImage(product=product, image=image)
            for image in self.cleaned_data.get('additional_images', [])
        ])


class UserForm(forms.ModelForm):
    password = forms.CharField(required=False, widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ('name', 'email', 'phone', 'address', 'role', 'is_active', 'is_staff', 'password')
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)
        if not user.username:
            user.username = user.email
        if commit:
            user.save()
        return user


class PaymentQRForm(forms.ModelForm):
    class Meta:
        model = PaymentQR
        fields = ('title', 'notes', 'qr_code')
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
        }


class UPISettingsForm(forms.ModelForm):
    class Meta:
        model = UPISettings
        fields = ('upi_id', 'supported_apps', 'qr_code', 'is_active')
        widgets = {
            'supported_apps': forms.TextInput(attrs={'placeholder': 'GPay, PhonePe, Paytm, Navi, BHIM'}),
        }
