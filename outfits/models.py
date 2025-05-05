# outfits/models.py
from django.db import models
from django.utils.text import slugify
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone # --- เพิ่ม import timezone ---
from datetime import date, timedelta
from decimal import Decimal
from django.db.models import Sum
from django.db.models.signals import post_save
from django.dispatch import receiver

# --- Category Model ---
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="ชื่อหมวดหมู่")
    slug = models.SlugField(max_length=100, unique=True, blank=True, help_text="ใช้สำหรับ URL (จะสร้างให้เองถ้าเว้นว่าง)")
    class Meta: verbose_name = "หมวดหมู่"; verbose_name_plural = "หมวดหมู่"; ordering = ('name',)
    def save(self, *args, **kwargs):
        if not self.slug: self.slug = slugify(self.name); original_slug = self.slug; counter = 1
        while Category.objects.filter(slug=self.slug).exists(): self.slug = f'{original_slug}-{counter}'; counter += 1
        super().save(*args, **kwargs)
    def __str__(self): return self.name

# --- Outfit Model ---
class Outfit(models.Model):
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='outfits', verbose_name="หมวดหมู่")
    name = models.CharField(max_length=100, verbose_name="ชื่อชุด")
    description = models.TextField(verbose_name="รายละเอียด")
    image = models.ImageField(upload_to='outfits/', null=True, blank=True, verbose_name="รูปภาพ")
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="ราคาเช่าต่อวัน")
    is_active = models.BooleanField(default=True, verbose_name="ใช้งาน")
    class Meta: verbose_name = "ชุด"; verbose_name_plural = "ชุด"; ordering = ('name',)
    def __str__(self): return self.name
    def is_available(self, start_date, end_date, quantity=1):
        if not start_date or not end_date or start_date > end_date or quantity < 1: return False
        relevant_statuses = ['pending', 'waiting_for_approval', 'processing', 'shipped', 'rented']
        overlapping_items = self.order_items.filter(order__status__in=relevant_statuses, order__rental_start_date__lte=end_date, order__rental_end_date__gte=start_date)
        booked_quantity = overlapping_items.aggregate(total_quantity=Sum('quantity'))['total_quantity'] or 0
        if booked_quantity >= 1: return False
        return True

