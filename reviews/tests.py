from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from products.models import Category, Product

from .models import Review


class ProductReviewTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(
			username='reviewer@example.com',
			email='reviewer@example.com',
			name='Product Reviewer',
			password='password123',
		)
		category = Category.objects.create(category_name='FPS')
		self.product = Product.objects.create(
			category=category,
			product_name='AIM One',
			brand='AIM CORE',
			price=Decimal('2499.00'),
		)

	def test_product_detail_renders_star_rating_form(self):
		self.client.force_login(self.user)

		response = self.client.get(reverse('product_detail', args=[self.product.product_id]))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Add a review')
		self.assertContains(response, 'role="radiogroup"')
		self.assertContains(response, 'aria-label="5 stars"')
		self.assertContains(response, 'class="star-rating-value" aria-live="polite">0 / 5')
		self.assertContains(response, 'Be the first to share your experience')

	def test_customer_can_submit_and_update_review(self):
		self.client.force_login(self.user)
		review_url = reverse('add_review', args=[self.product.product_id])

		response = self.client.post(review_url, {'rating': '5', 'comment': 'Excellent tracking.'})

		self.assertRedirects(
			response,
			f"{reverse('product_detail', args=[self.product.product_id])}#reviews",
		)
		self.assertEqual(Review.objects.count(), 1)
		review = Review.objects.get()
		self.assertEqual(review.rating, 5)

		self.client.post(review_url, {'rating': '4', 'comment': 'Still excellent.'})
		review.refresh_from_db()
		self.assertEqual(Review.objects.count(), 1)
		self.assertEqual(review.rating, 4)

		detail_response = self.client.get(reverse('product_detail', args=[self.product.product_id]))
		self.assertContains(detail_response, '4.0 / 5')
		self.assertContains(detail_response, '4 out of 5 stars')
		self.assertContains(detail_response, 'class="review-rating-number">4 / 5')
		self.assertContains(detail_response, 'Still excellent.')

	def test_review_submission_requires_sign_in(self):
		response = self.client.post(
			reverse('add_review', args=[self.product.product_id]),
			{'rating': '5', 'comment': 'Great mouse.'},
		)

		self.assertRedirects(
			response,
			f"{reverse('login')}?next={reverse('add_review', args=[self.product.product_id])}",
		)
		self.assertEqual(Review.objects.count(), 0)
