from django import forms
from .models import Outfit, Rental
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model

class OutfitForm(forms.ModelForm):
    class Meta:
        model = Outfit
        fields = ['name', 'description', 'price', 'image', 'size', 'material', 'is_available'] # เพิ่ม is_available

# Form สำหรับหน้า Detail เพื่อระบุจำนวนวันเช่าก่อน Add to Cart
class AddToCartForm(forms.Form):
    duration_days = forms.IntegerField(min_value=1, initial=1, label="ระยะเวลาเช่า (วัน)")
    # quantity = forms.IntegerField(min_value=1, initial=1) # ถ้า 1 Outfit เช่าได้หลายตัวพร้อมกัน

# Form สำหรับหน้า Cart เพื่อ Update จำนวนวัน
class UpdateCartForm(forms.Form):
     duration_days = forms.IntegerField(min_value=1)
     update = forms.BooleanField(required=False, initial=False, widget=forms.HiddenInput)


class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(label="Email", required=True) # ทำให้ Email จำเป็น

    class Meta:
        model = get_user_model()
        fields = ("username", "email",)

class PaymentForm(forms.ModelForm):
    payment_date = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        required=True
    )
    payment_slip = forms.ImageField(required=True)

    class Meta:
        model = Rental
        fields = ['payment_slip', 'payment_date']