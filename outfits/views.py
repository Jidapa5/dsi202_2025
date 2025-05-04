# outfits/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.views.generic import ListView, DetailView # ใช้ Generic Views
from django.urls import reverse, reverse_lazy
from django.contrib import messages
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Q # สำหรับ OR query ใน search
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseServerError, JsonResponse, HttpResponseNotFound
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
from datetime import timedelta
import json
import omise # Import omise library

# --- เพิ่ม imports สำหรับ register_view ---
from django.contrib.auth.forms import UserCreationForm # Import ฟอร์มสมัครสมาชิก
from django.contrib.auth import login # Import login function

# Import models และ forms
from .models import Outfit, Category, Order, OrderItem
from .forms import OutfitForm, CheckoutForm, CartAddItemForm, CartUpdateItemForm
# from .cart import Cart # ถ้าสร้าง Class จัดการ Cart แยก

# --- Helper Function (ถ้าต้องการ Class จัดการ Cart) ---
# def get_cart(request):
#     # สร้างหรือดึง Cart object จาก session
#     # ...

# --- Context Processors (ถ้าสร้าง) ---
# def categories_processor(request):
#     return {'all_categories': Category.objects.all()}
# def cart_processor(request):
#     cart_session = request.session.get('cart', {})
#     cart_item_count = sum(item['quantity'] for item in cart_session.values())
#     return {'cart_item_count': cart_item_count}

# --- Outfit Views ---

def home(request):
    # ดึงข้อมูลชุดแนะนำ (ตัวอย่าง: สุ่ม 6 รายการที่ active)
    featured_outfits = Outfit.objects.filter(is_active=True).select_related('category').order_by('?')[:6] # เพิ่ม select_related

    # สร้าง Context Dictionary
    context = {
        'featured_outfits': featured_outfits
        # สามารถเพิ่ม context อื่นๆ ที่ต้องการส่งไปหน้า home ได้
    }
    # Render template พร้อมส่ง context ไปด้วย
    return render(request, 'outfits/home.html', context)


class OutfitListView(ListView):
    model = Outfit
    template_name = 'outfits/list.html'
    context_object_name = 'outfits'
    paginate_by = 12 # แสดงผลหน้าละ 12 รายการ

    def get_queryset(self):
        # แสดงเฉพาะ active outfits และดึง category มาพร้อมกัน
        return Outfit.objects.filter(is_active=True).select_related('category')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "รายการชุดทั้งหมด" # เพิ่ม title สำหรับ template
        return context


class OutfitByCategoryListView(ListView):
    model = Outfit
    template_name = 'outfits/list.html'
    context_object_name = 'outfits'
    paginate_by = 12

    def get_queryset(self):
        self.category = get_object_or_404(Category, slug=self.kwargs['category_slug'])
        # กรองตาม category และ is_active และดึง category มาด้วย (ถึงแม้จะรู้ category แล้วก็ตาม)
        return Outfit.objects.filter(category=self.category, is_active=True).select_related('category')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.category
        context['title'] = f"หมวดหมู่: {self.category.name}"
        return context


class OutfitDetailView(DetailView):
    model = Outfit
    template_name = 'outfits/detail.html'
    context_object_name = 'outfit'

    def get_queryset(self):
        # ดึงเฉพาะ active outfit และ category ที่เกี่ยวข้อง
        return Outfit.objects.filter(is_active=True).select_related('category')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['add_to_cart_form'] = CartAddItemForm() # เพิ่มฟอร์ม Add to Cart
        # ตัวอย่าง: แสดงสินค้าที่เกี่ยวข้องในหมวดหมู่เดียวกัน (ไม่เอาตัวมันเอง)
        if self.object.category:
             context['related_outfits'] = Outfit.objects.filter(
                 category=self.object.category, is_active=True
             ).exclude(pk=self.object.pk).select_related('category')[:4] # เอาแค่ 4 รายการ
        return context


class OutfitSearchView(ListView):
    model = Outfit
    template_name = 'outfits/list.html'
    context_object_name = 'outfits'
    paginate_by = 12

    def get_queryset(self):
        query = self.request.GET.get('q', '')
        self.query = query # เก็บ query ไว้ใช้ใน get_context_data
        if query:
            # ค้นหาจากชื่อ หรือ description และต้อง is_active
            return Outfit.objects.filter(
                (Q(name__icontains=query) | Q(description__icontains=query)) & Q(is_active=True)
            ).select_related('category')
        return Outfit.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.query # ส่ง query ที่เก็บไว้ไปให้ template
        context['title'] = f"ผลการค้นหาสำหรับ '{self.query}'" if self.query else "ค้นหาชุด"
        return context


