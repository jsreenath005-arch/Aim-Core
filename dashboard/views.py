import csv

from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.models import User
from orders.models import Order, Payment, PaymentQR, UPISettings
from products.models import Product

from .forms import PaymentQRForm, ProductForm, UPISettingsForm, UserForm


staff_required = user_passes_test(
	lambda user: user.is_authenticated and user.is_staff,
	login_url='login',
)
ORDER_STATUSES = ('pending', 'processing', 'shipped', 'delivered', 'cancelled')


@staff_required
def dashboard_home(request):
	return render(request, 'dashboard/home.html', {
		'products': Product.objects.select_related('category').order_by('-product_id'),
		'users': User.objects.order_by('-user_id'),
		'orders': Order.objects.select_related('user').prefetch_related('items__product', 'payments').order_by('-order_date'),
		'product_count': Product.objects.count(),
		'user_count': User.objects.count(),
		'order_count': Order.objects.count(),
		'order_statuses': ORDER_STATUSES,
		'payment_qrs': PaymentQR.objects.filter(is_active=True).order_by('-created_at'),
		'upi_settings': UPISettings.objects.filter(is_active=True).order_by('-updated_at').first(),
		'qr_form': PaymentQRForm(),
		'upi_form': UPISettingsForm(),
	})


@staff_required
@require_POST
def order_status_update(request, order_id):
	order = get_object_or_404(Order, order_id=order_id)
	status = request.POST.get('status', '').strip().lower()
	if status not in ORDER_STATUSES:
		messages.error(request, 'Choose a valid order status.', extra_tags='dashboard')
	else:
		order.status = status
		order.save(update_fields=['status'])
		messages.success(request, f'Order #{order.order_id} status updated.', extra_tags='dashboard')
	return redirect('dashboard:home')


@staff_required
@require_POST
def payment_confirm(request, payment_id):
	with transaction.atomic():
		payment = get_object_or_404(
			Payment.objects.select_for_update().select_related('order'),
			payment_id=payment_id,
		)
		if payment.payment_status != 'pending':
			messages.error(request, f'Payment #{payment.payment_id} is not pending.', extra_tags='dashboard')
		else:
			reference = request.POST.get('reference', '').strip()
			payment.payment_status = 'paid'
			if reference:
				payment.reference = reference
				payment.save(update_fields=['payment_status', 'reference'])
			else:
				payment.save(update_fields=['payment_status'])
			if payment.order.status == 'pending':
				payment.order.status = 'processing'
				payment.order.save(update_fields=['status'])
			messages.success(request, f'Payment for order #{payment.order_id} confirmed.', extra_tags='dashboard')
	return redirect('dashboard:home')


@staff_required
def order_report(request):
	response = HttpResponse(content_type='text/csv; charset=utf-8')
	response['Content-Disposition'] = 'attachment; filename="orders-report.csv"'
	writer = csv.writer(response)
	writer.writerow(['Order ID', 'Order date', 'Customer name', 'Customer email', 'Customer phone', 'Shipping address', 'Items', 'Total amount', 'Order status', 'Payment method', 'Payment status'])
	orders = Order.objects.select_related('user').prefetch_related('items__product', 'payments').order_by('-order_date')
	for order in orders:
		items = ', '.join(
			f'{item.product.product_name} x {item.quantity}'
			for item in order.items.all()
		)
		payment = order.payments.first()
		writer.writerow([
			order.order_id,
			order.order_date.isoformat(),
			order.user.name,
			order.user.email,
			order.user.phone or '',
			order.shipping_address,
			items,
			order.total_amount,
			order.status,
			payment.payment_method if payment else '',
			payment.payment_status if payment else '',
		])
	return response


@staff_required
def product_create(request):
	form = ProductForm(request.POST or None, request.FILES or None)
	if request.method == 'POST' and form.is_valid():
		form.save()
		messages.success(request, 'Product added successfully.', extra_tags='dashboard')
		return redirect('dashboard:home')
	return render(request, 'dashboard/product_form.html', {
		'form': form,
		'title': 'Add product',
	})


@staff_required
def product_edit(request, product_id):
	product = get_object_or_404(Product, product_id=product_id)
	form = ProductForm(request.POST or None, request.FILES or None, instance=product)
	if request.method == 'POST' and form.is_valid():
		form.save()
		messages.success(request, 'Product updated successfully.', extra_tags='dashboard')
		return redirect('dashboard:home')
	return render(request, 'dashboard/product_form.html', {
		'form': form,
		'title': 'Edit product',
		'product': product,
	})


@staff_required
def product_delete(request, product_id):
	product = get_object_or_404(Product, product_id=product_id)
	if request.method == 'POST':
		product.delete()
		messages.success(request, 'Product deleted successfully.', extra_tags='dashboard')
	return redirect('dashboard:home')


@staff_required
def user_create(request):
	form = UserForm(request.POST or None)
	if request.method == 'POST' and form.is_valid():
		form.save()
		messages.success(request, 'User added successfully.', extra_tags='dashboard')
		return redirect('dashboard:home')
	return render(request, 'dashboard/user_form.html', {'form': form, 'title': 'Add user'})


@staff_required
def user_edit(request, user_id):
	user = get_object_or_404(User, user_id=user_id)
	form = UserForm(request.POST or None, instance=user)
	if request.method == 'POST' and form.is_valid():
		form.save()
		messages.success(request, 'User updated successfully.', extra_tags='dashboard')
		return redirect('dashboard:home')
	return render(request, 'dashboard/user_form.html', {'form': form, 'title': 'Edit user', 'managed_user': user})


@staff_required
def user_delete(request, user_id):
	user = get_object_or_404(User, user_id=user_id)
	if request.method == 'POST' and user != request.user:
		user.delete()
		messages.success(request, 'User deleted successfully.', extra_tags='dashboard')
	return redirect('dashboard:home')


@staff_required
def payment_qr_upload(request):
	form = PaymentQRForm(request.POST or None, request.FILES or None)
	if request.method == 'POST':
		if form.is_valid():
			form.save()
			messages.success(request, 'QR payment code uploaded successfully.', extra_tags='dashboard')
			return redirect('dashboard:home')
		messages.error(request, 'Please provide a valid QR code upload.', extra_tags='dashboard')
	return redirect('dashboard:home')


@staff_required
def upi_settings_update(request):
	upi_settings = UPISettings.objects.filter(is_active=True).order_by('-updated_at').first()
	form = UPISettingsForm(request.POST or None, request.FILES or None, instance=upi_settings)
	if request.method == 'POST':
		if form.is_valid():
			form.save()
			messages.success(request, 'UPI payment settings updated successfully.', extra_tags='dashboard')
			return redirect('dashboard:home')
		messages.error(request, 'Please enter a valid UPI configuration.', extra_tags='dashboard')
	return redirect('dashboard:home')

# Create your views here.
