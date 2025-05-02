from django import forms
from .models import Outfit

class OutfitForm(forms.ModelForm):
    class Meta:
        model = Outfit
        fields = ['name', 'description', 'price', 'image']

class RentForm(forms.Form):
    duration = forms.IntegerField(min_value=1, label="ระยะเวลาเช่า (วัน)")