# outfits/views.py (อัปเดต profile view และ checkout view)

from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, DetailView
from django.contrib import messages
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest, Http404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.db import transaction
from django.contrib.auth import login, get_user_model
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal
import json
import logging

# --- Import models และ forms ---
from .models import Outfit, Category, Order, OrderItem, UserProfile # เพิ่ม UserProfile
from .forms import (
    CheckoutForm, CartAddItemForm, CustomUserCreationForm,
    OutfitForm, PaymentSlipUploadForm, UserEditForm, UserProfileForm # เพิ่ม Form ใหม่
)

logger = logging.getLogger(__name__)

# ---------- หน้าหลัก / สมัครสมาชิก ----------
def home(request):
    featured_outfits = Outfit.objects.filter(is_active=True).order_by('?')[:6]
    categories = Category.objects.all()
    cart = request.session.get(settings.CART_SESSION_ID, {})
    cart_outfit_ids = list(cart.keys())
    return render(request, 'outfits/home.html', {
        'featured_outfits': featured_outfits, 'categories': categories,
        'cart_outfit_ids': cart_outfit_ids })

def register_view(request):
    if request.user.is_authenticated: return redirect(settings.LOGIN_REDIRECT_URL)
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid(): user = form.save(); login(request, user); messages.success(request, f"สมัครสมาชิกสำเร็จ!"); return redirect(settings.LOGIN_REDIRECT_URL)
        else: messages.error(request, "เกิดข้อผิดพลาดในการสมัครสมาชิก")
    else: form = CustomUserCreationForm()
    return render(request, 'registration/register.html', {'form': form})

# ---------- ชุดทั้งหมด / รายละเอียด ----------
class OutfitListView(ListView):
    model=Outfit; template_name='outfits/list.html'; context_object_name='outfits'; paginate_by=12
    def get_queryset(self): return Outfit.objects.filter(is_active=True).select_related('category')
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all(); context['title'] = "รายการชุดทั้งหมด"
        cart = self.request.session.get(settings.CART_SESSION_ID, {}); context['cart_outfit_ids'] = list(cart.keys())
        return context

class OutfitByCategoryListView(ListView):
    model=Outfit; template_name='outfits/list.html'; context_object_name='outfits'; paginate_by=12
    def get_queryset(self): self.category = get_object_or_404(Category, slug=self.kwargs['category_slug']); return Outfit.objects.filter(category=self.category, is_active=True).select_related('category')
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs); context['category'] = self.category; context['categories'] = Category.objects.all(); context['title'] = f"หมวดหมู่: {self.category.name}"
        cart = self.request.session.get(settings.CART_SESSION_ID, {}); context['cart_outfit_ids'] = list(cart.keys())
        return context

class OutfitDetailView(DetailView):
    model=Outfit; template_name='outfits/detail.html'; context_object_name='outfit'
    def get_queryset(self): return Outfit.objects.filter(is_active=True).select_related('category')
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs); context['add_to_cart_form'] = CartAddItemForm()
        if self.object.category: context['related_outfits'] = Outfit.objects.filter(category=self.object.category, is_active=True).exclude(pk=self.object.pk).select_related('category')[:4]
        cart = self.request.session.get(settings.CART_SESSION_ID, {}); context['cart_outfit_ids'] = list(cart.keys())
        try:
            is_currently_available = self.object.is_available(timezone.now().date(), timezone.now().date()); context['current_status_text'] = "ว่าง" if is_currently_available else "ถูกเช่าอยู่"
        except Exception as e: logger.error(f"Error checking availability: {e}"); context['current_status_text'] = "Error"
        return context

class OutfitSearchView(ListView):
    model=Outfit; template_name='outfits/list.html'; context_object_name='outfits'; paginate_by=12
    def get_queryset(self): query = self.request.GET.get('q', '').strip(); self.query = query; return Outfit.objects.filter(Q(name__icontains=query)|Q(description__icontains=query)|Q(category__name__icontains=query), is_active=True).select_related('category').distinct() if query else Outfit.objects.none()
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs); context['query'] = self.query; context['categories'] = Category.objects.all(); context['title'] = f"ผลการค้นหาสำหรับ '{self.query}'" if self.query else "ค้นหาชุด"
        cart = self.request.session.get(settings.CART_SESSION_ID, {}); context['cart_outfit_ids'] = list(cart.keys())
        return context

