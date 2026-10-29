from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from products.models import Category, Product

from .models import Cart, CartItem


class AddToCartTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='buyer@example.com',
            email='buyer@example.com',
            name='Buyer',
            password='password123',
        )
        self.category = Category.objects.create(category_name='FPS')
        self.product = Product.objects.create(
            category=self.category,
            product_name='AIM One',
            brand='AIM CORE',
            price='2499.00',
            stock=5,
        )
        self.detail_url = reverse('product_detail', args=[self.product.product_id])
        self.add_url = reverse('add_to_cart', args=[self.product.product_id])
        self.client.force_login(self.user)

    def test_in_stock_product_can_be_added_to_cart(self):
        response = self.client.post(self.add_url, {'next': self.detail_url})

        self.assertRedirects(response, self.detail_url)
        self.assertEqual(CartItem.objects.get(product=self.product).quantity, 1)
        self.assertContains(self.client.get(reverse('cart')), 'AIM One')

    def test_out_of_stock_product_reports_error_instead_of_silent_failure(self):
        self.product.stock = 0
        self.product.save(update_fields=['stock'])

        response = self.client.post(self.add_url, {'next': self.detail_url}, follow=True)

        self.assertRedirects(response, self.detail_url)
        self.assertContains(response, 'This product is currently out of stock.')
        self.assertFalse(CartItem.objects.filter(product=self.product).exists())

    def test_cart_limit_reports_error_instead_of_success(self):
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=self.product.stock)

        response = self.client.post(self.add_url, {'next': self.detail_url}, follow=True)

        self.assertRedirects(response, self.detail_url)
        self.assertContains(response, 'You already have the maximum available quantity in your cart.')
        self.assertEqual(CartItem.objects.get(cart=cart, product=self.product).quantity, self.product.stock)
