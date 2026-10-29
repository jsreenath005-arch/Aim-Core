from io import BytesIO
from decimal import Decimal
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.test import override_settings
from django.urls import reverse
from PIL import Image

from accounts.models import User
from cart.models import CartItem
from orders.models import Order, Payment, UPISettings
from products.models import Category, Product


class DashboardProductSyncTests(TestCase):
	def setUp(self):
		self.staff_user = User.objects.create_user(
			username='admin@example.com',
			email='admin@example.com',
		name='Admin',
		password='test-password',
		is_staff=True,
		is_superuser=True,
		)
		self.category = Category.objects.create(category_name='FPS')
		self.client.force_login(self.staff_user)

	def test_dashboard_has_direct_link_to_home_page(self):
		response = self.client.get(reverse('dashboard:home'))

		self.assertContains(
			response,
			f'href="{reverse("home")}" class="btn btn-outline-primary">View home page</a>',
		)

	def test_product_form_uses_multiline_special_feature_input_without_color_options(self):
		response = self.client.get(reverse('dashboard:product_create'))

		self.assertContains(response, '<textarea name="special_feature"', html=False)
		self.assertContains(response, 'Enter each special feature on a new line')
		self.assertNotContains(response, 'Color options')
		self.assertNotContains(response, 'name="color"', html=False)

	def test_product_form_includes_subtitle_and_detail_page_displays_it(self):
		response = self.client.get(reverse('dashboard:product_create'))
		self.assertContains(response, 'name="subtitle"')

		product = Product.objects.create(
			**self.product_data(
				category=self.category,
				subtitle='LIGHTSPEED Wireless Gaming Mouse',
			),
		)
		detail_response = self.client.get(reverse('product_detail', args=[product.product_id]))

		self.assertContains(detail_response, 'LIGHTSPEED Wireless Gaming Mouse')

	def test_product_detail_preserves_special_feature_line_breaks(self):
		product = Product.objects.create(
			**self.product_data(
				category=self.category,
				special_feature='Adjustable DPI\nOnboard memory',
			),
		)

		response = self.client.get(reverse('product_detail', args=[product.product_id]))

		self.assertContains(response, 'Adjustable DPI<br>Onboard memory', html=False)

	def product_data(self, product_name='AIM One', **overrides):
		data = {
			'category': self.category.category_id,
			'product_name': product_name,
			'brand': 'AIM CORE',
			'subtitle': '',
			'price': '4999.00',
			'discount_percentage': '10.00',
			'special_feature': 'Silent optical switches',
			'dpi': '26000',
			'connectivity': 'Wireless',
			'battery_life': 'Up to 70 hours',
			'weight': '60g',
			'buttons': '6',
			'rgb': 'Yes',
			'stock': '12',
			'description': 'Precision gaming mouse.',
			'image_url': 'https://example.com/mouse.jpg',
		}
		data.update(overrides)
		return data

	def test_create_product_is_visible_on_home_and_customer_catalog(self):
		response = self.client.post(
			reverse('dashboard:product_create'),
			{
				**self.product_data(subtitle='LIGHTSPEED Wireless Gaming Mouse'),
			},
		)

		self.assertEqual(response.status_code, 302)
		self.assertEqual(response.url, reverse('dashboard:home'))
		product = Product.objects.get(product_name='AIM One')
		dashboard_response = self.client.get(reverse('dashboard:home'))
		self.assertContains(dashboard_response, 'Product added successfully.')
		self.assertNotContains(dashboard_response, 'cart-toast-stack')
		self.assertNotContains(dashboard_response, 'href="/cart/"')
		self.assertNotContains(dashboard_response, 'href="/orders/checkout/"')
		home_response = self.client.get(reverse('home'))
		catalog_response = self.client.get(reverse('product_list'))
		self.assertContains(home_response, product.brand)
		self.assertContains(home_response, 'LIGHTSPEED Wireless Gaming Mouse')
		self.assertContains(home_response, '10% OFF')
		self.assertContains(home_response, 'class="product-card-view"')
		self.assertContains(home_response, f'href="{reverse("product_detail", args=[product.product_id])}">View →</a>')
		self.assertNotContains(home_response, 'Silent optical switches')
		self.assertContains(catalog_response, product.brand)
		self.assertContains(catalog_response, 'LIGHTSPEED Wireless Gaming Mouse')
		self.assertContains(catalog_response, '₹4499.10')
		detail_response = self.client.get(reverse('product_detail', args=[product.product_id]))
		self.assertNotContains(detail_response, 'Color:')
		self.assertContains(detail_response, 'Silent optical switches')
		self.assertContains(detail_response, 'Wireless')
		self.assertContains(detail_response, 'Up to 70 hours')
		self.assertContains(detail_response, '₹4499.10')
		self.assertNotContains(detail_response, 'Add to cart')

		cart_response = self.client.post(
			reverse('add_to_cart', args=[product.product_id]),
		)
		self.assertRedirects(cart_response, reverse('dashboard:home'))
		self.assertFalse(CartItem.objects.exists())
		self.assertRedirects(
			self.client.get(reverse('checkout')),
			reverse('dashboard:home'),
		)

	def test_admin_can_add_multiple_detail_only_product_images(self):
		def make_image(name, color):
			image_bytes = BytesIO()
			Image.new('RGB', (2, 2), color=color).save(image_bytes, format='PNG')
			return SimpleUploadedFile(name, image_bytes.getvalue(), content_type='image/png')

		with tempfile.TemporaryDirectory() as media_root:
			with override_settings(MEDIA_ROOT=media_root):
				response = self.client.post(
					reverse('dashboard:product_create'),
					{
						**self.product_data(),
						'additional_images': [
							make_image('side-view.png', 'red'),
							make_image('top-view.png', 'blue'),
						],
					},
				)

				self.assertRedirects(response, reverse('dashboard:home'))
				product = Product.objects.get(product_name='AIM One')
				self.assertEqual(product.additional_images.count(), 2)
				detail_response = self.client.get(reverse('product_detail', args=[product.product_id]))
				self.assertContains(detail_response, 'side-view.png')
				self.assertContains(detail_response, 'top-view.png')
				self.assertContains(detail_response, 'data-gallery-src')
				self.assertNotContains(self.client.get(reverse('home')), 'side-view.png')
				self.assertNotContains(self.client.get(reverse('product_list')), 'side-view.png')

	def test_admin_rejects_discount_outside_zero_to_hundred(self):
		response = self.client.post(
			reverse('dashboard:product_create'),
			{
				**self.product_data(discount_percentage='101.00'),
			},
		)

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Ensure this value is less than or equal to 100')
		self.assertFalse(Product.objects.exists())

	def test_get_upi_settings_endpoint_does_not_create_settings(self):
		response = self.client.get(reverse('dashboard:upi_settings_update'))

		self.assertRedirects(response, reverse('dashboard:home'))
		self.assertFalse(UPISettings.objects.exists())

	def test_product_name_is_read_only_after_product_creation(self):
		product = Product.objects.create(**self.product_data(category=self.category))
		edit_url = reverse('dashboard:product_edit', args=[product.product_id])
		response = self.client.get(edit_url)

		self.assertTrue(response.context['form'].fields['product_name'].disabled)
		self.assertContains(response, 'name="product_name"')
		self.assertContains(response, 'disabled')

		response = self.client.post(
			edit_url,
			{
				**self.product_data('Tampered name', price='5999.00'),
			},
		)

		self.assertRedirects(response, reverse('dashboard:home'))
		product.refresh_from_db()
		self.assertEqual(product.product_name, 'AIM One')
		self.assertEqual(product.price, Decimal('5999.00'))

		dashboard_response = self.client.get(reverse('dashboard:home'))
		self.assertContains(dashboard_response, 'AIM One')
		self.assertNotContains(dashboard_response, 'product-name-form')
		self.assertNotContains(dashboard_response, 'Save name')

	def test_delete_product_removes_it_from_customer_pages(self):
		product = Product.objects.create(**self.product_data(category=self.category))

		response = self.client.post(
			reverse('dashboard:product_delete', args=[product.product_id]),
		)

		self.assertRedirects(response, reverse('dashboard:home'))
		self.assertFalse(Product.objects.filter(pk=product.pk).exists())
		self.assertNotContains(self.client.get(reverse('home')), 'AIM One')
		self.assertNotContains(self.client.get(reverse('product_list')), 'AIM One')

	def test_admin_can_update_order_status_visible_to_customer_and_export_report(self):
		customer = User.objects.create_user(
			username='customer@example.com',
			email='customer@example.com',
			name='Customer One',
			password='test-password',
		)
		order = Order.objects.create(
			user=customer,
			total_amount='4999.00',
			shipping_address='1 Example Street',
		)

		response = self.client.post(
			reverse('dashboard:order_status_update', args=[order.order_id]),
			{'status': 'shipped'},
		)

		self.assertRedirects(response, reverse('dashboard:home'))
		order.refresh_from_db()
		self.assertEqual(order.status, 'shipped')
		self.assertContains(self.client.get(reverse('dashboard:home')), 'Customer One')
		self.client.force_login(customer)
		self.assertContains(self.client.get(reverse('order_list')), 'Shipped')

		self.client.force_login(self.staff_user)
		report = self.client.get(reverse('dashboard:order_report'))
		self.assertEqual(report['Content-Type'], 'text/csv; charset=utf-8')
		self.assertIn('attachment; filename="orders-report.csv"', report['Content-Disposition'])
		self.assertContains(report, 'customer@example.com')
		self.assertContains(report, 'shipped')

	def test_customer_cannot_update_order_status(self):
		customer = User.objects.create_user(
			username='customer@example.com',
			email='customer@example.com',
			name='Customer One',
			password='test-password',
		)
		order = Order.objects.create(
			user=customer,
			total_amount='4999.00',
			shipping_address='1 Example Street',
		)
		self.client.force_login(customer)

		response = self.client.post(
			reverse('dashboard:order_status_update', args=[order.order_id]),
			{'status': 'delivered'},
		)

		self.assertEqual(response.status_code, 302)
		order.refresh_from_db()
		self.assertEqual(order.status, 'pending')

	def test_admin_can_confirm_pending_payment_and_store_reference(self):
		customer = User.objects.create_user(
			username='customer@example.com',
			email='customer@example.com',
			name='Customer One',
			password='test-password',
		)
		order = Order.objects.create(
			user=customer,
			total_amount='4999.00',
			shipping_address='1 Example Street',
		)
		payment = Payment.objects.create(
			order=order,
			payment_method='upi',
			payment_status='pending',
			gateway='GPay',
		)

		response = self.client.post(
			reverse('dashboard:payment_confirm', args=[payment.payment_id]),
			{'reference': 'UPI-12345'},
		)

		self.assertRedirects(response, reverse('dashboard:home'))
		payment.refresh_from_db()
		order.refresh_from_db()
		self.assertEqual(payment.payment_status, 'paid')
		self.assertEqual(payment.reference, 'UPI-12345')
		self.assertEqual(order.status, 'processing')
		self.assertContains(self.client.get(reverse('dashboard:home')), 'UPI · Paid')

	def test_customer_cannot_confirm_payment(self):
		customer = User.objects.create_user(
			username='customer@example.com',
			email='customer@example.com',
			name='Customer One',
			password='test-password',
		)
		order = Order.objects.create(
			user=customer,
			total_amount='4999.00',
			shipping_address='1 Example Street',
		)
		payment = Payment.objects.create(
			order=order,
			payment_method='upi',
			payment_status='pending',
		)
		self.client.force_login(customer)

		response = self.client.post(
			reverse('dashboard:payment_confirm', args=[payment.payment_id]),
			{'reference': 'UPI-12345'},
		)

		self.assertEqual(response.status_code, 302)
		payment.refresh_from_db()
		order.refresh_from_db()
		self.assertEqual(payment.payment_status, 'pending')
		self.assertEqual(order.status, 'pending')
