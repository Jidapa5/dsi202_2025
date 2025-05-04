from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.views import View, generic
from django.views.decorators.http import require_POST
from django.contrib.auth.forms import AuthenticationForm # ใช้ Form มาตรฐาน
from django.contrib.auth import login, logout, get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.conf import settings
from django.utils import timezone
from django.db import transaction # เพิ่ม import สำหรับ atomic transaction
from decimal import Decimal # เพิ่ม import

from .models import Outfit, Rental
from .forms import (
    OutfitForm,
    UserRegistrationForm,
    PaymentForm,
    AddToCartForm, # เพิ่ม
    UpdateCartForm # เพิ่ม
)
from .cart import Cart # Import Cart class (ต้องสร้างไฟล์ cart.py)

# === Authentication Views ===

def register(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # login(request, user) # อาจจะ Login ให้เลย หรือให้ไป Login เอง
            messages.success(request, f'Account created for {user.username}! Please log in.')
            return redirect('login')
        else:
             messages.error(request, "Please correct the errors below.")
    else:
        form = UserRegistrationForm()
    return render(request, 'outfits/register.html', {'form': form})

# Login และ Logout ใช้ View มาตรฐานของ Django ที่กำหนดใน mindvibe_project/urls.py

# === Outfit Views ===

class OutfitListView(generic.ListView):
    model = Outfit
    template_name = 'outfits/list.html'
    context_object_name = 'outfits'
    paginate_by = 9 # เพิ่ม Pagination

    def get_queryset(self):
        # แสดงเฉพาะชุดที่ is_available = True
        return Outfit.objects.filter(is_available=True).order_by('-id')

class OutfitDetailView(generic.DetailView):
    model = Outfit
    template_name = 'outfits/detail.html'
    context_object_name = 'outfit'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['add_to_cart_form'] = AddToCartForm() # ส่งฟอร์ม Add to cart ไปด้วย
        return context

class OutfitSearchView(generic.ListView):
     model = Outfit
     template_name = 'outfits/search_results.html' # เปลี่ยนชื่อ template
     context_object_name = 'results'

     def get_queryset(self):
         query = self.request.GET.get('q')
         if query:
             return Outfit.objects.filter(name__icontains=query, is_available=True)
         return Outfit.objects.none()

     def get_context_data(self, **kwargs):
         context = super().get_context_data(**kwargs)
         context['query'] = self.request.GET.get('q', '')
         return context


# === Cart Views ===

@require_POST
def add_to_cart(request, outfit_id):
    cart = Cart(request)
    outfit = get_object_or_404(Outfit, id=outfit_id, is_available=True)
    form = AddToCartForm(request.POST)
    if form.is_valid():
        cd = form.cleaned_data
        cart.add(outfit=outfit, duration_days=cd['duration_days'])
        messages.success(request, f'"{outfit.name}" added to your cart.')
    else:
         messages.error(request, 'Invalid duration.') # ควรมี error handling ดีกว่านี้
    return redirect('cart_detail') # เปลี่ยนชื่อ URL ให้ชัดเจน

@require_POST
def remove_from_cart(request, outfit_id):
    cart = Cart(request)
    outfit = get_object_or_404(Outfit, id=outfit_id)
    cart.remove(outfit)
    messages.info(request, f'"{outfit.name}" removed from your cart.')
    return redirect('cart_detail')

def cart_detail(request):
    cart = Cart(request)
    # เตรียม form สำหรับ update แต่ละ item ใน template
    for item in cart:
        item['update_duration_form'] = UpdateCartForm(initial={'duration_days': item['duration_days']})
    return render(request, 'outfits/cart_detail.html', {'cart': cart})

@require_POST
def cart_update(request, outfit_id):
    cart = Cart(request)
    outfit = get_object_or_404(Outfit, id=outfit_id)
    form = UpdateCartForm(request.POST)
    if form.is_valid():
        cd = form.cleaned_data
        cart.add(outfit=outfit, duration_days=cd['duration_days'], update_duration=True)
        messages.success(request, 'Cart updated.')
    else:
         messages.error(request, 'Invalid duration.')
    return redirect('cart_detail')


def clear_cart(request):
    cart = Cart(request)
    cart.clear()
    messages.info(request, 'Cart cleared.')
    return redirect('cart_detail')


# === Checkout and Rental Views ===

@login_required
def checkout(request):
    cart = Cart(request)
    if not cart:
        messages.warning(request, "Your cart is empty.")
        return redirect('outfit-list')

    # คำนวณราคารวมใหม่ทุกครั้ง เผื่อราคาชุดมีการเปลี่ยนแปลง
    total_price = cart.get_total_price()

    if request.method == 'POST':
        payment_form = PaymentForm(request.POST, request.FILES)
        if payment_form.is_valid():
            try:
                # ใช้ transaction เพื่อให้แน่ใจว่าการสร้าง Rental และการเคลียร์ cart ทำพร้อมกัน
                with transaction.atomic():
                    # สร้าง Rental object เดียวสำหรับ checkout ครั้งนี้ (ต้องปรับ Model ถ้าต้องการเก็บหลายชุด)
                    # *** หรือ สร้าง Rental หลายอันตามจำนวน item ในตะกร้า ? ***
                    # แบบง่าย: สร้าง Rental สำหรับ item แรก หรือสร้าง Order ก่อน
                    # แบบปัจจุบันในโค้ดเดิม: สร้าง Rental หลายอัน - จะลองปรับปรุงเล็กน้อย

                    rental_records = []
                    for item in cart:
                        outfit = item['outfit']
                        # ตรวจสอบอีกครั้งว่าชุดยังว่างอยู่ไหม
                        if not outfit.is_available:
                             messages.error(request, f'Sorry, "{outfit.name}" is no longer available.')
                             return redirect('cart_detail') # กลับไปที่ตะกร้า

                        rental = Rental.objects.create(
                            user=request.user,
                            outfit=outfit,
                            rental_start_date=timezone.now().date(), # หรือให้ user เลือกวันเริ่ม
                            duration_days=item['duration_days'],
                            calculated_price=item['total_price'],
                            payment_slip=payment_form.cleaned_data['payment_slip'],
                            payment_date=payment_form.cleaned_data['payment_date'],
                            status='payment_verification' # สถานะรอตรวจสอบ
                        )
                        rental_records.append(rental)

                        # **สำคัญ:** ควร Mark ชุดว่าไม่ว่าง (is_available=False) หรือไม่?
                        # ถ้า Mark เลย User คนอื่นจะเช่าไม่ได้ทันที แม้ยังไม่ Confirm payment
                        # หรือจะรอ Admin Confirm แล้วค่อย Mark? -> ต้องมี Logic เพิ่ม
                        # outfit.is_available = False
                        # outfit.save()

                    # เคลียร์ตะกร้าหลังสร้างรายการเช่าสำเร็จ
                    cart.clear()

                messages.success(request, 'Your order has been placed and is pending payment verification.')
                return redirect('checkout_success') # Redirect ไปหน้าขอบคุณ

            except Exception as e:
                # จัดการ Error ที่อาจเกิดขึ้นระหว่าง Transaction
                messages.error(request, f'An error occurred: {e}. Please try again.')
                # ไม่ต้อง clear cart ถ้าเกิด Error

        else:
            messages.error(request, 'Please correct the errors in the payment form.')
    else:
        payment_form = PaymentForm()

    # ข้อมูล Payment ควรอ่านจาก Config หรือ DB
    bank_info = {
        'bank_account_number': getattr(settings, 'BANK_ACCOUNT_NUMBER', 'N/A'),
        'qr_code_image_url': getattr(settings, 'QR_CODE_IMAGE_URL', None)
    }

    return render(request, 'outfits/checkout.html', {
        'cart': cart,
        'total_price': total_price,
        'payment_form': payment_form,
        'bank_info': bank_info
    })

@login_required
def checkout_success(request):
    # อาจจะแสดงข้อมูล Order ล่าสุด หรือแค่ข้อความขอบคุณ
    return render(request, 'outfits/checkout_success.html')


# === User Profile View ===

@login_required
def user_profile(request):
    user_rentals = Rental.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'outfits/user_profile.html', {'rentals': user_rentals})