# --- Order Model (เพิ่ม Field และ Status) ---
class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', 'รอชำระเงิน'),
        ('waiting_for_approval', 'รอตรวจสอบสลิป'),
        ('processing', 'กำลังดำเนินการ'),
        ('shipped', 'จัดส่งแล้ว'),
        ('rented', 'กำลังเช่า'),
        # ('return_pending', 'รอส่งคืน'), # อาจใช้ rented แทน หรือแยกก็ได้
        ('return_shipped', 'ลูกค้าส่งคืนแล้ว'), # <--- เพิ่ม: ลูกค้าแจ้งส่งของคืนแล้ว
        ('return_received', 'ได้รับคืนแล้ว'),
        ('completed', 'เสร็จสิ้น'),
        ('cancelled', 'ยกเลิก'),
        ('failed', 'การชำระเงินล้มเหลว/สลิปไม่ถูกต้อง'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders', verbose_name="ผู้ใช้")
    first_name = models.CharField(max_length=100, verbose_name="ชื่อจริง")
    last_name = models.CharField(max_length=100, verbose_name="นามสกุล")
    email = models.EmailField(verbose_name="อีเมล")
    phone = models.CharField(max_length=20, verbose_name="เบอร์โทรศัพท์")
    address = models.TextField(verbose_name="ที่อยู่สำหรับจัดส่ง")
    rental_start_date = models.DateField(verbose_name="วันที่เริ่มเช่า", null=True, blank=True)
    rental_end_date = models.DateField(verbose_name="วันที่สิ้นสุดเช่า", null=True, blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="ยอดรวม")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="วันที่สร้าง")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="วันที่อัปเดต")
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending', verbose_name="สถานะ")
    paid = models.BooleanField(default=False, verbose_name="ยืนยันการชำระเงินแล้ว")
    payment_method = models.CharField(max_length=50, default='Bank Transfer', editable=False, verbose_name="วิธีชำระเงิน")
    payment_slip = models.ImageField(upload_to='payment_slips/%Y/%m/', blank=True, null=True, verbose_name="สลิปการโอนเงิน")
    payment_datetime = models.DateTimeField(blank=True, null=True, verbose_name="วันเวลาที่โอน (ตามที่แจ้ง)")
    admin_payment_note = models.TextField(blank=True, verbose_name="หมายเหตุ (การชำระเงิน)")
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="ค่าจัดส่ง")
    shipping_tracking_number = models.CharField(max_length=100, blank=True, null=True, verbose_name="เลขพัสดุ (ส่ง)")

    # --- เพิ่ม Field สำหรับการส่งคืน ---
    return_tracking_number = models.CharField(max_length=100, blank=True, null=True, verbose_name="เลขพัสดุ (คืน)")
    return_slip = models.ImageField(
        upload_to='return_slips/%Y/%m/', # เก็บรูปสลิปส่งคืน
        blank=True,
        null=True,
        verbose_name="รูปถ่าย/สลิปส่งคืน"
    )
    return_initiated_at = models.DateTimeField( # วันเวลาที่ลูกค้ากดแจ้งส่งคืน
        blank=True,
        null=True,
        verbose_name="วันที่แจ้งส่งคืน"
    )
    # --- จบส่วนที่เพิ่ม ---

    class Meta: verbose_name = "คำสั่งเช่า"; verbose_name_plural = "คำสั่งเช่า"; ordering = ('-created_at',)
    def __str__(self): return f"คำสั่งเช่า #{self.id} ({self.first_name} {self.last_name})"
    @property
    def rental_duration_days(self):
        if self.rental_start_date and self.rental_end_date and self.rental_end_date >= self.rental_start_date:
            return (self.rental_end_date - self.rental_start_date).days + 1
        return 0
    def calculate_items_total(self):
        total = Decimal('0.00')
        duration = self.rental_duration_days
        if duration > 0 and self.pk:
            for item in self.items.all():
                if item.price_per_day is not None: total += item.price_per_day * duration * item.quantity
        return total
    def calculate_total_amount(self):
        items_total = self.calculate_items_total()
        grand_total = items_total + self.shipping_cost
        return grand_total
    def clean(self):
        if self.rental_start_date and self.rental_end_date:
            if self.rental_end_date < self.rental_start_date: raise ValidationError("วันที่สิ้นสุดเช่าต้องไม่ก่อนวันที่เริ่มเช่า")
        elif self.rental_start_date or self.rental_end_date:
             if not (self.rental_start_date and self.rental_end_date): pass

# --- OrderItem Model ---
class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE, verbose_name="คำสั่งเช่า")
    outfit = models.ForeignKey(Outfit, related_name='order_items', on_delete=models.PROTECT, verbose_name="ชุด")
    price_per_day = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="ราคาต่อวัน (ณ ตอนสั่ง)", null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1, verbose_name="จำนวน")
    class Meta: verbose_name = "รายการในคำสั่งเช่า"; verbose_name_plural = "รายการในคำสั่งเช่า"
    def __str__(self): return f"{self.quantity} x {self.outfit.name} (Order #{self.order.id})"
    @property
    def item_total_cost(self):
        if hasattr(self, 'order') and self.order:
             duration = self.order.rental_duration_days
             if self.price_per_day is not None and duration > 0: return self.price_per_day * duration * self.quantity
        return Decimal('0.00')
    def save(self, *args, **kwargs):
        if not self.pk and self.outfit and self.price_per_day is None: self.price_per_day = self.outfit.price
        super().save(*args, **kwargs)

# --- UserProfile Model ---
class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile', verbose_name="ผู้ใช้")
    phone = models.CharField(max_length=20, blank=True, verbose_name="เบอร์โทรศัพท์")
    address = models.TextField(blank=True, verbose_name="ที่อยู่ (สำหรับบันทึก)")
    class Meta: verbose_name = "ข้อมูลโปรไฟล์ผู้ใช้"; verbose_name_plural = "ข้อมูลโปรไฟล์ผู้ใช้"
    def __str__(self): return f"Profile for {self.user.username}"

# --- Signal Receivers ---
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created: UserProfile.objects.create(user=instance)
    if hasattr(instance, 'profile'): instance.profile.save()
    else: UserProfile.objects.create(user=instance)