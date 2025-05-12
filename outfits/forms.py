from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import Outfit, Order, UserProfile

# --- CustomUserCreationForm ---
class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        help_text=_('Required. Please enter a valid email address.'),
        widget=forms.EmailInput(attrs={'autocomplete': 'email'})
    )
    first_name = forms.CharField(max_length=150, required=False, label=_('First Name'))
    last_name = forms.CharField(max_length=150, required=False, label=_('Last Name'))

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "first_name", "last_name")

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email__iexact=email).exists():
            raise ValidationError(_("An account with this email already exists."))
        return email

# --- OutfitForm ---
class OutfitForm(forms.ModelForm):
    class Meta:
        model = Outfit
        fields = '__all__'

# --- CheckoutForm ---
class CheckoutForm(forms.Form):
    text_input = forms.TextInput(attrs={'class': 'form-input'})
    email_input = forms.EmailInput(attrs={'class': 'form-input', 'autocomplete': 'email'})
    textarea = forms.Textarea(attrs={'rows': 3, 'class': 'form-textarea'})
    date_input = forms.DateInput(attrs={'type': 'date', 'class': 'form-input'})

    first_name = forms.CharField(label=_('First Name'), max_length=100, widget=text_input)
    last_name = forms.CharField(label=_('Last Name'), max_length=100, widget=text_input)
    email = forms.EmailField(label=_('Email'), widget=email_input)
    phone = forms.CharField(label=_('Phone Number'), max_length=20, widget=forms.TextInput(attrs={'class': 'form-input', 'autocomplete': 'tel'}))
    address = forms.CharField(label=_('Shipping Address'), widget=textarea)
    rental_start_date = forms.DateField(
        label=_('Rental Start Date'),
        widget=date_input,
        initial=lambda: timezone.now().date() + timezone.timedelta(days=1)
    )
    rental_end_date = forms.DateField(
        label=_('Return Date'),
        widget=date_input,
        initial=lambda: timezone.now().date() + timezone.timedelta(days=4)
    )

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("rental_start_date")
        end_date = cleaned_data.get("rental_end_date")

        if start_date and end_date and end_date < start_date:
            self.add_error('rental_end_date', _("Return date cannot be before the start date."))
        return cleaned_data

# --- CartAddItemForm ---
class CartAddItemForm(forms.Form):
    pass

# --- PaymentSlipUploadForm ---
class PaymentSlipUploadForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['payment_datetime', 'payment_slip']
        widgets = {
            'payment_datetime': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'placeholder': _('dd/mm/yyyy hh:mm')
            }),
            'payment_slip': forms.FileInput(attrs={'accept': 'image/*,application/pdf'}),
        }

# --- UserEditForm ---
class UserEditForm(forms.ModelForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-input', 'autocomplete': 'email'})
    )
    first_name = forms.CharField(
        required=False,
        label=_('First Name'),
        widget=forms.TextInput(attrs={'class': 'form-input', 'autocomplete': 'given-name'})
    )
    last_name = forms.CharField(
        required=False,
        label=_('Last Name'),
        widget=forms.TextInput(attrs={'class': 'form-input', 'autocomplete': 'family-name'})
    )

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.exclude(pk=self.instance.pk).filter(email__iexact=email).exists():
            raise forms.ValidationError(_("This email address is already in use by another account."))
        return email

# --- UserProfileForm ---
class UserProfileForm(forms.ModelForm):
    phone = forms.CharField(
        required=False,
        label=_('Phone Number'),
        widget=forms.TextInput(attrs={'class': 'form-input', 'autocomplete': 'tel'})
    )
    address = forms.CharField(
        required=False,
        label=_('Saved Address (for faster checkout)'),
        widget=forms.Textarea(attrs={'rows': 4, 'class': 'form-textarea', 'autocomplete': 'street-address'})
    )

    class Meta:
        model = UserProfile
        fields = ('phone', 'address')

# --- ReturnUploadForm ---
class ReturnUploadForm(forms.ModelForm):
    return_tracking_number = forms.CharField(
        label=_('Return Tracking Number'),
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-input'})
    )
    return_slip = forms.ImageField(
        label=_('Attach Return Slip/Parcel Photo'),
        required=True,
        widget=forms.ClearableFileInput(attrs={'class': 'form-input'})
    )

    class Meta:
        model = Order
        fields = ['return_tracking_number', 'return_slip']
