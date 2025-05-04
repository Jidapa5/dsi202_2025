from django.db import models
from django.conf import settings
from django.utils import timezone # เพิ่ม import

class Outfit(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    image = models.ImageField(upload_to='outfits/', null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00) # เปลี่ยนเป็น DecimalField
    is_available = models.BooleanField(default=True) # เปลี่ยนจาก is_rented เป็น is_available
    size = models.CharField(max_length=20, blank=True, null=True)
    material = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.name

class Rental(models.Model):
    STATUS_CHOICES = [
        ('pending_payment', 'Pending Payment'),
        ('payment_verification', 'Payment Verification'), # เพิ่มสถานะรอตรวจสอบ
        ('paid', 'Paid'),
        ('rented', 'Rented Out'), # ชุดกำลังถูกเช่า
        ('returned', 'Returned'), # ชุดถูกคืนแล้ว
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='rentals')
    # อาจจะต้องปรับโครงสร้าง ถ้า 1 Rental มีหลาย Outfit (Many-to-Many ผ่าน Intermediate Model)
    # แต่สำหรับตอนนี้ ทำให้ง่ายคือ 1 Rental ต่อ 1 Outfit ก่อน
    outfit = models.ForeignKey(Outfit, on_delete=models.CASCADE)
    rental_start_date = models.DateField(default=timezone.now) # เพิ่มวันเริ่มเช่า
    duration_days = models.IntegerField() # เปลี่ยนชื่อจาก duration
    # total_price ควรคำนวณตอนสร้าง หรือเก็บแยกดีกว่า?
    calculated_price = models.DecimalField(max_digits=10, decimal_places=2) # เปลี่ยนเป็น DecimalField
    payment_slip = models.ImageField(upload_to='payment_slips/', null=True, blank=True)
    payment_date = models.DateTimeField(null=True, blank=True) # เปลี่ยนเป็น DateTimeField
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending_payment') # เพิ่ม status
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} rents {self.outfit.name} ({self.status})"

    # เพิ่ม property เพื่อคำนวณวันคืน
    @property
    def return_date(self):
        if self.rental_start_date and self.duration_days:
            return self.rental_start_date + timezone.timedelta(days=self.duration_days)
        return None