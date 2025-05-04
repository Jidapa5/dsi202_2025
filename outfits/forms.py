from django import forms
from .models import Outfit
from django.contrib.auth.forms import UserCreationForm # Added
from django.contrib.auth import get_user_model # Added

class OutfitForm(forms.ModelForm):
    class Meta:
        model = Outfit
        fields = ['name', 'description', 'price', 'image', 'size', 'material']  # Modified

class RentForm(forms.Form):
    duration = forms.IntegerField(min_value=1, label="ระยะเวลาเช่า (วัน)")

class UserRegistrationForm(UserCreationForm): # Added
    email = forms.EmailField(label="Email")

    class Meta:
        model = get_user_model()
        fields = ("username", "email",)

class PaymentForm(forms.ModelForm):  # เพิ่ม Form นี้
    class Meta:
        model = Rental
        fields = ['payment_slip', 'payment_date']