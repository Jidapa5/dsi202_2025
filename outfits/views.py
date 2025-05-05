# outfits/views.py (เวอร์ชัน Bank Transfer)

from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, DetailView
from django.contrib import messages
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest, Http404
from django.views.decorators.csrf import csrf_exempt # ยังไม่จำเป็น แต่เผื่อไว้
from django.views.decorators.http import require_POST
from django.db import transaction
from django.contrib.auth import login, get_user_model
from datetime import date, timedelta
from decimal import Decimal
# import omise # --- ลบออก ---
import json
import logging

from .models import Outfit, Category, Order, OrderItem
from .forms import (
    CheckoutForm, CartAddItemForm, CartUpdateItemForm, CustomUserCreationForm,
    OutfitForm, PaymentSlipUploadForm # <--- เพิ่ม form ใหม่
)

logger = logging.getLogger(__name__)

# --- ลบ Config Omise ออก ---
# omise.api_secret = settings.OMISE_SECRET_KEY
# omise.api_version = settings.OMISE_API_VERSION

# ---------- หน้าหลัก / สมัครสมาชิก (เหมือนเดิม) ----------

def home(request):
    featured_outfits = Outfit.objects.filter(is_active=True).order_by('?')[:6]
    categories = Category.objects.all()
    return render(request, 'outfits/home.html', {
        'featured_outfits': featured_outfits,
        'categories': categories
    })

def register_view(request):
    if request.user.is_authenticated:
        return redirect(settings.LOGIN_REDIRECT_URL) # ไป profile หลัง login
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"สมัครสมาชิกสำเร็จ! ยินดีต้อนรับ, {user.username}")
            return redirect(settings.LOGIN_REDIRECT_URL) # ไป profile หลังสมัคร
        else:
            messages.error(request, "เกิดข้อผิดพลาดในการสมัครสมาชิก กรุณาตรวจสอบข้อมูล")
    else:
        form = CustomUserCreationForm()
    return render(request, 'registration/register.html', {'form': form})


# ---------- ชุดทั้งหมด / รายละเอียด (เหมือนเดิม) ----------

class OutfitListView(ListView):
    model = Outfit
    template_name = 'outfits/list.html'
    context_object_name = 'outfits'
    paginate_by = 12

    def get_queryset(self):
        return Outfit.objects.filter(is_active=True).select_related('category')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['title'] = "รายการชุดทั้งหมด"
        return context

class OutfitByCategoryListView(ListView):
    model = Outfit
    template_name = 'outfits/list.html'
    context_object_name = 'outfits'
    paginate_by = 12

    def get_queryset(self):
        self.category = get_object_or_404(Category, slug=self.kwargs['category_slug'])
        return Outfit.objects.filter(category=self.category, is_active=True).select_related('category')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.category
        context['categories'] = Category.objects.all()
        context['title'] = f"หมวดหมู่: {self.category.name}"
        return context

class OutfitDetailView(DetailView):
    model = Outfit
    template_name = 'outfits/detail.html'
    context_object_name = 'outfit'

    def get_queryset(self):
        return Outfit.objects.filter(is_active=True).select_related('category')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['add_to_cart_form'] = CartAddItemForm()
        if self.object.category:
            context['related_outfits'] = Outfit.objects.filter(
                category=self.object.category, is_active=True
            ).exclude(pk=self.object.pk).select_related('category')[:4]
        return context

class OutfitSearchView(ListView):
    model = Outfit
    template_name = 'outfits/list.html'
    context_object_name = 'outfits'
    paginate_by = 12

    def get_queryset(self):
        query = self.request.GET.get('q', '').strip()
        self.query = query
        if query:
            return Outfit.objects.filter(
                Q(name__icontains=query) | Q(description__icontains=query) | Q(category__name__icontains=query),
                is_active=True
            ).select_related('category').distinct()
        return Outfit.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.query
        context['categories'] = Category.objects.all()
        context['title'] = f"ผลการค้นหาสำหรับ '{self.query}'" if self.query else "ค้นหาชุด"
        return context


# ---------- ตะกร้า (เหมือนเดิม) ----------

