# outfits/admin.py
from django.contrib import admin
# อัปเดต import ให้ครบ
from .models import Outfit, Category, Order, OrderItem

# --- Category Admin (เหมือนเดิม) ---
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)

# --- Outfit Admin (แก้ไข) ---
@admin.register(Outfit)
class OutfitAdmin(admin.ModelAdmin):
    # แก้ไข list_display เอา is_rented ออก ใส่ is_active แทน
    list_display = ('name', 'category', 'price', 'is_active') # <--- แก้ไขบรรทัดนี้
    list_filter = ('category', 'is_active') # <--- แก้ไขบรรทัดนี้ให้ตรงกัน
    search_fields = ('name', 'description')
    list_editable = ('price', 'is_active')
    autocomplete_fields = ('category',)
    readonly_fields = ('image_preview',)

    def image_preview(self, obj):
        from django.utils.html import format_html
        if obj.image:
            return format_html('<img src="{}" style="max-height: 100px; max-width: 100px;" />', obj.image.url)
        return "(No image)"
    image_preview.short_description = 'Preview'

# --- OrderItem Inline Admin (เหมือนเดิม) ---
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    fields = ('outfit', 'price', 'rental_start_date', 'rental_duration_days', 'quantity', 'get_cost', 'get_rental_end_date')
    readonly_fields = ('price', 'get_cost', 'get_rental_end_date')
    extra = 0
    can_delete = False
    autocomplete_fields = ('outfit',)

    def get_cost(self, obj):
        return obj.get_cost()
    get_cost.short_description = 'ราคารวมรายการนี้'

    def get_rental_end_date(self, obj):
        return obj.get_rental_end_date()
    get_rental_end_date.short_description = 'วันสิ้นสุดเช่า'

# --- Order Admin (เหมือนเดิม) ---
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_display', 'created_at', 'status', 'total_amount', 'paid', 'payment_method')
    list_filter = ('status', 'paid', 'created_at')
    search_fields = ('id', 'first_name', 'last_name', 'email', 'phone', 'user__username', 'payment_id')
    readonly_fields = ('id', 'user_link', 'created_at', 'updated_at', 'total_amount', 'payment_id') # เพิ่ม id
    list_editable = ('status',)
    inlines = [OrderItemInline]

    fieldsets = (
        ('ข้อมูลคำสั่งเช่า', {'fields': ('id', 'user_link', 'status', 'created_at', 'updated_at')}),
        ('ข้อมูลลูกค้า', {'fields': ('first_name', 'last_name', 'email', 'phone', 'address')}),
        ('ข้อมูลการชำระเงิน', {'fields': ('total_amount', 'paid', 'payment_method', 'payment_id')}),
    )

    def user_display(self, obj):
        return obj.user.username if obj.user else "Guest"
    user_display.short_description = 'ผู้ใช้'

    def user_link(self, obj):
        from django.urls import reverse
        from django.utils.html import format_html
        if obj.user:
            url = reverse("admin:auth_user_change", args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', url, obj.user.username)
        return "Guest"
    user_link.short_description = 'ผู้ใช้ (ลิงก์)'

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ('first_name', 'last_name', 'email', 'phone', 'address', 'paid', 'payment_method')
        return self.readonly_fields