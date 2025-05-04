from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.views.decorators.http import require_POST
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.conf import settings
from .models import Outfit, Rental
from .forms import OutfitForm, RentForm, UserRegistrationForm, PaymentForm  # แก้ไข Import

def add_to_cart(request, pk):
    outfit = get_object_or_404(Outfit, pk=pk)
    cart = request.session.get('cart', {})
    if pk not in cart:
        cart[pk] = {'name': outfit.name, 'price': outfit.price, 'quantity': 1}
    else:
        cart[pk]['quantity'] += 1
    request.session['cart'] = cart
    return redirect('cart')

def cart_view(request):
    cart = request.session.get('cart', {})
    outfits = []
    total_price = 0
    for pk, item in cart.items():
        outfit = Outfit.objects.get(pk=pk) # Ensure outfit exists
        outfits.append({
            'outfit': outfit,
            'quantity': item['quantity'],
            'total': item['quantity'] * item['price']
        })
        total_price += item['quantity'] * item['price']
    return render(request, 'outfits/cart.html', {'outfits': outfits, 'total_price': total_price})

@require_POST
def update_cart(request, pk):
    cart = request.session.get('cart', {})
    quantity = int(request.POST.get('quantity', 1))
    if pk in cart:
        cart[pk]['quantity'] = quantity
        if quantity < 1:
            del cart[pk]
    request.session['cart'] = cart
    return redirect('cart')

def clear_cart(request):
    request.session['cart'] = {}
    return redirect('cart')

# หน้าจ่ายเงิน
def checkout(request):
    cart = request.session.get('cart', {})
    # คำนวณราคารวม, รายละเอียดคำสั่งซื้อ ฯลฯ
    total_price = 0
    for item in cart.values():
        total_price += item['price'] * item['quantity']

    if request.method == 'POST':
        payment_form = PaymentForm(request.POST, request.FILES)
        if payment_form.is_valid():
            # สร้าง Rental object สำหรับแต่ละ item ในตะกร้า
            for item_id, item_data in cart.items():
                outfit = Outfit.objects.get(pk=item_id)
                Rental.objects.create(
                    user=request.user,
                    outfit=outfit,
                    duration=item_data['quantity'],  # Assuming quantity is duration
                    total_price=item_data['price'] * item_data['quantity'],
                    payment_slip=payment_form.cleaned_data['payment_slip'],
                    payment_date=payment_form.cleaned_data['payment_date']
                )
            request.session['cart'] = {}  # เคลียร์ตะกร้าหลังสั่งซื้อ
            return redirect('checkout_success')
        else:
            messages.error(request, 'Please correct the errors in the payment form.')
    else:
        payment_form = PaymentForm()

    return render(request, 'outfits/checkout.html', {
        'cart': cart,
        'total_price': total_price,
        'payment_form': payment_form,
        'bank_account_number': '1234567890',  # Replace with your actual bank account number
        'qr_code_image': '/static/path/to/your/qr_code.png'  # Replace with your actual QR code image path
    })

# หน้าจ่ายเงินสำเร็จ
def checkout_success(request):
    return render(request, 'outfits/checkout_success.html')