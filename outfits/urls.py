# outfits/urls.py
from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from . import views

app_name = 'outfits'

urlpatterns = [
    # หน้า Home และรายการชุด
    path('', views.home, name='home'),
    path('list/', views.OutfitListView.as_view(), name='outfit-list'),
    path('search/', views.OutfitSearchView.as_view(), name='outfit-search'),
    path('category/<slug:category_slug>/', views.OutfitByCategoryListView.as_view(), name='outfits-by-category'),
    path('outfit/<int:pk>/', views.OutfitDetailView.as_view(), name='outfit-detail'),

    # สมัครสมาชิก
    path('register/', views.register_view, name='register'),

    # ตะกร้าสินค้า
    path('cart/', views.cart_detail, name='cart_detail'),
    path('cart/add/<int:outfit_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:outfit_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/update/<int:outfit_id>/', views.update_cart_item, name='update_cart_item'),

    # เช่าและชำระเงิน
    path('checkout/', views.checkout_view, name='checkout'),
    path('payment/', views.payment_process_view, name='payment_process'),
    path('payment/result/', views.payment_result_view, name='payment_result'),
    path('payment/webhook/', csrf_exempt(views.omise_webhook_view), name='payment_webhook'),

    # คำสั่งเช่า
    path('order/confirmation/<int:order_id>/', views.order_confirmation_view, name='order_confirmation'),
    path('orders/', views.order_history_view, name='order_history'),
    path('orders/<int:order_id>/', views.order_detail_view, name='order_detail'),

    # จัดการสินค้า (เฉพาะแอดมิน)
    path('manage/create/', views.create_outfit, name='create-outfit'),
]
