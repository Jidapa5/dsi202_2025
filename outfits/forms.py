# outfits/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm # เพิ่ม UserChangeForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
# --- แก้ไข import model ให้ถูกต้อง ---
from .models import Outfit, Order, UserProfile # เพิ่ม UserProfile

# --- CustomUserCreationForm (แก้ไข Indentation) ---
class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email") # เอา password ออก ใช้ field ของ UserCreationForm

    def clean_email(self):
        email = self.cleaned_data.get('email')
        # --- ตรวจสอบการย่อหน้าตรงนี้ ---
        if email and User.objects.filter(email=email).exists():
            raise ValidationError("อีเมลนี้มีผู้ใช้งานแล้ว")
        # --- บรรทัด return ต้องย่อหน้าเท่ากับ if (อยู่ในระดับเดียวกัน) ---
        return email

# --- OutfitForm ---
class OutfitForm(forms.ModelForm):
    class Meta:
        model = Outfit
        fields = '__all__' # หรือระบุ fields ที่ต้องการ

# --- CheckoutForm ---
class CheckoutForm(forms.Form):
    first_name = forms.CharField(label='ชื่อจริง', max_length=100, widget=forms.TextInput(attrs={'class': 'form-input'}))
    last_name = forms.CharField(label='นามสกุล', max_length=100, widget=forms.TextInput(attrs={'class': 'form-input'}))
    email = forms.EmailField(label='อีเมล', widget=forms.EmailInput(attrs={'class': 'form-input'}))
    phone = forms.CharField(label='เบอร์โทรศัพท์', max_length=20, widget=forms.TextInput(attrs={'class': 'form-input'}))
    address = forms.CharField(label='ที่อยู่จัดส่ง', widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-textarea'}))
    rental_start_date = forms.DateField(label='วันที่เริ่มเช่า', widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}), initial=timezone.now().date() + timezone.timedelta(days=1))
    rental_end_date = forms.DateField(label='วันที่คืน', widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}), initial=timezone.now().date() + timezone.timedelta(days=4))

    def clean_rental_start_date(self):
         start_date = self.cleaned_data.get('rental_start_date')
         # if start_date and start_date < timezone.now().date(): raise ValidationError("วันที่เริ่มเช่าต้องไม่เป็นวันที่ผ่านมาแล้ว")
         return start_date
    def clean(self):
        cleaned_data = super().clean(); start_date = cleaned_data.get("rental_start_date"); end_date = cleaned_data.get("rental_end_date")
        if start_date and end_date:
            if end_date < start_date: self.add_error('rental_end_date', "วันที่คืนต้องไม่ก่อนวันที่เริ่มเช่า")
        return cleaned_data

# --- CartAddItemForm ---
class CartAddItemForm(forms.Form): pass # ฟอร์มเปล่า

# --- PaymentSlipUploadForm ---
class PaymentSlipUploadForm(forms.ModelForm):
    payment_datetime = forms.DateTimeField(label='วันที่และเวลาโอนเงิน', widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-input'}), required=True)
    payment_slip = forms.ImageField(label='แนบสลิปโอนเงิน', required=True, widget=forms.ClearableFileInput(attrs={'class': 'form-input'}))
    class Meta: model = Order; fields = ['payment_datetime', 'payment_slip']

# --- Form สำหรับแก้ไข User ---
class UserEditForm(forms.ModelForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-input'}))
    first_name = forms.CharField(required=False, label='ชื่อจริง', widget=forms.TextInput(attrs={'class': 'form-input'}))
    last_name = forms.CharField(required=False, label='นามสกุล', widget=forms.TextInput(attrs={'class': 'form-input'}))

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.exclude(pk=self.instance.pk).filter(email=email).exists():
            raise forms.ValidationError("อีเมลนี้มีผู้ใช้งานอื่นใช้อยู่แล้ว")
        return email

# --- Form สำหรับแก้ไข User Profile ---
class UserProfileForm(forms.ModelForm):
    phone = forms.CharField(required=False, label='เบอร์โทรศัพท์', widget=forms.TextInput(attrs={'class': 'form-input'}))
    address = forms.CharField(required=False, label='ที่อยู่ (สำหรับบันทึก)', widget=forms.Textarea(attrs={'rows': 4, 'class': 'form-textarea'}))

    class Meta:
        model = UserProfile
        fields = ('phone', 'address')

class ReturnUploadForm(forms.ModelForm):
    return_tracking_number = forms.CharField(
        label='เลขพัสดุส่งคืน',
        max_length=100,
        required=True, # บังคับกรอกเลขพัสดุ
        widget=forms.TextInput(attrs={'class': 'form-input'})
    )
    return_slip = forms.ImageField(
        label='แนบรูปถ่ายพัสดุ/สลิปส่งคืน',
        required=True, # บังคับแนบรูป
        widget=forms.ClearableFileInput(attrs={'class': 'form-input'})
    )

    class Meta:
        model = Order # ผูกกับ Model Order
        # ระบุ fields ที่จะให้ฟอร์มนี้จัดการ
        fields = ['return_tracking_number', 'return_slip']