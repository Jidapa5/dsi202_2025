# outfits/admin.py (เพิ่ม UserProfileInline และ UserAdmin ใหม่)

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import ngettext
from .models import Outfit, Category, Order, OrderItem, UserProfile # เพิ่ม UserProfile

# --- Category Admin ---
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug'); prepopulated_fields = {'slug': ('name',)}; search_fields = ('name',)

# --- Outfit Admin ---
@admin.register(Outfit)
class OutfitAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'is_active'); list_filter = ('category', 'is_active'); search_fields = ('name', 'description')
    list_editable = ('price', 'is_active'); autocomplete_fields = ('category',); readonly_fields = ('image_preview',)
    def image_preview(self, obj):
        if obj.image: return format_html('<a href="{0}" target="_blank"><img src="{0}" style="max-height: 100px;" /></a>', obj.image.url)
        return "(No image)"; image_preview.short_description = 'Preview'

# --- OrderItem Inline Admin ---
class OrderItemInline(admin.TabularInline):
    model = OrderItem; fields = ('outfit', 'quantity', 'price_per_day', 'get_item_total_cost_display')
    readonly_fields = ('price_per_day', 'get_item_total_cost_display'); extra = 0; can_delete = False; autocomplete_fields = ('outfit',)
    def get_item_total_cost_display(self, obj): cost = obj.item_total_cost; return f"{cost:,.2f} บาท"
    get_item_total_cost_display.short_description = 'ราคารวมรายการนี้'

# --- Order Admin ---
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_display', 'created_at', 'rental_start_date','status', 'total_amount', 'paid', 'payment_slip_thumbnail')
    list_filter = ('status', 'paid', 'created_at', 'rental_start_date'); search_fields = ('id', 'first_name', 'last_name', 'email', 'phone', 'user__username')
    readonly_fields = ('id', 'user_link', 'created_at', 'updated_at', 'total_amount','payment_method', 'payment_datetime', 'payment_slip_display','shipping_tracking_number', 'return_tracking_number')
    inlines = [OrderItemInline]; actions = ['mark_payment_approved', 'mark_payment_rejected']
    fieldsets = ( ('ข้อมูลคำสั่งเช่า', {'fields': ('id', 'user_link', 'status', 'paid', 'created_at', 'updated_at')}),
                  ('ข้อมูลลูกค้าและการจัดส่ง', {'fields': ('first_name', 'last_name', 'email', 'phone', 'address', 'shipping_cost', 'shipping_tracking_number', 'return_tracking_number')}),
                  ('ช่วงเวลาเช่า', {'fields': ('rental_start_date', 'rental_end_date')}),
                  ('ข้อมูลการชำระเงิน', {'fields': ('total_amount', 'payment_method', 'payment_datetime', 'payment_slip_display', 'admin_payment_note')}), )
    def payment_slip_thumbnail(self, obj):
         if obj.payment_slip: return format_html('<a href="{0}" target="_blank"><img src="{0}" style="max-height: 40px;" /></a>', obj.payment_slip.url)
         return "ไม่มีสลิป"; payment_slip_thumbnail.short_description = 'สลิป'
    def payment_slip_display(self, obj):
         if obj.payment_slip: return format_html('<a href="{0}" target="_blank"><img src="{0}" style="max-height: 300px;" /></a>', obj.payment_slip.url)
         return "ยังไม่มีสลิป"; payment_slip_display.short_description = 'สลิปที่แนบมา'
    def user_display(self, obj): return obj.user.username if obj.user else "Guest"; user_display.short_description = 'ผู้ใช้'
    def user_link(self, obj):
         if obj.user: url = reverse("admin:auth_user_change", args=[obj.user.id]); return format_html('<a href="{}">{}</a>', url, obj.user.username)
         return "Guest"; user_link.short_description = 'ผู้ใช้ (ลิงก์)'
    def get_readonly_fields(self, request, obj=None):
        base_readonly = list(self.readonly_fields);
        if obj: current_readonly = base_readonly + ['user_link','first_name','last_name','email','phone','address','rental_start_date','rental_end_date','shipping_cost','total_amount','paid','payment_method','payment_datetime','payment_slip_display']
        if obj and obj.status not in ['waiting_for_approval', 'failed']: current_readonly.append('admin_payment_note')
        return tuple(current_readonly) if obj else tuple(base_readonly)
    @admin.action(description='อนุมัติการชำระเงินที่เลือก')
    def mark_payment_approved(self, request, queryset):
        valid_queryset = queryset.filter(status='waiting_for_approval', payment_slip__isnull=False); updated_count = 0
        for order in valid_queryset: order.status = 'processing'; order.paid = True; order.admin_payment_note = f"Approved by {request.user.username} on {timezone.now().strftime('%Y-%m-%d %H:%M')}"; order.save(); updated_count += 1
        if updated_count > 0: self.message_user(request, ngettext('%d order approved.','%d orders approved.',updated_count,) % updated_count, messages.SUCCESS)
        else: self.message_user(request, "No valid orders selected.", messages.WARNING)
    @admin.action(description='ปฏิเสธการชำระเงินที่เลือก')
    def mark_payment_rejected(self, request, queryset):
        valid_queryset = queryset.filter(status='waiting_for_approval'); updated_count = 0; reject_reason = f"Rejected by {request.user.username} on {timezone.now().strftime('%Y-%m-%d %H:%M')}."
        for order in valid_queryset: order.status = 'failed'; order.paid = False; order.admin_payment_note = reject_reason; order.save(); updated_count += 1
        if updated_count > 0: self.message_user(request, ngettext('%d order rejected.','%d orders rejected.',updated_count,) % updated_count, messages.WARNING)
        else: self.message_user(request, "No valid orders selected.", messages.WARNING)

# --- เพิ่มส่วนจัดการ User Profile ---
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'ข้อมูลเพิ่มเติม (Profile)'
    fields = ('phone', 'address') # ระบุ field ที่จะให้แก้ในหน้า User Admin
    # ถ้าต้องการให้แสดง field มากกว่านี้ ก็เพิ่มเข้าไป
    # fields = ('phone', 'address', 'other_field')

# ขยาย UserAdmin เดิมของ Django
class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    # สามารถปรับแต่งการแสดงผลของ User หลักได้ที่นี่ (ถ้าต้องการ)
    # list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff')

# ยกเลิกการลงทะเบียน UserAdmin เดิม แล้วลงทะเบียนใหม่ด้วย UserAdmin ที่เราสร้าง
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

# @admin.register(UserProfile)
# class UserProfileAdmin(admin.ModelAdmin):
#     list_display = ('user', 'phone')
#     search_fields = ('user__username', 'user__email', 'phone')