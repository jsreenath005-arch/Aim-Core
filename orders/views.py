from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect, render

from cart.models import Cart

from .models import Order, OrderItem, Payment


@login_required(login_url='login')
def order_list(request):
    if request.user.is_staff:
        return redirect('dashboard:home')
    orders = request.user.orders.prefetch_related('items__product', 'payments').all()
    return render(request, 'orders.html', {'orders': orders})


@login_required(login_url='login')
def payment_history(request):
    if request.user.is_staff:
        return redirect('dashboard:home')
    payments = Payment.objects.filter(order__user=request.user).select_related('order').order_by('-payment_date')
    return render(request, 'payment_history.html', {'payments': payments})


@login_required(login_url='login')
def checkout(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('dashboard:home')

    if request.method != 'POST':
        return redirect('cart')

    cart = Cart.objects.filter(user=request.user).first()
    items = list(cart.items.select_related('product') if cart else [])

    shipping_address = request.POST.get('shipping_address', '').strip()
    payment_method = request.POST.get('payment_method', '').strip().lower()
    payment_gateway = request.POST.get('payment_gateway', '').strip()

    if not items:
        messages.error(request, 'Your cart is empty.')
        return redirect('cart')
    if not shipping_address:
        messages.error(request, 'Enter a shipping address to continue.')
    elif payment_method not in {'upi', 'cod'}:
        messages.error(request, 'Choose a valid payment method.')
    elif payment_method == 'upi' and not payment_gateway:
        messages.error(request, 'Choose a UPI app or gateway before placing the order.')
    else:
        try:
            with transaction.atomic():
                locked_cart = Cart.objects.select_for_update().get(pk=cart.pk)
                locked_items = list(locked_cart.items.select_related('product'))
                if not locked_items:
                    messages.error(request, 'Your cart is empty.')
                    return redirect('cart')

                total = Decimal('0.00')
                for item in locked_items:
                    if item.quantity > item.product.stock:
                        raise ValueError(f'{item.product.product_name} does not have enough stock.')
                    total += item.product.price * item.quantity

                order = Order.objects.create(
                    user=request.user,
                    total_amount=total,
                    shipping_address=shipping_address,
                    status='pending',
                )
                for item in locked_items:
                    OrderItem.objects.create(
                        order=order,
                        product=item.product,
                        quantity=item.quantity,
                        price=item.product.price,
                    )
                    item.product.stock -= item.quantity
                    item.product.save(update_fields=['stock'])
                Payment.objects.create(
                    order=order,
                    payment_method=payment_method,
                    payment_status='pending',
                    gateway=payment_gateway or payment_method,
                )
                locked_cart.items.all().delete()
        except ValueError as error:
            messages.error(request, str(error))
        else:
            messages.success(request, f'Order #{order.order_id} placed successfully.')
            return redirect('order_list')

    return redirect('cart')