def get_cart_items_and_total(request):
    cart_session = request.session.get(settings.CART_SESSION_ID, {})
    cart_items_data = []
    cart_subtotal_per_day = Decimal('0.00')

    outfit_ids = cart_session.keys()
    outfits_in_cart = {str(o.id): o for o in Outfit.objects.filter(id__in=outfit_ids, is_active=True)}

    valid_cart_session = {}
    for outfit_id, item_data in cart_session.items():
        outfit = outfits_in_cart.get(outfit_id)
        if outfit:
            quantity = int(item_data.get('quantity', 0))
            if quantity > 0:
                price_per_day = outfit.price
                item_subtotal = price_per_day * quantity
                cart_subtotal_per_day += item_subtotal

                cart_items_data.append({
                    'outfit': outfit,
                    'quantity': quantity,
                    'price_per_day': price_per_day,
                    'item_subtotal': item_subtotal,
                    'update_form': CartUpdateItemForm(initial={'quantity': quantity})
                })
                valid_cart_session[outfit_id] = {'quantity': quantity}

    if len(valid_cart_session) != len(cart_session):
        request.session[settings.CART_SESSION_ID] = valid_cart_session
        request.session.modified = True

    return cart_items_data, cart_subtotal_per_day

def cart_detail(request):
    cart_items, cart_subtotal_per_day = get_cart_items_and_total(request)
    return render(request, 'outfits/cart_detail.html', {
        'cart_items': cart_items,
        'cart_subtotal_per_day': cart_subtotal_per_day,
    })

@require_POST
def add_to_cart(request, outfit_id):
    outfit = get_object_or_404(Outfit, id=outfit_id, is_active=True)
    cart = request.session.get(settings.CART_SESSION_ID, {})
    form = CartAddItemForm(request.POST)

    if form.is_valid():
        quantity_to_add = form.cleaned_data['quantity']
        outfit_key = str(outfit_id)
        current_quantity = cart.get(outfit_key, {}).get('quantity', 0)
        new_quantity = current_quantity + quantity_to_add
        cart[outfit_key] = {'quantity': new_quantity}
        request.session[settings.CART_SESSION_ID] = cart
        request.session.modified = True
        messages.success(request, f"เพิ่ม '{outfit.name}' ({quantity_to_add} ชุด) ลงในตะกร้าแล้ว")
    else:
        error_msg = "จำนวนไม่ถูกต้อง"
        if form.errors:
            error_msg = next(iter(form.errors.values()))[0]
        messages.error(request, error_msg)

    redirect_url = request.POST.get('next', reverse('outfits:cart_detail'))
    return redirect(redirect_url)

@require_POST
def update_cart_item(request, outfit_id):
    cart = request.session.get(settings.CART_SESSION_ID, {})
    outfit_key = str(outfit_id)
    form = CartUpdateItemForm(request.POST)

    if outfit_key not in cart:
        messages.warning(request, "ไม่พบสินค้านี้ในตะกร้า")
        return redirect('outfits:cart_detail')

    outfit = get_object_or_404(Outfit, id=outfit_id)

    if form.is_valid():
        quantity = form.cleaned_data['quantity']
        if quantity > 0:
            cart[outfit_key]['quantity'] = quantity
            messages.success(request, f"อัปเดตจำนวน '{outfit.name}' เป็น {quantity} ชุดแล้ว")
        else:
            del cart[outfit_key]
            messages.success(request, f"ลบ '{outfit.name}' ออกจากตะกร้าแล้ว")
        request.session[settings.CART_SESSION_ID] = cart
        request.session.modified = True
    else:
        error_msg = "ข้อมูลไม่ถูกต้อง"
        if form.errors:
            error_msg = next(iter(form.errors.values()))[0]
        messages.error(request, error_msg)

    return redirect('outfits:cart_detail')

@require_POST
def remove_from_cart(request, outfit_id):
    cart = request.session.get(settings.CART_SESSION_ID, {})
    outfit_key = str(outfit_id)

    if outfit_key in cart:
        try:
            outfit_name = Outfit.objects.get(id=outfit_id).name
        except Outfit.DoesNotExist:
            outfit_name = f"สินค้า ID {outfit_id}"
        del cart[outfit_key]
        request.session[settings.CART_SESSION_ID] = cart
        request.session.modified = True
        messages.success(request, f"ลบ '{outfit_name}' ออกจากตะกร้าแล้ว")
    else:
        messages.warning(request, "ไม่พบสินค้านี้ในตะกร้า")

    return redirect('outfits:cart_detail')


# ---------- เช่าและชำระเงิน (ปรับปรุงสำหรับ Bank Transfer) ----------

