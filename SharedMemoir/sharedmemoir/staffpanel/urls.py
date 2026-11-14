from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="staff_dashboard"),
    path("orders/", views.order_list, name="staff_orders"),
    path("orders/<int:pk>/", views.order_detail, name="staff_order_detail"),
]