from django.urls import path

from . import views

urlpatterns = [
    path('', views.order_list, name='order_list'),
    path('payments/', views.payment_history, name='payment_history'),
    path('checkout/', views.checkout, name='checkout'),
]
