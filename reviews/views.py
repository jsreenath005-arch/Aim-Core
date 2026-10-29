from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse

from products.models import Product

from .forms import ReviewForm
from .models import Review


@login_required(login_url='login')
def add_review(request, product_id):
	product = get_object_or_404(Product, product_id=product_id)
	if request.method != 'POST':
		return redirect('product_detail', product_id=product_id)

	review = Review.objects.filter(product=product, user=request.user).first()
	form = ReviewForm(request.POST, instance=review)
	if form.is_valid():
		review = form.save(commit=False)
		review.product = product
		review.user = request.user
		review.save()
		messages.success(request, 'Your review has been saved.')
	else:
		messages.error(request, 'Choose a star rating and enter a review of 2,000 characters or fewer.')
	return redirect(f"{reverse('product_detail', args=[product.product_id])}#reviews")
