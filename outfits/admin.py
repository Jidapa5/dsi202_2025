# outfits/admin.py
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import ngettext
from .models import Outfit, Category, Order, OrderItem, UserProfile

# --- Category Admin ---
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)

# --- Outfit Admin ---
@admin.register(Outfit)
class OutfitAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'is_active', 'image_thumbnail')
    list_filter = ('category', 'is_active')
    search_fields = ('name', 'description', 'category__name')
    list_editable = ('price', 'is_active')
    autocomplete_fields = ('category',)
    readonly_fields = ('image_preview',)
    fieldsets = (
        (None, {'fields': ('name', 'category', 'description')}),
        ('Pricing & Status', {'fields': ('price', 'is_active')}),
        ('Image', {'fields': ('image', 'image_preview')}),
    )

    @admin.display(description='Thumbnail')
    def image_thumbnail(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 40px; max-width: 40px;" />', obj.image.url)
        return "(No image)"

    @admin.display(description='Image Preview')
    def image_preview(self, obj):
        if obj.image:
            return format_html('<a href="{0}" target="_blank"><img src="{0}" style="max-height: 200px;" /></a>', obj.image.url)
        return "(No image)"

# --- OrderItem Inline ---
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    fields = ('outfit_link', 'quantity', 'price_per_day', 'get_item_total_cost_display')
    readonly_fields = ('outfit_link','price_per_day', 'get_item_total_cost_display')
    extra = 0
    can_delete = False

    @admin.display(description='Outfit')
    def outfit_link(self, obj):
        if obj.outfit:
            url = reverse("admin:outfits_outfit_change", args=[obj.outfit.id])
            return format_html('<a href="{}">{}</a>', url, obj.outfit.name)
        return "-"

    @admin.display(description='Item Total Cost')
    def get_item_total_cost_display(self, obj):
        return f"{obj.item_rental_subtotal:,.2f}"

# --- Order Admin ---
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_display', 'created_at', 'rental_start_date', 'status', 'total_amount_display', 'payment_slip_thumbnail')
    list_filter = ('status', 'created_at', 'rental_start_date')
    search_fields = ('id', 'first_name', 'last_name', 'email', 'phone', 'user__username')
    readonly_fields = (
        'id', 'user_link', 'created_at', 'updated_at', 'total_amount_display',
        'payment_method', 'payment_datetime', 'payment_slip_display',
        'return_slip_display', 'return_initiated_at'
    )
    inlines = [OrderItemInline]
    actions = ['mark_payment_approved', 'mark_payment_rejected', 'mark_shipped', 'mark_return_received']

    fieldsets = (
        ('Order Information', {'fields': ('id', 'user_link', 'status', 'created_at', 'updated_at')}),
        ('Customer & Shipping', {'fields': ('first_name', 'last_name', 'email', 'phone', 'address', 'shipping_cost')}),
        ('Rental Period', {'fields': ('rental_start_date', 'rental_end_date')}),
        ('Payment Details', {'fields': ('total_amount_display', 'payment_method', 'payment_datetime', 'payment_slip_display', 'admin_payment_note')}),
        ('Return Details', {'fields': ('return_tracking_number', 'return_slip_display', 'return_initiated_at')}),
    )

    @admin.display(description='Payment Slip')
    def payment_slip_thumbnail(self, obj):
        if obj.payment_slip:
            return format_html('<a href="{0}" target="_blank"><img src="{0}" style="max-height: 40px;" /></a>', obj.payment_slip.url)
        return "No Slip"

    @admin.display(description='Attached Payment Slip')
    def payment_slip_display(self, obj):
        if obj.payment_slip:
            return format_html('<a href="{0}" target="_blank"><img src="{0}" style="max-height: 300px;" /></a>', obj.payment_slip.url)
        return "No slip uploaded."

    @admin.display(description='Attached Return Slip')
    def return_slip_display(self, obj):
        if obj.return_slip:
            return format_html('<a href="{0}" target="_blank"><img src="{0}" style="max-height: 300px;" /></a>', obj.return_slip.url)
        return "No return slip uploaded."

    @admin.display(ordering='user__username', description='User')
    def user_display(self, obj):
        return obj.user.username if obj.user else "Guest"

    @admin.display(description='User (Admin Link)')
    def user_link(self, obj):
        if obj.user:
            url = reverse("admin:auth_user_change", args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', url, obj.user.username)
        return "Guest"

    @admin.display(ordering='total_amount', description='Total Amount')
    def total_amount_display(self, obj):
        return f"{obj.total_amount:,.2f}"

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if obj:
            readonly.extend(['user_link', 'payment_method'])
            if obj.status not in ['pending', 'waiting_for_approval', 'failed']:
                readonly.extend(['payment_datetime', 'payment_slip_display', 'admin_payment_note'])
            if obj.status in ['return_received', 'completed']:
                readonly.extend(['return_tracking_number', 'return_slip_display', 'return_initiated_at'])
        return tuple(readonly)

    # --- Actions ---
    @admin.action(description='Mark selected orders as Payment Approved')
    def mark_payment_approved(self, request, queryset):
        valid_queryset = queryset.filter(status='waiting_for_approval', payment_slip__isnull=False)
        updated_count = 0
        for order in valid_queryset:
            order.status = 'processing'
            order.admin_payment_note = f"Approved by {request.user.username} on {timezone.now().strftime('%Y-%m-%d %H:%M')}."
            order.save()
            updated_count += 1
        self.message_user(request, ngettext(
            f'{updated_count} order was successfully marked as payment approved.',
            f'{updated_count} orders were successfully marked as payment approved.',
            updated_count
        ), messages.SUCCESS)

    @admin.action(description='Mark selected orders as Payment Rejected')
    def mark_payment_rejected(self, request, queryset):
        valid_queryset = queryset.filter(status='waiting_for_approval')
        updated_count = 0
        for order in valid_queryset:
            order.status = 'failed'
            order.admin_payment_note = f"Rejected by {request.user.username} on {timezone.now().strftime('%Y-%m-%d %H:%M')}."
            order.save()
            updated_count += 1
        self.message_user(request, ngettext(
            f'{updated_count} order was successfully marked as payment rejected.',
            f'{updated_count} orders were successfully marked as payment rejected.',
            updated_count
        ), messages.WARNING)

    @admin.action(description='Mark selected orders as Shipped')
    def mark_shipped(self, request, queryset):
        valid_queryset = queryset.filter(status='processing')
        updated_count = 0
        for order in valid_queryset:
            order.status = 'shipped'
            order.save()
            updated_count += 1
        self.message_user(request, ngettext(
            f'{updated_count} order was successfully marked as shipped.',
            f'{updated_count} orders were successfully marked as shipped.',
            updated_count
        ), messages.SUCCESS)

    @admin.action(description='Mark selected orders as Return Received')
    def mark_return_received(self, request, queryset):
        valid_queryset = queryset.filter(status='return_shipped')
        updated_count = 0
        for order in valid_queryset:
            order.status = 'return_received'
            order.save()
            updated_count += 1
        self.message_user(request, ngettext(
            f'{updated_count} order was successfully marked as return received.',
            f'{updated_count} orders were successfully marked as return received.',
            updated_count
        ), messages.SUCCESS)

# --- User Profile Inline ---
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Additional Info (Profile)'
    fields = ('phone', 'address')

# --- Custom User Admin ---
class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'date_joined')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups', 'date_joined')

admin.site.unregister(User)
admin.site.register(User, UserAdmin)