# === Admin Views ===

# ตรวจสอบว่าเป็น Superuser หรือไม่
def is_admin(user):
    return user.is_superuser

@login_required
@user_passes_test(is_admin)
def create_outfit(request):
    if request.method == 'POST':
        form = OutfitForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Outfit created successfully!')
            return redirect('outfit-list') # หรือไปหน้า Admin Dashboard
    else:
        form = OutfitForm()
    return render(request, 'outfits/create_outfit_form.html', {'form': form}) # สร้าง Template นี้ด้วย

# --- Views ที่ต้อง Implement เพิ่มเติม (Conceptual) ---

@login_required
@user_passes_test(is_admin)
def admin_rental_list(request):
    # ดึงข้อมูล Rental ทั้งหมด หรือ Filter ตามสถานะ
    # rentals = Rental.objects.all().order_by('-created_at')
    # return render(request, 'outfits/admin_rental_list.html', {'rentals': rentals}) # สร้าง Template นี้
    pass # Placeholder

@login_required
@user_passes_test(is_admin)
@require_POST # ควรใช้ POST เพื่อเปลี่ยนสถานะ
def admin_confirm_payment(request, rental_id):
    # rental = get_object_or_404(Rental, id=rental_id)
    # rental.status = 'paid' # หรือ 'rented'
    # rental.outfit.is_available = False # Mark ชุดว่าไม่ว่าง
    # rental.save()
    # rental.outfit.save()
    # messages.success(request, 'Payment confirmed.')
    # return redirect('admin_rental_list') # Redirect กลับไปหน้า List
    pass # Placeholder

@login_required
@user_passes_test(is_admin)
@require_POST
def admin_mark_returned(request, rental_id):
    # rental = get_object_or_404(Rental, id=rental_id)
    # rental.status = 'returned'
    # rental.outfit.is_available = True # Mark ชุดว่าว่างแล้ว
    # rental.save()
    # rental.outfit.save()
    # messages.success(request, 'Outfit marked as returned.')
    # return redirect('admin_rental_list')
    pass # Placeholder

# === Home View ===
def home(request):
     # อาจจะแสดงชุดแนะนำ หรือข้อมูลอื่นๆ
     featured_outfits = Outfit.objects.filter(is_available=True).order_by('?')[:3] # สุ่ม 3 ชุด
     return render(request, 'outfits/home.html', {'featured_outfits': featured_outfits})