# ---------- ตะกร้า ----------
def get_cart_items_and_total(request):
    cart_session = request.session.get(settings.CART_SESSION_ID, {})
    cart_items_data = []; cart_subtotal_per_day = Decimal('0.00')
    outfit_ids = list(cart_session.keys())
    outfits_in_cart = {str(o.id): o for o in Outfit.objects.filter(id__in=outfit_ids, is_active=True)}
    valid_cart_session = {}; ids_to_remove = []
    for outfit_id in outfit_ids:
        item_data = cart_session[outfit_id]; outfit = outfits_in_cart.get(outfit_id)
        if outfit:
            quantity = 1; price_per_day = outfit.price; item_subtotal = price_per_day * quantity
            cart_subtotal_per_day += item_subtotal
            cart_items_data.append({'outfit': outfit, 'quantity': quantity, 'price_per_day': price_per_day, 'item_subtotal': item_subtotal})
            valid_cart_session[outfit_id] = {'quantity': quantity}
        else: ids_to_remove.append(outfit_id)
    session_changed = False
    if ids_to_remove:
        new_valid_cart = {k: v for k, v in valid_cart_session.items() if k not in ids_to_remove}
        valid_cart_session = new_valid_cart; session_changed = True
    if set(valid_cart_session.keys()) != set(cart_session.keys()) or session_changed :
         request.session[settings.CART_SESSION_ID] = valid_cart_session; request.session.modified = True
    return cart_items_data, cart_subtotal_per_day

def cart_detail(request):
    cart_items, cart_subtotal_per_day = get_cart_items_and_total(request)
    return render(request, 'outfits/cart_detail.html', { 'cart_items': cart_items, 'cart_subtotal_per_day': cart_subtotal_per_day })

@require_POST
def add_to_cart(request, outfit_id):
    outfit = get_object_or_404(Outfit, id=outfit_id, is_active=True); cart = request.session.get(settings.CART_SESSION_ID, {}); outfit_key = str(outfit_id)
    if outfit_key in cart: messages.warning(request, f"'{outfit.name}' อยู่ในตะกร้าแล้ว")
    else: cart[outfit_key] = {'quantity': 1}; request.session[settings.CART_SESSION_ID] = cart; request.session.modified = True; messages.success(request, f"เพิ่ม '{outfit.name}' ลงในตะกร้าแล้ว")
    redirect_url = request.POST.get('next', reverse('outfits:cart_detail')); return redirect(redirect_url)

@require_POST
def remove_from_cart(request, outfit_id):
    cart = request.session.get(settings.CART_SESSION_ID, {}); outfit_key = str(outfit_id)
    if outfit_key in cart:
        try: outfit_name = Outfit.objects.get(id=outfit_id).name
        except Outfit.DoesNotExist: outfit_name = f"สินค้า ID {outfit_id}"
        del cart[outfit_key]; request.session[settings.CART_SESSION_ID] = cart; request.session.modified = True
        messages.success(request, f"ลบ '{outfit_name}' ออกจากตะกร้าแล้ว")
    else: messages.warning(request, "ไม่พบสินค้านี้ในตะกร้า")
    return redirect('outfits:cart_detail')

