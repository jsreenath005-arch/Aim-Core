from django.conf import settings
from django.db import models
from products.models import Product


class Cart(models.Model):
    cart_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='carts', db_column='user_id')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'CART'

    def __str__(self):
        return f"{self.user.email}'s Cart"


class CartItem(models.Model):
    cart_item_id = models.AutoField(primary_key=True)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items', db_column='cart_id')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='cart_items', db_column='product_id')
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = 'CART_ITEM'

    def __str__(self):
        return f"{self.product.product_name} - {self.quantity}"