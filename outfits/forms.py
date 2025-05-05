from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Outfit
from django import forms

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")


class OutfitForm(forms.ModelForm):
    class Meta:
        model = Outfit
        fields = '__all__'

class CheckoutForm(forms.Form):
    first_name = forms.CharField(label='ชื่อจริง', max_length=30)
    last_name = forms.CharField(label='นามสกุล', max_length=30)
    email = forms.EmailField(label='อีเมล')
    phone = forms.CharField(label='เบอร์โทรศัพท์', max_length=15)
    address = forms.CharField(label='ที่อยู่จัดส่ง', widget=forms.Textarea)
    rental_start_date = forms.DateField(label='วันที่เริ่มเช่า', widget=forms.SelectDateWidget)
    rental_duration_days = forms.IntegerField(label='จำนวนวันเช่า', min_value=1)

from django import forms

class CartAddItemForm(forms.Form):
    quantity = forms.IntegerField(
        label="จำนวน",
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={"class": "w-full p-2 border rounded"})
    )

class CartUpdateItemForm(forms.Form):
    quantity = forms.IntegerField(
        label="จำนวน",
        min_value=0,
        widget=forms.NumberInput(attrs={"class": "w-full p-2 border rounded"})
    )
