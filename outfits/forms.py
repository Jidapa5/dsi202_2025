# outfits/forms.py
from django import forms
from django.utils import timezone
from .models import Outfit, Order, Category # Import Category, Order

# --- Outfit Form (เพิ่ม category) ---
class OutfitForm(forms.ModelForm):
    class Meta:
        model = Outfit
        fields = ['category', 'name', 'description', 'price', 'image', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }


# --- Cart Add/Update Form (อาจจะใช้ใน template โดยตรง หรือสร้างฟอร์ม) ---
class CartAddItemForm(forms.Form):
    quantity = forms.IntegerField(min_value=1, initial=1, widget=forms.NumberInput(attrs={'min': '1'}))
    # update = forms.BooleanField(required=False, initial=False, widget=forms.HiddenInput) # ใช้แยกแยะว่าเป็นการเพิ่มใหม่หรืออัปเดต

class CartUpdateItemForm(forms.Form):
    quantity = forms.IntegerField(min_value=0, widget=forms.NumberInput(attrs={'min': '0'})) # 0 หมายถึงลบ


# --- Checkout Form ---
class CheckoutForm(forms.Form):
    first_name = forms.CharField(max_length=100, label="ชื่อจริง", required=True,
                                 widget=forms.TextInput(attrs={'placeholder': 'ชื่อจริง'}))
    last_name = forms.CharField(max_length=100, label="นามสกุล", required=True,
                                widget=forms.TextInput(attrs={'placeholder': 'นามสกุล'}))
    email = forms.EmailField(label="อีเมล", required=True,
                             widget=forms.EmailInput(attrs={'placeholder': 'example@mail.com'}))
    phone = forms.CharField(max_length=20, label="เบอร์โทรศัพท์", required=True,
                            widget=forms.TextInput(attrs={'placeholder': '08xxxxxxxx'}))
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': 4, 'placeholder': 'บ้านเลขที่, ถนน, ตำบล, อำเภอ, จังหวัด, รหัสไปรษณีย์'}),
                              label="ที่อยู่สำหรับติดต่อ/จัดส่ง", required=True)
    rental_start_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'min': timezone.now().date().isoformat()}),
        label="วันที่เริ่มเช่า", required=True, initial=timezone.now().date()
    )
    rental_duration_days = forms.IntegerField(min_value=1, initial=1, label="จำนวนวันเช่า", required=True,
                                            widget=forms.NumberInput(attrs={'min': '1'}))

    # อาจจะเพิ่ม field อื่นๆ เช่น หมายเหตุ

    def clean_rental_start_date(self):
        date = self.cleaned_data.get('rental_start_date')
        if date and date < timezone.now().date():
            raise forms.ValidationError("วันที่เริ่มเช่าต้องไม่เป็นวันที่ผ่านมาแล้ว")
        return date

    # clean() method สำหรับ validate ข้อมูลทั้งหมดพร้อมกัน (เช่น เช็ค availability)
    # def clean(self):
    #     cleaned_data = super().clean()
    #     start_date = cleaned_data.get('rental_start_date')
    #     duration = cleaned_data.get('rental_duration_days')
    #     cart_items = self.initial.get('cart_items') # ต้องส่ง cart_items มาตอนสร้าง form instance

    #     if start_date and duration and cart_items:
    #         end_date = start_date + timedelta(days=duration - 1)
    #         for item_context in cart_items:
    #             outfit = item_context['outfit']
    #             if not outfit.is_available(start_date, end_date):
    #                 raise forms.ValidationError(f"ขออภัย ชุด '{outfit.name}' ไม่ว่างในช่วงวันที่ {start_date.strftime('%d/%m/%Y')} ถึง {end_date.strftime('%d/%m/%Y')}")
    #     return cleaned_data


# --- RentForm (ไม่น่าจะได้ใช้แล้ว) ---
# class RentForm(forms.Form):
#     duration = forms.IntegerField(min_value=1, label="ระยะเวลาเช่า (วัน)")