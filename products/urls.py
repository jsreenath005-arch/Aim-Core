from django.urls import path

from . import views
from reviews.views import add_review

urlpatterns = [
    path('', views.product_list, name='product_list'),
    path('<int:product_id>/', views.product_detail, name='product_detail'),
    path('<int:product_id>/reviews/add/', add_review, name='add_review'),
]
