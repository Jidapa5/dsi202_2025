# outfits/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Outfit, Order, UserProfile

# --- CustomUserCreationForm ---
class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        help_text='Required. Please enter a valid email address.',
        widget=forms.EmailInput(attrs={'autocomplete': 'email'})
    )
    first_name = forms.CharField(max_length=150, required=False, label='First Name') # Add first/last name
    last_name = forms.CharField(max_length=150, required=False, label='Last Name')

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "first_name", "last_name") # Include names

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email__iexact=email).exists(): # Case-insensitive check
            raise ValidationError("An account with this email already exists.")
        return email

# --- OutfitForm (For Admin or potential future use) ---
class OutfitForm(forms.ModelForm):
    class Meta:
        model = Outfit
        fields = '__all__' # Or specify fields needed

# --- CheckoutForm ---
class CheckoutForm(forms.Form):
    # Define widgets for consistent styling
    text_input = forms.TextInput(attrs={'class': 'form-input'})
    email_input = forms.EmailInput(attrs={'class': 'form-input', 'autocomplete': 'email'})
    textarea = forms.Textarea(attrs={'rows': 3, 'class': 'form-textarea'})
    date_input = forms.DateInput(attrs={'type': 'date', 'class': 'form-input'})

    first_name = forms.CharField(label='First Name', max_length=100, widget=text_input)
    last_name = forms.CharField(label='Last Name', max_length=100, widget=text_input)
    email = forms.EmailField(label='Email', widget=email_input)
    phone = forms.CharField(label='Phone Number', max_length=20, widget=forms.TextInput(attrs={'class': 'form-input', 'autocomplete': 'tel'}))
    address = forms.CharField(label='Shipping Address', widget=textarea)
    rental_start_date = forms.DateField(
        label='Rental Start Date',
        widget=date_input,
        initial=lambda: timezone.now().date() + timezone.timedelta(days=1) # Default to tomorrow
    )
    rental_end_date = forms.DateField(
        label='Return Date',
        widget=date_input,
        initial=lambda: timezone.now().date() + timezone.timedelta(days=4) # Default to 4 days later
    )

    def clean_rental_start_date(self):
         start_date = self.cleaned_data.get('rental_start_date')
         # Optional: Prevent choosing past dates, adjust as needed
         # if start_date and start_date < timezone.now().date():
         #    raise ValidationError("Start date cannot be in the past.")
         return start_date

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("rental_start_date")
        end_date = cleaned_data.get("rental_end_date")

        if start_date and end_date:
            if end_date < start_date:
                self.add_error('rental_end_date', "Return date cannot be before the start date.")
            # Optional: Add minimum/maximum rental duration validation
            # min_duration = 1
            # max_duration = 14
            # duration = (end_date - start_date).days + 1
            # if duration < min_duration:
            #     self.add_error('rental_end_date', f"Minimum rental duration is {min_duration} day(s).")
            # if duration > max_duration:
            #     self.add_error('rental_end_date', f"Maximum rental duration is {max_duration} days.")
        return cleaned_data

# --- CartAddItemForm (Kept simple, quantity handled in view/template) ---
class CartAddItemForm(forms.Form):
    pass # Currently just a placeholder, logic is in the view

# --- PaymentSlipUploadForm ---

class PaymentSlipUploadForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['payment_datetime', 'payment_slip']
        widgets = {
            'payment_datetime': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'placeholder': 'dd/mm/yyyy hh:mm'
            }),
            'payment_slip': forms.FileInput(attrs={
                'accept': 'image/*,application/pdf'
            }),
        }

# --- UserEditForm (For profile page) ---
class UserEditForm(forms.ModelForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-input', 'autocomplete': 'email'})
    )
    first_name = forms.CharField(
        required=False,
        label='First Name',
        widget=forms.TextInput(attrs={'class': 'form-input', 'autocomplete': 'given-name'})
    )
    last_name = forms.CharField(
        required=False,
        label='Last Name',
        widget=forms.TextInput(attrs={'class': 'form-input', 'autocomplete': 'family-name'})
    )

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')

    def clean_email(self):
        """Prevent changing email to one that already exists for another user."""
        email = self.cleaned_data.get('email')
        if email and User.objects.exclude(pk=self.instance.pk).filter(email__iexact=email).exists():
            raise forms.ValidationError("This email address is already in use by another account.")
        return email

# --- UserProfileForm (For profile page) ---
class UserProfileForm(forms.ModelForm):
    phone = forms.CharField(
        required=False,
        label='Phone Number',
        widget=forms.TextInput(attrs={'class': 'form-input', 'autocomplete': 'tel'})
    )
    address = forms.CharField(
        required=False,
        label='Saved Address (for faster checkout)',
        widget=forms.Textarea(attrs={'rows': 4, 'class': 'form-textarea', 'autocomplete': 'street-address'})
    )

    class Meta:
        model = UserProfile
        fields = ('phone', 'address')

# --- ReturnUploadForm (For initiating return) ---
class ReturnUploadForm(forms.ModelForm):
    return_tracking_number = forms.CharField(
        label='Return Tracking Number',
        max_length=100,
        required=True, # Make tracking number mandatory
        widget=forms.TextInput(attrs={'class': 'form-input'})
    )
    return_slip = forms.ImageField(
        label='Attach Return Slip/Parcel Photo',
        required=True, # Make photo mandatory
        widget=forms.ClearableFileInput(attrs={'class': 'form-input'})
    )

    class Meta:
        model = Order # Linked to the Order model
        fields = ['return_tracking_number', 'return_slip']