@login_required
def checkout_view(request):
    cart_items, cart_subtotal_per_day = get_cart_items_and_total(request)
    if not cart_items:
        messages.warning(request, "ตะกร้าของคุณว่างเปล่า กรุณาเลือกชุดก่อน")
        return redirect('outfits:outfit-list')

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    start_date = form.cleaned_data['rental_start_date']
                    end_date = form.cleaned_data['rental_end_date']

                    unavailable_items = []
                    for item_data in cart_items:
                        if not item_data['outfit'].is_available(start_date, end_date):
                            unavailable_items.append(item_data['outfit'].name)

                    if unavailable_items:
                        messages.error(request, f"ขออภัย ชุดต่อไปนี้ไม่ว่างในช่วงวันที่คุณเลือก: {', '.join(unavailable_items)}")
                        context = {
                             'form': form,
                             'cart_items': cart_items,
                             'cart_subtotal_per_day': cart_subtotal_per_day,
                        }
                        return render(request, 'outfits/checkout.html', context)

                    order = Order.objects.create(
                        user=request.user,
                        first_name=form.cleaned_data['first_name'],
                        last_name=form.cleaned_data['last_name'],
                        email=form.cleaned_data['email'],
                        phone=form.cleaned_data['phone'],
                        address=form.cleaned_data['address'],
                        rental_start_date=start_date,
                        rental_end_date=end_date,
                        status='pending', # ยังรอชำระเงิน
                        payment_method='Bank Transfer' # กำหนดวิธีชำระเงิน
                        # shipping_cost = ?
                    )

                    for item_data in cart_items:
                        OrderItem.objects.create(
                            order=order,
                            outfit=item_data['outfit'],
                            quantity=item_data['quantity'],
                        )

                    order.total_amount = order.calculate_total_amount()
                    order.save()

                    del request.session[settings.CART_SESSION_ID]
                    request.session.modified = True

                    request.session['latest_order_id'] = order.id

                    # Redirect ไปหน้าแจ้งโอนเงิน (payment_process)
                    return redirect('outfits:payment_process', order_id=order.id)

            except Exception as e:
                 logger.error(f"Error creating order for user {request.user.id}: {e}", exc_info=True)
                 messages.error(request, "เกิดข้อผิดพลาดในการสร้างคำสั่งเช่า กรุณาลองใหม่อีกครั้ง")
                 context = {
                     'form': form,
                     'cart_items': cart_items,
                     'cart_subtotal_per_day': cart_subtotal_per_day,
                 }
                 return render(request, 'outfits/checkout.html', context)
        else:
             messages.error(request, "กรุณากรอกข้อมูลให้ถูกต้องครบถ้วน")
             context = {
                 'form': form,
                 'cart_items': cart_items,
                 'cart_subtotal_per_day': cart_subtotal_per_day,
             }
             return render(request, 'outfits/checkout.html', context)
    else:
        initial_data = {}
        if request.user.is_authenticated:
            initial_data = {
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'email': request.user.email,
            }
        form = CheckoutForm(initial=initial_data)

    context = {
        'form': form,
        'cart_items': cart_items,
        'cart_subtotal_per_day': cart_subtotal_per_day,
    }
    return render(request, 'outfits/checkout.html', context)

# --- แก้ไข View สำหรับหน้าแจ้งโอนเงิน ---
@login_required
def payment_process_view(request, order_id):
    # ดึง Order ที่ผู้ใช้นี้สร้างและสถานะเป็น 'pending'
    order = get_object_or_404(Order, id=order_id, user=request.user, status='pending')
    form = PaymentSlipUploadForm() # ฟอร์มเปล่าสำหรับ GET

    if request.method == 'POST':
        # รับข้อมูลจากฟอร์มที่ submit มา พร้อมไฟล์
        form = PaymentSlipUploadForm(request.POST, request.FILES, instance=order) # ผูก form กับ order instance
        if form.is_valid():
            try:
                # บันทึกข้อมูล payment_datetime และ payment_slip ลง order
                # form.save() ทำได้เลยเพราะผูก instance ไว้แล้ว
                updated_order = form.save(commit=False)
                updated_order.status = 'waiting_for_approval' # เปลี่ยนสถานะเป็นรอตรวจสอบ
                updated_order.save()

                messages.success(request, f"แจ้งการชำระเงินสำหรับคำสั่งเช่า #{order.id} เรียบร้อยแล้ว กรุณารอการตรวจสอบจากเจ้าหน้าที่")
                # Redirect ไปหน้า Order Detail หรือ Payment Result
                return redirect('outfits:order_detail', order_id=order.id)
            except Exception as e:
                logger.error(f"Error saving payment slip for order {order.id}: {e}", exc_info=True)
                messages.error(request, "เกิดข้อผิดพลาดในการบันทึกข้อมูล กรุณาลองใหม่อีกครั้ง")
        else:
            # ถ้า form ไม่ valid (เช่น ไม่ได้แนบสลิป) ให้แสดง error
             messages.error(request, "กรุณากรอกข้อมูลและแนบสลิปให้ถูกต้อง")


    # --- ส่วนแสดงข้อมูลบัญชี (สำหรับ GET และ POST ที่ form ไม่ valid) ---
    bank_details = {
        'account_name': settings.BANK_ACCOUNT_NAME,
        'account_number': settings.BANK_ACCOUNT_NUMBER,
        'bank_name': settings.BANK_NAME,
        'qr_code_url': settings.BANK_QR_CODE_IMAGE_URL, # อาจเป็น None
    }

    context = {
        'order': order,
        'form': form, # ส่ง form (ที่อาจมี error) กลับไป template
        'bank_details': bank_details,
    }
    return render(request, 'outfits/payment_process.html', context)

