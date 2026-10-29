from django.conf import settings
from django.db import models
from products.models import Product


class Order(models.Model):
    order_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders', db_column='user_id')
    order_date = models.DateTimeField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    shipping_address = models.TextField()
    status = models.CharField(max_length=50, default='pending')

    class Meta:
        db_table = 'ORDER'

    def __str__(self):
        return f"Order #{self.order_id}"


class OrderItem(models.Model):
    order_item_id = models.AutoField(primary_key=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items', db_column='order_id')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='order_items', db_column='product_id')
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'ORDER_ITEM'

    def __str__(self):
        return f"{self.product.product_name} - {self.quantity}"


class Payment(models.Model):
    payment_id = models.AutoField(primary_key=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments', db_column='order_id')
    payment_method = models.CharField(max_length=50)
    payment_status = models.CharField(max_length=50, default='pending')
    payment_date = models.DateTimeField(auto_now_add=True)
    gateway = models.CharField(max_length=100, blank=True, null=True)
    reference = models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        db_table = 'PAYMENT'

    @property
    def payment_method_label(self):
        labels = {
            'card': 'Card',
            'upi': 'UPI',
            'cod': 'Cash on Delivery',
        }
        return labels.get(self.payment_method.lower(), self.payment_method.replace('_', ' ').title())

    @property
    def payment_status_label(self):
        labels = {
            'pending': 'Pending',
            'paid': 'Paid',
        }
        return labels.get(self.payment_status.lower(), self.payment_status.title())

    def __str__(self):
        return f"Payment {self.payment_id}"


class PaymentQR(models.Model):
    qr_id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=200)
    notes = models.TextField(blank=True, null=True)
    qr_code = models.ImageField(upload_to='payment_qr/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'PAYMENT_QR'

    def __str__(self):
        return self.title


class UPISettings(models.Model):
    setting_id = models.AutoField(primary_key=True)
    upi_id = models.CharField(max_length=100, default='gamingmouse@upi')
    supported_apps = models.TextField(default='GPay, PhonePe, Paytm, Navi, BHIM, Other UPI')
    qr_code = models.ImageField(upload_to='payment_qr/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'UPI_SETTINGS'

    def __str__(self):
        return self.upi_id

    @property
    def apps(self):
        return [app.strip() for app in self.supported_apps.split(',') if app.strip()]