# ---------- เช่าและชำระเงิน ----------
@login_required
def checkout_view(request):
    cart_items, cart_subtotal_per_day = get_cart_items_and_total(request);
    if not cart_items: messages.warning(request, "ตะกร้าว่างเปล่า"); return redirect('outfits:outfit-list')
    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    start_date = form.cleaned_data['rental_start_date']; end_date = form.cleaned_data['rental_end_date']; unavailable_items = []
                    for item_data in cart_items:
                        if not item_data['outfit'].is_available(start_date, end_date, quantity=1): unavailable_items.append(item_data['outfit'].name)
                    if unavailable_items:
                        messages.error(request, f"ขออภัย ชุดไม่ว่างช่วงวันที่เลือก: {', '.join(unavailable_items)}")
                        context = {'form': form, 'cart_items': cart_items, 'cart_subtotal_per_day': cart_subtotal_per_day}; return render(request, 'outfits/checkout.html', context)
                    order = Order(user=request.user, **form.cleaned_data); order.status = 'pending'; order.payment_method = 'Bank Transfer'; order.save()
                    order_items_to_create = []
                    for item_data in cart_items: order_items_to_create.append(OrderItem(order=order, outfit=item_data['outfit'], quantity=1, price_per_day=item_data['outfit'].price))
                    OrderItem.objects.bulk_create(order_items_to_create)
                    order_from_db = Order.objects.get(pk=order.pk); order_from_db.total_amount = order_from_db.calculate_total_amount(); order_from_db.save()
                    del request.session[settings.CART_SESSION_ID]; request.session.modified = True; request.session['latest_order_id'] = order_from_db.id
                    return redirect('outfits:payment_process', order_id=order_from_db.id)
            except Exception as e:
                 logger.error(f"Error creating order: {e}", exc_info=True); messages.error(request, f"เกิดข้อผิดพลาด: {e}")
                 context = {'form': form, 'cart_items': cart_items, 'cart_subtotal_per_day': cart_subtotal_per_day}; return render(request, 'outfits/checkout.html', context)
        else:
             messages.error(request, "กรุณากรอกข้อมูลให้ถูกต้อง")
             context = {'form': form, 'cart_items': cart_items, 'cart_subtotal_per_day': cart_subtotal_per_day}; return render(request, 'outfits/checkout.html', context)
    else: # --- GET request ---
        initial_data = {}
        if request.user.is_authenticated:
            initial_data = {'first_name': request.user.first_name, 'last_name': request.user.last_name, 'email': request.user.email}
            # --- ดึงข้อมูลจาก Profile มาใส่ ---
            try:
                profile = request.user.profile # หรือ UserProfile.objects.get(user=request.user)
                if profile.phone: initial_data['phone'] = profile.phone
                if profile.address: initial_data['address'] = profile.address
            except UserProfile.DoesNotExist: pass
            except AttributeError: logger.warning(f"User {request.user.id} has no profile attribute.") ; pass
            # --- จบส่วนดึงข้อมูล Profile ---
        form = CheckoutForm(initial=initial_data) # ใส่ initial data ตอนสร้างฟอร์ม
        context = {'form': form, 'cart_items': cart_items, 'cart_subtotal_per_day': cart_subtotal_per_day}; return render(request, 'outfits/checkout.html', context)

@login_required
def payment_process_view(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user); form = None
    if order.status == 'pending':
        if request.method == 'POST':
            form = PaymentSlipUploadForm(request.POST, request.FILES, instance=order)
            if form.is_valid():
                try: updated_order = form.save(commit=False); updated_order.status = 'waiting_for_approval'; updated_order.save(); messages.success(request, f"แจ้งชำระเงิน #{order.id} เรียบร้อยแล้ว"); return redirect('outfits:order_detail', order_id=order.id)
                except Exception as e: logger.error(f"Error saving slip: {e}", exc_info=True); messages.error(request, "เกิดข้อผิดพลาดในการบันทึกข้อมูล")
            else: messages.error(request, "กรุณากรอกข้อมูลและแนบสลิปให้ถูกต้อง")
        else: form = PaymentSlipUploadForm()
    elif order.status == 'waiting_for_approval': messages.info(request, f"คำสั่งเช่า #{order.id} กำลังรอตรวจสอบสลิป")
    elif order.status == 'failed': messages.error(request, f"ชำระเงิน #{order.id} ไม่ถูกต้อง ({order.admin_payment_note or ''})")
    else: messages.info(request, f"สถานะคำสั่งเช่า #{order.id}: {order.get_status_display()}")
    bank_details = {'account_name': settings.BANK_ACCOUNT_NAME, 'account_number': settings.BANK_ACCOUNT_NUMBER,'bank_name': settings.BANK_NAME, 'qr_code_path': settings.BANK_QR_CODE_STATIC_PATH if settings.BANK_QR_CODE_STATIC_PATH else None}
    context = {'order': order, 'form': form, 'bank_details': bank_details}; return render(request, 'outfits/payment_process.html', context)

