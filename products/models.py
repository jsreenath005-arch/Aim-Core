from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator


class Category(models.Model):
    category_id = models.AutoField(primary_key=True)
    category_name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'CATEGORY'

    def __str__(self):
        return self.category_name


class Product(models.Model):
    product_id = models.AutoField(primary_key=True)
    category = models.ForeignKey('Category', on_delete=models.CASCADE, related_name='products', db_column='category_id')
    product_name = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=255, blank=True, null=True)
    brand = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    special_feature = models.CharField(max_length=255, blank=True, null=True)
    dpi = models.CharField(max_length=50, blank=True, null=True)
    connectivity = models.CharField(max_length=100, blank=True, null=True)
    battery_life = models.CharField(max_length=100, blank=True, null=True)
    weight = models.CharField(max_length=50, blank=True, null=True)
    buttons = models.CharField(max_length=50, blank=True, null=True)
    rgb = models.CharField(max_length=50, blank=True, null=True)
    stock = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    image_url = models.CharField(max_length=500, blank=True, null=True)

    class Meta:
        db_table = 'PRODUCT'

    @property
    def discounted_price(self):
        return self.price * (1 - self.discount_percentage / 100)

    def __str__(self):
        return self.product_name


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='additional_images')
    image = models.ImageField(upload_to='products/gallery/')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('id',)

    def __str__(self):
        return f'{self.product.product_name} image'