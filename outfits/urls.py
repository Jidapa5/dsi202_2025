from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('outfits/', views.OutfitListView.as_view(), name='outfit-list'),
    path('search/', views.OutfitSearchView.as_view(), name='outfit-search'),
    path('outfits/<int:pk>/', views.OutfitDetailView.as_view(), name='outfit-detail'),
    path('create/', views.create_outfit, name='create-outfit'),
]
