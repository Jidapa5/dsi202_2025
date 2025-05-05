# outfits/models.py
from django.db import models
from django.utils.text import slugify
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import date, timedelta # แก้ไข import
from decimal import Decimal

# --- Category Model (เหมือนเดิม) ---
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
            original_slug = self.slug
            counter = 1
            while Category.objects.filter(slug=self.slug).exists():
                self.slug = f'{original_slug}-{counter}'
                counter += 1
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

# --- Outfit Model (เหมือนเดิม) ---
class Outfit(models.Model):
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='outfits', verbose_name="หมวดหมู่")
    name = models.CharField(max_length=100, verbose_name="ชื่อชุด")
    description = models.TextField(verbose_name="รายละเอียด")
    image = models.ImageField(upload_to='outfits/', null=True, blank=True, verbose_name="รูปภาพ")
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="ราคาเช่าต่อวัน")
    is_active = models.BooleanField(default=True, verbose_name="ใช้งาน")

    class Meta:
        verbose_name = "ชุด"
        verbose_name_plural = "ชุด"
        ordering = ('name',)

    def __str__(self):
        return self.name

    def is_available(self, start_date, end_date):
        """
        ตรวจสอบว่าชุดนี้ว่างในช่วงวันที่ระบุหรือไม่
        (ต้องปรับปรุง Logic ให้แม่นยำขึ้นตามสถานะ Order)
        """
        if not start_date or not end_date or start_date > end_date:
            return False

        # ค้นหา OrderItems ที่มีการเช่าชุดนี้และช่วงเวลาทับซ้อน
        # สถานะที่ถือว่า 'ไม่ว่าง': กำลังดำเนินการ, กำลังเช่า (อาจรวม รอชำระเงิน ถ้าต้องการจองทันที)
        overlapping_rentals = OrderItem.objects.filter(
            outfit=self,
            order__status__in=['processing', 'rented'], # หรือ ['pending', 'processing', 'rented']
            rental_start_date__lte=end_date,   # เริ่มเช่า <= วันสิ้นสุดที่ขอ
            rental_end_date__gte=start_date    # สิ้นสุดเช่า >= วันเริ่มต้นที่ขอ
        )

        # ถ้าพบรายการที่ทับซ้อน แสดงว่าไม่ว่าง
        return not overlapping_rentals.exists()


