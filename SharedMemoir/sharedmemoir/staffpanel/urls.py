from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="staff_dashboard"),
    path("orders/", views.order_list, name="staff_orders"),
    path("orders/<int:pk>/", views.order_detail, name="staff_order_detail"),
    path("orders/<int:pk>/start/", views.order_start, name="staff_order_start"),
    path("orders/<int:pk>/deliver/", views.order_deliver, name="staff_order_deliver"),
    path("orders/<int:pk>/ship/", views.order_ship, name="staff_order_ship"),
    path("catalogue/", views.catalogue, name="staff_catalogue"),
    path("catalogue/covers/new/", views.cover_form, name="staff_cover_create"),
    path("catalogue/covers/<int:pk>/edit/", views.cover_form, name="staff_cover_edit"),
    path("catalogue/covers/<int:pk>/toggle/", views.cover_toggle, name="staff_cover_toggle"),
    path("catalogue/packages/<int:pk>/edit/", views.tier_form, name="staff_tier_edit"),
    path("catalogue/gift-boxes/<int:pk>/stock/", views.giftbox_stock, name="staff_giftbox_stock"),
    path("customers/", views.customer_list, name="staff_customers"),
    path("customers/<int:pk>/", views.customer_detail, name="staff_customer_detail"),
    path("customers/<int:pk>/toggle-active/", views.customer_toggle_active, name="staff_customer_toggle"),
    path("reviews/", views.review_list, name="staff_reviews"),
    path("reviews/<int:pk>/toggle/", views.review_toggle, name="staff_review_toggle"),
]