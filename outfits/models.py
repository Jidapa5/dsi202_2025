# outfits/models.py
from django.db import models
from django.utils.text import slugify
from django.conf import settings # Import settings เพื่อเอา User model
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal # Import Decimal ถ้าใช้ DecimalField

# --- Category Model ---
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="ชื่อหมวดหมู่")
    slug = models.SlugField(max_length=100, unique=True, blank=True, help_text="ใช้สำหรับ URL (จะสร้างให้เองถ้าเว้นว่าง)")

    class Meta:
        verbose_name = "หมวดหมู่"
        verbose_name_plural = "หมวดหมู่"
        ordering = ('name',)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
            # Check for uniqueness after slugify (in case of similar names)
            original_slug = self.slug
            counter = 1
            while Category.objects.filter(slug=self.slug).exists():
                self.slug = f'{original_slug}-{counter}'
                counter += 1
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

# --- Outfit Model ---
class Outfit(models.Model):
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='outfits', verbose_name="หมวดหมู่")
    name = models.CharField(max_length=100, verbose_name="ชื่อชุด")
    description = models.TextField(verbose_name="รายละเอียด")
    image = models.ImageField(upload_to='outfits/', null=True, blank=True, verbose_name="รูปภาพ")
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="ราคาเช่าต่อวัน") # เปลี่ยนเป็น DecimalField เพื่อความแม่นยำ
    is_active = models.BooleanField(default=True, verbose_name="ใช้งาน")

    class Meta:
        verbose_name = "ชุด"
        verbose_name_plural = "ชุด"
        ordering = ('name',)

    def __str__(self):
        return self.name

    def is_available(self, start_date, end_date):
        """
        ตรวจสอบว่าชุดนี้ว่างในช่วงเวลาที่ระบุหรือไม่
        โดยเช็คจาก OrderItem ที่มีสถานะเกี่ยวข้องกับการเช่า (เช่น processing, rented)
        (โค้ดส่วนนี้เป็นการประมาณการ อาจต้องปรับแก้ตาม Logic จริง)
        """
        if not start_date or not end_date or start_date > end_date:
            return False

        overlapping_rentals = OrderItem.objects.filter(
            outfit=self,
            order__status__in=['processing', 'rented'],
            rental_start_date__isnull=False,
        ).exclude(
            order__status__in=['cancelled', 'completed', 'failed']
        )

        for item in overlapping_rentals:
            item_end_date = item.get_rental_end_date()
            if item_end_date:
                # Check for overlap: (item_start <= requested_end) and (item_end >= requested_start)
                if item.rental_start_date <= end_date and item_end_date >= start_date:
                    return False # พบการซ้อนทับ
        return True


# --- Order Model ---
class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', 'รอชำระเงิน'),
        ('processing', 'กำลังดำเนินการ'),
        ('rented', 'กำลังเช่า'),
        ('completed', 'เสร็จสิ้น'),
        ('cancelled', 'ยกเลิก'),
        ('failed', 'การชำระเงินล้มเหลว'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders', verbose_name="ผู้ใช้")
    first_name = models.CharField(max_length=100, verbose_name="ชื่อจริง")
    last_name = models.CharField(max_length=100, verbose_name="นามสกุล")
    email = models.EmailField(verbose_name="อีเมล")
    phone = models.CharField(max_length=20, verbose_name="เบอร์โทรศัพท์")
    address = models.TextField(verbose_name="ที่อยู่")

    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="ยอดรวม")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="วันที่สร้าง")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="วันที่อัปเดต")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="สถานะ")

    payment_method = models.CharField(max_length=50, blank=True, verbose_name="วิธีชำระเงิน")
    payment_id = models.CharField(max_length=100, blank=True, null=True, verbose_name="Payment ID (จาก Gateway)")
    paid = models.BooleanField(default=False, verbose_name="ชำระเงินแล้ว")

    class Meta:
        verbose_name = "คำสั่งเช่า"
        verbose_name_plural = "คำสั่งเช่า"
        ordering = ('-created_at',)

    def __str__(self):
        return f"คำสั่งเช่า #{self.id} ({self.first_name} {self.last_name})"

    def get_total_cost(self):
        # คำนวณใหม่จาก items
        total = Decimal('0.00')
        for item in self.items.all():
             total += item.get_cost() # ใช้ get_cost ที่แก้ไขแล้ว
        return total


# --- OrderItem Model ---
class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE, verbose_name="คำสั่งเช่า")
    outfit = models.ForeignKey(Outfit, related_name='order_items', on_delete=models.PROTECT, verbose_name="ชุด")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="ราคาต่อวัน (ณ ตอนสั่ง)", null=True) # อนุญาตให้เป็น Null ชั่วคราวตอนสร้างใน admin
    quantity = models.PositiveIntegerField(default=1, verbose_name="จำนวน")
    rental_start_date = models.DateField(verbose_name="วันที่เริ่มเช่า", null=True) # อนุญาตให้เป็น Null ชั่วคราวตอนสร้างใน admin
    rental_duration_days = models.PositiveIntegerField(default=1, verbose_name="จำนวนวันเช่า")

    class Meta:
        verbose_name = "รายการในคำสั่งเช่า"
        verbose_name_plural = "รายการในคำสั่งเช่า"

    def __str__(self):
        return f"{self.quantity} x {self.outfit.name} (Order #{self.order.id})"

    def get_cost(self):
        # *** แก้ไขแล้ว: ตรวจสอบค่า None ก่อนคำนวณ ***
        if self.price is not None and self.rental_duration_days is not None and self.quantity is not None:
            try:
                # ใช้ Decimal เพื่อความแม่นยำ
                return Decimal(self.price) * Decimal(self.rental_duration_days) * Decimal(self.quantity)
            except (TypeError, ValueError):
                # ดักจับ Error อื่นๆ ที่อาจเกิดขึ้นระหว่างการแปลงค่า
                return Decimal('0.00')
        # ถ้าค่าไม่ครบ ให้ return 0
        return Decimal('0.00')

    def get_rental_end_date(self):
        if self.rental_start_date and self.rental_duration_days:
            return self.rental_start_date + timedelta(days=self.rental_duration_days - 1)
        return None

    def clean(self):
        # Validation ตอนบันทึกข้อมูลจริง (ไม่ใช่ตอนแสดงใน admin add)
        if self.pk: # ตรวจสอบเฉพาะตอนแก้ไข หรือหลังจากสร้างแล้ว
            if self.rental_duration_days < 1:
                raise ValidationError("จำนวนวันเช่าต้องมากกว่า 0")
            if self.rental_start_date and self.rental_start_date < timezone.now().date():
                raise ValidationError("วันที่เริ่มเช่าต้องไม่เป็นอดีต")
            if self.price is None:
                raise ValidationError("ราคาต่อวันต้องไม่เป็นค่าว่าง")
            if self.rental_start_date is None:
                raise ValidationError("วันที่เริ่มเช่าต้องไม่เป็นค่าว่าง")

    def save(self, *args, **kwargs):
        # ตั้งราคา price จาก outfit.price ตอนสร้าง item ครั้งแรก (ถ้ายังไม่มี)
        if not self.pk and self.outfit and self.price is None:
             self.price = self.outfit.price
        super().save(*args, **kwargs)