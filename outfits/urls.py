from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('outfits/', views.OutfitListView.as_view(), name='outfit-list'),
    path('search/', views.OutfitSearchView.as_view(), name='outfit-search'),
    path('outfits/<int:pk>/', views.OutfitDetailView.as_view(), name='outfit-detail'),
    path('create/', views.create_outfit, name='create-outfit'),
    path('rent/<int:pk>/', views.rent_outfit, name='rent-outfit'),
     path('cart/', views.cart_view, name='cart'),
path('cart/add/<int:pk>/', views.add_to_cart, name='add_to_cart'),
path('cart/update/<int:pk>/', views.update_cart, name='update_cart'),
path('cart/clear/', views.clear_cart, name='clear_cart'), 
]