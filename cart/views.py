from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from orders.models import PaymentQR, UPISettings
from products.models import Product

from .models import Cart, CartItem


def cart_view(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('dashboard:home')

    items = []
    total = 0
    total_quantity = 0
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
        items = list(cart.items.select_related('product') if cart else [])
        for item in items:
            item.subtotal = item.product.price * item.quantity
            total += item.subtotal
            total_quantity += item.quantity

    return render(request, 'cart.html', {
        'items': items,
        'total': total,
        'total_quantity': total_quantity,
        'qr_codes': PaymentQR.objects.filter(is_active=True).order_by('-created_at'),
        'upi_settings': UPISettings.objects.filter(is_active=True).order_by('-updated_at').first(),
    })


@login_required(login_url='login')
def add_to_cart(request, product_id):
    if request.user.is_staff:
        return redirect('dashboard:home')

    product = get_object_or_404(Product, product_id=product_id)
    next_url = request.POST.get('next') or 'cart'
    if request.method == 'POST' and product.stock <= 0:
        messages.error(request, 'This product is currently out of stock.')
        return redirect(next_url)

    if request.method == 'POST' and product.stock > 0:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        item, created = CartItem.objects.get_or_create(cart=cart, product=product)
        if not created and item.quantity >= product.stock:
            messages.error(request, 'You already have the maximum available quantity in your cart.')
            return redirect(next_url)
        if not created:
            item.quantity += 1
            item.save(update_fields=['quantity'])
        messages.success(request, f'{product.product_name} was added to your cart.')
    return redirect(next_url)


@login_required(login_url='login')
def update_cart_item(request, cart_item_id):
    item = get_object_or_404(CartItem, cart_item_id=cart_item_id, cart__user=request.user)
    if request.method == 'POST':
        try:
            quantity = int(request.POST.get('quantity', 1))
        except (TypeError, ValueError):
            quantity = 1
        item.quantity = max(1, min(quantity, item.product.stock))
        item.save(update_fields=['quantity'])
    return redirect('cart')


@login_required(login_url='login')
def remove_from_cart(request, cart_item_id):
    item = get_object_or_404(CartItem, cart_item_id=cart_item_id, cart__user=request.user)
    if request.method == 'POST':
        item.delete()
    return redirect('cart')
