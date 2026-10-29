from decimal import Decimal
import io

from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from cart.models import Cart, CartItem
from orders.models import Order, OrderItem, Payment, PaymentQR
from products.models import Category, Product


class CheckoutAndPaymentFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='customer@example.com',
            email='customer@example.com',
            name='Test Customer',
            password='password123',
            phone='9876543210',
            address='12 Market Street, Bengaluru',
        )
        self.category = Category.objects.create(category_name='FPS')
        self.product = Product.objects.create(
            category=self.category,
            product_name='AIM One',
            brand='AIM CORE',
            price=Decimal('2499.00'),
            discount_percentage=Decimal('10.00'),
            special_feature='Silent optical switches',
            dpi='26000',
            connectivity='Wireless',
            weight='60g',
            buttons='6',
            rgb='Yes',
            stock=5,
            description='Precision gaming mouse.',
            image_url='https://example.com/mouse.jpg',
        )
        self.cart = Cart.objects.create(user=self.user)
        self.cart_item = CartItem.objects.create(cart=self.cart, product=self.product, quantity=2)
        self.client.force_login(self.user)

    def test_checkout_creates_order_and_payment_record(self):
        response = self.client.post(
            reverse('checkout'),
            {
                'shipping_address': '12 Market Street, Bengaluru',
                'payment_method': 'upi',
                'payment_gateway': 'GPay',
            },
        )

        self.assertRedirects(response, reverse('order_list'))
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(OrderItem.objects.count(), 1)
        self.assertEqual(Payment.objects.count(), 1)

        order = Order.objects.get(user=self.user)
        self.assertEqual(order.status, 'pending')
        self.assertEqual(order.total_amount, Decimal('4998.00'))

        payment = Payment.objects.get(order=order)
        self.assertEqual(payment.payment_method, 'upi')
        self.assertEqual(payment.payment_status, 'pending')
        self.assertFalse(CartItem.objects.filter(cart=self.cart).exists())
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)

    def test_add_to_cart_and_checkout_do_not_require_or_store_color_options(self):
        self.cart_item.delete()
        first_add_response = self.client.post(
            reverse('add_to_cart', args=[self.product.product_id]),
            {'color_option': 'ignored-legacy-value'},
        )
        second_add_response = self.client.post(
            reverse('add_to_cart', args=[self.product.product_id]),
            {},
        )

        self.assertRedirects(first_add_response, reverse('cart'))
        self.assertRedirects(second_add_response, reverse('cart'))
        detail_response = self.client.get(reverse('product_detail', args=[self.product.product_id]))
        self.assertContains(detail_response, 'Add to cart')
        self.assertNotContains(detail_response, 'Choose a color')
        self.assertNotContains(detail_response, 'name="color_option"', html=False)

        cart_response = self.client.get(reverse('cart'))
        self.assertNotContains(cart_response, 'Choose a color')
        self.assertNotContains(cart_response, 'Color:')
        self.assertEqual(CartItem.objects.filter(cart=self.cart).count(), 1)
        self.assertEqual(CartItem.objects.get(cart=self.cart).quantity, 2)

        response = self.client.post(
            reverse('checkout'),
            {
                'shipping_address': '12 Market Street, Bengaluru',
                'payment_method': 'cod',
            },
        )

        self.assertRedirects(response, reverse('order_list'))
        self.assertEqual(OrderItem.objects.filter(order__user=self.user).count(), 1)
        self.assertContains(self.client.get(reverse('order_list')), 'AIM One × 2')
        self.assertNotContains(self.client.get(reverse('order_list')), 'Color:')

    def test_order_history_shows_payment_and_shipping_details(self):
        self.client.post(
            reverse('checkout'),
            {
                'shipping_address': '12 Market Street, Bengaluru',
                'payment_method': 'cod',
            },
        )

        response = self.client.get(reverse('order_list'))
        self.assertContains(response, 'Cash on Delivery')
        self.assertContains(response, 'Pending')
        self.assertContains(response, '12 Market Street, Bengaluru')
        self.assertContains(response, 'My Orders &amp; Status')
        self.assertContains(response, reverse('payment_history'))

    def test_payment_history_lists_payment_details(self):
        response = self.client.post(
            reverse('checkout'),
            {
                'shipping_address': '12 Market Street, Bengaluru',
                'payment_method': 'upi',
                'payment_gateway': 'GPay',
            },
        )

        payment_history_response = self.client.get(reverse('payment_history'))
        self.assertEqual(payment_history_response.status_code, 200)
        self.assertContains(payment_history_response, 'Payment History')
        self.assertContains(payment_history_response, 'Order #')
        self.assertContains(payment_history_response, 'UPI')
        self.assertContains(payment_history_response, 'GPay')
        self.assertContains(payment_history_response, 'Pending')
        self.assertRedirects(response, reverse('order_list'))
        self.assertContains(self.client.get(reverse('order_list')), 'Your order will be processed after an admin verifies your payment.')

    def test_checkout_does_not_accept_unavailable_card_payments(self):
        response = self.client.post(
            reverse('checkout'),
            {
                'shipping_address': '12 Market Street, Bengaluru',
                'payment_method': 'card',
            },
        )

        self.assertRedirects(response, reverse('cart'))
        self.assertFalse(Order.objects.exists())
        self.assertTrue(CartItem.objects.filter(cart=self.cart).exists())

    def test_admin_can_upload_qr_code_for_payments(self):
        admin = User.objects.create_user(
            username='admin@example.com',
            email='admin@example.com',
            name='Admin User',
            password='password123',
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_login(admin)

        qr_buffer = io.BytesIO()
        Image.new('RGB', (40, 40), color='white').save(qr_buffer, format='PNG')
        qr_data = qr_buffer.getvalue()
        response = self.client.post(
            reverse('dashboard:payment_qr_upload'),
            {
                'title': 'UPI QR Code',
                'notes': 'Scan to pay using any UPI app.',
                'qr_code': SimpleUploadedFile('qr.png', qr_data, content_type='image/png'),
            },
        )

        self.assertRedirects(response, reverse('dashboard:home'))
        self.assertTrue(PaymentQR.objects.filter(title='UPI QR Code').exists())

        self.client.force_login(self.user)
        checkout_response = self.client.get(reverse('cart'))
        self.assertContains(checkout_response, 'Pay by UPI')
        self.assertContains(checkout_response, 'gamingmouse@upi')
        self.assertContains(checkout_response, 'GPay')
        self.assertContains(checkout_response, 'Navi')
        self.assertNotContains(checkout_response, 'QR Payment')

    def test_checkout_page_redirects_to_cart(self):
        response = self.client.get(reverse('checkout'))

        self.assertRedirects(response, reverse('cart'))
        cart_response = self.client.get(response.url)
        self.assertContains(cart_response, 'Place Order')
        self.assertContains(cart_response, 'Shipping Details')
