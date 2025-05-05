# outfits/admin.py (เวอร์ชัน Bank Transfer)

from django.contrib import admin, messages # เพิ่ม messages
from django.utils.html import format_html
from django.urls import reverse
from .models import Outfit, Category, Order, OrderItem
from django.utils.translation import ngettext # สำหรับ messages

# --- Category Admin (เหมือนเดิม) ---
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)

# --- Outfit Admin (เหมือนเดิม) ---
@admin.register(Outfit)
class OutfitAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('name', 'description')
    list_editable = ('price', 'is_active')
    autocomplete_fields = ('category',)
    readonly_fields = ('image_preview',)

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 100px; max-width: 100px;" />', obj.image.url)
        return "(No image)"
    image_preview.short_description = 'Preview'

# --- OrderItem Inline Admin (เหมือนเดิมจากครั้งก่อน) ---
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    fields = ('outfit', 'quantity', 'price_per_day', 'get_item_total_cost_display')
    readonly_fields = ('price_per_day', 'get_item_total_cost_display')
    extra = 0
    can_delete = True
    autocomplete_fields = ('outfit',)

    def get_item_total_cost_display(self, obj):
        if obj.order:
            cost = obj.item_total_cost
            # ใช้ f-string และ format specifier สำหรับ comma และ .2f
            return f"{cost:,.2f} บาท"
        return "N/A"
    get_item_total_cost_display.short_description = 'ราคารวมรายการนี้'


# --- Order Admin (ปรับปรุงสำหรับ Bank Transfer) ---
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'user_display', 'created_at', 'rental_start_date',
        'status', 'total_amount', 'paid', 'payment_slip_thumbnail' # เพิ่ม thumbnail
    )
    list_filter = ('status', 'paid', 'created_at', 'rental_start_date')
    search_fields = ('id', 'first_name', 'last_name', 'email', 'phone', 'user__username')
    readonly_fields = (
        'id', 'user_link', 'created_at', 'updated_at', 'total_amount',
        'payment_method', 'payment_datetime', 'payment_slip_display', # แสดงสลิปแบบ readonly
        'shipping_tracking_number', 'return_tracking_number'
    )
    list_editable = ('status',) # อาจจะต้องเอาออกถ้าให้ approve ผ่าน action
    inlines = [OrderItemInline]
    actions = ['mark_payment_approved', 'mark_payment_rejected'] # <--- เพิ่ม Actions

    fieldsets = (
        ('ข้อมูลคำสั่งเช่า', {
            'fields': ('id', 'user_link', 'status', 'paid', 'created_at', 'updated_at')
        }),
        ('ข้อมูลลูกค้าและการจัดส่ง', {
            'fields': ('first_name', 'last_name', 'email', 'phone', 'address', 'shipping_cost', 'shipping_tracking_number', 'return_tracking_number')
        }),
        ('ช่วงเวลาเช่า', {
            'fields': ('rental_start_date', 'rental_end_date')
        }),
        ('ข้อมูลการชำระเงิน (Bank Transfer)', { # เปลี่ยนชื่อ section
            'fields': ('total_amount', 'payment_method', 'payment_datetime', 'payment_slip_display', 'admin_payment_note') # เพิ่ม field ที่เกี่ยวข้อง
        }),
    )

    def payment_slip_thumbnail(self, obj):
        """แสดงรูปสลิปเล็กๆ ใน List View"""
        if obj.payment_slip:
            return format_html('<a href="{0}" target="_blank"><img src="{0}" style="max-height: 40px; max-width: 40px;" /></a>', obj.payment_slip.url)
        return "ไม่มีสลิป"
    payment_slip_thumbnail.short_description = 'สลิป'

    def payment_slip_display(self, obj):
        """แสดงรูปสลิปใหญ่ขึ้นใน Detail View"""
        if obj.payment_slip:
            return format_html('<a href="{0}" target="_blank"><img src="{0}" style="max-height: 300px; max-width: 300px;" /></a>', obj.payment_slip.url)
        return "ยังไม่มีการแนบสลิป"
    payment_slip_display.short_description = 'สลิปที่แนบมา'

    def user_display(self, obj):
        return obj.user.username if obj.user else "Guest"
    user_display.short_description = 'ผู้ใช้'

    def user_link(self, obj):
        if obj.user:
            url = reverse("admin:auth_user_change", args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', url, obj.user.username)
        return "Guest"
    user_link.short_description = 'ผู้ใช้ (ลิงก์)'

    def get_readonly_fields(self, request, obj=None):
        # ทำให้ field ส่วนใหญ่ readonly หลังสร้าง order
        base_readonly = list(self.readonly_fields)
        if obj:
            # เพิ่ม admin_payment_note เข้าไปในส่วนที่ *ไม่* readonly ตอนแก้ไข
            # ยกเว้นถ้าสถานะไม่ใช่ waiting_for_approval หรือ failed
            current_readonly = base_readonly + [
                'user_link', 'first_name', 'last_name', 'email', 'phone',
                'address', 'rental_start_date', 'rental_end_date', 'shipping_cost'
            ]
            # ถ้าสถานะเป็น pending หรือ completed แล้ว ไม่ควรแก้ note การจ่ายเงิน
            if obj.status not in ['waiting_for_approval', 'failed']:
                 current_readonly.append('admin_payment_note')
            return tuple(current_readonly)

        return tuple(base_readonly)

    # --- Admin Actions ---
    @admin.action(description='อนุมัติการชำระเงินที่เลือก')
    def mark_payment_approved(self, request, queryset):
        updated_count = 0
        for order in queryset.filter(status='waiting_for_approval'):
            order.status = 'processing' # เปลี่ยนเป็นกำลังดำเนินการ
            order.paid = True
            order.admin_payment_note = f"Approved by {request.user.username} on {timezone.now().strftime('%Y-%m-%d %H:%M')}"
            order.save()
            updated_count += 1
            # Optional: ส่ง email แจ้งลูกค้า

        self.message_user(request, ngettext(
            '%d order was successfully marked as payment approved.',
            '%d orders were successfully marked as payment approved.',
            updated_count,
        ) % updated_count, messages.SUCCESS)

    @admin.action(description='ปฏิเสธการชำระเงินที่เลือก (สลิปไม่ถูกต้อง)')
    def mark_payment_rejected(self, request, queryset):
        # อาจจะต้องเพิ่มหน้าต่างให้กรอกเหตุผลใน admin_payment_note
        # แต่ตอนนี้เอาแบบง่ายไปก่อน
        updated_count = 0
        for order in queryset.filter(status='waiting_for_approval'):
            order.status = 'failed' # เปลี่ยนเป็น failed
            order.paid = False
            order.admin_payment_note = f"Rejected by {request.user.username} on {timezone.now().strftime('%Y-%m-%d %H:%M')}. Reason: Invalid Slip (Please provide detail)."
            # ควรลบไฟล์สลิปเก่าออกด้วยหรือไม่? (อาจจะเก็บไว้เป็นหลักฐาน)
            # order.payment_slip.delete(save=False) # ถ้าจะลบไฟล์
            order.save()
            updated_count += 1
            # Optional: ส่ง email แจ้งลูกค้า

        self.message_user(request, ngettext(
            '%d order was marked as payment rejected.',
            '%d orders were marked as payment rejected.',
            updated_count,
        ) % updated_count, messages.WARNING) # ใช้ messages.WARNING หรือ ERROR