@login_required # หรือใช้ permission check
def create_outfit(request):
    # if not request.user.is_staff:
    #    messages.error(request, "คุณไม่มีสิทธิ์เข้าถึงหน้านี้")
    #    return redirect('outfits:home')

    if request.method == 'POST':
        form = OutfitForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, f"สร้างชุด '{form.cleaned_data['name']}' สำเร็จ!")
            # ควร redirect ไปหน้า admin หรือหน้า list ของ admin แทน
            return redirect('outfits:outfit-list')
        else:
            messages.error(request, "มีข้อผิดพลาดในการสร้างชุด โปรดตรวจสอบข้อมูล")
    else:
        form = OutfitForm()
    # อย่าลืมสร้าง template 'outfits/outfit_form.html'
    return render(request, 'outfits/outfit_form.html', {'form': form, 'title': 'สร้างชุดใหม่'})


# --- View สำหรับสมัครสมาชิก ---
def register_view(request):
    if request.user.is_authenticated: # ถ้า login อยู่แล้ว ไม่ควรเข้าหน้านี้
        return redirect(settings.LOGIN_REDIRECT_URL)

    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save() # สร้าง User ใหม่ในฐานข้อมูล
            login(request, user) # ทำการ Login ให้ User อัตโนมัติ
            messages.success(request, f"สมัครสมาชิกสำเร็จ! ยินดีต้อนรับ, {user.username}")
            return redirect(settings.LOGIN_REDIRECT_URL) # Redirect ไปหน้า Home หรือหน้าที่ตั้งค่าไว้
        else:
            messages.error(request, "เกิดข้อผิดพลาดในการสมัครสมาชิก กรุณาตรวจสอบข้อมูล")
    else: # GET request
        form = UserCreationForm()

    context = {'form': form}
    # ต้องสร้าง template 'registration/register.html'
    return render(request, 'registration/register.html', context)


# --- Cart Views (Session-based) ---

@require_POST # บังคับให้เป็น POST request
def add_to_cart(request, outfit_id):
    outfit = get_object_or_404(Outfit, id=outfit_id, is_active=True)
    cart = request.session.get('cart', {})
    form = CartAddItemForm(request.POST)

    if form.is_valid():
        quantity = form.cleaned_data['quantity']
        outfit_key = str(outfit_id)

        cart_item = cart.get(outfit_key)
        if cart_item:
            # ถ้ามีอยู่แล้ว ให้บวกเพิ่ม
            cart[outfit_key]['quantity'] += quantity
            messages.success(request, f"เพิ่ม '{outfit.name}' อีก {quantity} ชิ้นลงในตะกร้า (รวมเป็น {cart[outfit_key]['quantity']} ชิ้น)")
        else:
            # ถ้ายังไม่มี ให้เพิ่มใหม่
            cart[outfit_key] = {'quantity': quantity, 'price': str(outfit.price)} # เก็บราคา ณ ตอนเพิ่ม
            messages.success(request, f"เพิ่ม '{outfit.name}' ({quantity} ชิ้น) ลงในตะกร้าแล้ว")

        request.session['cart'] = cart
        request.session.modified = True

        # ตอบกลับเป็น JSON ถ้าเป็น AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
             cart_item_count = sum(item['quantity'] for item in cart.values())
             return JsonResponse({'message': 'เพิ่มสินค้าสำเร็จ', 'cart_item_count': cart_item_count})
        else:
            # ถ้าเป็น request ปกติ redirect ไปหน้าตะกร้า
            return redirect('outfits:cart_detail')
    else:
         messages.error(request, "ข้อมูลที่ส่งมาไม่ถูกต้อง (จำนวนต้องเป็นตัวเลข)")
         return redirect('outfits:outfit-detail', pk=outfit_id)