@login_required
def payment_result_view(request):
    order_id = request.session.get('latest_order_id'); order = None
    if order_id:
        try: order = Order.objects.get(id=order_id, user=request.user)
        except Order.DoesNotExist: pass
    if order:
         if order.status == 'waiting_for_approval': messages.info(request, f"คำสั่งเช่า #{order.id} กำลังรอตรวจสอบสลิป")
         elif order.status == 'processing': messages.success(request, f"ชำระเงิน #{order.id} เรียบร้อยแล้ว")
         elif order.status == 'failed': messages.error(request, f"ชำระเงิน #{order.id} ไม่สำเร็จ")
         else: messages.info(request, f"สถานะคำสั่งเช่า #{order.id}: {order.get_status_display()}")
    else: messages.info(request, "ยินดีต้อนรับสู่ MindVibe!")
    return render(request, 'outfits/payment_result.html', {'order': order})

# ---------- ประวัติ / รายละเอียด Order / Profile ----------
@login_required
def order_history_view(request):
    print(f"--- Running order_history_view for user: {request.user} ---")
    orders = Order.objects.filter(user=request.user).prefetch_related('items', 'items__outfit').order_by('-created_at')
    print(f"--- Orders found: {orders.count()} ---")
    print(f"--- Rendering template: outfits/order_history.html ---")
    return render(request, 'outfits/order_history.html', {'orders': orders})

@login_required
def order_detail_view(request, order_id):
    print(f"--- Running order_detail_view for user: {request.user}, order_id: {order_id} ---")
    order = get_object_or_404(Order.objects.prefetch_related('items', 'items__outfit'), id=order_id, user=request.user)
    print(f"--- Order status: {order.status}, Items count: {order.items.count()} ---")
    print(f"--- Rendering template: outfits/order_detail.html ---")
    context = {'order': order}
    return render(request, 'outfits/order_detail.html', context)

# --- แก้ไข User Profile View ---
@login_required
def user_profile_view(request):
    user = request.user
    # ใช้ get_or_create เพื่อความปลอดภัย
    profile, created = UserProfile.objects.get_or_create(user=user)

    if request.method == 'POST':
        # รับข้อมูลจาก POST request ผูกกับ instance ปัจจุบัน
        user_form = UserEditForm(request.POST, instance=user)
        profile_form = UserProfileForm(request.POST, instance=profile)

        # ตรวจสอบความถูกต้องของทั้งสองฟอร์ม
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'อัปเดตข้อมูลโปรไฟล์สำเร็จ!')
            return redirect('outfits:user_profile') # กลับมาหน้าเดิม
        else:
            # ถ้าฟอร์มไม่ถูกต้อง ให้แสดงข้อความ error
            # ตัว form ที่ส่งกลับไปใน context จะมี error message อยู่แล้ว
            messages.error(request, 'เกิดข้อผิดพลาด กรุณาตรวจสอบข้อมูลที่กรอก')
    else: # GET request
        # สร้างฟอร์มโดยใส่ข้อมูลปัจจุบันลงไป
        user_form = UserEditForm(instance=user)
        profile_form = UserProfileForm(instance=profile)

    context = {
        'user_form': user_form,
        'profile_form': profile_form,
    }
    # ใช้ template ชื่อ user_profile.html
    return render(request, 'outfits/user_profile.html', context)

# --- Admin Views ---
# (ส่วน Admin ไม่ได้ใช้แล้ว)