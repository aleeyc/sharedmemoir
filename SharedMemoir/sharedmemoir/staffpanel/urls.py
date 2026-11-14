from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="staff_dashboard"),
    path("orders/", views.order_list, name="staff_orders"),
    path("orders/<int:pk>/", views.order_detail, name="staff_order_detail"),
    path("orders/<int:pk>/start/", views.order_start, name="staff_order_start"),
    path("orders/<int:pk>/deliver/", views.order_deliver, name="staff_order_deliver"),
    path("orders/<int:pk>/ship/", views.order_ship, name="staff_order_ship"),    
]