# --- Order Model (ปรับปรุง get_total_cost) ---
class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', 'รอชำระเงิน'),
        ('processing', 'กำลังดำเนินการ'), # จ่ายเงินแล้ว รอจัดส่ง
        ('shipped', 'จัดส่งแล้ว'),       # เพิ่มสถานะ: จัดส่งแล้ว
        ('rented', 'กำลังเช่า'),         # ลูกค้ารับของแล้ว เริ่มนับวันเช่า
        ('return_pending', 'รอส่งคืน'),  # ครบกำหนด ลูกค้าต้องส่งคืน
        ('return_received', 'ได้รับคืนแล้ว'), # ร้านได้รับของคืนแล้ว รอตรวจสอบ
        ('completed', 'เสร็จสิ้น'),       # ตรวจสอบของเรียบร้อย
        ('cancelled', 'ยกเลิก'),
        ('failed', 'การชำระเงินล้มเหลว'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders', verbose_name="ผู้ใช้")
    first_name = models.CharField(max_length=100, verbose_name="ชื่อจริง")
    last_name = models.CharField(max_length=100, verbose_name="นามสกุล")
    email = models.EmailField(verbose_name="อีเมล")
    phone = models.CharField(max_length=20, verbose_name="เบอร์โทรศัพท์")
    address = models.TextField(verbose_name="ที่อยู่สำหรับจัดส่ง") # เปลี่ยนชื่อให้ชัดเจน

    # วันที่เช่า (อาจย้ายไปเก็บที่ OrderItem ถ้าต้องการให้แต่ละชิ้นมีวันเช่าต่างกัน)
    # แต่ถ้ายึดตาม form ปัจจุบัน ให้เก็บที่ Order
    rental_start_date = models.DateField(verbose_name="วันที่เริ่มเช่า", null=True, blank=True)
    rental_end_date = models.DateField(verbose_name="วันที่สิ้นสุดเช่า", null=True, blank=True)

    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="ยอดรวม")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="วันที่สร้าง")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="วันที่อัปเดต")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="สถานะ")

    payment_method = models.CharField(max_length=50, blank=True, verbose_name="วิธีชำระเงิน")
    payment_id = models.CharField(max_length=100, blank=True, null=True, verbose_name="Payment ID (จาก Gateway)")
    paid = models.BooleanField(default=False, verbose_name="ชำระเงินแล้ว")

    # เพิ่ม Field สำหรับการจัดส่งและคืน
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="ค่าจัดส่ง")
    shipping_tracking_number = models.CharField(max_length=100, blank=True, null=True, verbose_name="เลขพัสดุ (ส่ง)")
    return_tracking_number = models.CharField(max_length=100, blank=True, null=True, verbose_name="เลขพัสดุ (คืน)")


    class Meta:
        verbose_name = "คำสั่งเช่า"
        verbose_name_plural = "คำสั่งเช่า"
        ordering = ('-created_at',)

    def __str__(self):
        return f"คำสั่งเช่า #{self.id} ({self.first_name} {self.last_name})"

    @property
    def rental_duration_days(self):
        """คำนวณจำนวนวันเช่าจากวันที่เริ่มและสิ้นสุด"""
        if self.rental_start_date and self.rental_end_date and self.rental_end_date >= self.rental_start_date:
             # +1 เพราะนับรวมวันแรกด้วย (เช่น เช่า 5 ถึง 6 คือ 2 วัน)
            return (self.rental_end_date - self.rental_start_date).days + 1
        return 0

    def calculate_items_total(self):
        """คำนวณราคารวมเฉพาะค่าเช่าสินค้า"""
        total = Decimal('0.00')
        duration = self.rental_duration_days
        if duration > 0:
            for item in self.items.all():
                 # ดึงราคาต่อวันจาก OrderItem (ที่บันทึกไว้ตอนสั่ง)
                if item.price_per_day is not None:
                    total += item.price_per_day * duration * item.quantity
        return total

    def calculate_total_amount(self):
        """คำนวณยอดรวมทั้งหมด (ค่าเช่า + ค่าส่ง)"""
        items_total = self.calculate_items_total()
        # อาจเพิ่มค่าส่งหรือค่าธรรมเนียมอื่นๆ ตรงนี้
        grand_total = items_total + self.shipping_cost
        return grand_total

    def save(self, *args, **kwargs):
        # คำนวณ total_amount ใหม่ทุกครั้งก่อน save (ถ้าต้องการ)
        # หรือจะคำนวณตอนสร้าง Order เท่านั้นก็ได้
        self.total_amount = self.calculate_total_amount()
        super().save(*args, **kwargs)

    def clean(self):
        if self.rental_start_date and self.rental_end_date:
            if self.rental_end_date < self.rental_start_date:
                raise ValidationError("วันที่สิ้นสุดเช่าต้องไม่ก่อนวันที่เริ่มเช่า")
            if self.rental_start_date < timezone.now().date() and not self.pk: # ตรวจสอบเฉพาะตอนสร้างใหม่
                 raise ValidationError("วันที่เริ่มเช่าต้องไม่เป็นอดีต")
        elif self.rental_start_date or self.rental_end_date:
             raise ValidationError("ต้องระบุทั้งวันที่เริ่มเช่าและวันที่สิ้นสุดเช่า")


# --- OrderItem Model (ปรับปรุง) ---
class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE, verbose_name="คำสั่งเช่า")
    outfit = models.ForeignKey(Outfit, related_name='order_items', on_delete=models.PROTECT, verbose_name="ชุด")
    # เก็บราคาต่อวัน ณ ตอนที่สั่งซื้อ ป้องกันกรณีราคาชุดเปลี่ยนทีหลัง
    price_per_day = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="ราคาต่อวัน (ณ ตอนสั่ง)", null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1, verbose_name="จำนวน")

    # *** ลบ field วันที่เช่าออกจาก OrderItem (ย้ายไปที่ Order) ***
    # rental_start_date = models.DateField(verbose_name="วันที่เริ่มเช่า", null=True)
    # rental_end_date = models.DateField(verbose_name="วันที่สิ้นสุดเช่า", null=True) # เพิ่ม field นี้

    class Meta:
        verbose_name = "รายการในคำสั่งเช่า"
        verbose_name_plural = "รายการในคำสั่งเช่า"

    def __str__(self):
        return f"{self.quantity} x {self.outfit.name} (Order #{self.order.id})"

    @property
    def item_total_cost(self):
        """คำนวณราคารวมสำหรับรายการสินค้านี้ ตามจำนวนวันที่เช่าใน Order"""
        duration = self.order.rental_duration_days
        if self.price_per_day is not None and duration > 0:
            return self.price_per_day * duration * self.quantity
        return Decimal('0.00')

    def save(self, *args, **kwargs):
        # ดึงราคาปัจจุบันของ Outfit มาใส่ใน price_per_day ตอนสร้าง OrderItem ครั้งแรก
        if not self.pk and self.outfit and self.price_per_day is None:
            self.price_per_day = self.outfit.price
        super().save(*args, **kwargs)

    # ลบ clean() และ get_rental_end_date() ออก เพราะย้ายไป Order แล้ว