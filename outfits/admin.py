from django.contrib import admin, messages # เพิ่ม messages
from django.utils.html import format_html # สำหรับสร้าง Link ใน Admin
from .models import Outfit, Rental

@admin.register(Outfit)
class OutfitAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'size', 'material', 'is_available')
    list_filter = ('is_available', 'size', 'material')
    search_fields = ('name', 'description', 'material')
    list_editable = ('is_available',) # อาจจะให้แก้ is_available จากหน้า List ได้เลย

@admin.register(Rental)
class RentalAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user_link', # เปลี่ยนจาก 'user'
        'outfit_link', # เปลี่ยนจาก 'outfit'
        'rental_start_date',
        'duration_days',
        'status',
        'payment_slip_link', # เปลี่ยนจาก 'payment_slip'
        'payment_date',
        'created_at'
    )
    list_filter = ('status', 'rental_start_date', 'payment_date')
    search_fields = ('user__username', 'outfit__name', 'id') # ค้นหาจาก username, ชื่อชุด, ID
    readonly_fields = ('created_at', 'updated_at', 'calculated_price', 'user_link', 'outfit_link', 'payment_slip_link') # ทำให้ Field บางอันอ่านได้อย่างเดียว
    list_per_page = 25 # แสดงผลหน้าละ 25 รายการ
    ordering = ('-created_at',) # เรียงตามวันที่สร้างล่าสุดก่อน

    # --- Custom Action สำหรับยืนยันการชำระเงิน ---
    def confirm_payment_action(self, request, queryset):
        """
        Action เพื่อเปลี่ยนสถานะ Rental ที่เลือกเป็น 'Paid'
        และ Mark Outfit ว่า is_available = False
        """
        updated_count = 0
        for rental in queryset:
            # ทำงานเฉพาะกับ Rental ที่รอการตรวจสอบ และมีสลิปแนบมา
            if rental.status == 'payment_verification' and rental.payment_slip:
                rental.status = 'paid' # หรืออาจจะเป็น 'rented' ถ้าจะให้เริ่มเช่าเลย
                rental.save()

                # Mark Outfit ว่าไม่ว่างแล้ว
                rental.outfit.is_available = False
                rental.outfit.save()

                updated_count += 1
            elif rental.status != 'payment_verification':
                 # แจ้งเตือนถ้าเลือกรายการที่ไม่ใช่สถานะ payment_verification
                 self.message_user(request, f"Rental ID {rental.id} is not in 'Payment Verification' status.", messages.WARNING)
            elif not rental.payment_slip:
                 # แจ้งเตือนถ้าไม่มีสลิป
                 self.message_user(request, f"Rental ID {rental.id} does not have a payment slip.", messages.WARNING)


        if updated_count > 0:
            self.message_user(request, f'Successfully confirmed payment for {updated_count} rental(s). Outfit availability updated.', messages.SUCCESS)
        else:
             self.message_user(request, 'No rentals were updated. Please check status and payment slip.', messages.INFO)


    confirm_payment_action.short_description = "✅ Confirm Payment & Mark Outfit Unavailable" # ชื่อที่จะแสดงใน Dropdown

    # --- Custom Action สำหรับ Mark ว่าคืนชุดแล้ว ---
    def mark_returned_action(self, request, queryset):
        """
        Action เพื่อเปลี่ยนสถานะ Rental ที่เลือกเป็น 'Returned'
        และ Mark Outfit ว่า is_available = True
        """
        updated_count = 0
        # ทำงานเฉพาะกับ Rental ที่จ่ายเงินแล้ว หรือกำลังถูกเช่า
        eligible_statuses = ['paid', 'rented']
        for rental in queryset.filter(status__in=eligible_statuses):
            rental.status = 'returned'
            rental.save()

            # Mark Outfit ว่าว่างแล้ว
            # อาจจะต้องเช็คก่อนว่าไม่มี Rental อื่นที่ Active ของชุดนี้อยู่ (กรณีซับซ้อน)
            rental.outfit.is_available = True
            rental.outfit.save()

            updated_count += 1

        if updated_count > 0:
            self.message_user(request, f'Successfully marked {updated_count} rental(s) as returned. Outfit availability updated.', messages.SUCCESS)
        else:
            self.message_user(request, f'No rentals were marked as returned (they might not be in "Paid" or "Rented" status).', messages.WARNING)

    mark_returned_action.short_description = "↩️ Mark as Returned & Make Outfit Available"

    # --- กำหนด Actions ที่จะใช้ ---
    actions = [confirm_payment_action, mark_returned_action]

    # --- ทำให้ Field ที่เป็น ForeignKey หรือ FileField แสดงเป็น Link ---
    @admin.display(description='User')
    def user_link(self, obj):
        # สร้าง Link ไปยังหน้า User ใน Admin (ถ้า User model register ไว้)
        # หรือจะแสดงแค่ username ก็ได้ obj.user.username
        from django.urls import reverse
        link = reverse("admin:auth_user_change", args=[obj.user.id]) # ต้องเช็ค path ของ user admin
        return format_html('<a href="{}">{}</a>', link, obj.user.username)

    @admin.display(description='Outfit')
    def outfit_link(self, obj):
        # สร้าง Link ไปยังหน้า Outfit ใน Admin
        from django.urls import reverse
        link = reverse("admin:outfits_outfit_change", args=[obj.outfit.id]) # outfits_outfit คือ appname_modelname
        return format_html('<a href="{}">{}</a>', link, obj.outfit.name)

    @admin.display(description='Payment Slip')
    def payment_slip_link(self, obj):
        # แสดง Link ไปยังไฟล์สลิป
        if obj.payment_slip:
            return format_html('<a href="{}" target="_blank">View Slip</a>', obj.payment_slip.url)
        return "No Slip"