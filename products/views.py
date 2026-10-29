from django.db.models import Avg, Count, Q
from django.shortcuts import render

from reviews.forms import ReviewForm
from reviews.models import Review

from .models import Category, Product


def home_page(request):
    categories = Category.objects.all()[:5]
    featured_products = Product.objects.all()[:4]
    return render(request, 'index.html', {
        'categories': categories,
        'featured_products': featured_products,
        'product_count': Product.objects.count(),
    })


def product_list(request):
    selected_category = None
    category_id = request.GET.get('category')
    search_query = request.GET.get('q', '').strip()
    products = Product.objects.select_related('category').all()

    if category_id:
        selected_category = Category.objects.filter(category_id=category_id).first()
        if selected_category:
            products = products.filter(category=selected_category)

    if search_query:
        products = products.filter(
            Q(product_name__icontains=search_query)
            | Q(brand__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(special_feature__icontains=search_query)
            | Q(category__category_name__icontains=search_query)
        )

    return render(request, 'products.html', {
        'products': products,
        'selected_category': selected_category,
        'search_query': search_query,
    })


def product_detail(request, product_id):
    product = Product.objects.select_related('category').prefetch_related('additional_images').get(product_id=product_id)
    related_products = Product.objects.filter(category=product.category).exclude(product_id=product.product_id)[:4]
    reviews = Review.objects.filter(product=product).select_related('user')
    summary = reviews.aggregate(average=Avg('rating'), count=Count('id'))
    review_form = ReviewForm(instance=reviews.filter(user=request.user).first()) if request.user.is_authenticated else None
    current_rating = review_form['rating'].value() if review_form else None
    return render(request, 'product_detail.html', {
        'product': product,
        'related_products': related_products,
        'reviews': reviews,
        'review_average': summary['average'],
        'review_count': summary['count'],
        'review_form': review_form,
        'rating_options': [
            {'value': value, 'checked': str(current_rating or '') == str(value)}
            for value in range(1, 6)
        ],
    })
