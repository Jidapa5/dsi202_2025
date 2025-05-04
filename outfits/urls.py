from django.urls import path
from . import views

# กำหนด app_name ช่วยให้เรียก URL ง่ายขึ้นใน Template
app_name = 'outfits'

urlpatterns = [
    path('', views.home, name='home'),

    # Outfit URLs
    path('outfits/', views.OutfitListView.as_view(), name='outfit-list'),
    path('search/', views.OutfitSearchView.as_view(), name='outfit-search'),
    path('outfits/<int:pk>/', views.OutfitDetailView.as_view(), name='outfit-detail'),

    # Cart URLs
    path('cart/', views.cart_detail, name='cart_detail'),
    path('cart/add/<int:outfit_id>/', views.add_to_cart, name='cart_add'),
    path('cart/remove/<int:outfit_id>/', views.remove_from_cart, name='cart_remove'),
    path('cart/update/<int:outfit_id>/', views.cart_update, name='cart_update'),
    path('cart/clear/', views.clear_cart, name='cart_clear'),

    # Checkout URLs
    path('checkout/', views.checkout, name='checkout'),
    path('checkout/success/', views.checkout_success, name='checkout_success'),

    # User Profile URL
    path('profile/', views.user_profile, name='user_profile'),

    # Admin URLs (ตัวอย่าง)
    path('admin/outfits/create/', views.create_outfit, name='create_outfit'),
    # เพิ่ม URL สำหรับ Admin views อื่นๆ ที่นี่
    # path('admin/rentals/', views.admin_rental_list, name='admin_rental_list'),
    # path('admin/rentals/confirm/<int:rental_id>/', views.admin_confirm_payment, name='admin_confirm_payment'),
    # path('admin/rentals/return/<int:rental_id>/', views.admin_mark_returned, name='admin_mark_returned'),

    # URL เก่าที่ไม่ใช้แล้ว (ถ้ามี)
    # path('rent/<int:pk>/', views.rent_outfit, name='rent-outfit'), # เอาออกถ้าไม่ได้ใช้ rent_outfit view
]