def cart_detail(request):
    cart_session = request.session.get('cart', {})
    cart_items_context = []
    total_cart_price = 0.0
    outfit_ids = cart_session.keys()

    outfits_in_cart = {str(o.id): o for o in Outfit.objects.filter(id__in=outfit_ids, is_active=True)}

    items_to_remove = []
    for outfit_id, item_data in cart_session.items():
        outfit = outfits_in_cart.get(outfit_id)
        if outfit:
            quantity = item_data['quantity']
            price = outfit.price # ใช้ราคาปัจจุบันจาก DB
            item_total = float(price) * quantity
            cart_items_context.append({
                'outfit': outfit,
                'quantity': quantity,
                'update_form': CartUpdateItemForm(initial={'quantity': quantity}),
                'total_price': item_total,
                'price_per_item': price,
            })
            total_cart_price += item_total
        else:
            items_to_remove.append(outfit_id)

    if items_to_remove:
        cart_changed = False
        for key in items_to_remove:
            if key in cart_session:
                 del cart_session[key]
                 cart_changed = True
        if cart_changed:
             request.session['cart'] = cart_session
             request.session.modified = True
             messages.warning(request, "สินค้าบางรายการในตะกร้าไม่มีอยู่แล้วหรือถูกปิดใช้งาน และได้ถูกลบออกจากตะกร้า")

    context = {
        'cart_items': cart_items_context,
        'total_cart_price': total_cart_price,
    }
    # อย่าลืมสร้าง template 'outfits/cart_detail.html'
    return render(request, 'outfits/cart_detail.html', context)

@require_POST
def update_cart_item(request, outfit_id):
    outfit = get_object_or_404(Outfit, id=outfit_id, is_active=True)
    cart = request.session.get('cart', {})
    outfit_key = str(outfit_id)
    form = CartUpdateItemForm(request.POST)

    if outfit_key not in cart:
         messages.error(request, "ไม่พบสินค้านี้ในตะกร้า")
         return redirect('outfits:cart_detail')

    if form.is_valid():
        quantity = form.cleaned_data['quantity']
        if quantity > 0:
            cart[outfit_key]['quantity'] = quantity
            request.session['cart'] = cart
            request.session.modified = True
            messages.success(request, f"อัปเดตจำนวน '{outfit.name}' เป็น {quantity} ชิ้น")
        else: # ถ้า quantity เป็น 0 ให้ลบออก
            del cart[outfit_key]
            request.session['cart'] = cart
            request.session.modified = True
            messages.success(request, f"ลบ '{outfit.name}' ออกจากตะกร้าแล้ว")
    else:
         messages.error(request, "จำนวนที่กรอกไม่ถูกต้อง")

    return redirect('outfits:cart_detail')

@require_POST
def remove_from_cart(request, outfit_id):
    cart = request.session.get('cart', {})
    outfit_key = str(outfit_id)

    if outfit_key in cart:
        del cart[outfit_key]
        request.session['cart'] = cart
        request.session.modified = True
        messages.success(request, "ลบสินค้าออกจากตะกร้าแล้ว")
    else:
        messages.warning(request, "ไม่พบสินค้านี้ในตะกร้า")

    return redirect('outfits:cart_detail')


# --- Checkout and Payment Views ---

