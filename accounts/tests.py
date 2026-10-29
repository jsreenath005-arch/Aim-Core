from unittest.mock import patch

from django.conf import settings
from django.core import mail
from django.test import TestCase
from django.urls import reverse

from .models import User


class AuthenticationTests(TestCase):
	def setUp(self):
		self.customer = User.objects.create_user(
			username='customer@example.com',
			email='customer@example.com',
			name='Customer',
			password='customer-password',
		)
		self.admin = User.objects.create_user(
			username='admin@example.com',
			email='admin@example.com',
			name='Admin',
			password='admin-password',
			is_staff=True,
		)

	def test_customer_login_redirects_home(self):
		response = self.client.post(reverse('login'), {
			'email': 'customer@example.com',
			'password': 'customer-password',
		})

		self.assertRedirects(response, reverse('home'))

	def test_customer_login_returns_to_safe_next_page(self):
		next_url = reverse('product_list')

		response = self.client.post(reverse('login') + f'?next={next_url}', {
			'email': 'customer@example.com',
			'password': 'customer-password',
			'next': next_url,
		})

		self.assertRedirects(response, next_url)

	def test_customer_login_ignores_external_next_page(self):
		response = self.client.post(reverse('login'), {
			'email': 'customer@example.com',
			'password': 'customer-password',
			'next': 'https://example.com/',
		})

		self.assertRedirects(response, reverse('home'))

	def test_admin_user_login_redirects_dashboard(self):
		response = self.client.post(reverse('login'), {
			'email': 'admin@example.com',
			'password': 'admin-password',
		})

		self.assertRedirects(response, reverse('dashboard:home'))

	def test_required_markers_are_shown_on_authentication_forms(self):
		pages_and_required_counts = (
			('login', 2),
			('register', 4),
			('admin_login', 2),
			('admin_register', 5),
		)
		for page_name, required_count in pages_and_required_counts:
			with self.subTest(page=page_name):
				response = self.client.get(reverse(page_name))
				self.assertEqual(response.content.decode().count('class="required-mark"'), required_count)
				if page_name in ('register', 'admin_register'):
					self.assertContains(response, 'data-password-strength')
					self.assertContains(response, 'At least one special character')

	def test_registration_rejects_password_missing_required_characters(self):
		response = self.client.post(reverse('register'), {
			'name': 'New Customer',
			'email': 'new-customer@example.com',
			'password': 'password',
			'confirmation': 'password',
		})

		self.assertContains(response, 'at least one uppercase letter')
		self.assertContains(response, 'at least one number')
		self.assertContains(response, 'at least one special character')
		self.assertFalse(User.objects.filter(email='new-customer@example.com').exists())

	def test_login_validates_missing_identifier(self):
		missing_response = self.client.post(reverse('login'), {'email': '', 'password': ''})
		self.assertContains(missing_response, 'Username/email and password are required.')
		self.assertContains(missing_response, 'id="login-identifier-error"')
		self.assertContains(missing_response, 'id="login-password-error"')

		identifier_response = self.client.post(reverse('login'), {'email': '   ', 'password': 'password'})
		self.assertContains(identifier_response, 'Username or email is required.')
		self.assertContains(identifier_response, 'id="login-identifier-error"')

		password_response = self.client.post(reverse('login'), {'email': 'customer@example.com', 'password': ''})
		self.assertContains(password_response, 'Password is required.')
		self.assertContains(password_response, 'id="login-password-error"')

		invalid_response = self.client.post(reverse('login'), {
			'email': 'unknown-user',
			'password': 'password',
		})
		self.assertContains(invalid_response, 'The username/email or password is incorrect.')

	def test_registration_validates_email_password_and_confirmation(self):
		invalid_email_response = self.client.post(reverse('register'), {
			'name': 'New Customer',
			'email': 'not-an-email',
			'password': 'N0tCommon!BlueMouse',
			'confirmation': 'N0tCommon!BlueMouse',
		})
		self.assertContains(invalid_email_response, 'Enter a valid email address.')

		weak_password_response = self.client.post(reverse('register'), {
			'name': 'New Customer',
			'email': 'new-customer@example.com',
			'password': '12345678',
			'confirmation': '12345678',
		})
		self.assertContains(weak_password_response, 'password')

		mismatch_response = self.client.post(reverse('register'), {
			'name': 'New Customer',
			'email': 'new-customer@example.com',
			'password': 'N0tCommon!BlueMouse',
			'confirmation': 'N0tCommon!GreenMouse',
		})
		self.assertContains(mismatch_response, 'The passwords do not match.')
		self.assertFalse(User.objects.filter(email='new-customer@example.com').exists())

	def test_registration_does_not_collect_phone_number(self):
		response = self.client.post(reverse('register'), {
			'name': 'New Customer',
			'email': 'new-customer@example.com',
			'phone': '+14155552671',
			'password': 'N0tCommon!BlueMouse',
			'confirmation': 'N0tCommon!BlueMouse',
		})

		self.assertRedirects(response, reverse('home'))
		self.client.logout()
		self.assertNotContains(self.client.get(reverse('register')), 'name="phone"')
		self.assertFalse(User.objects.get(email='new-customer@example.com').phone)

	@patch('accounts.views.send_phone_verification_code')
	def test_profile_sends_code_without_saving_unverified_phone(self, send_code):
		self.client.force_login(self.customer)

		response = self.client.post(reverse('profile'), {
			'action': 'send_phone_code',
			'phone': '+14155552671',
		})

		self.assertRedirects(response, reverse('profile'))
		send_code.assert_called_once_with('+14155552671')
		self.customer.refresh_from_db()
		self.assertFalse(self.customer.phone)
		self.assertFalse(self.customer.phone_verified)
		self.assertContains(self.client.get(reverse('profile')), '+14155552671')

	@patch('accounts.views.send_phone_verification_code')
	@patch('accounts.views.verify_phone_verification_code', return_value=False)
	def test_profile_does_not_save_phone_when_code_is_invalid(self, verify_code, send_code):
		self.client.force_login(self.customer)
		self.client.post(reverse('profile'), {
			'action': 'send_phone_code',
			'phone': '+14155552671',
		})

		response = self.client.post(reverse('profile'), {
			'action': 'verify_phone_code',
			'verification_code': '123456',
		}, follow=True)

		self.assertRedirects(response, reverse('profile'))
		self.assertContains(response, 'That verification code is not valid.')
		verify_code.assert_called_once_with('+14155552671', '123456')
		self.customer.refresh_from_db()
		self.assertFalse(self.customer.phone)
		self.assertFalse(self.customer.phone_verified)

	@patch('accounts.views.send_phone_verification_code')
	@patch('accounts.views.verify_phone_verification_code', return_value=True)
	def test_profile_saves_phone_only_after_successful_verification(self, verify_code, send_code):
		self.client.force_login(self.customer)
		self.client.post(reverse('profile'), {
			'action': 'send_phone_code',
			'phone': '+14155552671',
		})

		response = self.client.post(reverse('profile'), {
			'action': 'verify_phone_code',
			'verification_code': '123456',
		})

		self.assertRedirects(response, reverse('profile'))
		verify_code.assert_called_once_with('+14155552671', '123456')
		self.customer.refresh_from_db()
		self.assertEqual(self.customer.phone, '+14155552671')
		self.assertTrue(self.customer.phone_verified)

	def test_customer_session_persists_after_browser_close(self):
		self.client.post(reverse('login'), {
			'email': 'customer@example.com',
			'password': 'customer-password',
		})

		self.assertFalse(self.client.session.get_expire_at_browser_close())

	def test_admin_session_expires_when_browser_closes(self):
		self.client.post(reverse('login'), {
			'email': 'admin@example.com',
			'password': 'admin-password',
		})

		self.assertTrue(self.client.session.get_expire_at_browser_close())

	def test_admin_registration_creates_staff_account(self):
		response = self.client.post(reverse('admin_register'), {
			'username': 'new-admin',
			'name': 'New Admin',
			'email': 'new-admin@example.com',
			'password': 'AdminPass1!',
			'confirmation': 'AdminPass1!',
		})

		self.assertRedirects(response, reverse('dashboard:home'))
		new_admin = User.objects.get(username='new-admin')
		self.assertTrue(new_admin.is_staff)
		self.assertTrue(new_admin.is_superuser)

	def test_forgot_password_sends_reset_email(self):
		response = self.client.post(reverse('password_reset'), {
			'email': self.customer.email,
		})

		self.assertRedirects(response, reverse('password_reset_done'))
		self.assertEqual(len(mail.outbox), 1)
		self.assertIn('reset', mail.outbox[0].subject.lower())

	def test_browser_close_session_setting_is_enabled(self):
		self.assertTrue(settings.SESSION_EXPIRE_AT_BROWSER_CLOSE)
