# outfits/urls.py (เพิ่ม return URL)
from django.urls import path
from . import views

app_name = 'outfits'

urlpatterns = [
    # หน้า Home และรายการชุด
    path('', views.home, name='home'),
    path('list/', views.OutfitListView.as_view(), name='outfit-list'),
    path('search/', views.OutfitSearchView.as_view(), name='outfit-search'),
    path('category/<slug:category_slug>/', views.OutfitByCategoryListView.as_view(), name='outfits-by-category'),
    path('outfit/<int:pk>/', views.OutfitDetailView.as_view(), name='outfit-detail'),

    # สมัครสมาชิก / โปรไฟล์
    path('register/', views.register_view, name='register'),
    path('profile/', views.user_profile_view, name='user_profile'),

    # ตะกร้าสินค้า
    path('cart/', views.cart_detail, name='cart_detail'),
    path('cart/add/<int:outfit_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:outfit_id>/', views.remove_from_cart, name='remove_from_cart'),
    # --- ไม่มี update_cart_item ---

    # เช่าและชำระเงิน (แจ้งโอน)
    path('checkout/', views.checkout_view, name='checkout'),
    path('payment/<int:order_id>/', views.payment_process_view, name='payment_process'),
    path('payment/result/', views.payment_result_view, name='payment_result'),
    # --- ไม่มี payment_webhook ---

    # คำสั่งเช่า และ การส่งคืน
    path('orders/', views.order_history_view, name='order_history'),
    path('orders/<int:order_id>/', views.order_detail_view, name='order_detail'),
    # --- *** เพิ่ม URL สำหรับหน้าแจ้งส่งคืน *** ---
    path('orders/<int:order_id>/return/', views.initiate_return_view, name='initiate_return'),

]