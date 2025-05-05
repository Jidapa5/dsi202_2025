# outfits/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
# --- แก้ไข import model ให้ถูกต้อง ---
from .models import Outfit, Order # ต้อง import Order ด้วยสำหรับ PaymentSlipUploadForm

# --- CustomUserCreationForm (เหมือนเดิม) ---
class CustomUserCreationForm(UserCreationForm):
    # อาจจะเพิ่ม first_name, last_name ถ้าต้องการให้กรอกตอนสมัคร
    # first_name = forms.CharField(max_length=150, required=False)
    # last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        # fields = ("username", "email", "first_name", "last_name") # ถ้าเพิ่ม field
        fields = ("username", "email")

    def clean_email(self):
        email = self.cleaned_data.get('email')
        # ตรวจสอบ email ซ้ำ (เผื่อ Django version เก่าไม่มี unique=True ใน model)
        if email and User.objects.filter(email=email).exists():
            raise ValidationError("อีเมลนี้มีผู้ใช้งานแล้ว")
        return email

# --- OutfitForm (เหมือนเดิม) ---
class OutfitForm(forms.ModelForm):
    class Meta:
        model = Outfit
        fields = '__all__' # หรือระบุ fields ที่ต้องการ

# --- CheckoutForm (เหมือนเดิม) ---
class CheckoutForm(forms.Form):
    first_name = forms.CharField(label='ชื่อจริง', max_length=100, widget=forms.TextInput(attrs={'class': 'form-input'}))
    last_name = forms.CharField(label='นามสกุล', max_length=100, widget=forms.TextInput(attrs={'class': 'form-input'}))
    email = forms.EmailField(label='อีเมล', widget=forms.EmailInput(attrs={'class': 'form-input'}))
    phone = forms.CharField(label='เบอร์โทรศัพท์', max_length=20, widget=forms.TextInput(attrs={'class': 'form-input'}))
    address = forms.CharField(label='ที่อยู่จัดส่ง', widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-textarea'}))

    rental_start_date = forms.DateField(
        label='วันที่เริ่มเช่า',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
        initial=timezone.now().date() + timezone.timedelta(days=1)
    )
    rental_end_date = forms.DateField(
        label='วันที่คืน',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
        initial=timezone.now().date() + timezone.timedelta(days=4)
    )

    def clean_rental_start_date(self):
        start_date = self.cleaned_data.get('rental_start_date')
        if start_date and start_date < timezone.now().date():
            raise ValidationError("วันที่เริ่มเช่าต้องไม่เป็นวันที่ผ่านมาแล้ว")
        return start_date

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("rental_start_date")
        end_date = cleaned_data.get("rental_end_date")

        if start_date and end_date:
            if end_date < start_date:
                self.add_error('rental_end_date', "วันที่คืนต้องไม่ก่อนวันที่เริ่มเช่า")
            else:
                duration = (end_date - start_date).days + 1
                # สามารถเพิ่ม validation อื่นๆ ได้ เช่น จำนวนวันเช่าขั้นต่ำ/สูงสุด
                # if duration < 2:
                #    self.add_error(None, "ระยะเวลาเช่าขั้นต่ำคือ 2 วัน")
        return cleaned_data

# --- CartAddItemForm (เหมือนเดิม) ---
class CartAddItemForm(forms.Form):
    quantity = forms.IntegerField(
        label="จำนวน",
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={"class": "quantity-input", "style": "width: 60px; text-align: center;"})
    )

# --- CartUpdateItemForm (เหมือนเดิม) ---
class CartUpdateItemForm(forms.Form):
    quantity = forms.IntegerField(
        label="จำนวน",
        min_value=0,
        widget=forms.NumberInput(attrs={"class": "quantity-input", "style": "width: 60px; text-align: center;"})
    )


# --- เพิ่ม Form สำหรับอัปโหลดสลิป (ตรวจสอบว่ามีส่วนนี้) ---
class PaymentSlipUploadForm(forms.ModelForm):
    payment_datetime = forms.DateTimeField(
        label='วันที่และเวลาโอนเงิน',
        # ใช้ DateTimeInput สำหรับ DateTimeField
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-input'}),
        required=True
    )
    payment_slip = forms.ImageField(
        label='แนบสลิปโอนเงิน',
        required=True,
        # ใช้ ClearableFileInput สำหรับ ImageField/FileField จะดีกว่า
        widget=forms.ClearableFileInput(attrs={'class': 'form-input'})
    )

    class Meta:
        model = Order # ระบุ model ที่จะผูกด้วย
        fields = ['payment_datetime', 'payment_slip'] # ระบุ fields ที่จะใช้จาก Model Order