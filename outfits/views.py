from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView
from django.urls import reverse
from django.contrib import messages
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.db import transaction
from django.contrib.auth import login
from datetime import timedelta
import omise
import json

from .models import Outfit, Category, Order, OrderItem
from .forms import OutfitForm, CheckoutForm, CartAddItemForm, CartUpdateItemForm, CustomUserCreationForm
from .utils import calculate_cart_total


# ---------- หน้าหลัก / สมัครสมาชิก ----------

def home(request):
    featured_outfits = Outfit.objects.filter(is_active=True).order_by('?')[:6]
    return render(request, 'outfits/home.html', {'featured_outfits': featured_outfits})


def register_view(request):
    if request.user.is_authenticated:
        return redirect(settings.LOGIN_REDIRECT_URL)
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"สมัครสมาชิกสำเร็จ! ยินดีต้อนรับ, {user.username}")
            return redirect(settings.LOGIN_REDIRECT_URL)
        else:
            messages.error(request, "เกิดข้อผิดพลาดในการสมัครสมาชิก กรุณาตรวจสอบข้อมูล")
    else:
        form = CustomUserCreationForm()
    return render(request, 'registration/register.html', {'form': form})


# ---------- ชุดทั้งหมด / รายละเอียด ----------

class OutfitListView(ListView):
    model = Outfit
    template_name = 'outfits/list.html'
    context_object_name = 'outfits'
    paginate_by = 12

    def get_queryset(self):
        return Outfit.objects.filter(is_active=True).select_related('category')


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
        query = self.request.GET.get('q', '')
        self.query = query
        if query:
            return Outfit.objects.filter(
                Q(name__icontains=query) | Q(description__icontains=query), is_active=True
            ).select_related('category')
        return Outfit.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.query
        return context


# ---------- ตะกร้า ----------

@login_required
def cart_detail(request):
    cart = request.session.get('cart', {})
    cart_items = []
    total_price = 0.0

    outfit_ids = cart.keys()
    outfits = {str(o.id): o for o in Outfit.objects.filter(id__in=outfit_ids, is_active=True)}

    for outfit_id, item_data in cart.items():
        outfit = outfits.get(outfit_id)
        if outfit:
            quantity = item_data['quantity']
            price = float(outfit.price)
            total = price * quantity
            total_price += total
            cart_items.append({
                'outfit': outfit,
                'quantity': quantity,
                'price': price,
                'total': total
            })

    return render(request, 'outfits/cart_detail.html', {
        'cart_items': cart_items,
        'total_price': total_price
    })


@require_POST
def add_to_cart(request, outfit_id):
    outfit = get_object_or_404(Outfit, id=outfit_id, is_active=True)
    cart = request.session.get('cart', {})
    form = CartAddItemForm(request.POST)

    if form.is_valid():
        quantity = form.cleaned_data['quantity']
        outfit_key = str(outfit_id)

        if outfit_key in cart:
            cart[outfit_key]['quantity'] += quantity
        else:
            cart[outfit_key] = {'quantity': quantity, 'price': str(outfit.price)}

        request.session['cart'] = cart
        request.session.modified = True
        messages.success(request, f"เพิ่ม {outfit.name} ลงในตะกร้าแล้ว")
    else:
        messages.error(request, "จำนวนไม่ถูกต้อง")

    return redirect('outfits:cart_detail')


@require_POST
def update_cart_item(request, outfit_id):
    cart = request.session.get('cart', {})
    outfit_key = str(outfit_id)
    form = CartUpdateItemForm(request.POST)

    if form.is_valid() and outfit_key in cart:
        quantity = form.cleaned_data['quantity']
        if quantity > 0:
            cart[outfit_key]['quantity'] = quantity
        else:
            del cart[outfit_key]

        request.session['cart'] = cart
        request.session.modified = True
        messages.success(request, "อัปเดตจำนวนสินค้าแล้ว")
    else:
        messages.error(request, "ข้อมูลไม่ถูกต้อง")

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


# ---------- ชำระเงิน / สรุปคำสั่งซื้อ ----------

@login_required
def checkout_view(request):
    cart = request.session.get('cart', {})
    if not cart:
        messages.warning(request, "ตะกร้าของคุณว่างเปล่า")
        return redirect('outfits:cart_detail')

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            request.session['checkout_data'] = form.cleaned_data
            return redirect('outfits:payment_process')
    else:
        form = CheckoutForm()

    return render(request, 'outfits/checkout.html', {'form': form})


@login_required
def payment_process_view(request):
    cart = request.session.get('cart', {})
    checkout_data = request.session.get('checkout_data')

    if not cart or not checkout_data:
        messages.error(request, "ไม่พบข้อมูลการสั่งซื้อ")
        return redirect('outfits:cart_detail')

    amount = int(calculate_cart_total(cart) * 100)
    omise.api_secret = settings.OMISE_SECRET_KEY

    try:
        charge = omise.Charge.create(
            amount=amount,
            currency='thb',
            description='เช่าชุดกับ MindVibe',
            capture=True,
            card=request.POST.get('omiseToken')
        )
    except omise.errors.BaseError as e:
        messages.error(request, f"เกิดข้อผิดพลาด: {str(e)}")
        return redirect('outfits:checkout')

    if charge.paid:
        with transaction.atomic():
            order = Order.objects.create(
                user=request.user,
                total_price=amount / 100,
                **checkout_data
            )
            for outfit_id, item in cart.items():
                outfit = get_object_or_404(Outfit, id=outfit_id)
                OrderItem.objects.create(
                    order=order,
                    outfit=outfit,
                    quantity=item['quantity'],
                    price=outfit.price
                )
        del request.session['cart']
        del request.session['checkout_data']
        return redirect('outfits:order_confirmation', order_id=order.id)
    else:
        messages.error(request, "ไม่สามารถชำระเงินได้")
        return redirect('outfits:checkout')


@login_required
def order_confirmation_view(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'outfits/order_confirmation.html', {'order': order})


@login_required
def payment_result_view(request):
    return render(request, 'outfits/payment_result.html')


@csrf_exempt
def omise_webhook_view(request):
    payload = json.loads(request.body)
    event = payload.get("object")

    if event == "charge.complete":
        return JsonResponse({"received": True})
    return HttpResponseBadRequest("Invalid webhook")

@login_required
def order_history_view(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'outfits/order_history.html', {'orders': orders})

@login_required
def order_detail_view(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'outfits/order_detail.html', {'order': order})

from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
def create_outfit(request):
    if request.method == 'POST':
        form = OutfitForm(request.POST, request.FILES)
        if form.is_valid():
            outfit = form.save()
            messages.success(request, f"เพิ่มชุดใหม่สำเร็จ: {outfit.name}")
            return redirect('outfits:outfit-detail', pk=outfit.pk)
    else:
        form = OutfitForm()
    return render(request, 'outfits/create_outfit.html', {'form': form})
