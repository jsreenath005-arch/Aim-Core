from django.test import TestCase
from django.urls import reverse

from accounts.models import User

from .models import Category, Product


class ProductSearchTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(
            category_name='Wireless',
            description='Wireless gaming mice',
        )
        self.product = Product.objects.create(
            category=self.category,
            product_name='Falcon Pro',
            brand='AIM CORE',
            price='79.99',
            description='Lightweight wireless mouse',
            stock=5,
        )
        Product.objects.create(
            category=self.category,
            product_name='Glide',
            brand='Other Brand',
            price='49.99',
            description='Wired mouse',
            stock=3,
        )

    def test_product_search_filters_case_insensitively_and_shows_query(self):
        response = self.client.get(reverse('product_list'), {'q': 'aim core'})

        self.assertEqual(list(response.context['products']), [self.product])
        self.assertEqual(response.context['search_query'], 'aim core')
        self.assertContains(response, 'Results for “aim core”')

    def test_blank_product_search_shows_all_products(self):
        response = self.client.get(reverse('product_list'), {'q': '   '})

        self.assertEqual(response.context['products'].count(), 2)

    def test_search_form_requires_a_non_blank_query(self):
        response = self.client.get(reverse('product_list'))

        self.assertContains(response, 'data-search-form')
        self.assertContains(response, 'name="q"', html=False)
        self.assertContains(response, 'required')
        self.assertContains(response, 'Enter a search term.')

    def test_navigation_includes_all_categories_added_to_catalog(self):
        added_category = Category.objects.create(
            category_name='Ergonomic',
            description='Ergonomic gaming mice',
        )
        Product.objects.create(
            category=added_category,
            product_name='Ergo One',
            brand='AIM CORE',
            price='59.99',
        )

        response = self.client.get(reverse('home'))

        self.assertContains(
            response,
            f'href="{reverse("product_list")}?category={added_category.category_id}"',
            html=False,
        )
        self.assertContains(response, 'Ergonomic')

    def test_product_detail_shows_stock_and_a_sign_in_purchase_link(self):
        response = self.client.get(reverse('product_detail', args=[self.product.product_id]))

        self.assertContains(response, 'IN STOCK')
        self.assertContains(response, '5 AVAILABLE')
        self.assertContains(response, 'Sign in to add to cart')
        self.assertNotContains(response, 'Out of Stock')

    def test_product_detail_does_not_label_staff_view_as_out_of_stock(self):
        staff_user = User.objects.create_user(
            username='staff@example.com',
            email='staff@example.com',
            name='Staff',
            password='password123',
            is_staff=True,
        )
        self.client.force_login(staff_user)

        response = self.client.get(reverse('product_detail', args=[self.product.product_id]))

        self.assertContains(response, 'Purchases are unavailable for staff accounts')
        self.assertContains(response, 'IN STOCK · 5 AVAILABLE')
        self.assertNotContains(response, 'Out of Stock')

    def test_product_detail_shows_out_of_stock_only_when_stock_is_zero(self):
        self.product.stock = 0
        self.product.save(update_fields=['stock'])

        response = self.client.get(reverse('product_detail', args=[self.product.product_id]))

        self.assertContains(response, 'OUT OF STOCK')
        self.assertContains(response, 'Out of Stock')
        self.assertNotContains(response, 'IN STOCK')