# --- แก้ไข payment_result_view ให้แสดงสถานะต่างๆ ---
@login_required
def payment_result_view(request):
    order_id = request.session.get('latest_order_id')
    order = None
    if order_id:
        try:
            order = Order.objects.get(id=order_id, user=request.user)
        except Order.DoesNotExist:
            pass

    if order:
        if order.status == 'waiting_for_approval':
            messages.info(request, f"คำสั่งเช่า #{order.id} ได้รับข้อมูลการชำระเงินแล้ว กำลังรอการตรวจสอบสลิปจากเจ้าหน้าที่")
        elif order.status == 'processing':
             messages.success(request, f"การชำระเงินสำหรับคำสั่งเช่า #{order.id} ได้รับการยืนยันแล้ว กำลังดำเนินการจัดส่ง")
        elif order.status == 'failed':
            messages.error(request, f"การชำระเงินสำหรับคำสั่งเช่า #{order.id} ไม่ถูกต้อง กรุณาตรวจสอบและแจ้งโอนอีกครั้ง หรือติดต่อเจ้าหน้าที่ ({order.admin_payment_note or ''})")
        elif order.status == 'pending':
            messages.warning(request, f"คำสั่งเช่า #{order.id} ยังรอการแจ้งชำระเงิน")
            return redirect('outfits:payment_process', order_id=order.id) # พาไปหน้าแจ้งโอนเลย
        # อาจเพิ่มเงื่อนไขสำหรับสถานะอื่นๆ เช่น shipped, completed
        else:
             messages.info(request, f"สถานะคำสั่งเช่า #{order.id}: {order.get_status_display()}")
    else:
        messages.warning(request, "ไม่พบข้อมูลคำสั่งเช่าล่าสุด")

    # ไม่ต้องเคลียร์ session แล้ว เพราะอาจจะ refresh หน้านี้ได้
    # if 'latest_order_id' in request.session:
    #      del request.session['latest_order_id']
    #      request.session.modified = True

    return render(request, 'outfits/payment_result.html', {'order': order})

# --- ลบ omise_webhook_view ออก ---

# --- Order History / Detail (เหมือนเดิม แต่ template จะแสดงผลต่างไป) ---
@login_required
def order_history_view(request):
    orders = Order.objects.filter(user=request.user).prefetch_related('items', 'items__outfit').order_by('-created_at')
    return render(request, 'outfits/order_history.html', {'orders': orders})

@login_required
def order_detail_view(request, order_id):
    order = get_object_or_404(
        Order.objects.prefetch_related('items', 'items__outfit'),
        id=order_id,
        user=request.user
    )
    # ถ้า admin ดู อาจจะต้อง bypass user check
    # if not order.user == request.user and not request.user.is_staff:
    #     raise Http404

    # ดึง form upload slip มาด้วย เผื่อกรณีที่สถานะยังเป็น pending
    slip_upload_form = None
    if order.status == 'pending':
        # อาจจะไม่ต้องแสดงฟอร์มตรงนี้ แต่ให้ไปหน้า payment_process
        pass
        # slip_upload_form = PaymentSlipUploadForm()

    context = {
        'order': order,
        'slip_upload_form': slip_upload_form, # ส่งไปเผื่อ แต่จริงๆ ควรทำที่ payment_process
    }
    return render(request, 'outfits/order_detail.html', context)

# --- User Profile View (เหมือนเดิม) ---
@login_required
def user_profile_view(request):
    user = request.user
    context = {'user': user}
    return render(request, 'outfits/user_profile.html', context)

# --- ส่วนจัดการ Outfit (Admin - ควรย้ายไป Admin App หรือใช้ Django Admin) ---
from django.contrib.admin.views.decorators import staff_member_required

# @staff_member_required
# def create_outfit(request):
#     # ... (code เดิม) ...
#     # return render(request, 'outfits/admin/create_outfit.html', {'form': form})
#     pass # แนะนำให้ใช้ Django Admin Interface จัดการจะดีกว่า

# --- ลบ View ที่ไม่ใช้แล้ว ---
# def order_confirmation_view(request, order_id):
#     pass