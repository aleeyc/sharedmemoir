from django.urls import path

from . import views

urlpatterns = [
    path("checkout/", views.checkout, name="checkout"),
    path("orders/<int:pk>/success/", views.order_success, name="order_success"),
]