@login_required
def checkout_view(request):
    cart_session = request.session.get('cart', {})
    if not cart_session:
        messages.warning(request, "ตะกร้าของคุณว่างเปล่า")
        return redirect('outfits:outfit-list')

    outfit_ids = cart_session.keys()
    outfits_in_cart = {str(o.id): o for o in Outfit.objects.filter(id__in=outfit_ids, is_active=True)}
    cart_items_for_form = []

    items_to_remove_before_checkout = []
    for outfit_id, item_data in cart_session.items():
        outfit = outfits_in_cart.get(outfit_id)
        if outfit:
            cart_items_for_form.append({'outfit': outfit, 'quantity': item_data['quantity']})
        else:
            items_to_remove_before_checkout.append(outfit_id)

    if items_to_remove_before_checkout:
        cart_changed = False
        for key in items_to_remove_before_checkout:
            if key in cart_session:
                del cart_session[key]
                cart_changed = True
        if cart_changed:
            request.session['cart'] = cart_session
            request.session.modified = True
            messages.error(request, "มีสินค้าบางรายการในตะกร้าไม่มีอยู่แล้ว โปรดตรวจสอบตะกร้าของคุณอีกครั้งก่อนดำเนินการต่อ")
            return redirect('outfits:cart_detail')
        if not cart_session:
             messages.warning(request, "ตะกร้าของคุณว่างเปล่า")
             return redirect('outfits:outfit-list')

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            cleaned_data = form.cleaned_data
            start_date = cleaned_data['rental_start_date']
            duration = cleaned_data['rental_duration_days']
            end_date = start_date + timedelta(days=duration - 1)

            # --- ตรวจสอบ Availability ---
            all_available = True
            unavailable_items = []
            for item_context in cart_items_for_form:
                 outfit_obj = item_context['outfit']
                 if not outfit_obj.is_available(start_date, end_date): # ต้องแน่ใจว่า is_available ทำงานถูกต้อง
                     all_available = False
                     unavailable_items.append(outfit_obj.name)

            if not all_available:
                 messages.error(request, f"ขออภัย ชุดต่อไปนี้ไม่ว่างในช่วงเวลาที่คุณเลือก: {', '.join(unavailable_items)}")
                 context = {'form': form, 'cart_items': cart_items_for_form}
                 # อย่าลืมสร้าง template 'outfits/checkout.html'
                 return render(request, 'outfits/checkout.html', context)
            # --- สิ้นสุดการตรวจสอบ ---

            try:
                with transaction.atomic():
                    order = Order.objects.create(
                        user=request.user,
                        first_name=cleaned_data['first_name'],
                        last_name=cleaned_data['last_name'],
                        email=cleaned_data['email'],
                        phone=cleaned_data['phone'],
                        address=cleaned_data['address'],
                        status='pending',
                    )

                    final_total_amount = 0
                    for item_context in cart_items_for_form:
                        outfit_obj = item_context['outfit']
                        qty = item_context['quantity']
                        item_price = outfit_obj.price # ราคาต่อวัน ณ ตอนสั่ง
                        # แปลงเป็น Decimal ก่อนคูณ ถ้า price เป็น DecimalField
                        item_total = item_price * duration * qty

                        OrderItem.objects.create(
                            order=order,
                            outfit=outfit_obj,
                            price=item_price,
                            quantity=qty,
                            rental_start_date=start_date,
                            rental_duration_days=duration,
                        )
                        final_total_amount += item_total

                    order.total_amount = final_total_amount
                    order.save()

                request.session['cart'] = {}
                request.session.modified = True
                request.session['order_id'] = order.id

                messages.success(request, "สร้างคำสั่งเช่าสำเร็จ กรุณาดำเนินการชำระเงิน")
                return redirect(reverse('outfits:payment_process'))

            except Exception as e:
                messages.error(request, f"เกิดข้อผิดพลาดในการสร้างคำสั่งเช่า: {e}")
                # ควร Log error
                context = {'form': form, 'cart_items': cart_items_for_form}
                return render(request, 'outfits/checkout.html', context)

    else: # GET request
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
        'cart_items': cart_items_for_form,
    }
    # อย่าลืมสร้าง template 'outfits/checkout.html'
    return render(request, 'outfits/checkout.html', context)


