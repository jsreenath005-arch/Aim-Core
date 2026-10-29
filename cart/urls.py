from django.urls import path

from . import views

urlpatterns = [
    path('', views.cart_view, name='cart'),
    path('add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('update/<int:cart_item_id>/', views.update_cart_item, name='update_cart_item'),
    path('remove/<int:cart_item_id>/', views.remove_from_cart, name='remove_from_cart'),
]
