from .models import Category


def navigation_categories(request):
    return {
        'navigation_categories': Category.objects.filter(
            products__isnull=False,
        ).distinct().order_by('category_name'),
    }