@login_required
def payment_process_view(request):
    order_id = request.session.get('order_id')
    if not order_id:
        messages.error(request, "ไม่พบข้อมูลคำสั่งเช่าสำหรับชำระเงิน")
        return redirect('outfits:home')

    try:
        order = Order.objects.get(id=order_id, user=request.user)
    except Order.DoesNotExist:
         messages.error(request, "ไม่พบคำสั่งเช่า หรือคุณไม่มีสิทธิ์เข้าถึง")
         if 'order_id' in request.session: del request.session['order_id']
         return redirect('outfits:home')

    if order.paid:
         messages.info(request, f"คำสั่งเช่า #{order.id} ชำระเงินเรียบร้อยแล้ว")
         return redirect('outfits:order_detail', order_id=order.id)

    if order.status not in ['pending', 'failed']:
         messages.warning(request, f"คำสั่งเช่า #{order.id} ไม่อยู่ในสถานะที่สามารถชำระเงินได้ (สถานะปัจจุบัน: {order.get_status_display()})")
         return redirect('outfits:order_detail', order_id=order.id)

    omise.api_key = settings.OMISE_SECRET_KEY
    omise.api_version = settings.OMISE_API_VERSION
    qr_code_image_url = None
    error_message = None

    try:
        if not order.payment_id or order.status == 'failed':
            charge = omise.Charge.create(
                amount=int(order.total_amount * 100), # ต้องเป็น Integer หน่วยสตางค์
                currency='THB',
                description=f'Order {order.id} - {order.email}',
                source={'type': 'promptpay'},
                return_uri=request.build_absolute_uri(reverse('outfits:payment_result')),
                metadata={'order_id': order.id}
            )

            if charge and charge.status == 'pending' and charge.source and charge.source.scannable_code:
                qr_code_image_url = charge.source.scannable_code.image.download_uri
                order.payment_id = charge.id
                order.status = 'pending'
                order.save()
            elif charge:
                 error_message = f"ไม่สามารถสร้าง QR Code ได้ สถานะ Charge: {charge.status}"
                 if charge.failure_message: error_message += f" ({charge.failure_message})"
            else:
                 error_message = "ไม่สามารถสร้าง QR Code ได้ ข้อมูลไม่ถูกต้อง"
        else:
             try:
                 charge = omise.Charge.retrieve(order.payment_id)
                 if charge and charge.status == 'pending' and charge.source and charge.source.scannable_code:
                      qr_code_image_url = charge.source.scannable_code.image.download_uri
                 elif charge and charge.status != 'pending':
                      error_message = f"สถานะการชำระเงินปัจจุบัน: {charge.status}. ไม่สามารถสร้าง QR Code ใหม่ได้"
                 else:
                      error_message = "ไม่พบข้อมูล QR Code สำหรับการชำระเงินนี้"
             except omise.errors.NotFoundError:
                  error_message = "ไม่พบข้อมูลการชำระเงินเดิม อาจถูกยกเลิกไปแล้ว"
                  order.payment_id = None
                  order.status = 'failed'
                  order.save()
             except omise.errors.OmiseError as e:
                  error_message = f"เกิดข้อผิดพลาดในการดึงข้อมูล Omise เดิม: {e}"

    except omise.errors.OmiseError as e:
        error_message = f"เกิดข้อผิดพลาดในการเชื่อมต่อ Omise: {e}"
        # ควร Log error เพิ่มเติม
    except Exception as e:
        error_message = f"เกิดข้อผิดพลาดไม่คาดคิด: {e}"
        # ควร Log error เพิ่มเติม

    if error_message:
         messages.error(request, error_message)

    context = {
        'order': order,
        'qr_code_image_url': qr_code_image_url,
        'error_message': error_message,
    }
    # อย่าลืมสร้าง template 'outfits/payment_process.html'
    return render(request, 'outfits/payment_process.html', context)


@login_required
def payment_result_view(request):
    order_id = request.session.get('order_id')
    # if 'order_id' in request.session: del request.session['order_id'] # อาจจะลบทีหลังเมื่อยืนยันว่าจ่ายแล้ว

    if not order_id:
         messages.warning(request, "ไม่พบข้อมูลติดตามผลการชำระเงิน")
         return redirect('outfits:home')

    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
         messages.error(request, "ไม่พบคำสั่งเช่าที่เกี่ยวข้อง")
         return redirect('outfits:home')

    # แสดงผลตามสถานะล่าสุดใน DB (ที่ควรถูกอัปเดตโดย webhook)
    if order.paid and order.status == 'processing':
        if 'order_id' in request.session: del request.session['order_id'] # ลบเมื่อยืนยันว่าจ่ายแล้ว
        messages.success(request, f"การชำระเงินสำหรับคำสั่งเช่า #{order.id} สำเร็จเรียบร้อย!")
        return redirect('outfits:order_confirmation', order_id=order.id)
    elif order.status == 'pending':
         messages.info(request, f"ระบบกำลังรอการยืนยันการชำระเงินสำหรับคำสั่งเช่า #{order.id}. กรุณาสแกน QR Code และชำระเงิน หรือตรวจสอบสถานะอีกครั้ง")
         return redirect('outfits:payment_process') # กลับไปหน้าจ่ายเงิน/แสดง QR
    elif order.status == 'failed':
         messages.error(request, f"การชำระเงินสำหรับคำสั่งเช่า #{order.id} ล้มเหลว กรุณาลองใหม่อีกครั้ง")
         # ไม่ต้องลบ order_id ออกจาก session เพื่อให้ลองใหม่ได้
         return redirect('outfits:payment_process')
    else:
         messages.info(request, f"สถานะคำสั่งเช่า #{order.id}: {order.get_status_display()}")
         if 'order_id' in request.session: del request.session['order_id'] # ลบถ้าสถานะไม่ใช่ pending/failed
         return redirect('outfits:order_detail', order_id=order.id)


