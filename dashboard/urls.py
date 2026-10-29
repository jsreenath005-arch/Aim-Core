from django.urls import path

from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_home, name='home'),
    path('orders/<int:order_id>/status/', views.order_status_update, name='order_status_update'),
    path('payments/<int:payment_id>/confirm/', views.payment_confirm, name='payment_confirm'),
    path('orders/report.csv', views.order_report, name='order_report'),
    path('products/new/', views.product_create, name='product_create'),
    path('products/<int:product_id>/edit/', views.product_edit, name='product_edit'),
    path('products/<int:product_id>/delete/', views.product_delete, name='product_delete'),
    path('users/new/', views.user_create, name='user_create'),
    path('users/<int:user_id>/edit/', views.user_edit, name='user_edit'),
    path('users/<int:user_id>/delete/', views.user_delete, name='user_delete'),
    path('payments/qr-upload/', views.payment_qr_upload, name='payment_qr_upload'),
    path('payments/upi-settings/', views.upi_settings_update, name='upi_settings_update'),
]