@csrf_exempt
def omise_webhook_view(request):
    if request.method == 'POST':
        try:
            webhook_data = json.loads(request.body)

            if webhook_data.get('object') == 'event' and webhook_data.get('key') == 'charge.complete':
                charge_data = webhook_data.get('data')
                if not charge_data or charge_data.get('object') != 'charge':
                    return HttpResponseBadRequest("Invalid charge data")

                charge_id = charge_data.get('id')
                if not charge_id:
                    return HttpResponseBadRequest("Missing charge ID")

                try:
                    omise.api_key = settings.OMISE_SECRET_KEY
                    charge = omise.Charge.retrieve(charge_id)

                    try:
                        # ใช้ payment_id ที่เก็บไว้ตอนสร้าง charge ใน payment_process_view
                        order = Order.objects.get(payment_id=charge.id)

                        with transaction.atomic():
                            order = Order.objects.select_for_update().get(pk=order.pk)

                            if charge.paid and charge.status == 'successful':
                                if not order.paid: # ทำเฉพาะเมื่อยังไม่ได้ mark ว่าจ่ายแล้ว
                                    order.paid = True
                                    order.status = 'processing'
                                    order.payment_method = f"{charge.source.type.replace('_',' ').title()} (Omise)" # เก็บวิธีจ่ายเงิน
                                    order.save()
                                    # --- ส่ง Email ยืนยัน ---
                                    # send_order_confirmation_email(order)
                            elif not order.paid: # ถ้ายังไม่จ่าย และ charge ไม่สำเร็จ
                                order.status = 'failed'
                                order.save()

                    except Order.DoesNotExist:
                        # ไม่เจอ Order ที่ตรงกับ Payment ID นี้ -> Log ไว้ แต่ตอบ 200 OK
                        print(f"Error: Order not found for completed charge ID {charge.id}")
                        pass # Return 200 OK below

                except omise.errors.OmiseError as e:
                    print(f"Error retrieving Omise charge {charge_id} in webhook: {e}")
                    return HttpResponseServerError("Omise API Error")
                except Exception as e:
                    print(f"Error processing webhook for charge {charge_id}: {e}")
                    return HttpResponseServerError("Webhook Processing Error")

            # ตอบ 200 OK ให้ Omise เสมอถ้าได้รับ Event ที่รู้จัก (charge.complete)
            return HttpResponse(status=200)

        except json.JSONDecodeError:
            return HttpResponseBadRequest("Invalid JSON")
        except Exception as e:
            print(f"Unexpected error in webhook view: {e}")
            return HttpResponseServerError("Webhook Processing Error")
    else:
        return HttpResponseBadRequest("Method Not Allowed")


# --- Order Status/History Views ---

@login_required
def order_confirmation_view(request, order_id):
     try:
         order = Order.objects.prefetch_related('items', 'items__outfit').get(id=order_id, user=request.user)
     except Order.DoesNotExist:
          messages.error(request, "ไม่พบคำสั่งเช่าที่คุณต้องการ")
          return redirect('outfits:order_history')

     # ควรเช็คว่าจ่ายเงินแล้วจริงๆ หรืออย่างน้อยสถานะเป็น processing
     if not order.paid or order.status not in ['processing', 'rented', 'completed']:
         messages.warning(request, "คำสั่งเช่ายังไม่ได้ยืนยันการชำระเงิน")
         return redirect('outfits:order_detail', order_id=order.id)

     context = {'order': order}
     # อย่าลืมสร้าง template 'outfits/order_confirmation.html'
     return render(request, 'outfits/order_confirmation.html', context)

@login_required
def order_history_view(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    context = {'orders': orders}
    # อย่าลืมสร้าง template 'outfits/order_history.html'
    return render(request, 'outfits/order_history.html', context)

@login_required
def order_detail_view(request, order_id):
    try:
        order = Order.objects.prefetch_related('items', 'items__outfit', 'items__outfit__category').get(id=order_id, user=request.user)
    except Order.DoesNotExist:
         messages.error(request, "ไม่พบคำสั่งเช่าที่คุณต้องการ")
         return redirect('outfits:order_history')

    context = {'order': order}
    # อย่าลืมสร้าง template 'outfits/order_detail_customer.html'
    return render(request, 'outfits/order_detail_customer.html', context)